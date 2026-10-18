"""The corpus a retriever is built over: the Chunks of every file the parse report lists as parsed (ADR 0039).

The parse report, not the parse cache, decides which files count: the cache also keeps the Chunks of files
an earlier run parsed that are no longer in the corpus, such as withdrawn preprints (ADR 0038).
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from functools import cached_property
from pathlib import Path

from ..parsing.cache import ParseCache
from ..parsing.chunker import Chunk
from ..parsing.config import ChunkingConfig, ParseConfig
from ..parsing.report import UnreadableReport, read_report


class CorpusError(RuntimeError):
    """The Chunks can't be read as the parse config and report describe them, worded for the person running it."""


@dataclass(frozen=True)
class Corpus:
    parser_key: str  # the GROBID image the files were parsed with
    chunking: ChunkingConfig
    parsed: tuple[tuple[str, str], ...]  # the (pinned id, sha256) of each parsed file, in the report's order
    chunks: tuple[Chunk, ...]  # every file's Chunks, file by file, each file's in order
    from_record: bool  # the report was parsed from the full-text record, not `--files`

    @property
    def files(self) -> tuple[str, ...]:
        """The sha256 of each parsed file. Two pinned ids can hold the same bytes, and then one file's Chunks."""
        return tuple(sha256 for _, sha256 in self.parsed)

    @property
    def chunking_key(self) -> str:
        return self.chunking.key

    @cached_property
    def fingerprint(self) -> str:
        """Names the parser, the set of files and their Chunks, so an index built over another parse is never taken
        for this one. The Chunks count because a change to the TEI reader or the Chunker rebuilds them under the
        same cache keys (ADR 0030)."""
        digest = hashlib.sha256("\n".join([self.parser_key, *sorted(self.files)]).encode())
        for chunk in self.chunks:
            digest.update(json.dumps(asdict(chunk), sort_keys=True, ensure_ascii=False).encode())
        return digest.hexdigest()


def load_corpus(config: ParseConfig, cache_root: Path, report_path: Path) -> Corpus:
    rerun = "Run `just parse` (with the same --files, if the report came from a --files run), then try again."
    if not report_path.exists():
        raise CorpusError(f"there is no parse report at {report_path}, so there are no Chunks to index. {rerun}")
    try:
        run = read_report(report_path)
    except UnreadableReport as error:
        raise CorpusError(str(error)) from error
    chunking = {name: str(value) for name, value in config.chunking.describe().items()}
    if run.image != config.grobid.reference or run.chunking != chunking:
        raise CorpusError(f"the parse report {report_path} was written with another GROBID image or chunking config than {_config_name(config)}. {rerun}")
    if not run.parsed:
        raise CorpusError(f"the parse report {report_path} lists no parsed file, so there are no Chunks to index. {rerun}")
    cache = ParseCache(cache_root, config.grobid.parser_key, config.chunking.key)
    chunks: list[Chunk] = []
    missing, other_config = [], []
    for pinned_id, sha256 in run.parsed:
        if (found := cache.chunks(sha256)) is not None:
            chunks += found
        elif keys := cache.chunking_keys(sha256):
            other_config.append(f"{pinned_id} (Chunks only under {', '.join(keys)})")
        else:
            missing.append(pinned_id)
    if missing and len(missing) == len(run.parsed):
        raise CorpusError(f"the parse cache {cache_root} holds no Chunks for the files in {report_path}: it is empty or another cache. {rerun}")
    if other_config:
        raise CorpusError(
            f"the parse cache {cache_root} was built with another chunking config than {config.chunking.key} for"
            f" {_count(len(other_config))}: {', '.join(other_config)}. {rerun}"
        )
    if missing:
        raise CorpusError(f"the parse cache {cache_root} has no Chunks for {_count(len(missing))} in {report_path}: {', '.join(missing)}. {rerun}")
    return Corpus(config.grobid.parser_key, config.chunking, tuple(run.parsed), tuple(chunks), run.from_record)


def _config_name(config: ParseConfig) -> str:
    return f"{config.grobid.parser_key} with {config.chunking.key}"


def _count(files: int) -> str:
    return "1 file" if files == 1 else f"{files} files"
