"""Work grouping (#51): which included Editions are one Work, from the manifest rows alone, so the manifest stays
a pure function of the Snapshot.

Two included Editions are one Work when they share an identifier (arXiv id, DOI or ACL ID), a file's sha256 in
the full-text record, or a title (compared by `title_key`) together with the first author's surname. Two Works
that share a title but not a first author are a Suspected pair: listed, never joined. Each Work has a Canonical
Edition, the venue Edition when there is one and otherwise the latest Version of its preprint, and a readable
`work_id` made from it. A Work is a Survey when the Canonical Edition's title says so; nothing is demoted for it.
"""

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations

from .editions import bare_arxiv_id

Row = dict[str, str]

# Letters NFKD leaves alone, spelled as an English-language citation would.
_SPELLED_OUT = str.maketrans({"ı": "i", "ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "Đ": "D", "ß": "ss", "æ": "ae", "Æ": "AE"})
# Words a slug skips, so it is made of the title's content words, as in the Work groups.
_SHORT_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in", "into", "is", "of", "on", "or", "the",
    "to", "via", "what", "when", "which", "why", "with",
}  # fmt: skip
SLUG_TITLE_WORDS = 3
SURVEY_WORD = re.compile(r"\b(survey|review|overview|tutorial)\b")


def normalise(text: str) -> str:
    """Text without case, accents, punctuation or extra whitespace: "Costa-jussà" becomes "costa jussa"."""
    ascii_text = unicodedata.normalize("NFKD", text.translate(_SPELLED_OUT)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text).split())


def first_author(row: Row) -> str:
    """The first author's name as the manifest gives it, which may be "Surname, Given"."""
    return row["authors"].split("; ")[0].strip()


def surname(row: Row) -> str:
    """The first author's surname, normalised: what comes before a comma ("Vieira, Tim"), else the last word of
    their name ("Tim Vieira")."""
    name = first_author(row)
    if "," in name:
        return normalise(name.partition(",")[0])
    words = name.split()
    return normalise(words[-1]) if words else ""


def identifiers(row: Mapping[str, str]) -> set[str]:
    """The row's arXiv id, DOI and ACL ID as comparable names, such as "doi:10.18653/v1/p16-1162"."""
    names = {f"arxiv:{bare_arxiv_id(row['arxiv_id']).casefold()}"} if row["arxiv_id"] else set()
    return names | {f"{kind}:{row[kind].casefold()}" for kind in ("doi", "acl_id") if row[kind]}


def file_hashes(row: Row) -> set[str]:
    """The sha256 of each of the row's files in the full-text record, as names such as "sha256:9f86d0…"."""
    return {f"sha256:{held.split(' ')[1]}" for held in row["pdf_files"].split("|") if held}


def title_key(title: str) -> str:
    """The title as two Editions of one paper are compared: normalised, a hyphen inside a word dropped rather than
    made a space, and the words sorted, so "Robust End-to-End" and "End-to-End Robust" or "Pre-trained" and
    "Pretrained" compare equal (ADR 0062)."""
    return " ".join(sorted(normalise(re.sub(r"(?<=\w)-(?=\w)", "", title)).split()))


def title_and_author(row: Row) -> set[str]:
    """The title's key with the first author's surname, as a name such as "title:kudo|improving models …".
    A title alone never names a Work: two papers may share one."""
    title, author = title_key(row["title"]), surname(row)
    return {f"title:{author}|{title}"} if title and author else set()


class _UnionFind:
    """Union-find over row positions, joined through the names they share."""

    def __init__(self, size: int) -> None:
        self._parent = list(range(size))
        self._holder: dict[str, int] = {}

    def add(self, position: int, names: Iterable[str]) -> None:
        for name in names:
            self._join(self._holder.setdefault(name, position), position)

    def root(self, position: int) -> int:
        while (parent := self._parent[position]) != position:
            self._parent[position] = self._parent[parent]
            position = parent
        return position

    def _join(self, first: int, second: int) -> None:
        first, second = self.root(first), self.root(second)
        self._parent[max(first, second)] = min(first, second)


# Each signal joins Editions together with every signal before it, weakest last.
SIGNALS: list[tuple[str, list[Callable[[Row], set[str]]]]] = [
    ("an identifier", [identifiers]),
    ("file bytes", [identifiers, file_hashes]),
    ("title and first author", [identifiers, file_hashes, title_and_author]),
]


