"""The retrieval config file: each retriever's settings (ADRs 0039 and 0042)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table

from .bm25 import BM25Config
from .dense import DenseConfig
from .retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")
COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class RetrievalConfig:
    bm25: BM25Config
    dense: DenseConfig

    @property
    def retrievers(self) -> dict[str, RetrieverConfig]:
        """Every configured retriever, by the name `--retriever` takes."""
        return {config.name: config for config in (self.bm25, self.dense)}


def load_retrieval_config(path: Path = DEFAULT_PATH) -> RetrievalConfig:
    raw = tomllib.loads(path.read_text())
    fields = read_table(raw, "bm25", {"k1": float, "b": float}, path)
    bm25 = BM25Config(**fields)
    if bm25.k1 < 0:
        raise ConfigError(f"[bm25] k1 {bm25.k1} must not be negative")
    if not 0 <= bm25.b <= 1:
        raise ConfigError(f"[bm25] b {bm25.b} is not between 0 and 1")
    dense = DenseConfig(**read_table(raw, "dense", {name: str for name in ("model", "revision", "model_sha256", "query_instruction")}, path))
    if not COMMIT.fullmatch(dense.revision):
        raise ConfigError(f"[dense] revision {dense.revision!r} is not a 40-hex commit")
    if not SHA256.fullmatch(dense.model_sha256):
        raise ConfigError(f"[dense] model_sha256 {dense.model_sha256!r} is not 64 hex digits")
    return RetrievalConfig(bm25=bm25, dense=dense)
