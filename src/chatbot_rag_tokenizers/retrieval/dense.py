"""A dense retriever (ADRs 0042 and 0050): each Chunk's context header plus its text, embedded once, searched by exact dot product.

The vectors are L2-normalised float32, so the dot product is the cosine. A query is embedded with its
table's query instruction in front of it (bge-small's model card asks for one for retrieval); Chunks are
embedded without it. Every Chunk is scored, with no vector database or approximate search, and ties keep corpus order.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..files import write_atomically
from ..parsing.chunker import Chunk
from . import embedder
from .retriever import indexed_text

SEARCH = "exact dot product over every Chunk's float32 vector"
_VECTORS = "vectors.npy"
_CHUNK_IDS = "chunk_ids.json"


@dataclass(frozen=True)
class DenseConfig:
    table: str  # the table's name after "dense." in the retrieval config, e.g. "bge-small" (ADR 0050)
    model: str  # the Hugging Face repo of the embedding model
    revision: str  # the commit of that repo (a Hugging Face commit, not an arXiv Version)
    model_sha256: str  # of its weights file
    pooling: str  # a key of embedder.POOLINGS
    max_tokens: int  # a longer text is cut to its first max_tokens tokens
    query_instruction: str  # put in front of every query, never in front of a Chunk

    @property
    def name(self) -> str:
        return f"dense.{self.table}"

    @property
    def embedding_model(self) -> embedder.EmbeddingModel:
        return embedder.EmbeddingModel(self.model, self.revision, self.model_sha256, self.pooling, self.max_tokens)

    def describe(self) -> dict[str, Any]:
        # The table's name is not a setting: it is left out, so naming the table kept bge-small's key (ADR 0050).
        return {
            "model": self.model,
            "revision": self.revision,
            "model_sha256": self.model_sha256,
            "query_instruction": self.query_instruction,
            "pooling": embedder.POOLINGS[self.pooling],
            "max_tokens": self.max_tokens,
            "search": SEARCH,
        }

    @property
    def key(self) -> str:
        settings = json.dumps(self.describe(), sort_keys=True, ensure_ascii=False)
        return f"dense-{hashlib.sha256(settings.encode()).hexdigest()[:12]}"

    def build(self, chunks: Sequence[Chunk]) -> "Dense":
        model = embedder.load_embedder(self.embedding_model)
        return Dense(self, [chunk.chunk_id for chunk in chunks], model.embed([indexed_text(chunk) for chunk in chunks]), model)

    def load(self, directory: Path) -> "Dense":
        chunk_ids = json.loads((directory / _CHUNK_IDS).read_text(encoding="utf-8"))
        return Dense(self, chunk_ids, np.load(directory / _VECTORS), embedder.load_embedder(self.embedding_model))


class Dense:
    def __init__(self, config: DenseConfig, chunk_ids: list[str], vectors: np.ndarray, model: embedder.Embedder) -> None:
        self.config = config
        self.chunk_ids = chunk_ids
        self.vectors = vectors
        self._embedder = model

    @property
    def device(self) -> str:
        return self._embedder.device

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        partial = directory / (_VECTORS + ".partial")
        with partial.open("wb") as f:
            np.save(f, self.vectors)
        partial.replace(directory / _VECTORS)
        write_atomically(directory / _CHUNK_IDS, json.dumps(self.chunk_ids) + "\n")

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        [vector] = self._embedder.embed([self.config.query_instruction + text])
        scores = self.vectors @ vector
        top = np.argsort(-scores, kind="stable")[:k]
        return [(self.chunk_ids[position], float(scores[position])) for position in top]
