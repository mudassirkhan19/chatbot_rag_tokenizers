"""The Collapsed ranking (ADRs 0053, 0057 and 0073): each Chunk once, however many files of its Work hold a copy.

The wrapper asks the retriever it wraps for a pool of Chunks and merges copies: Chunks of one Work, through the
manifest's work_id, from different files, that share at least `overlap` of their word 5-grams, counted on the
smaller Chunk's, where one of the two is the other's closest Chunk in its file. That is what a paper's arXiv
Versions and its preprint and venue Editions repeat, wherever their files put it: GROBID nests a Section in one
Edition only, headings change case, Sections are renumbered and a revision adds paragraphs, so the place in the
Section is no key (ADR 0073). Going down the pool, a Chunk joins the best-ranked slot of its Work that holds a copy
of it and no Chunk of its file; else it opens a slot. A Chunk whose Edition has no work_id is its Edition's own Work, so nothing the collapse can't place is
dropped. A Work's other Chunks are other text and keep their own slots, as the raw ranking gave them.

Each slot takes the place of its best-ranked copy, and shows the copy from the best file, best first by tier, then
by rank:

    1. the Canonical Edition's own file (for a preprint, its latest Version)
    2. any Edition's latest file
    3. any file, such as a v1

so a stale v1 stands for a passage only when no later copy of it was retrieved. Surveys are not demoted. No
retriever's code or index changes, and `query` keeps the raw `(chunk_id, score)` shape; `collapse` also gives,
by Chunk id, the Work, the merged Editions, the merged copies and whether the manifest flags its Edition a Survey.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ..parsing.chunker import Chunk
from .retriever import Retriever

SUFFIX = "+collapsed"
WORD = re.compile(r"\w+")  # a word of a Chunk's text, matched lower-cased
SHINGLE = 5  # the words in each run two copies are compared by


@dataclass(frozen=True)
class Merged:
    """What stands behind one Chunk of a Collapsed ranking."""

    work_id: str  # the manifest's work_id, or "edition:<id>" for an Edition with none
    editions: tuple[str, ...]  # the pinned ids (ids with Version) of the files of the copies merged into it, best first
    copies: tuple[str, ...]  # the ids of the copies merged into it, best first
    survey: bool  # the manifest's survey column says yes for the shown Chunk's Edition


@dataclass(frozen=True)
class Collapse:
    """One query's Collapsed ranking, with what stands behind each of its Chunks."""

    ranking: list[tuple[str, float]]  # at most k, each with its copies merged
    merged: dict[str, Merged]  # by the ranking's Chunk ids
    distinct: int  # the pool's Chunks once copies are merged, which is fewer than k when the pool ran short


