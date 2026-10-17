"""The parse cache: a local, gitignored directory with one folder per file sha256 (ADR 0025).

    <root>/<sha256>/<parser key>.tei.xml       GROBID's raw TEI, kept as it came
    <root>/<sha256>/<parser key>.chunks.jsonl  the Chunks, one JSON object per line, in order
    <root>/<sha256>/<parser key>.failure.json  or why the file failed the quality gate (ADR 0027)

The parser key names the pinned GROBID image, so a new image never reads an old parse.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .chunker import Chunk
from .quality import Failure


@dataclass(frozen=True)
class RecordedFailure:
    failure: Failure
    sections: int  # the Sections GROBID found, for the report; 0 when GROBID failed


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

    def _chunks_path(self, sha256: str) -> Path:
        return self._path(sha256, ".chunks.jsonl")

    def _failure_path(self, sha256: str) -> Path:
        """Beside the Chunks and under the same key: a failure is the outcome the Chunks would have been."""
        chunks = self._chunks_path(sha256)
        return chunks.with_name(chunks.name.removesuffix(".chunks.jsonl") + ".failure.json")

    def put_chunks(self, sha256: str, chunks: list[Chunk]) -> None:
        lines = [json.dumps(asdict(chunk), sort_keys=True, ensure_ascii=False) + "\n" for chunk in chunks]
        _write(self._chunks_path(sha256), "".join(lines))

    def failure(self, sha256: str) -> RecordedFailure | None:
        """The recorded Failure of a file, or None when none is recorded."""
        path = self._failure_path(sha256)
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        return RecordedFailure(Failure(record["reason"], record["detail"]), record["sections"])

    def put_failure(self, sha256: str, failure: Failure, sections: int) -> None:
        """Record a file's Failure, so no later run with the same key retries it, and drop any old Chunks."""
        record = {**asdict(failure), "sections": sections}
        _write(self._failure_path(sha256), json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        self._chunks_path(sha256).unlink(missing_ok=True)


def _write(path: Path, text: str) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file in the cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text)
    partial.replace(path)
