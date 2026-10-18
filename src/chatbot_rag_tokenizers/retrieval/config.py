"""The retrieval config file: each retriever's settings (ADR 0039)."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table

from .bm25 import BM25Config
from .retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")


@dataclass(frozen=True)
class RetrievalConfig:
    bm25: BM25Config

    @property
    def retrievers(self) -> dict[str, RetrieverConfig]:
        """Every configured retriever, by the name `--retriever` takes."""
        return {self.bm25.name: self.bm25}


def load_retrieval_config(path: Path = DEFAULT_PATH) -> RetrievalConfig:
    raw = tomllib.loads(path.read_text())
    fields = read_table(raw, "bm25", {"k1": float, "b": float}, path)
    bm25 = BM25Config(**fields)
    if bm25.k1 < 0:
        raise ConfigError(f"[bm25] k1 {bm25.k1} must not be negative")
    if not 0 <= bm25.b <= 1:
        raise ConfigError(f"[bm25] b {bm25.b} is not between 0 and 1")
    return RetrievalConfig(bm25=bm25)
