"""The parse step: each input file to TEI (from the cache, or else from GROBID), then to Chunks and a report line."""

from pathlib import Path

from .cache import ParseCache
from .chunker import chunk_document
from .config import ParseConfig
from .grobid import GrobidClient
from .inputs import InputFile
from .report import FileResult, write_report
from .tei import read_tei
from .tokens import TokenCounter


def parse(config: ParseConfig, files: list[InputFile], cache_dir: Path, report_path: Path) -> None:
    cache = ParseCache(cache_dir, config.grobid.parser_key, config.chunking.key)
    client = GrobidClient(config.grobid)
    counter = TokenCounter(config.chunking)
    results = []
    versions = set()
    for file in sorted(files, key=lambda f: (f.identity.pinned_id, f.identity.sha256)):
        sha256 = file.identity.sha256
        tei = cache.tei(sha256)
        if tei is None:
            tei = client.process(file.pdf)
            cache.put_tei(sha256, tei)
        document = read_tei(tei)
        chunks = chunk_document(document, file.identity, config.chunking.token_budget, counter.count)
        cache.put_chunks(sha256, chunks)
        versions.add(document.grobid_version)
        results.append(FileResult(file.identity.pinned_id, sha256, "parsed", len(document.sections), len(chunks)))
        print(f"{file.identity.pinned_id}: {len(document.sections)} Sections, {len(chunks)} Chunks")
    write_report(report_path, config, versions, results)
    print(f"parse: {len(results)} files, {sum(r.chunks for r in results)} Chunks; report in {report_path}")
