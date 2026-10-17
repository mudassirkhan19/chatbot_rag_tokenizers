"""The parse step: each input file to TEI (from the cache, or else from GROBID), then to Chunks and a report line."""

import sys
from pathlib import Path

from .cache import ParseCache
from .chunker import chunk_document
from .config import ParseConfig
from .grobid import GrobidClient, GrobidFailed
from .inputs import InputFile
from .quality import GROBID_ERROR, Failure, gate
from .report import FileResult, write_report
from .tei import UnreadableTei, read_tei
from .tokens import TokenCounter


class ParseErrors(RuntimeError):
    """Every file this run failed, worded for the person running it."""

    def __init__(self, failed: list[FileResult]) -> None:
        self.failed = failed
        count = "1 file" if len(failed) == 1 else f"{len(failed)} files"
        lines = [f"{count} failed. They have no Chunks; the parse report gives each one's reason."]
        lines += [f"  {result.pinned_id}: {result.failure}" for result in failed]
        super().__init__("\n".join(lines))


def parse(config: ParseConfig, files: list[InputFile], cache_dir: Path, report_path: Path, limit: int | None = None) -> None:
    """Parse each file in pinned-id order, the first ``limit`` of them when it is given.

    A file that fails the quality gate gets no Chunks and doesn't stop the run: this run's failures are
    raised together as ParseErrors once the report is written. An unreachable GROBID stops the run at once.
    """
    cache = ParseCache(cache_dir, config.grobid.parser_key, config.chunking.key)
    client = GrobidClient(config.grobid)
    counter = TokenCounter(config.chunking)
    results: list[FileResult] = []
    new_failures: list[FileResult] = []
    versions: set[str] = set()
    for file in sorted(files, key=lambda f: (f.identity.pinned_id, f.identity.sha256))[:limit]:
        pinned_id, sha256 = file.identity.pinned_id, file.identity.sha256
        if recorded := cache.failure(sha256):
            results.append(FileResult(pinned_id, sha256, recorded.sections, 0, recorded.failure))
            continue
        failure: Failure | None
        try:
            document = read_tei(_tei(cache, client, file))
        except GrobidFailed as error:
            failure, sections = error.failure, 0
        except UnreadableTei as error:
            failure, sections = Failure(GROBID_ERROR, f"unreadable TEI: {error}"), 0
        else:
            versions.add(document.grobid_version)
            failure, sections = gate(document, config.chunking), len(document.sections)
        if failure:
            print(f"{pinned_id}: failed: {failure}", file=sys.stderr)
            cache.put_failure(sha256, failure, sections)
            new_failures.append(FileResult(pinned_id, sha256, sections, 0, failure))
            results.append(new_failures[-1])
            continue
        chunks = chunk_document(document, file.identity, config.chunking.token_budget, counter.count)
        cache.put_chunks(sha256, chunks)
        results.append(FileResult(pinned_id, sha256, sections, len(chunks)))
        print(f"{pinned_id}: {sections} Sections, {len(chunks)} Chunks")
    write_report(report_path, config, versions, results)
    print(f"parse: {len(results)} files, {sum(r.chunks for r in results)} Chunks; report in {report_path}")
    if earlier := sum(1 for result in results if result.failure) - len(new_failures):
        count = "1 file" if earlier == 1 else f"{earlier} files"
        print(f"parse: {count} failed on an earlier run and were not retried; the parse report gives their reasons", file=sys.stderr)
    if new_failures:
        raise ParseErrors(new_failures)


def _tei(cache: ParseCache, client: GrobidClient, file: InputFile) -> str:
    """The file's TEI, from the cache or else from GROBID. Raises GrobidFailed when GROBID fails on it."""
    tei = cache.tei(file.identity.sha256)
    if tei is None:
        tei = client.process(file.pdf)
        cache.put_tei(file.identity.sha256, tei)
    return tei
