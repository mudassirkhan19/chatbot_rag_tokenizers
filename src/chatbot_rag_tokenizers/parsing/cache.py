"""The parse cache: a local, gitignored directory with one folder per file sha256 (ADRs 0027 and 0030).

    <root>/<sha256>/<parser key>.tei.xml                       GROBID's raw TEI, kept as it came
    <root>/<sha256>/<parser key>.bibliography.jsonl            the file's references, one per line, in order (ADR 0028)
    <root>/<sha256>/<parser key>.<chunking key>.chunks.jsonl   the Chunks, one JSON object per line, in order
    <root>/<sha256>/<parser key>.<chunking key>.failure.json   or why the file failed the quality gate (ADR 0029)

The parser key names the pinned GROBID image, so a new image never reads an old parse. The chunking
key hashes the chunking config, so each config's Chunks are kept apart and a config change re-chunks
from the cached TEI. A record that depends on the config as well as the parse (Chunks, a failure)
goes under both keys, through `_chunking_path`.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .chunker import Chunk
from .quality import Failure, Reason
from .tei import Reference


@dataclass(frozen=True)
class RecordedFailure:
    failure: Failure
    sections: int  # the Sections GROBID found, for the report; 0 when GROBID failed


class ParseCache:
    def __init__(self, root: Path, parser_key: str, chunking_key: str) -> None:
        self.root = root
        self.parser_key = parser_key
        self.chunking_key = chunking_key

    def _parser_path(self, sha256: str, suffix: str) -> Path:
        """A record of the parse alone: file hash plus parser version."""
        return self.root / sha256 / f"{self.parser_key}{suffix}"

    def _chunking_path(self, sha256: str, suffix: str) -> Path:
        """A record of the parse under the chunking config: file hash, parser version and config hash."""
        return self.root / sha256 / f"{self.parser_key}.{self.chunking_key}{suffix}"

    def tei(self, sha256: str) -> str | None:
        path = self._parser_path(sha256, ".tei.xml")
        return path.read_text(encoding="utf-8") if path.exists() else None

    def put_tei(self, sha256: str, tei: str) -> None:
        _write(self._parser_path(sha256, ".tei.xml"), tei)

    def _chunks_path(self, sha256: str) -> Path:
        return self._chunking_path(sha256, ".chunks.jsonl")

    def _failure_path(self, sha256: str) -> Path:
        """Under the same key as the Chunks: a failure is the outcome the Chunks would have been."""
        return self._chunking_path(sha256, ".failure.json")

    def put_chunks(self, sha256: str, chunks: list[Chunk]) -> None:
        """Record a file's Chunks and drop any old failure record, which would otherwise be read first."""
        lines = [json.dumps(asdict(chunk), sort_keys=True, ensure_ascii=False) + "\n" for chunk in chunks]
        _write(self._chunks_path(sha256), "".join(lines))
        self._failure_path(sha256).unlink(missing_ok=True)

    def failure(self, sha256: str) -> RecordedFailure | None:
        """The recorded Failure of a file, or None when none is recorded."""
        path = self._failure_path(sha256)
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        return RecordedFailure(Failure(Reason(record["reason"]), record["detail"]), record["sections"])

    def put_failure(self, sha256: str, failure: Failure, sections: int) -> None:
        """Record a file's Failure, so no later run with the same key retries it, and drop any old Chunks."""
        record = {**asdict(failure), "sections": sections}
        _write(self._failure_path(sha256), json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        self._chunks_path(sha256).unlink(missing_ok=True)

    def put_bibliography(self, sha256: str, references: tuple[Reference, ...]) -> None:
        """The file's bibliography: it depends on the parse alone, so it sits beside the TEI."""
        lines = [json.dumps(asdict(reference), sort_keys=True, ensure_ascii=False) + "\n" for reference in references]
        _write(self._parser_path(sha256, ".bibliography.jsonl"), "".join(lines))


def _write(path: Path, text: str) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file in the cache.

    Always UTF-8 with "\\n" line ends, so the bytes don't depend on the machine's locale.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8", newline="\n")
    partial.replace(path)
