"""The Fetcher: full-text PDFs for included Editions, each pinned to an exact Version or Edition.

An arXiv preprint gets its latest Version, plus v1 when it has several, always from a versioned
``export.arxiv.org`` URL. A venue Edition gets its ACL Anthology PDF, or else the first of its
OpenAlex open-access locations that serves a PDF. The sha256 of every file is kept in a committed
record in the Snapshot (``fulltext/pdfs.jsonl``), so `collect` rebuilds the manifest's file
columns and funnel status without the PDFs, and a re-download is checked against it. The PDFs
themselves are never committed.
"""

import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from . import indexed, report
from .editions import bare_arxiv_id
from .http import RateLimitedHttp
from .manifest import read_manifest, write_manifest

ARXIV_PDF_URL = "https://export.arxiv.org/pdf/{}"  # arXiv asks harvesters to use the export host
ARXIV_MIN_INTERVAL_SECONDS = 3.0  # arXiv's terms of use: one request every three seconds
OTHER_MIN_INTERVAL_SECONDS = 1.0  # the ACL Anthology and open-access hosts publish no limit
GONE_STATUS = {404, 410}
VERSION_SUFFIX = re.compile(r"v\d+$")  # an arXiv Version at the end of a pinned id
RETRY_LATER_STATUS = {408, 429}  # the host is busy, not refusing


@dataclass(frozen=True)
class PinnedFile:
    """One file an Edition's full text is pinned to, and where to get it, best source first."""

    name: str  # under the PDF directory, e.g. "2004.03720v1.pdf"
    urls: tuple[str, ...]


@dataclass(frozen=True)
class FetchedFile:
    """One line of the record: a file fetched for an Edition, or why it has no open PDF."""

    edition_id: str
    file: str  # "" when the Edition has no open PDF
    url: str
    sha256: str
    size: int
    fetched_at: str
    unavailable: str = ""  # why no source served a PDF; empty for a fetched file. ``url`` then lists the sources tried.


class FetchError(RuntimeError):
    """A file that should have been fetched wasn't."""


class UpstreamDrift(FetchError):
    """A source no longer serves the file the record pins, or serves different bytes."""


class FetchFailed(FetchError):
    """A file never fetched before couldn't be fetched: a network error, a server error or a body that isn't a PDF."""


class FetchErrors(RuntimeError):
    """Every file a run couldn't fetch, upstream drift first, worded for the person running it."""

    def __init__(self, errors: list[FetchError]) -> None:
        self.errors = errors
        drift = [e for e in errors if isinstance(e, UpstreamDrift)]
        failed = [e for e in errors if isinstance(e, FetchFailed)]
        lines = []
        if drift:
            lines.append(
                f"{_count_files(len(drift))} changed upstream since the record was made. This is upstream drift,"
                " not a pipeline failure. To re-pin a file to what its source serves now, delete its line from"
                " the record and fetch again."
            )
            lines += [f"  upstream drift: {e}" for e in drift]
        if failed:
            lines.append(
                f"{_count_files(len(failed), pinned=False)} couldn't be fetched. Their record is unchanged, so a rerun tries again."
            )
            lines += [f"  fetch failed: {e}" for e in failed]
        super().__init__("\n".join(lines))


