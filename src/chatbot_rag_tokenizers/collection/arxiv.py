"""arXiv client, reading the Snapshot before the network.

Keyword queries page through the search API. Each Edition's full record (every Version with
its date, the comments and the licence) comes from OAI-PMH in the ``arXivRaw`` format, which
the search API doesn't offer.

API manual: https://info.arxiv.org/help/api/user-manual.html
OAI-PMH: https://info.arxiv.org/help/oa/index.html
Terms of use: at most one request every three seconds, one connection at a time, across both.
"""

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from .editions import Edition
from .http import RateLimitedHttp
from .snapshot import SnapshotStore, StoredResponse

API_URL = "https://export.arxiv.org/api/query"
OAI_URL = "https://oaipmh.arxiv.org/oai"
MIN_INTERVAL_SECONDS = 3.0
MAX_RESULTS_PER_QUERY = 30_000  # the API refuses to page past this
EMPTY_PAGE_RETRIES = 3

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "raw": "http://arxiv.org/OAI/arXivRaw/",
}


class ArxivError(RuntimeError):
    pass


def _text(element: ET.Element, path: str) -> str:
    found = element.find(path, NS)
    if found is None or found.text is None:
        return ""
    return " ".join(found.text.split())


def _parse_entry(entry: ET.Element) -> Edition:
    abs_url = _text(entry, "atom:id")
    edition_id = abs_url.split("/abs/", 1)[1]
    return Edition(
        edition_id=edition_id,
        edition_kind="arxiv-preprint",
        title=_text(entry, "atom:title"),
        abstract=_text(entry, "atom:summary"),
        authors=[_text(author, "atom:name") for author in entry.findall("atom:author", NS)],
        year=_text(entry, "atom:published")[:4],
        arxiv_comments=_text(entry, "arxiv:comment"),
        journal_ref=_text(entry, "arxiv:journal_ref"),
        source_link=f"https://arxiv.org/abs/{edition_id}",
        arxiv_id=re.sub(r"v\d+$", "", edition_id),
        doi=_text(entry, "arxiv:doi"),
    )


@dataclass(frozen=True)
class ArxivRecord:
    """An arXiv Edition's full record: every Version, oldest first, with its submission time."""

    versions: list[tuple[str, str]]  # ("v1", "2020-04-07T21:21:06Z")
    comments: str
    licence: str  # "unknown" when the record has none

    @property
    def latest_version(self) -> str:
        return self.versions[-1][0]


def _parse_record(body: str) -> ArxivRecord:
    root = ET.fromstring(body)
    error = root.find("oai:error", NS)
    if error is not None:
        raise ArxivError(f"arXiv OAI-PMH error {error.get('code')}: {' '.join((error.text or '').split())}")
    raw = root.find(".//raw:arXivRaw", NS)
    if raw is None:
        raise ArxivError("arXiv OAI-PMH response has no arXivRaw record")
    versions = []
    for version in raw.findall("raw:version", NS):
        try:
            submitted = parsedate_to_datetime(_text(version, "raw:date")).astimezone(UTC)
        except (TypeError, ValueError) as error:
            raise ArxivError(f"arXiv record {_text(raw, 'raw:id')} has an unreadable Version date") from error
        versions.append((version.get("version", ""), submitted.strftime("%Y-%m-%dT%H:%M:%SZ")))
    # arXiv lists Versions oldest first, but sort numerically so v10 can never precede v9.
    versions.sort(key=lambda v: int(v[0].lstrip("v")))
    if not versions:
        raise ArxivError(f"arXiv record {_text(raw, 'raw:id')} lists no Versions")
    return ArxivRecord(
        versions=versions,
        comments=_text(raw, "raw:comments"),
        licence=_text(raw, "raw:license") or "unknown",
    )


def _parse_page(body: str) -> tuple[int, list[Edition]]:
    feed = ET.fromstring(body)
    entries = feed.findall("atom:entry", NS)
    # The API reports a malformed query as a single entry whose id points at its errors page.
    if len(entries) == 1 and "/api/errors" in _text(entries[0], "atom:id"):
        raise ArxivError(f"arXiv rejected the query: {_text(entries[0], 'atom:summary')}")
    total = int(_text(feed, "opensearch:totalResults") or 0)
    return total, [_parse_entry(entry) for entry in entries]


class ArxivSource:
    def __init__(self, snapshot: SnapshotStore, page_size: int) -> None:
        self.snapshot = snapshot
        self.page_size = page_size
        self._http: RateLimitedHttp | None = None  # created on the first Snapshot miss

    def _request(self, query: str, start: int) -> dict:
        # Ascending submission date keeps earlier pages stable while new papers arrive at the end.
        return {
            "source": "arxiv",
            "url": API_URL,
            "params": {
                "search_query": query,
                "start": start,
                "max_results": self.page_size,
                "sortBy": "submittedDate",
                "sortOrder": "ascending",
            },
        }

    def _page(self, query: str, start: int) -> tuple[int, list[Edition]]:
        request = self._request(query, start)
        stored = self.snapshot.load(request)
        if stored is None:
            stored = self._fetch(request, start)
        return _parse_page(stored.body)

    def _fetch(self, request: dict, start: int) -> StoredResponse:
        http = self._ensure_http()
        for attempt in range(1, EMPTY_PAGE_RETRIES + 1):
            print(f"  arxiv: fetching entries {start}+ for {request['params']['search_query']!r}", file=sys.stderr)
            body = http.get(request["url"], request["params"])
            total, editions = _parse_page(body)
            # arXiv sometimes returns an empty page, even "0 total" for a query that has matches.
            # Never store one as if it were the answer: retry, and accept an empty first page
            # only once it has come back empty every time.
            genuinely_empty = start == 0 and total == 0 and attempt == EMPTY_PAGE_RETRIES
            if editions or (0 < total <= start) or genuinely_empty:
                collected_at = datetime.now(UTC).date().isoformat()
                return self.snapshot.save(request, body, collected_at)
        raise ArxivError(f"arXiv kept returning an empty page at start={start} of {total}")

    def _ensure_http(self) -> RateLimitedHttp:
        # One client for search and OAI-PMH, so the three-second gap holds across both.
        if self._http is None:
            self._http = RateLimitedHttp(MIN_INTERVAL_SECONDS)
        return self._http

    def record(self, arxiv_id: str) -> ArxivRecord:
        """The full record of the unversioned ``arxiv_id``, e.g. ``2004.03720`` or ``hep-th/9901001``."""
        params = {"verb": "GetRecord", "identifier": f"oai:arXiv.org:{arxiv_id}", "metadataPrefix": "arXivRaw"}
        request = {"source": "arxiv-oai", "url": OAI_URL, "params": params}
        stored = self.snapshot.load(request)
        if stored is not None:
            return _parse_record(stored.body)
        body = self._ensure_http().get(OAI_URL, params)
        record = _parse_record(body)  # raises before an error response can be stored
        self.snapshot.save(request, body, datetime.now(UTC).date().isoformat())
        return record

    def search(self, query: str) -> list[Edition]:
        """Every Edition ``query`` finds, in API order, possibly with repeats across pages."""
        total, editions = self._page(query, 0)
        if total > MAX_RESULTS_PER_QUERY:
            print(
                f"  arxiv: {query!r} matches {total} entries; the API stops at {MAX_RESULTS_PER_QUERY}, narrow the query",
                file=sys.stderr,
            )
        for start in range(self.page_size, min(total, MAX_RESULTS_PER_QUERY), self.page_size):
            editions.extend(self._page(query, start)[1])
        return editions
