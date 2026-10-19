"""The retrieval config file: each retriever's settings (ADRs 0039, 0042 and 0050)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table
from chatbot_rag_tokenizers.parsing.config import SHA256

from .bm25 import BM25Config
from .dense import DenseConfig
from .embedder import POOLINGS
from .retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")
COMMIT = re.compile(r"[0-9a-f]{40}")
TABLE_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")  # the part of a retriever's name after "dense."
_DENSE_FIELDS = {"model": str, "revision": str, "model_sha256": str, "pooling": str, "max_tokens": int, "query_instruction": str}


@dataclass(frozen=True)
class RetrievalConfig:
    bm25: BM25Config
    dense: list[DenseConfig]  # one per [dense.<name>] table, in the file's order

    @property
    def retrievers(self) -> dict[str, RetrieverConfig]:
        """Every configured retriever, by the name `--retriever` takes."""
        configs: list[RetrieverConfig] = [self.bm25, *self.dense]
        return {config.name: config for config in configs}


def load_retrieval_config(path: Path = DEFAULT_PATH) -> RetrievalConfig:
    raw = tomllib.loads(path.read_text())
    fields = read_table(raw, "bm25", {"k1": float, "b": float}, path)
    bm25 = BM25Config(**fields)
    if bm25.k1 < 0:
        raise ConfigError(f"[bm25] k1 {bm25.k1} must not be negative")
    if not 0 <= bm25.b <= 1:
        raise ConfigError(f"[bm25] b {bm25.b} is not between 0 and 1")
    tables = raw.get("dense", {})
    if not isinstance(tables, dict) or not tables:
        raise ConfigError(f"{path} has no [dense.<name>] table")
    return RetrievalConfig(bm25=bm25, dense=[_load_dense_table(raw, table, path) for table in tables])


def _load_dense_table(raw: dict, table: str, path: Path) -> DenseConfig:
    name = f"dense.{table}"
    if not isinstance(raw["dense"][table], dict):
        raise ConfigError(f"[dense] {table} in {path} is not a table; give each dense model its own [dense.<name>] table")
    if not TABLE_NAME.fullmatch(table):
        raise ConfigError(f"[{name}] in {path}: a dense table's name is lower-case letters, digits and dashes")
    dense = DenseConfig(table=table, **read_table(raw, name, _DENSE_FIELDS, path))
    if not COMMIT.fullmatch(dense.revision):
        raise ConfigError(f"[{name}] revision {dense.revision!r} is not a 40-hex commit")
    if not SHA256.fullmatch(dense.model_sha256):
        raise ConfigError(f"[{name}] model_sha256 {dense.model_sha256!r} is not 64 hex digits")
    if dense.pooling not in POOLINGS:
        raise ConfigError(f"[{name}] pooling {dense.pooling!r} is not one of {', '.join(POOLINGS)}")
    if dense.max_tokens < 1:
        raise ConfigError(f"[{name}] max_tokens {dense.max_tokens} must be at least 1")
    return dense