def _count_files(count: int, pinned: bool = True) -> str:
    noun = "pinned file" if pinned else "file"
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class FulltextRecord:
    """The record at ``<snapshot>/fulltext/pdfs.jsonl``: one JSON line per file, sorted by Edition and file."""

    def __init__(self, snapshot_root: Path) -> None:
        self.path = snapshot_root / "fulltext" / "pdfs.jsonl"
        self._entries: dict[tuple[str, str], FetchedFile] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = FetchedFile(**json.loads(line))
                    self._entries[entry.edition_id, entry.file] = entry

    def get(self, file: str) -> FetchedFile | None:
        """The fetched file by name. The name is the pinned id, so it stays the same when an Edition is re-pinned."""
        return next((entry for (_, name), entry in self._entries.items() if name == file), None) if file else None

    def all(self) -> list[FetchedFile]:
        """Every line of the record, in its sorted order."""
        return [self._entries[key] for key in sorted(self._entries)]

    def entries(self, edition_id: str) -> list[FetchedFile]:
        return [entry for key, entry in sorted(self._entries.items()) if key[0] == edition_id]

    def has_no_open_pdf(self, edition_id: str, pinned: list[PinnedFile]) -> bool:
        """Whether every source the Edition is pinned to was tried and none served a PDF.

        A source added since, say by a refreshed Snapshot, makes it worth trying again.
        """
        return any(
            entry.unavailable and entry.url == _sources(file)
            for file in pinned
            for entry in self.entries(edition_id)
            if not entry.file
        )

    def put(self, entry: FetchedFile) -> None:
        self._entries[entry.edition_id, entry.file] = entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(asdict(self._entries[key]), sort_keys=True, separators=(",", ":")) for key in sorted(self._entries)]
        self.path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def file_name(pinned_id: str) -> str:
    """A file name for a pinned id: old-style arXiv ids and DOIs contain slashes."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", pinned_id) + ".pdf"


def pinned_id_of_file(edition_id: str, file: str) -> tuple[str, str]:
    """The pinned id and Version a recorded file holds: the inverse of `file_name` as `pinned_files` uses it.

    A preprint Edition (an arXiv id pinned to its latest Version) holds files named for its Versions, so
    "hep-th_9901001v1.pdf" of Edition "hep-th/9901001v2" holds "hep-th/9901001v1", Version "v1". Any other
    file is the Edition itself, a venue Edition with no Version: "10.5555/lrm.2022.7".
    """
    arxiv_id = VERSION_SUFFIX.sub("", edition_id)
    if arxiv_id != edition_id:
        stem = file.removesuffix(".pdf")
        version = stem.removeprefix(file_name(arxiv_id).removesuffix(".pdf"))
        if VERSION_SUFFIX.fullmatch(version) and file_name(arxiv_id + version) == file:
            return arxiv_id + version, version
    return edition_id, ""


def pinned_files(row: dict[str, str]) -> list[PinnedFile]:
    """The files a manifest row's full text is pinned to; empty when it has no open PDF source."""
    if row["edition_kind"] == "arxiv-preprint":
        labels = [entry.split(" ", 1)[0] for entry in row["versions"].split("|") if entry]
        latest = row["edition_id"].removeprefix(row["arxiv_id"])
        if not labels or latest not in labels:
            return []  # never fetch an unpinned preprint
        pinned = ["v1", latest] if latest != "v1" else [latest]
        return [
            PinnedFile(file_name(f"{row['arxiv_id']}{v}"), (ARXIV_PDF_URL.format(f"{row['arxiv_id']}{v}"),))
            for v in pinned
        ]
    # An arXiv link among a venue Edition's open-access links is the preprint, a different Edition.
    urls = [row["pdf_link"]] if row["pdf_link"] else []
    urls += [url for url in row["oa_pdf_urls"].split("|") if url and not _is_arxiv(url)]
    return [PinnedFile(file_name(row["edition_id"]), tuple(dict.fromkeys(urls)))] if urls else []


def _sources(file: PinnedFile) -> str:
    return "|".join(file.urls)


