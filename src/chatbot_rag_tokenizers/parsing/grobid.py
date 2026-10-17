"""The parser client: sends one PDF to the pinned GROBID service and returns its TEI XML (ADR 0024)."""

import httpx

from .config import GrobidConfig
from .quality import GROBID_ERROR, GROBID_TIMEOUT, Failure

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


class GrobidUnreachable(RuntimeError):
    """The service isn't running: no file can be parsed, so the run stops."""

    def __init__(self, url: str) -> None:
        super().__init__(f"the GROBID service isn't reachable at {url}. Start it with `just grobid-up` and run parse again.")


class GrobidFailed(RuntimeError):
    """GROBID couldn't parse this one file: an error answer or no answer in time."""

    def __init__(self, failure: Failure) -> None:
        self.failure = failure
        super().__init__(str(failure))


class GrobidClient:
    def __init__(self, config: GrobidConfig) -> None:
        self.service_url = config.url
        self.url = f"{config.url}/api/processFulltextDocument"
        self._http = httpx.Client(timeout=TIMEOUT_SECONDS)

    def process(self, pdf: bytes) -> str:
        """The TEI GROBID makes of one PDF. The GROBID version it reports is in the TEI header.

        Raises GrobidFailed when GROBID fails on this file, and GrobidUnreachable when the service is down.
        """
        try:
            response = self._http.post(
                self.url,
                data=_form_data(),
                files={"input": ("input.pdf", pdf, "application/pdf")},
                headers={"Accept": "application/xml"},
            )
        except httpx.ConnectError as error:
            raise GrobidUnreachable(self.service_url) from error
        except httpx.TimeoutException as error:
            raise GrobidFailed(Failure(GROBID_TIMEOUT, f"no answer within {TIMEOUT_SECONDS:g} s")) from error
        except httpx.TransportError as error:
            raise GrobidFailed(Failure(GROBID_ERROR, f"{type(error).__name__}: {error}")) from error
        if response.status_code != 200 or not response.text.strip():
            # GROBID answers 500 with a short message for a PDF it can't read, and 204 when it finds no text.
            message = " ".join(response.text.split())[:200]
            detail = f"HTTP {response.status_code}: {message}" if message else f"HTTP {response.status_code}"
            raise GrobidFailed(Failure(GROBID_ERROR, detail))
        return response.text


def _form_data() -> dict[str, list[str]]:
    """FORM as httpx takes it: a repeated field is one key with a list of values."""
    data: dict[str, list[str]] = {}
    for name, value in FORM:
        data.setdefault(name, []).append(value)
    return data
