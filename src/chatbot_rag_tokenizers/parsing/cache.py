"""The parse cache: a local, gitignored directory with one folder per file sha256 (ADR 0025).

    <root>/<sha256>/<parser key>.tei.xml       GROBID's raw TEI, kept as it came
    <root>/<sha256>/<parser key>.chunks.jsonl  the Chunks, one JSON object per line, in order
    <root>/<sha256>/<parser key>.bibliography.jsonl  the file's references, one per line, in order (ADR 0026)

The parser key names the pinned GROBID image, so a new image never reads an old parse.
"""

import json
from dataclasses import asdict
from pathlib import Path

from .chunker import Chunk
from .tei import Reference


class ParseCache:
    def __init__(self, root: Path, parser_key: str) -> None:
        self.root = root
        self.parser_key = parser_key

    def _path(self, sha256: str, suffix: str) -> Path:
        return self.root / sha256 / f"{self.parser_key}{suffix}"

    def tei(self, sha256: str) -> str | None:
        path = self._path(sha256, ".tei.xml")
        return path.read_text() if path.exists() else None

    def put_tei(self, sha256: str, tei: str) -> None:
        _write(self._path(sha256, ".tei.xml"), tei)

    def put_chunks(self, sha256: str, chunks: list[Chunk]) -> None:
        lines = [json.dumps(asdict(chunk), sort_keys=True, ensure_ascii=False) + "\n" for chunk in chunks]
        _write(self._path(sha256, ".chunks.jsonl"), "".join(lines))

    def put_bibliography(self, sha256: str, references: tuple[Reference, ...]) -> None:
        lines = [json.dumps(asdict(reference), sort_keys=True, ensure_ascii=False) + "\n" for reference in references]
        _write(self._path(sha256, ".bibliography.jsonl"), "".join(lines))


def _write(path: Path, text: str) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file in the cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text)
    partial.replace(path)
