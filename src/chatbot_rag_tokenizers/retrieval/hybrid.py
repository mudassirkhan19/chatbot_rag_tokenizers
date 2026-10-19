"""A hybrid retriever (ADR 0055): BM25 and one dense table, fused by reciprocal rank fusion.

A query takes each member's top `pool` Chunks and scores each Chunk by the sum of 1 / (k + rank) over the
members that ranked it, rank counting from 1, then ranks by that sum. A tie goes to the Chunk the member listed
first ranks higher, then to the one the next member ranks higher; a Chunk a member didn't rank comes after
every Chunk it did. With two members that settles every tie, so corpus order is never needed.

A hybrid stores no vectors of its own. Its index sits beside its members' in the index cache, and its record
names their keys (index.py), so loading it loads them.
"""

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..parsing.chunker import Chunk
from .retriever import Retriever, RetrieverConfig

FUSION = "reciprocal rank fusion: the sum of 1 / (k + rank) over the members, ties to the member listed first"


@dataclass(frozen=True)
class HybridConfig:
    table: str  # the table's name after "hybrid." in the retrieval config, e.g. "bm25+bge-small"
    members: tuple[RetrieverConfig, ...]  # BM25 and one dense table, in the order the table lists them
    k: int  # the RRF constant: a larger k flattens the difference between ranks
    pool: int  # how many Chunks each member ranks for a query

    @property
    def name(self) -> str:
        return f"hybrid.{self.table}"

    def describe(self) -> dict[str, Any]:
        # Each member's key names its settings, so a change to a member gives the hybrid a new key too.
        return {
            "members": ", ".join(f"{member.name} ({member.key})" for member in self.members),
            "k": self.k,
            "pool": self.pool,
            "fusion": FUSION,
        }

    @property
    def key(self) -> str:
        settings = json.dumps(self.describe(), sort_keys=True, ensure_ascii=False)
        return f"hybrid-{hashlib.sha256(settings.encode()).hexdigest()[:12]}"

    def build(self, chunks: Sequence[Chunk]) -> "Hybrid":
        """Builds every member over the Chunks. `index` doesn't call this: it reuses the members' cached indexes."""
        return Hybrid(self, [member.build(chunks) for member in self.members])

    def load(self, directory: Path) -> "Hybrid":
        """Loads the members from their folders beside the hybrid's, in the same chunking key's folder."""
        return Hybrid(self, [member.load(directory.parent / member.key) for member in self.members])


class Hybrid:
    def __init__(self, config: HybridConfig, members: list[Retriever]) -> None:
        self.config = config
        self.members = members

    @property
    def device(self) -> str:
        """The members' devices, e.g. "cpu+mps", or one when they agree."""
        return "+".join(dict.fromkeys(member.device for member in self.members))

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)  # no files of its own: the record is all there is

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        rankings = [[chunk_id for chunk_id, _ in member.query(text, self.config.pool)] for member in self.members]
        ranks: dict[str, list[float]] = {}
        for position, ranking in enumerate(rankings):
            for rank, chunk_id in enumerate(ranking, start=1):
                ranks.setdefault(chunk_id, [math.inf] * len(rankings))[position] = rank
        scores = {chunk_id: sum(1 / (self.config.k + rank) for rank in held if rank != math.inf) for chunk_id, held in ranks.items()}
        ranked = sorted(ranks, key=lambda chunk_id: (-scores[chunk_id], *ranks[chunk_id]))[:k]
        return [(chunk_id, scores[chunk_id]) for chunk_id in ranked]