def _is_arxiv(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    return host == "arxiv.org" or host.endswith(".arxiv.org")


def apply_record(rows: list[dict[str, str]], record: FulltextRecord) -> None:
    """Fill in each row's fetched files and, for included rows, its funnel status from the record.

    An included row reaches "full text" once every file it is pinned to is recorded, and is
    ``no_fulltext`` when it has no open PDF source or none of its sources served a PDF.
    """
    for row in rows:
        pinned = pinned_files(row)
        # A file the row is no longer pinned to, such as an older latest Version, stays in the record but not here.
        entries = [entry for file in pinned if (entry := record.get(file.name))]
        row["pdf_files"] = "|".join(f"{entry.file} {entry.sha256}" for entry in entries)
        if row["relevance_verdict"] != "included":
            continue
        if not pinned or record.has_no_open_pdf(row["edition_id"], pinned):
            row["funnel_status"] = "no_fulltext"
        elif len(entries) == len(pinned):
            row["funnel_status"] = "full text"
        else:
            row["funnel_status"] = "relevant"
    _exclude_borrowed_files(rows, record)


BORROWED_FILE = "borrowed file"  # the relevance stage of an Edition whose only file belongs to another one


def _exclude_borrowed_files(rows: list[dict[str, str]], record: FulltextRecord) -> None:
    """Exclude each included Edition whose only file belongs to another Edition (#44).

    The file is suspect when it came from an open-access location rather than the Edition's own
    source (its ACL Anthology PDF, or arXiv for a preprint): an OpenAlex link can resolve to another
    paper's PDF, as the CRAN `sentencepiece` package's did to an LREC paper. It is borrowed when
    another Edition holds the same bytes and no identifier or title links the two. Editions of one
    Work that hold the same bytes, such as a venue PDF that is the preprint's v1, stay included.
    """
    holders: dict[str, list[tuple[dict[str, str], str]]] = {}  # sha256 → (row, file) for every row holding it
    for row in rows:
        for held in row["pdf_files"].split("|"):
            if held:
                file, sha256 = held.split(" ")
                holders.setdefault(sha256, []).append((row, file))
    for row in rows:
        files = [held.split(" ") for held in row["pdf_files"].split("|") if held]
        if row["relevance_verdict"] != "included" or len(files) != 1:
            continue
        file, sha256 = files[0]
        entry = record.get(file)
        if entry is None or entry.url == row["pdf_link"] or _is_arxiv(entry.url):
            continue
        others = [(other, other_file) for other, other_file in holders[sha256] if other is not row]
        if not others or any(_linked(row, other) for other, _ in others):
            continue
        other, other_file = others[0]
        row["relevance_verdict"] = "excluded"
        row["relevance_stage"] = BORROWED_FILE
        row["relevance_reason"] = (
            f"file belongs to another Edition: {file}, from {entry.url}, has the same bytes as {other_file}"
            f" of {other['edition_id']}, and no identifier or title links the two"
        )
        row["funnel_status"] = "discovered"


def _linked(row: dict[str, str], other: dict[str, str]) -> bool:
    """Whether two rows share an arXiv id, DOI or ACL ID, or have the same title."""
    return bool(_identifiers(row) & _identifiers(other)) or _title_key(row["title"]) == _title_key(other["title"])


def _identifiers(row: dict[str, str]) -> set[str]:
    names = {f"arxiv:{bare_arxiv_id(row['arxiv_id']).casefold()}"} if row["arxiv_id"] else set()
    return names | {f"{kind}:{row[kind].casefold()}" for kind in ("doi", "acl_id") if row[kind]}


def _title_key(title: str) -> str:
    """A title without case, accents, punctuation or extra whitespace."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_title).split())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-")


class _Downloader:
    """Rate-limited GETs: arXiv on its own three-second clock, every other host on a one-second clock."""

    def __init__(self) -> None:
        self._arxiv: RateLimitedHttp | None = None
        self._other: RateLimitedHttp | None = None

    def get(self, url: str) -> httpx.Response:
        if _is_arxiv(url):
            self._arxiv = self._arxiv or RateLimitedHttp(ARXIV_MIN_INTERVAL_SECONDS)
            return self._arxiv.response(url)
        self._other = self._other or RateLimitedHttp(OTHER_MIN_INTERVAL_SECONDS)
        return self._other.response(url)


def _describe(response: httpx.Response) -> str:
    if response.status_code != 200:
        return f"HTTP {response.status_code}"
    content_type = response.headers.get("Content-Type", "no content type")
    return f"not a PDF ({content_type}, starts {response.content[:16]!r})"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(data)
    partial.replace(path)


def _refetch(downloader: _Downloader, entry: FetchedFile, path: Path) -> None:
    """Download a recorded file again and check it against the recorded hash."""
    pinned = f"{entry.file} from {entry.url} (sha256 {entry.sha256}, recorded {entry.fetched_at})"
    try:
        response = downloader.get(entry.url)
    except httpx.TransportError as error:
        raise FetchFailed(f"{entry.file}: {entry.url}: {error!r}") from error
    if response.status_code in GONE_STATUS:
        raise UpstreamDrift(f"{pinned} is no longer available: HTTP {response.status_code}")
    if response.status_code != 200 or not _is_pdf(response.content):
        raise FetchFailed(f"{entry.file}: {entry.url}: {_describe(response)}; the record pins sha256 {entry.sha256}")
    if (digest := _sha256(response.content)) != entry.sha256:
        raise UpstreamDrift(f"hash mismatch for {pinned}: it now serves sha256 {digest}")
    _write(path, response.content)


def _fetch_new(downloader: _Downloader, edition_id: str, kind: str, pinned: PinnedFile, path: Path) -> FetchedFile:
    """Fetch a file never fetched before from the first of its sources that serves a PDF.

    A venue Edition whose sources all answer that they have no PDF (gone, forbidden, or a web
    page instead) is recorded as having no open PDF. A preprint's pinned Version must exist, so
    for it that is a failure. So is a network or server error, which a rerun may not repeat;
    a venue Edition's next source is still tried first.
    """
    refused, failed = [], []
    for url in pinned.urls:
        try:
            response = downloader.get(url)
        except httpx.TransportError as error:
            failed.append(f"{url}: {error!r}")
            continue
        if response.status_code == 200 and _is_pdf(response.content):
            _write(path, response.content)
            return FetchedFile(
                edition_id, pinned.name, url, _sha256(response.content), len(response.content), _today()
            )
        if response.status_code >= 500 or response.status_code in RETRY_LATER_STATUS or kind == "arxiv-preprint":
            failed.append(f"{url}: {_describe(response)}")
        else:
            refused.append(f"{url}: {_describe(response)}")
    if failed:
        raise FetchFailed(f"{pinned.name}: {'; '.join(failed + refused)}")
    return FetchedFile(edition_id, "", _sources(pinned), "", 0, _today(), unavailable="; ".join(refused))


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class _LimitReached(Exception):
    """Raised to stop a run once ``--limit`` files have been downloaded."""


def fetch(snapshot_dir: Path, manifest_path: Path, report_path: Path, pdf_dir: Path, limit: int | None = None) -> None:
    """Download the pinned PDFs of every included Edition in the manifest, record their hashes and
    update the manifest.

    A file already in ``pdf_dir`` whose hash matches the record is kept; any other recorded file
    is downloaded again and must match its recorded hash. ``limit`` caps the number of files
    downloaded. A failed file doesn't stop the run: every failure is reported at the end.
    """
    rows = read_manifest(manifest_path)
    record = FulltextRecord(snapshot_dir)
    downloader = _Downloader()
    errors: list[FetchError] = []
    downloads = 0
    included = sorted((row for row in rows if row["relevance_verdict"] == "included"), key=lambda row: row["edition_id"])
    try:
        for row in included:
            edition_id = row["edition_id"]
            files = pinned_files(row)
            if record.has_no_open_pdf(edition_id, files):
                continue
            for pinned in files:
                path = pdf_dir / pinned.name
                entry = record.get(pinned.name)
                if entry and path.exists() and _sha256(path.read_bytes()) == entry.sha256:
                    continue
                if limit is not None and downloads >= limit:
                    raise _LimitReached
                downloads += 1
                if downloads % 50 == 0:
                    print(f"  fetch: {downloads} files downloaded", file=sys.stderr)
                try:
                    if entry:
                        _refetch(downloader, entry, path)
                    else:
                        record.put(_fetch_new(downloader, edition_id, row["edition_kind"], pinned, path))
                        record.save()
                except FetchError as error:
                    print(f"fetch: {error}", file=sys.stderr)
                    errors.append(error)
                    break
    except _LimitReached:
        print(f"fetch: stopped at the limit of {limit} downloads", file=sys.stderr)
    finally:
        apply_record(rows, record)
        indexed.apply_record(rows, indexed.IndexRecord(snapshot_dir))
        write_manifest(manifest_path, rows)
        report.write(report_path, rows)
    print(f"fetch: {downloads} files downloaded into {pdf_dir}", file=sys.stderr)
    report.summarise_fulltext(rows)
    if errors:
        raise FetchErrors(errors)