@dataclass(frozen=True)
class Work:
    work_id: str
    canonical: Row
    editions: list[Row]  # sorted by Edition id
    signal: str  # the weakest signal its Editions needed to be one Work, from SIGNALS; "" for a single Edition

    @property
    def survey(self) -> bool:
        return bool(SURVEY_WORD.search(normalise(self.canonical["title"])))


@dataclass(frozen=True)
class SuspectedPair:
    """Two Works with the same title but different first authors: never joined. Each side holds the Work's
    Editions with that title."""

    first: list[Row]
    second: list[Row]


@dataclass(frozen=True)
class Grouping:
    works: list[Work]  # sorted by work_id
    suspected: list[SuspectedPair]  # sorted by their Editions' ids


def group(rows: Iterable[Row]) -> Grouping:
    """The Works of the included rows and the Suspected pairs among them. Rows are only read."""
    included = sorted((row for row in rows if row["relevance_verdict"] == "included"), key=lambda row: row["edition_id"])
    roots = {signal: _roots(included, names) for signal, names in SIGNALS}
    final = roots[SIGNALS[-1][0]]
    members: dict[int, list[int]] = {}
    for position, root in enumerate(final):
        members.setdefault(root, []).append(position)

    def signal(positions: list[int]) -> str:
        if len(positions) == 1:
            return ""
        return next(name for name, _ in SIGNALS if len({roots[name][position] for position in positions}) == 1)

    found = sorted(
        ((_canonical([included[p] for p in positions]), positions) for positions in members.values()),
        key=lambda work: work[0]["edition_id"],
    )
    works, taken = [], set()
    for canonical, positions in found:
        work_id = base = _slug(canonical)
        suffix = 2
        while work_id in taken:
            work_id, suffix = f"{base}-{suffix}", suffix + 1
        taken.add(work_id)
        works.append(Work(work_id, canonical, [included[p] for p in positions], signal(positions)))
    return Grouping(sorted(works, key=lambda work: work.work_id), _suspected(included, final))


def _roots(included: list[Row], signals: list[Callable[[Row], set[str]]]) -> list[int]:
    """Each row's Work, as a row position, when Editions are joined by ``signals`` alone."""
    joins = _UnionFind(len(included))
    for position, row in enumerate(included):
        for names in signals:
            joins.add(position, names(row))
    return [joins.root(position) for position in range(len(included))]


def _suspected(included: list[Row], works: list[int]) -> list[SuspectedPair]:
    """Every two Works holding Editions with the same title."""
    by_title: dict[str, dict[int, list[Row]]] = {}
    for row, work in zip(included, works, strict=True):
        if title := title_key(row["title"]):
            by_title.setdefault(title, {}).setdefault(work, []).append(row)
    pairs = [
        SuspectedPair(first, second)
        for sides in by_title.values()
        for first, second in combinations(sorted(sides.values(), key=lambda side: side[0]["edition_id"]), 2)
    ]
    return sorted(pairs, key=lambda pair: (pair.first[0]["edition_id"], pair.second[0]["edition_id"]))


def apply(rows: list[Row]) -> None:
    """Fill each included row's work_id, canonical and survey columns; every other row's are blank."""
    for row in rows:
        row["work_id"] = row["canonical"] = row["survey"] = ""
    for work in group(rows).works:
        for row in work.editions:
            row["work_id"] = work.work_id
            row["canonical"] = "yes" if row is work.canonical else "no"
            row["survey"] = "yes" if work.survey else "no"


def _canonical(editions: list[Row]) -> Row:
    """The venue Edition with the latest year, ties going to the first by Edition id; with no venue Edition, the
    preprint whose latest Version is the most recent. A preprint's Edition id already names its latest Version."""
    venues = [row for row in editions if row["edition_kind"] == "venue"]
    if venues:
        return max(venues, key=lambda row: row["year"])
    return max(editions, key=lambda row: row["versions"].rpartition(" ")[2])


def _slug(canonical: Row) -> str:
    """`<surname>-<year>-<first three title words>`, as in the Work groups: "sennrich-2016-neural-machine-translation"."""
    words = [word for word in normalise(canonical["title"]).split() if word not in _SHORT_WORDS][:SLUG_TITLE_WORDS]
    return "-".join(part for part in [*surname(canonical).split(), canonical["year"], *words] if part)
