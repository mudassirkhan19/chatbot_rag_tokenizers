"""The retrieval config file: each retriever's settings (ADRs 0039, 0042, 0050 and 0058), the Collapsed ranking's pool and overlap (ADRs 0053 and 0073)
and the eval report's Comparison (ADR 0061)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table
from chatbot_rag_tokenizers.parsing.config import SHA256

from .bm25 import BM25Config
from .dense import DenseConfig
from .embedder import POOLINGS
from .hybrid import HybridConfig
from .retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")
COMMIT = re.compile(r"[0-9a-f]{40}")
TABLE_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")  # the part of a retriever's name after "dense."
HYBRID_NAME = re.compile(r"[a-z0-9][a-z0-9+-]*")  # after "hybrid.", e.g. "bm25+bge-small"
_DENSE_FIELDS = {"model": str, "revision": str, "model_sha256": str, "pooling": str, "max_tokens": int, "query_instruction": str}


@dataclass(frozen=True)
class ComparisonConfig:
    baseline: str  # the retriever every other is compared with, by its `--retriever` name
    resamples: int  # draws of the questions for each bootstrap interval
    seed: int  # of the bootstrap's generator, so two runs draw the same resamples


@dataclass(frozen=True)
class RetrievalConfig:
    bm25: BM25Config
    dense: list[DenseConfig]  # one per [dense.<name>] table, in the file's order
    hybrid: list[HybridConfig]  # one per [hybrid.<name>] table, in the file's order
    collapse_pool: int  # the raw Chunks the Collapsed ranking merges copies in
    collapse_overlap: float  # the share of word 5-grams two Chunks of a Work share to be copies (ADR 0073)
    comparison: ComparisonConfig  # how the eval report compares the retrievers (ADR 0061)

    @property
    def retrievers(self) -> dict[str, RetrieverConfig]:
        """Every configured retriever, by the name `--retriever` takes."""
        configs: list[RetrieverConfig] = [self.bm25, *self.dense, *self.hybrid]
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
    collapse = read_table(raw, "collapse", {"pool": int, "overlap": float}, path)
    pool, overlap = collapse["pool"], collapse["overlap"]
    if pool < 1:
        raise ConfigError(f"[collapse] pool {pool} must be at least 1")
    if not 0 < overlap <= 1:
        raise ConfigError(f"[collapse] overlap {overlap} must be above 0 and at most 1")
    dense = [_load_dense_table(raw, table, path) for table in tables]
    hybrid = [_load_hybrid_table(raw, table, path, bm25, dense) for table in raw.get("hybrid", {})]
    comparison = ComparisonConfig(**read_table(raw, "comparison", {"baseline": str, "resamples": int, "seed": int}, path))
    configured = [bm25.name, *(config.name for config in dense), *(config.name for config in hybrid)]
    if comparison.baseline not in configured:
        raise ConfigError(f"[comparison] baseline {comparison.baseline!r} is not a retriever in {path}; it configures {', '.join(configured)}")
    if comparison.resamples < 1:
        raise ConfigError(f"[comparison] resamples {comparison.resamples} must be at least 1")
    return RetrievalConfig(bm25=bm25, dense=dense, hybrid=hybrid, collapse_pool=pool, collapse_overlap=overlap, comparison=comparison)


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


def _load_hybrid_table(raw: dict, table: str, path: Path, bm25: BM25Config, dense: list[DenseConfig]) -> HybridConfig:
    name = f"hybrid.{table}"
    if not HYBRID_NAME.fullmatch(table):
        raise ConfigError(f"[{name}] in {path}: a hybrid table's name is lower-case letters, digits, dashes and pluses")
    fields = read_table(raw, name, {"members": list, "k": int, "pool": int}, path)
    fusable: dict[str, RetrieverConfig] = {bm25.name: bm25, **{config.name: config for config in dense}}
    configured = [bm25.name, *(config.name for config in dense), *(f"hybrid.{other}" for other in raw["hybrid"])]
    for member in fields["members"]:
        if member not in configured:
            raise ConfigError(f"[{name}] member {member!r} is not a retriever in {path}; it configures {', '.join(configured)}")
        if member not in fusable:
            raise ConfigError(f"[{name}] member {member!r} is not bm25 or a dense table")
    members = tuple(fusable[member] for member in fields["members"])
    if len(members) != 2 or sum(isinstance(member, BM25Config) for member in members) != 1:
        raise ConfigError(f"[{name}] fuses bm25 with one dense table, not {' and '.join(fields['members'])}")
    for field in ("k", "pool"):
        if fields[field] < 1:
            raise ConfigError(f"[{name}] {field} {fields[field]} must be at least 1")
    return HybridConfig(table=table, members=members, k=fields["k"], pool=fields["pool"])
