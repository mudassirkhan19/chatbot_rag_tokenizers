"""The quality gate: keeps garbled and empty parses out of the index (ADR 0029).

A file fails when GROBID errors or times out on it, or when its document has fewer Sections or
fewer characters of Section text than the chunking config allows. A failed file gets no Chunks.
"""

from dataclasses import dataclass
from enum import StrEnum

from .config import ChunkingConfig
from .tei import Document



class Reason(StrEnum):
    """Why a file failed, as the report and the failure record name it."""

    GROBID_ERROR = "GROBID error"
    GROBID_TIMEOUT = "GROBID timeout"
    TOO_FEW_SECTIONS = "too few Sections"
    TOO_LITTLE_TEXT = "too little body text"


@dataclass(frozen=True)
class Failure:
    """Why a file failed: its Reason, and the detail of this file."""

    reason: Reason
    detail: str

    def __str__(self) -> str:
        return f"{self.reason} ({self.detail})"


def gate(document: Document, chunking: ChunkingConfig) -> Failure | None:
    """The document's Failure, or None when it passes."""
    sections = len(document.sections)
    if sections < chunking.min_sections:
        return Failure(Reason.TOO_FEW_SECTIONS, f"{sections}, minimum {chunking.min_sections}")
    characters = sum(len(paragraph.text) for section in document.sections for paragraph in section.paragraphs)
    if characters < chunking.min_body_characters:
        return Failure(Reason.TOO_LITTLE_TEXT, f"{characters} characters, minimum {chunking.min_body_characters}")
    return None
