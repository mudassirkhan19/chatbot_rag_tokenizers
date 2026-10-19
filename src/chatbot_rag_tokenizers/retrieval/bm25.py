"""BM25 over each Chunk's context header plus its text (ADR 0039).

Tokens are lower-cased runs of letters and digits, numbers kept (a decimal whole), with no stemming and no stop words.
A term's weight is the Lucene form of BM25's idf, ln(1 + (N - df + 0.5) / (df + 0.5)), so it is never
negative, times its saturated count, tf (k1 + 1) / (tf + k1 (1 - b + b dl / avgdl)). Each distinct query
term counts once. A Chunk that shares no term with the query isn't ranked, and ties keep corpus order.
"""

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..files import write_atomically
from ..parsing.chunker import Chunk
from .retriever import indexed_text

# Names how BM25 cuts text into tokens. It is part of the BM25 key, so change it with the tokenisation.
TOKENS = "lower-cased letter and digit runs, decimals whole, no stemming, no stop words"
# A number with a decimal point or thousands comma ("0.1", "1,000") is one token; any other run of letters
# and digits is one too ("50k", "gpt2"); everything else separates tokens.
_TOKEN = re.compile(r"\d+(?:[.,]\d+)+|[^\W_]+")
_FILE = "bm25.json"


def tokenise(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True)
class BM25Config:
    k1: float
    b: float

    @property
    def name(self) -> str:
        return "bm25"

    def describe(self) -> dict[str, Any]:
        return {**asdict(self), "tokens": TOKENS}

    @property
    def key(self) -> str:
        settings = json.dumps(self.describe(), sort_keys=True, ensure_ascii=False)
        return f"bm25-{hashlib.sha256(settings.encode()).hexdigest()[:12]}"

    def build(self, chunks: Sequence[Chunk]) -> "BM25":
        lengths = []
        postings: dict[str, list[tuple[int, int]]] = {}
        for position, chunk in enumerate(chunks):
            counts = Counter(tokenise(indexed_text(chunk)))
            lengths.append(sum(counts.values()))
            for term, count in counts.items():
                postings.setdefault(term, []).append((position, count))
        return BM25(self, [chunk.chunk_id for chunk in chunks], lengths, postings)

    def load(self, directory: Path) -> "BM25":
        stored = json.loads((directory / _FILE).read_text(encoding="utf-8"))
        postings = {term: [(position, count) for position, count in entries] for term, entries in stored["postings"].items()}
        return BM25(self, stored["chunk_ids"], stored["lengths"], postings)


class BM25:
    def __init__(self, config: BM25Config, chunk_ids: list[str], lengths: list[int], postings: dict[str, list[tuple[int, int]]]) -> None:
        self.config = config
        self.chunk_ids = chunk_ids
        self.lengths = lengths
        self.postings = postings
        self.average_length = sum(lengths) / len(lengths) if lengths else 0.0

    @property
    def device(self) -> str:
        return "cpu"  # plain Python

    @property
    def parameters(self) -> None:
        return None  # no model

    @property
    def dimension(self) -> None:
        return None  # no vectors

    def save(self, directory: Path) -> None:
        stored = {"chunk_ids": self.chunk_ids, "lengths": self.lengths, "postings": self.postings}
        write_atomically(directory / _FILE, json.dumps(stored, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        k1, b = self.config.k1, self.config.b
        documents = len(self.chunk_ids)
        scores: dict[int, float] = {}
        # Terms in query order, so the sums are added in the same order on every run.
        for term in dict.fromkeys(tokenise(text)):
            entries = self.postings.get(term, [])
            if not entries:
                continue
            idf = math.log(1 + (documents - len(entries) + 0.5) / (len(entries) + 0.5))
            for position, count in entries:
                norm = k1 * (1 - b + b * self.lengths[position] / self.average_length)
                scores[position] = scores.get(position, 0.0) + idf * count * (k1 + 1) / (count + norm)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
        return [(self.chunk_ids[position], score) for position, score in ranked]