class Collapsed:
    """A retriever's Collapsed ranking, over the manifest's Works and the Chunks' text."""

    def __init__(
        self, retriever: Retriever, chunks: Mapping[str, Chunk], manifest: Iterable[Mapping[str, str]], pool: int, overlap: float
    ) -> None:
        self.retriever = retriever
        self.chunks = chunks
        self.pool = pool
        self.overlap = overlap
        self._work: dict[str, str] = {}  # each Edition's Work, for the Editions that have one
        self._canonical: set[str] = set()  # the Canonical Editions' ids
        self._survey: set[str] = set()  # the ids of the Editions flagged a Survey
        for row in manifest:
            if row["survey"] == "yes":
                self._survey.add(row["edition_id"])
            if row["work_id"]:
                self._work[row["edition_id"]] = row["work_id"]
                if row["canonical"] == "yes":
                    self._canonical.add(row["edition_id"])
        self._files: dict[str, list[str]] = {}  # each file's Chunk ids
        for chunk in chunks.values():
            self._files.setdefault(chunk.file_sha256, []).append(chunk.chunk_id)
        self._shingles: dict[str, frozenset[tuple[str, ...]]] = {}  # each Chunk's word 5-grams, once it is asked for
        self._closest: dict[tuple[str, str], float] = {}  # a Chunk's highest overlap with a file's Chunks, once asked for

    @property
    def device(self) -> str:
        return self.retriever.device

    @property
    def parameters(self) -> int | None:
        return self.retriever.parameters

    @property
    def dimension(self) -> int | None:
        return self.retriever.dimension

    def save(self, directory: Path) -> None:
        self.retriever.save(directory)

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        return self.collapse(text, k).ranking

    def collapse(self, text: str, k: int) -> Collapse:
        slots: list[tuple[str, list[tuple[str, float]]]] = []  # each passage's Work and copies, in raw order
        for chunk_id, score in self.retriever.query(text, max(self.pool, k)):
            work_id = self.work_of(self.chunks[chunk_id])
            slot = next((copies for work, copies in slots if work == work_id and self._joins(chunk_id, copies)), None)
            if slot is None:
                slots.append((work_id, [(chunk_id, score)]))
            else:
                slot.append((chunk_id, score))
        ranking, merged = [], {}
        for work_id, copies in slots[:k]:
            shown = min(copies, key=lambda hit: self._tier(self.chunks[hit[0]]))  # min keeps the best-ranked on a tie
            others = [chunk_id for chunk_id, _ in copies if chunk_id != shown[0]]
            ranking.append(shown)
            editions = tuple(dict.fromkeys(self.chunks[c].pinned_id for c in others))
            merged[shown[0]] = Merged(work_id, editions, tuple(others), self.chunks[shown[0]].edition_id in self._survey)
        return Collapse(ranking, merged, len(slots))

    def work_of(self, chunk: Chunk) -> str:
        return self._work.get(chunk.edition_id, f"edition:{chunk.edition_id}")

    def _joins(self, chunk_id: str, copies: list[tuple[str, float]]) -> bool:
        """Whether the Chunk is a copy of the passage these copies hold: from a file none of them is from, and sharing
        a copy of one of them."""
        file = self.chunks[chunk_id].file_sha256
        if any(self.chunks[other].file_sha256 == file for other, _ in copies):
            return False
        return any(self._is_copy(chunk_id, other) for other, _ in copies)

    def _is_copy(self, a: str, b: str) -> bool:
        """Two Chunks of different files are copies when they share at least `overlap` of their word 5-grams and one of
        them is the other's closest Chunk in its file: a table cut into two Chunks repeats its caption in both, and
        each is closer to its own copy in the other file than to the other's."""
        overlap = self._overlap(a, b)
        if overlap < self.overlap:
            return False
        return overlap >= self._closest_in(a, self.chunks[b].file_sha256) or overlap >= self._closest_in(b, self.chunks[a].file_sha256)

    def _closest_in(self, chunk_id: str, file: str) -> float:
        if (chunk_id, file) not in self._closest:
            self._closest[chunk_id, file] = max(self._overlap(chunk_id, other) for other in self._files[file])
        return self._closest[chunk_id, file]

    def _overlap(self, a: str, b: str) -> float:
        shingles_a, shingles_b = self._shingles_of(a), self._shingles_of(b)
        return len(shingles_a & shingles_b) / max(1, min(len(shingles_a), len(shingles_b)))

    def _shingles_of(self, chunk_id: str) -> frozenset[tuple[str, ...]]:
        if chunk_id not in self._shingles:
            words = WORD.findall(self.chunks[chunk_id].text.lower())
            self._shingles[chunk_id] = frozenset(tuple(words[i : i + SHINGLE]) for i in range(max(1, len(words) - SHINGLE + 1)))
        return self._shingles[chunk_id]

    def _tier(self, chunk: Chunk) -> int:
        latest = chunk.pinned_id == chunk.edition_id  # a preprint's Edition id names its latest Version (ADR 0015)
        return 0 if latest and chunk.edition_id in self._canonical else 1 if latest else 2
