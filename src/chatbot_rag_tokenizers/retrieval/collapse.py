"""The Collapsed ranking (ADRs 0053 and 0057): each Chunk once, however many files of its Work hold a copy.

The wrapper asks the retriever it wraps for a pool of Chunks and merges copies: Chunks of one Work, through the
manifest's work_id, from different files, at the same place in the same Section (the same Section path, and the
same count of Chunks before it in that Section). That is what a paper's arXiv Versions and its preprint and venue
Editions repeat. A Chunk whose Edition has no work_id is its Edition's own Work, so nothing the collapse can't
place is dropped. A Work's other Chunks are other text and keep their own slots, as the raw ranking gave them.

Each slot takes the place of its best-ranked copy, and shows the copy from the best file, best first by tier, then
by rank:

    1. the Canonical Edition's own file (for a preprint, its latest Version)
    2. any Edition's latest file
    3. any file, such as a v1

so a stale v1 stands for a passage only when no later copy of it was retrieved. Surveys are not demoted. No
retriever's code or index changes, and `query` keeps the raw `(chunk_id, score)` shape; `collapse` also gives,
by Chunk id, the Work, the merged Editions and the merged copies.
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
    editions: tuple[str, ...]  # the pinned ids (ids with Version) of the files of the copies merged into it, best first
    copies: tuple[str, ...]  # the ids of the copies merged into it, best first


@dataclass(frozen=True)
class Collapse:
    """One query's Collapsed ranking, with what stands behind each of its Chunks."""

    ranking: list[tuple[str, float]]  # at most k, each with its copies merged
    merged: dict[str, Merged]  # by the ranking's Chunk ids
    distinct: int  # the pool's Chunks once copies are merged, which is fewer than k when the pool ran short


class Collapsed:
    """A retriever's Collapsed ranking, over the manifest's Works and the Chunks' places in their Sections."""

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
        self._place: dict[str, int] = {}  # each Chunk's count of Chunks before it in its Section, in its file
        before: dict[tuple[str, tuple[str, ...]], int] = {}
        for chunk in chunks.values():
            section = (chunk.file_sha256, chunk.section_path)
            self._place[chunk.chunk_id] = before.get(section, 0)
            before[section] = self._place[chunk.chunk_id] + 1

    @property
    def device(self) -> str:
        return self.retriever.device

    def save(self, directory: Path) -> None:
        self.retriever.save(directory)

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        return self.collapse(text, k).ranking

    def collapse(self, text: str, k: int) -> Collapse:
        slots: dict[tuple[str, tuple[str, ...], int], list[tuple[str, float]]] = {}  # each passage's copies, in raw order
        for chunk_id, score in self.retriever.query(text, max(self.pool, k)):
            chunk = self.chunks[chunk_id]
            slots.setdefault((self.work_of(chunk), chunk.section_path, self._place[chunk_id]), []).append((chunk_id, score))
        ranking, merged = [], {}
        for (work_id, _, _), copies in list(slots.items())[:k]:
            shown = min(copies, key=lambda hit: self._tier(self.chunks[hit[0]]))  # min keeps the best-ranked on a tie
            others = [chunk_id for chunk_id, _ in copies if chunk_id != shown[0]]
            ranking.append(shown)
            merged[shown[0]] = Merged(work_id, tuple(dict.fromkeys(self.chunks[c].pinned_id for c in others)), tuple(others))
        return Collapse(ranking, merged, len(slots))

    def work_of(self, chunk: Chunk) -> str:
        return self._work.get(chunk.edition_id, f"edition:{chunk.edition_id}")

    def _tier(self, chunk: Chunk) -> int:
        latest = chunk.pinned_id == chunk.edition_id  # a preprint's Edition id names its latest Version (ADR 0015)
        return 0 if latest and chunk.edition_id in self._canonical else 1 if latest else 2
