"""The parse report writer: the committed Markdown summary of a parse run (ADR 0025).

It names the parser and the chunking config, gives one line per file and the totals. Nothing in it
depends on the time or the machine, so the same inputs give the same report.
"""

from dataclasses import dataclass
from pathlib import Path

from .config import ParseConfig


@dataclass(frozen=True)
class FileResult:
    """One file's line in the report."""

    pinned_id: str
    sha256: str
    status: str  # "parsed"
    sections: int
    chunks: int
    tables: int  # table Chunks (ADR 0026)
    captions: int  # figure caption Chunks


def write_report(path: Path, config: ParseConfig, grobid_versions: set[str], results: list[FileResult]) -> None:
    grobid = config.grobid
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
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
