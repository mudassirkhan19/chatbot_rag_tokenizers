"""The parse report writer: the committed Markdown summary of a parse run (ADR 0027).

It names the parser and the chunking config, gives one line per file and the totals. Nothing in it
depends on the time or the machine, so the same inputs give the same report. `read_report` reads back the
parser, the chunking config and the files, which is how `index` knows which Chunks make up the corpus.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .chunker import Chunk
from .config import ParseConfig
from .quality import Failure

# A text Chunk is counted as mostly numeric when more than this share of its words are numbers. Most such
# Chunks hold the cells of a table GROBID missed; they are kept, and only counted (ADR 0035).
NUMERIC_SHARE = 0.35
# A word that is a number, apart from the punctuation around it, with an optional sign and unit letter:
# "31.78", "(+2.8)", "4.7%" and "50k" are; "1.2e21" isn't, and "500 000" is two.
_NUMBER = re.compile(r"\W*[-+−]?\d[\d.,]*[kKMB×x]?\W*")


def is_mostly_numeric(chunk: Chunk) -> bool:
    """A text Chunk, never a table or caption, in which more than NUMERIC_SHARE of the words are numbers."""
    words = chunk.text.split() if chunk.kind == "text" else []
    return bool(words) and sum(1 for word in words if _NUMBER.fullmatch(word)) > NUMERIC_SHARE * len(words)


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
    numeric: int = 0  # text Chunks that are mostly numbers (ADR 0035)

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
        f"Numeric counts the text Chunks in which more than {NUMERIC_SHARE:.0%} of their words are numbers. Most hold"
        " the cells of a table GROBID missed. They are kept as text Chunks.",
        "",
        "| Pinned id | sha256 | Status | Sections | Chunks | Tables | Captions | Numeric |",
        "|---|---|---|---:|---:|---:|---:|---:|",
        *[
            f"| {r.pinned_id} | `{r.sha256}` | {r.status} | {r.sections} | {r.chunks} | {r.tables} | {r.captions} | {r.numeric} |"
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
        f"- Numeric text Chunks: {sum(r.numeric for r in results)}",
        f"- Parsed: {sum(1 for r in results if not r.failure)}",
        f"- Failed: {len(failures)}",
        "",
        "## Failures by reason",
        "",
        *([f"- {reason}: {count}" for reason, count in sorted(Counter(f.reason for f in failures).items())] or ["- none"]),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")  # the same bytes on every machine


@dataclass(frozen=True)
class ReportedRun:
    """What `read_report` reads back from a parse report: the parser, the chunking config and the files."""

    image: str  # the GROBID image reference, by digest
    chunking: dict[str, str]  # each setting `ChunkingConfig.describe` gives, as the report prints it
    parsed: list[tuple[str, str]]  # (pinned id, sha256) of each parsed file, in the report's order


class UnreadableReport(ValueError):
    """The file isn't a parse report that `write_report` wrote."""


_IMAGE = re.compile(r"^- Image: `([^`]+)`", re.M)
_SETTING = re.compile(r"^- (\w+): `([^`]*)`$")
_FILE = re.compile(r"^\| (\S+) \| `([0-9a-f]{64})` \| (parsed|failed: .*?) \|", re.M)


def read_report(path: Path) -> ReportedRun:
    text = path.read_text(encoding="utf-8")
    image = _IMAGE.search(text)
    _, found, rest = text.partition("\n## Chunking config\n")
    if not image or not found:
        raise UnreadableReport(f"{path} is not a parse report: it names no GROBID image or chunking config")
    chunking = {match[1]: match[2] for line in rest.split("\n## ", 1)[0].splitlines() if (match := _SETTING.match(line))}
    parsed = [(pinned_id, sha256) for pinned_id, sha256, status in _FILE.findall(text) if status == "parsed"]
    return ReportedRun(image[1], chunking, parsed)
