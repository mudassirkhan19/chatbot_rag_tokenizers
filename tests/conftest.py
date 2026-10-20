import csv
import hashlib
import shutil
import socket
from collections.abc import Sequence
from pathlib import Path

import httpx
import numpy as np
import pytest

from chatbot_rag_tokenizers.chat import model as answer_model
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.collection import judge
from chatbot_rag_tokenizers.collection.snapshot import SnapshotStore
from chatbot_rag_tokenizers.retrieval import embedder
from chatbot_rag_tokenizers.retrieval.bm25 import tokenise
from parse_support import FakeGrobid, fake_pdf

FIXTURES = Path(__file__).parent / "fixtures"
NAMES_PROMPT = load_chat_config(Path(__file__).parents[1] / "config" / "retrieval.toml").names_prompt

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


OPENALEX_API = "https://api.openalex.org/works"
OPENALEX_FIXTURE_QUERY = '"subword tokenization" OR "byte pair encoding"'


def openalex_request(cursor: str) -> dict:
    """The request description the collector records for one OpenAlex works page."""
    return {
        "source": "openalex",
        "url": OPENALEX_API,
        "params": {
            "search.title_and_abstract": OPENALEX_FIXTURE_QUERY,
            "select": "id,doi,ids,title,publication_year,type,authorships,abstract_inverted_index,"
            "primary_location,locations,best_oa_location",
            "sort": "publication_date:asc",
            "per_page": 100,
            "cursor": cursor,
        },
    }


@pytest.fixture
def fixture_snapshot(tmp_path: Path) -> Path:
    """A hand-built Snapshot: two results pages from each of arXiv, Semantic Scholar and OpenAlex
    for the fixture queries, the fixture Seed's record, references and citations, the full record of
    each arXiv Edition that passes the rules, the ACL Anthology page of each reported ACL ID, and a
    cached judge verdict for each Candidate that passes the rules."""
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
    for cursor, page in [("*", "page-0.json"), ("FIXTURE-CURSOR-1", "page-1.json")]:
        body = (FIXTURES / "openalex" / page).read_text()
        store.save(openalex_request(cursor), body, collected_at="2026-10-16")
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


@pytest.fixture
def no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything tries to load the judge model."""

    def refuse(config):
        raise AssertionError("the judge model was loaded")

    monkeypatch.setattr(judge, "load_judge", refuse)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def grobid(monkeypatch: pytest.MonkeyPatch, no_network) -> FakeGrobid:
    """The fake GROBID service in place of the real one, for the offline `parse` tests."""
    fake = FakeGrobid()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: fake.handle(request))
    return fake


@pytest.fixture
def wechsel(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """A Seed PDF named as in data/pdfs/seeds, whose TEI the fake service knows."""
    pdf = tmp_path / "pdfs" / "wechsel_2112.06598v2.pdf"
    pdf.parent.mkdir(exist_ok=True)
    pdf.write_bytes(fake_pdf("wechsel v2"))
    grobid.serve(pdf.read_bytes(), "wechsel_2112.06598v2.tei.xml")
    return pdf


class FakeEmbedder:
    """A hashed bag of words in place of the embedding model: each token adds 1 to one of 64 dimensions,
    chosen by the sha256 of the model id and the token, and the counts are normalised. Texts sharing words
    point the same way, and two model ids hash words apart, so they rank differently."""

    DIMENSIONS = 64

    def __init__(self, model: str, revision: str) -> None:
        self.model = model
        self.revision = revision
        self.device = "cpu"
        self.parameters = self.DIMENSIONS * 30522  # as if it had a weight per dimension per word of BERT's vocabulary

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.DIMENSIONS), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in tokenise(text):
                salted = f"{self.model}\n{token}".encode()
                vectors[row, int(hashlib.sha256(salted).hexdigest(), 16) % self.DIMENSIONS] += 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch: pytest.MonkeyPatch) -> list[FakeEmbedder]:
    """Every test embeds with FakeEmbedder, so none downloads or loads a model. Returns the embedders made."""
    made: list[FakeEmbedder] = []

    def load(settings, device=None):
        made.append(FakeEmbedder(settings.model, settings.revision))
        return made[-1]

    monkeypatch.setattr(embedder, "load_embedder", load)
    return made


class FakeAnswerModel:
    """A scripted answer model in place of the pinned one: it replies with the script's answer for the first key
    found in the chat's last user message, and records every chat it is given. A key scripted with a list of
    answers gives the next one each time it is asked, then keeps giving the last, as a model whose reply varies
    between runs. An unscripted question fails the test, so every answer a test sees is one it wrote.

    A chat asking for the papers a question names (the [chat] names prompt) is answered apart: from ``names``, by the
    question, or NONE, so a test that doesn't script names retrieves as before. It is recorded in ``namings``."""

    pin = "fake-answer-model"

    def __init__(self) -> None:
        self.script: dict[str, str | list[str]] = {}
        self.chats: list[list[dict[str, str]]] = []
        self.names: dict[str, str] = {}
        self.namings: list[list[dict[str, str]]] = []

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        if messages[0]["content"] == NAMES_PROMPT:
            self.namings.append(list(messages))
            return self.names.get(messages[-1]["content"], "NONE")
        self.chats.append(list(messages))
        last = messages[-1]["content"]
        for key, answer in self.script.items():
            if key in last:
                if isinstance(answer, list):
                    return answer.pop(0) if len(answer) > 1 else answer[0]
                return answer
        raise AssertionError(f"the fake answer model has no answer scripted for {last[:120]!r}")


@pytest.fixture(autouse=True)
def fake_answer_model(monkeypatch: pytest.MonkeyPatch) -> FakeAnswerModel:
    """Every test answers with FakeAnswerModel, so none needs Ollama. Returns it, for the test to script."""
    fake = FakeAnswerModel()
    monkeypatch.setattr(answer_model, "load_answer_model", lambda settings: fake)
    return fake
