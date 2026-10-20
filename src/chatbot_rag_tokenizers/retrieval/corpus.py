"""The corpus a retriever is built over: the Chunks of every file the parse report lists as parsed (ADR 0039).

The parse report, not the parse cache, decides which files count: the cache also keeps the Chunks of files
an earlier run parsed that are no longer in the corpus, such as withdrawn preprints (ADR 0038). It decides what
they cite too: one file pinned under two ids has one set of cached Chunks, stamped with the id of whichever
parsed it last, so each report row's Chunks are restamped with its pinned id and that id's Edition (ADR 0066).
"""

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from ..parsing.cache import ParseCache
from ..parsing.chunker import Chunk
from ..parsing.config import ChunkingConfig, ParseConfig
from ..parsing.inputs import editions_by_name, editions_in_manifest
from ..parsing.report import UnreadableReport, read_report


class CorpusError(RuntimeError):
    """The Chunks can't be read as the parse config and report describe them, worded for the person running it."""


@dataclass(frozen=True)
class Corpus:
    parser_key: str  # the GROBID image the files were parsed with
    chunking: ChunkingConfig
    parsed: tuple[tuple[str, str], ...]  # the (pinned id, sha256) of each parsed file, in the report's order
    chunks: tuple[Chunk, ...]  # every file's Chunks, file by file, each file's in order, citing the report's ids
    from_record: bool  # the report was parsed from the full-text record, not `--files`
    # Names the parser, the set of files and their Chunks as the cache holds them, so an index built over another
    # parse is never taken for this one. The Chunks count because a change to the TEI reader or the Chunker rebuilds
    # them under the same cache keys (ADR 0030). The restamped ids don't: an index holds no Edition id (ADR 0066).
    fingerprint: str

    @property
    def files(self) -> tuple[str, ...]:
        """The sha256 of each parsed file. Two pinned ids can hold the same bytes, and then one file's Chunks."""
        return tuple(sha256 for _, sha256 in self.parsed)

    @property
    def chunking_key(self) -> str:
        return self.chunking.key


def load_corpus(config: ParseConfig, cache_root: Path, report_path: Path, manifest_path: Path) -> Corpus:
    """The corpus the parse report lists. A report parsed from the full-text record takes each pinned id's Edition
    from the manifest, as `parse` did; one from `--files` takes it from the pinned ids, as `parse --files` did."""
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
    if run.from_record and not manifest_path.exists():
        raise CorpusError(
            f"the parse report {report_path} was parsed from the full-text record, so the manifest names its files' Editions,"
            f" and there is no manifest at {manifest_path}. Pass the manifest it was parsed with (--manifest)."
        )
    editions = editions_in_manifest(manifest_path) if run.from_record else editions_by_name([pinned_id for pinned_id, _ in run.parsed])
    if unknown := [pinned_id for pinned_id, _ in run.parsed if pinned_id not in editions]:
        raise CorpusError(
            f"the manifest {manifest_path} includes no Edition pinned to {_count(len(unknown))} in {report_path}: {', '.join(unknown)}. {rerun}"
        )
    cache = ParseCache(cache_root, config.grobid.parser_key, config.chunking.key)
    cached: list[Chunk] = []
    chunks: list[Chunk] = []
    missing, other_config = [], []
    for pinned_id, sha256 in run.parsed:
        if (found := cache.chunks(sha256)) is not None:
            cached += found
            edition_id, version = editions[pinned_id]
            chunks += [replace(chunk, edition_id=edition_id, pinned_id=pinned_id, version=version) for chunk in found]
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
    fingerprint = _fingerprint(config.grobid.parser_key, [sha256 for _, sha256 in run.parsed], cached)
    return Corpus(config.grobid.parser_key, config.chunking, tuple(run.parsed), tuple(chunks), run.from_record, fingerprint)


def _fingerprint(parser_key: str, files: list[str], chunks: list[Chunk]) -> str:
    digest = hashlib.sha256("\n".join([parser_key, *sorted(files)]).encode())
    for chunk in chunks:
        digest.update(json.dumps(asdict(chunk), sort_keys=True, ensure_ascii=False).encode())
    return digest.hexdigest()


def _config_name(config: ParseConfig) -> str:
    return f"{config.grobid.parser_key} with {config.chunking.key}"


def _count(files: int) -> str:
    return "1 file" if files == 1 else f"{files} files"
