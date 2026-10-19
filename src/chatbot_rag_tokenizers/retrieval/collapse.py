"""The Collapsed ranking (ADR 0053): at most one Chunk per Work, over any retriever.

The wrapper asks the retriever it wraps for a pool of Chunks, maps each to its Work through the manifest's
work_id, and keeps the Works in the order their best-ranked Chunk came in. A Chunk whose Edition has no
work_id is its Edition's own Work, so nothing the collapse can't place is dropped. For each Work it shows,
best first by tier, then by rank:

    1. a Chunk of the Canonical Edition's own file (for a preprint, its latest Version)
    2. a Chunk of any Edition's latest file
    3. any Chunk, such as a v1's

so a stale v1 stands for a paper only when no later file of it was retrieved. Surveys are not demoted: a
Survey's Work collapses like any other. No retriever's code or index changes, and `query` keeps the raw
`(chunk_id, score)` shape; `collapse` also gives, by Chunk id, the Work, the merged Editions and the Work's
other Chunks in the pool.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ..parsing.chunker import Chunk
from .retriever import Retriever

SUFFIX = "+collapsed"


@dataclass(frozen=True)
class Merged:
    """What stands behind one Chunk of a Collapsed ranking."""

    work_id: str  # the manifest's work_id, or "edition:<id>" for an Edition with none
    editions: tuple[str, ...]  # the pinned ids (ids with Version) of the Work's other files in the pool, best first
    siblings: tuple[str, ...]  # the ids of the Work's other Chunks in the pool, best first


@dataclass(frozen=True)
class Collapse:
    """One query's Collapsed ranking, with what stands behind each of its Chunks."""

    ranking: list[tuple[str, float]]  # at most k, one Chunk per Work
    merged: dict[str, Merged]  # by the ranking's Chunk ids
    works: int  # the Works in the pool, which is fewer than k when the pool ran short


class Collapsed:
    """A retriever's Collapsed ranking, over the manifest's Works."""

    def __init__(self, retriever: Retriever, chunks: Mapping[str, Chunk], manifest: Iterable[Mapping[str, str]], pool: int) -> None:
        self.retriever = retriever
        self.chunks = chunks
        self.pool = pool
        self._work: dict[str, str] = {}  # each Edition's Work, for the Editions that have one
        self._canonical: set[str] = set()  # the Canonical Editions' ids
        for row in manifest:
            if row["work_id"]:
                self._work[row["edition_id"]] = row["work_id"]
                if row["canonical"] == "yes":
                    self._canonical.add(row["edition_id"])

    @property
    def device(self) -> str:
        return self.retriever.device

    def save(self, directory: Path) -> None:
        self.retriever.save(directory)

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        return self.collapse(text, k).ranking

    def collapse(self, text: str, k: int) -> Collapse:
        members: dict[str, list[tuple[str, float]]] = {}  # each Work's Chunks in the pool, in raw order
        for chunk_id, score in self.retriever.query(text, max(self.pool, k)):
            members.setdefault(self.work_of(self.chunks[chunk_id]), []).append((chunk_id, score))
        ranking, merged = [], {}
        for work_id, ranked in list(members.items())[:k]:
            shown = min(ranked, key=lambda hit: self._tier(self.chunks[hit[0]]))  # min keeps the best-ranked on a tie
            pinned = self.chunks[shown[0]].pinned_id
            others = [chunk_id for chunk_id, _ in ranked if chunk_id != shown[0]]
            editions = dict.fromkeys(self.chunks[chunk_id].pinned_id for chunk_id in others if self.chunks[chunk_id].pinned_id != pinned)
            ranking.append(shown)
            merged[shown[0]] = Merged(work_id, tuple(editions), tuple(others))
        return Collapse(ranking, merged, len(members))

    def work_of(self, chunk: Chunk) -> str:
        return self._work.get(chunk.edition_id, f"edition:{chunk.edition_id}")

    def _tier(self, chunk: Chunk) -> int:
        latest = chunk.pinned_id == chunk.edition_id  # a preprint's Edition id names its latest Version (ADR 0015)
        return 0 if latest and chunk.edition_id in self._canonical else 1 if latest else 2
