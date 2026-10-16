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


S2_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIXTURE_QUERY = '"subword tokenization" | sentencepiece'


def s2_request(token: str | None) -> dict:
    """The request description the collector records for one Semantic Scholar bulk-search page."""
    params = {
        "query": S2_FIXTURE_QUERY,
        "fields": "paperId,externalIds,url,title,abstract,venue,year,authors",
        "fieldsOfStudy": "Computer Science,Linguistics",
        "sort": "paperId:asc",
    }
    if token is not None:
        params["token"] = token
    return {"source": "semantic-scholar", "url": S2_API, "params": params}


S2_GRAPH = "https://api.semanticscholar.org/graph/v1/paper"
S2_FIELDS = "paperId,externalIds,url,title,abstract,venue,year,authors"
FIXTURE_SEED = "ARXIV:1808.06226"


def s2_seed_request(path: str = "", offset: int | None = None) -> dict:
    """The request description for a Seed's own record (``path=""``) or one page of its
    ``/references`` or ``/citations``."""
    params: dict = {"fields": S2_FIELDS}
    if offset is not None:
        params |= {"offset": offset, "limit": 1000}
    return {"source": "semantic-scholar", "url": f"{S2_GRAPH}/{FIXTURE_SEED}{path}", "params": params}


def acl_request(acl_id: str) -> dict:
    """The request description the collector records for one ACL Anthology paper page."""
    return {"source": "acl-anthology", "url": f"https://aclanthology.org/{acl_id}/", "params": {}}


@pytest.fixture
def fixture_snapshot(tmp_path: Path) -> Path:
    """A hand-built Snapshot: two arXiv and two Semantic Scholar results pages for the fixture
    queries, the fixture Seed's record, references and citations, the full record of each arXiv
    Edition that passes the rules, the ACL Anthology page of each reported ACL ID, and a cached
    judge verdict for each Candidate that passes the rules."""
    root = tmp_path / "snapshot"
    store = SnapshotStore(root)
    for start, page in [(0, "page-0.xml"), (4, "page-1.xml")]:
        body = (FIXTURES / "arxiv" / page).read_text()
        store.save(arxiv_request(start, 4), body, collected_at="2026-10-16")
    for record in sorted((FIXTURES / "arxiv-oai").glob("*.xml")):
        arxiv_id = record.stem.replace("_", "/")
        store.save(arxiv_record_request(arxiv_id), record.read_text(), collected_at="2026-10-16")
    for token, page in [(None, "page-0.json"), ("FIXTURE-TOKEN-1", "page-1.json")]:
        body = (FIXTURES / "semantic-scholar" / page).read_text()
        store.save(s2_request(token), body, collected_at="2026-10-16")
    seed_pages = [
        (s2_seed_request(), "sentencepiece-paper.json"),
        (s2_seed_request("/references", 0), "sentencepiece-references.json"),
        (s2_seed_request("/citations", 0), "sentencepiece-citations-0.json"),
        (s2_seed_request("/citations", 1000), "sentencepiece-citations-1.json"),
    ]
    for request, page in seed_pages:
        store.save(request, (FIXTURES / "seeds" / page).read_text(), collected_at="2026-10-16")
    for paper in sorted((FIXTURES / "acl-anthology").glob("*.html")):
        store.save(acl_request(paper.stem), paper.read_text(), collected_at="2026-10-16")
    # The Findings paper that cites the Seed is invented for the fixtures, so the Anthology has no
    # such paper: the collector stores a 404 as an empty body.
    store.save(acl_request("2022.findings-acl.99"), "", collected_at="2026-10-16")
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
