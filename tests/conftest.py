import shutil
import socket
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.collection.snapshot import SnapshotStore

FIXTURES = Path(__file__).parent / "fixtures"

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_OAI = "https://oaipmh.arxiv.org/oai"
FIXTURE_QUERY = "ti:tokenizer OR ti:tokenization"


def arxiv_request(start: int, page_size: int) -> dict:
    """The request description the collector records for one arXiv results page."""
    return {
        "source": "arxiv",
        "url": ARXIV_API,
        "params": {
            "search_query": FIXTURE_QUERY,
            "start": start,
            "max_results": page_size,
            "sortBy": "submittedDate",
            "sortOrder": "ascending",
        },
    }


def arxiv_record_request(arxiv_id: str) -> dict:
    """The request description the collector records for one arXiv Edition's full record."""
    return {
        "source": "arxiv-oai",
        "url": ARXIV_OAI,
        "params": {
            "verb": "GetRecord",
            "identifier": f"oai:arXiv.org:{arxiv_id}",
            "metadataPrefix": "arXivRaw",
        },
    }


@pytest.fixture
def fixture_snapshot(tmp_path: Path) -> Path:
    """A hand-built Snapshot: two arXiv results pages for the fixture query, each Edition's full
    record, and a cached judge verdict for each Candidate that passes the rules."""
    root = tmp_path / "snapshot"
    store = SnapshotStore(root)
    for start, page in [(0, "page-0.xml"), (4, "page-1.xml")]:
        body = (FIXTURES / "arxiv" / page).read_text()
        store.save(arxiv_request(start, 4), body, collected_at="2026-10-16")
    for record in sorted((FIXTURES / "arxiv-oai").glob("*.xml")):
        arxiv_id = record.stem.replace("_", "/")
        store.save(arxiv_record_request(arxiv_id), record.read_text(), collected_at="2026-10-16")
    shutil.copytree(FIXTURES / "verdicts", root / "verdicts")
    return root


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything tries to open a network connection."""

    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted during an offline run")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
