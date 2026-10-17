"""The parse report writer: the committed Markdown summary of a parse run (ADR 0027).

It names the parser and the chunking config, gives one line per file and the totals. Nothing in it
depends on the time or the machine, so the same inputs give the same report.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import ParseConfig
from .quality import Failure


@dataclass(frozen=True)
class FileResult:
    """One file's line in the report."""

    pinned_id: str
    sha256: str
    sections: int
    chunks: int
    failure: Failure | None = None  # why the file failed the quality gate; None when it was parsed
    tables: int = 0  # table Chunks (ADR 0028)
    captions: int = 0  # figure caption Chunks

    @property
    def status(self) -> str:
        return f"failed: {self.failure}" if self.failure else "parsed"


def write_report(path: Path, config: ParseConfig, grobid_versions: set[str], results: list[FileResult]) -> None:
    grobid = config.grobid
    failures = [r.failure for r in results if r.failure]
    lines = [
        "# Parse report",
        "",
        "Written by `parse`. The Chunks themselves are in the local parse cache, which is not committed.",
        "",
        "## Parser",
        "",
        f"- Image: `{grobid.reference}` (tag `{grobid.tag}`)",
        f"- GROBID version: {', '.join(sorted(grobid_versions)) or 'none (no file parsed)'}",
        "",
        "## Chunking config",
        "",
        *[f"- {name}: `{value}`" for name, value in config.chunking.describe().items()],
        "",
        "## Quality gate",
        "",
        f"A file fails when GROBID errors or times out on it, when it has fewer than {config.chunking.min_sections}"
        f" Sections (the abstract counts as one), or when its Sections hold fewer than"
        f" {config.chunking.min_body_characters} characters of text. A failed file gets no Chunks.",
        "",
        "## Files",
        "",
        "| Pinned id | sha256 | Status | Sections | Chunks | Tables | Captions |",
        "|---|---|---|---:|---:|---:|---:|",
        *[
            f"| {r.pinned_id} | `{r.sha256}` | {r.status} | {r.sections} | {r.chunks} | {r.tables} | {r.captions} |"
            for r in results
        ],
        "",
        "## Totals",
        "",
        f"- Files: {len(results)}",
        f"- Sections: {sum(r.sections for r in results)}",
        f"- Chunks: {sum(r.chunks for r in results)}",
        f"- Table Chunks: {sum(r.tables for r in results)}",
        f"- Caption Chunks: {sum(r.captions for r in results)}",
        f"- Parsed: {sum(1 for r in results if not r.failure)}",
        f"- Failed: {len(failures)}",
        "",
        "## Failures by reason",
        "",
        *([f"- {reason}: {count}" for reason, count in sorted(Counter(f.reason for f in failures).items())] or ["- none"]),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")  # the same bytes on every machine
