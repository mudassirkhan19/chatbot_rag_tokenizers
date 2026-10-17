"""The parser client: sends one PDF to the pinned GROBID service and returns its TEI XML (ADR 0024)."""

import httpx

from .config import GrobidConfig

# Full-text processing with coordinates on and consolidation off. Consolidation would call external
# metadata services, making the network part of parsing and its output depend on them.
FORM = [
    ("consolidateHeader", "0"),
    ("consolidateCitations", "0"),
    ("consolidateFunders", "0"),
    ("includeRawCitations", "1"),  # each reference keeps its printed string, for the dedup stage
    ("segmentSentences", "1"),  # every paragraph comes in <s> elements: the Chunker's sentence boundaries
    *[("teiCoordinates", element) for element in ("head", "p", "s", "figure", "formula", "biblStruct", "note", "title")],
]
TIMEOUT_SECONDS = 300.0  # a long paper takes a few seconds; a busy service may queue it


class GrobidClient:
    def __init__(self, config: GrobidConfig) -> None:
        self.url = f"{config.url}/api/processFulltextDocument"
        self._http = httpx.Client(timeout=TIMEOUT_SECONDS)

    def process(self, pdf: bytes) -> str:
        """The TEI GROBID makes of one PDF. The GROBID version it reports is in the TEI header."""
        response = self._http.post(
            self.url,
            data=_form_data(),
            files={"input": ("input.pdf", pdf, "application/pdf")},
            headers={"Accept": "application/xml"},
        )
        response.raise_for_status()
        return response.text


def _form_data() -> dict[str, list[str]]:
    """FORM as httpx takes it: a repeated field is one key with a list of values."""
    data: dict[str, list[str]] = {}
    for name, value in FORM:
        data.setdefault(name, []).append(value)
    return data
