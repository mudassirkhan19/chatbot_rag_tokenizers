"""The index cache: a local, gitignored directory with one folder per chunking config and retriever (ADR 0039).

    <root>/<chunking key>/<retriever key>/index.json   the record: the retriever and its settings, the corpus
                                                       it was built over, its Chunk count, build time and device
    <root>/<chunking key>/<retriever key>/...          the retriever's own files, e.g. bm25.json

The chunking key hashes the chunking config and the retriever key hashes the retriever's settings, so a
change to either builds a new index beside the old one. The record names the corpus's files and a hash of their
Chunks too, so an index built before the parse report gained or lost files, or before the Chunks were rebuilt
differently (a TEI reader or Chunker change, ADR 0043), is rebuilt. The record is written last: an interrupted
build leaves no record, and the next run builds again.

A hybrid's folder holds only its record (ADR 0053). The record names its members' keys, their folders beside it,
and its build time and device are theirs. Building a hybrid builds any member that is missing first, and loading
it needs every member's index.
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..files import write_atomically
from .corpus import Corpus
from .hybrid import HybridConfig
from .retriever import Retriever, RetrieverConfig

_RECORD = "index.json"


class IndexMissing(RuntimeError):
    """No index of this retriever over this corpus is in the cache, worded for the person running it."""


@dataclass(frozen=True)
class Index:
    retriever: Retriever
    build_seconds: float
    build_device: str


def directory(root: Path, corpus: Corpus, config: RetrieverConfig) -> Path:
    return root / corpus.chunking_key / config.key


def build(root: Path, corpus: Corpus, configs: list[RetrieverConfig]) -> None:
    """Build each retriever over the corpus, unless the cache already holds that index, and a hybrid's members before it."""
    for config in _members_first(configs):
        folder = directory(root, corpus, config)
        if _record(folder, corpus) is not None:
            print(f"index: {config.name} is up to date in {folder}")
            continue
        extra: dict[str, Any] = {}
        if isinstance(config, HybridConfig):
            # Its members were built just before it: it embeds nothing, and takes their build time and device.
            members = [_built(root, corpus, member) for member in config.members]
            seconds = sum(member["build_seconds"] for member in members)
            device = "+".join(dict.fromkeys(member.get("device", "cpu") for member in members))
            extra["members"] = {member.name: member.key for member in config.members}
            folder.mkdir(parents=True, exist_ok=True)
        else:
            started = time.perf_counter()
            retriever = config.build(corpus.chunks)
            seconds = time.perf_counter() - started
            retriever.save(folder)
            device = retriever.device
        record = {
            "retriever": config.name,
            "settings": config.describe(),
            "chunking_key": corpus.chunking_key,
            "corpus": corpus.fingerprint,
            "files": len(corpus.files),
            "chunks": len(corpus.chunks),
            "build_seconds": round(seconds, 3),
            "device": device,
            **extra,
        }
        write_atomically(folder / _RECORD, json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"index: built {config.name} over {len(corpus.chunks)} Chunks from {len(corpus.files)} files in {seconds:.2f} s on {device}; in {folder}")


def load(root: Path, corpus: Corpus, config: RetrieverConfig) -> Index:
    for member in _members(config):
        _built(root, corpus, member)
    record = _built(root, corpus, config)
    folder = directory(root, corpus, config)
    # A BM25 index built before records named their device was built in plain Python, on the CPU.
    return Index(config.load(folder), record["build_seconds"], record.get("device", "cpu"))


def _built(root: Path, corpus: Corpus, config: RetrieverConfig) -> dict[str, Any]:
    """The record of the retriever's index over this corpus; IndexMissing when there is none."""
    record = _record(directory(root, corpus, config), corpus)
    if record is None:
        raise IndexMissing(f"no {config.name} index over the parsed Chunks is in {root}. Run `just index`, then try again.")
    return record


def _members(config: RetrieverConfig) -> tuple[RetrieverConfig, ...]:
    return config.members if isinstance(config, HybridConfig) else ()


def _members_first(configs: list[RetrieverConfig]) -> list[RetrieverConfig]:
    """The retrievers to build, each once, with a hybrid's members before it."""
    ordered = {needed.name: needed for config in configs for needed in [*_members(config), config]}
    return list(ordered.values())


def _record(folder: Path, corpus: Corpus) -> dict[str, Any] | None:
    """The index's record when it was built over this corpus, else None."""
    path = folder / _RECORD
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["corpus"] != corpus.fingerprint:
        print(f"index: {folder} was built over other files than the parse report lists", file=sys.stderr)
        return None
    return record
