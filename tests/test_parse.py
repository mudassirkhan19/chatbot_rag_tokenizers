"""Offline runs of `parse --files` against a fake GROBID service that answers with committed TEI fixtures.

The TEI fixture is GROBID 0.9.1-crf's real output for WECHSEL v2 (arXiv 2112.06598v2, CC BY 4.0 in the
manifest), with only its request timestamp fixed. No PDF is committed: the "PDFs" are a few generated
bytes, and the fake service maps their sha256 to the fixture.
"""

import hashlib
import json
import xml.etree.ElementTree as ET
from email.parser import BytesParser
from email.policy import HTTP
from pathlib import Path

import httpx
import pytest
from tokenizers import Tokenizer

from chatbot_rag_tokenizers.cli import main
from conftest import FIXTURES

ROOT = Path(__file__).parents[1]
REPO_CONFIG = ROOT / "config" / "parse.toml"
TEI = FIXTURES / "tei"
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
WECHSEL_TITLE = "WECHSEL: Effective initialization of subword embeddings for cross-lingual transfer of monolingual language models"


def fake_pdf(name: str) -> bytes:
    return f"%PDF-1.5\n% {name}\n%%EOF\n".encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeGrobid:
    """Stands in for the GROBID service: the sha256 of the uploaded PDF picks the TEI it answers with.

    Every request's URL and form fields are recorded.
    """

    def __init__(self) -> None:
        self.tei_by_hash: dict[str, str] = {}
        self.requests: list[tuple[str, list[tuple[str, str]]]] = []

    def serve(self, pdf: bytes, tei_fixture: str) -> None:
        self.tei_by_hash[sha256(pdf)] = (TEI / tei_fixture).read_text()

    def handle(self, request: httpx.Request) -> httpx.Response:
        request.read()
        head = f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
        form = BytesParser(policy=HTTP).parsebytes(head + request.content)
        fields: list[tuple[str, str]] = []
        upload = b""
        for part in form.iter_parts():
            name = str(part.get_param("name", header="content-disposition"))
            payload = part.get_payload(decode=True)
            assert isinstance(payload, bytes)
            if name == "input":
                upload = payload
            else:
                fields.append((name, payload.decode()))
        self.requests.append((str(request.url), fields))
        if str(request.url) != GROBID_URL or sha256(upload) not in self.tei_by_hash:
            return httpx.Response(500, text="unexpected request", request=request)
        return httpx.Response(200, text=self.tei_by_hash[sha256(upload)], request=request)


@pytest.fixture
def grobid(monkeypatch: pytest.MonkeyPatch, no_network) -> FakeGrobid:
    fake = FakeGrobid()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: fake.handle(request))
    return fake


@pytest.fixture
def wechsel(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """A Seed PDF named as in data/pdfs/seeds, whose TEI the fake service knows."""
    pdf = tmp_path / "pdfs" / "wechsel_2112.06598v2.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(fake_pdf("wechsel v2"))
    grobid.serve(pdf.read_bytes(), "wechsel_2112.06598v2.tei.xml")
    return pdf


def run_parse(tmp_path: Path, *files: Path, config: Path = REPO_CONFIG) -> None:
    main(
        [
            "parse",
            "--config", str(config),
            "--cache", str(tmp_path / "cache"),
            "--report", str(tmp_path / "parse-report.md"),
            "--files", *map(str, files),
        ]
    )  # fmt: skip


def config_with_budget(tmp_path: Path, token_budget: int) -> Path:
    """The repo's parse config with another token budget, written beside the test's other files."""
    text = REPO_CONFIG.read_text().replace("token_budget = 350", f"token_budget = {token_budget}")
    text = text.replace('tokenizer_file = "', f'tokenizer_file = "{REPO_CONFIG.parent}/')
    path = tmp_path / f"parse-{token_budget}.toml"
    path.write_text(text)
    return path


def section_chunks(chunks: list[dict], number: str) -> list[dict]:
    """The text Chunks of one Section (tables and captions are covered in test_parse_elements.py)."""
    return [c for c in chunks if c["section_number"] == number and c["kind"] == "text"]


def read_chunks(tmp_path: Path, pdf: Path) -> list[dict]:
    """The Chunks the parse cache holds for one file."""
    [path] = (tmp_path / "cache" / sha256(pdf.read_bytes())).glob("*.chunks.jsonl")
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_seed_file_gets_its_pinned_id_from_its_name_and_its_hash_on_the_spot(tmp_path, wechsel):
    run_parse(tmp_path, wechsel)

    chunks = read_chunks(tmp_path, wechsel)
    assert chunks
    assert {(c["pinned_id"], c["version"], c["file_sha256"]) for c in chunks} == {
        ("2112.06598v2", "v2", sha256(fake_pdf("wechsel v2")))
    }


def test_grobid_is_asked_for_full_text_with_coordinates_and_without_consolidation(tmp_path, wechsel, grobid):
    run_parse(tmp_path, wechsel)

    [(url, fields)] = grobid.requests
    assert url == GROBID_URL
    form = dict(fields)
    assert form["consolidateHeader"] == form["consolidateCitations"] == form["consolidateFunders"] == "0"
    assert form["segmentSentences"] == "1"
    coordinates = [value for name, value in fields if name == "teiCoordinates"]
    assert {"head", "p", "s"} <= set(coordinates)


def test_the_abstract_and_each_body_section_are_sections_with_paths_rebuilt_from_their_numbers(tmp_path, wechsel):
    run_parse(tmp_path, wechsel)

    paths = [tuple(c["section_path"]) for c in read_chunks(tmp_path, wechsel)]
    sections = list(dict.fromkeys(paths))
    # GROBID lost the headings of Sections 3, 4 and 6 (their text joins the Section before), and run-in
    # headings came out as unnumbered Sections: they sit under the numbered Section before them.
    assert sections == [
        ("Abstract",),
        ("1 Introduction",),
        ("2 Related Work",),
        ("2 Related Work", "Multilingual representations."),
        ("2 Related Work", "Cross-lingual transfer of monolingual LMs."),
        ("3.1 Subword Embedding Computation",),
        ("3.2 Subword similarity-based Transfer",),
        ("5 Results",),
        ("5 Results", "5.1 Transferring RoBERTa"),
        ("5 Results", "5.2 Transferring GPT-2 5.2.1 To Medium-Resource Languages"),
        ("5 Results", "5.2 Transferring GPT-2 5.2.1 To Medium-Resource Languages", "5.2.2 To Low-Resource Languages"),
        ("5 Results", "5.3 Is freezing necessary?"),
        ("6.2 Risks",),
        ("7 Conclusion",),
        # The annex: appendix Sections number their own (ADR 0026).
        ("A Grid search over k and τ",),
        ("B Hyperparameters",),
        ("C Qualitative subword correspondence",),
        ("D Using Word Embeddings without subword information",),
        ("E Choosing a transfer baseline",),
        ("F Sensitivity Analysis w. r. t. training data size",),
    ]
    # No Section comes back after another one started: its Chunks are contiguous.
    assert len(sections) == len([path for i, path in enumerate(paths) if i == 0 or paths[i - 1] != path])


def test_no_chunk_crosses_a_section(tmp_path, wechsel):
    run_parse(tmp_path, wechsel)
    chunks = read_chunks(tmp_path, wechsel)

    [abstract] = section_chunks(chunks, "")[:1]
    assert abstract["section_title"] == "Abstract"
    assert abstract["text"].startswith("Large pretrained language models (LMs) have become the central building block")
    assert abstract["text"].endswith("We make our code and models publicly available.")
    introduction = section_chunks(chunks, "1")
    assert introduction[0]["text"].startswith("Large LMs based on the Transformer architecture")
    assert introduction[-1]["text"].endswith("We show and discuss results in Section 5.")
    assert section_chunks(chunks, "2")[0]["text"].startswith("Large Language Models. Training Language Models")


@pytest.mark.parametrize("token_budget", [350, 40])
def test_chunks_stay_within_the_token_budget_counted_with_the_pinned_tokenizer(tmp_path, wechsel, token_budget):
    run_parse(tmp_path, wechsel, config=config_with_budget(tmp_path, token_budget))

    tokenizer = Tokenizer.from_file(str(REPO_CONFIG.parent / "tokenizers" / "bert-base-uncased.tokenizer.json"))
    tokenizer.no_truncation()
    chunks = read_chunks(tmp_path, wechsel)
    for chunk in chunks:
        assert chunk["token_count"] == len(tokenizer.encode(chunk["text"], add_special_tokens=False).ids)
        assert 0 < chunk["token_count"] <= token_budget
    # Whole paragraphs are packed: at 350 tokens most Chunks hold more than one short paragraph's worth.
    if token_budget == 350:
        assert len([c for c in chunks if c["kind"] == "text" and not c["appendix"]]) == 29


def wechsel_sentences(section_number: str) -> list[str]:
    """The sentences GROBID found in one Section of the fixture, read straight from the TEI."""
    tei = {"t": "http://www.tei-c.org/ns/1.0"}
    root = ET.parse(TEI / "wechsel_2112.06598v2.tei.xml").getroot()
    [div] = [d for d in root.iterfind("t:text/t:body/t:div", tei) if d.find(f"t:head[@n='{section_number}']", tei) is not None]
    return [" ".join("".join(s.itertext()).split()) for s in div.iterfind("t:p/t:s", tei)]


def test_a_paragraph_over_the_budget_is_split_at_sentences_without_overlap(tmp_path, wechsel):
    # Section 5.3 is one paragraph of about 300 tokens; at a budget of 100 it must be split.
    run_parse(tmp_path, wechsel, config=config_with_budget(tmp_path, 100))

    chunks = section_chunks(read_chunks(tmp_path, wechsel), "5.3")
    sentences = wechsel_sentences("5.3")
    assert len(sentences) > len(chunks) > 1
    # Together the Chunks are the paragraph, once, in order, and each one is a run of whole sentences.
    assert " ".join(c["text"] for c in chunks) == " ".join(sentences)
    for chunk in chunks:
        assert any(chunk["text"] == " ".join(sentences[i:j]) for i in range(len(sentences)) for j in range(i + 1, len(sentences) + 1))


def test_the_context_header_is_stored_apart_from_the_text(tmp_path, wechsel):
    run_parse(tmp_path, wechsel)

    [chunk] = section_chunks(read_chunks(tmp_path, wechsel), "5.3")
    assert chunk["header"] == f"{WECHSEL_TITLE} › 5 Results › 5.3 Is freezing necessary?"
    assert chunk["text"].startswith("Previous work using the TransInner method freezes")
    assert "WECHSEL: Effective initialization" not in chunk["text"]


def test_each_chunk_carries_its_citation_anchor(tmp_path, wechsel):
    run_parse(tmp_path, wechsel)
    chunks = read_chunks(tmp_path, wechsel)

    # Section 5.3's one paragraph starts at the foot of page 8 and ends on page 9.
    [freezing] = section_chunks(chunks, "5.3")
    anchor = {k: freezing[k] for k in ("pinned_id", "version", "section_number", "section_title", "page_start", "page_end")}
    assert anchor == {
        "pinned_id": "2112.06598v2",
        "version": "v2",
        "section_number": "5.3",
        "section_title": "Is freezing necessary?",
        "page_start": 8,
        "page_end": 9,
    }
    assert (chunks[0]["page_start"], chunks[0]["page_end"]) == (1, 1)  # the abstract
    assert freezing["kind"] == "text" and freezing["appendix"] is False
    # Chunk ids are the file hash and the Chunk's place in the file.
    prefix = sha256(fake_pdf("wechsel v2"))[:16]
    assert [c["chunk_id"] for c in chunks[:2]] == [f"{prefix}-0000", f"{prefix}-0001"]
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)


@pytest.mark.parametrize(
    "name, pinned_id, version",
    [
        ("bpe-dropout_1910.13267v1.pdf", "1910.13267v1", "v1"),
        ("zero-shot-tokenizer-transfer_2405.07883v2.pdf", "2405.07883v2", "v2"),
        ("2004.03720v3.pdf", "2004.03720v3", "v3"),  # as `fetch` names a file
        ("P16-1162.pdf", "P16-1162", ""),  # a venue Edition has no Version
    ],
)
def test_pinned_ids_come_from_file_names(tmp_path, grobid, name, pinned_id, version):
    pdf = tmp_path / name
    pdf.write_bytes(fake_pdf(name))
    grobid.serve(pdf.read_bytes(), "wechsel_2112.06598v2.tei.xml")

    run_parse(tmp_path, pdf)

    assert {(c["pinned_id"], c["version"]) for c in read_chunks(tmp_path, pdf)} == {(pinned_id, version)}


def test_a_rerun_reuses_the_cached_parse_without_calling_grobid(tmp_path, wechsel, grobid):
    run_parse(tmp_path, wechsel)
    first = read_chunks(tmp_path, wechsel)
    assert len(grobid.requests) == 1

    run_parse(tmp_path, wechsel)
    assert len(grobid.requests) == 1
    assert read_chunks(tmp_path, wechsel) == first

    # A file with another hash is parsed, even under a name seen before.
    wechsel.write_bytes(fake_pdf("wechsel v2, re-downloaded"))
    grobid.serve(wechsel.read_bytes(), "wechsel_2112.06598v2.tei.xml")
    run_parse(tmp_path, wechsel)
    assert len(grobid.requests) == 2


def test_the_report_names_the_parser_and_config_and_gives_a_line_per_file_and_totals(tmp_path, wechsel, grobid):
    seed = tmp_path / "pdfs" / "sennrich-bpe_1508.07909v5.pdf"
    seed.write_bytes(fake_pdf("sennrich v5"))
    grobid.serve(seed.read_bytes(), "wechsel_2112.06598v2.tei.xml")  # any TEI will do for the report

    run_parse(tmp_path, wechsel, seed)

    report = (tmp_path / "parse-report.md").read_text()
    digest = "sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd"
    assert f"- Image: `grobid/grobid@{digest}` (tag `0.9.1-crf`)" in report
    assert "- GROBID version: 0.9.1" in report
    assert "- token_budget: `350`" in report
    assert "- tokenizer: `google-bert/bert-base-uncased`" in report
    # One line per file in pinned-id order: the abstract, 13 body Sections and 6 appendix Sections.
    assert (
        f"| 1508.07909v5 | `{sha256(fake_pdf('sennrich v5'))}` | parsed | 20 | 52 | 11 | 5 |\n"
        f"| 2112.06598v2 | `{sha256(fake_pdf('wechsel v2'))}` | parsed | 20 | 52 | 11 | 5 |\n"
    ) in report
    assert "- Files: 2\n- Sections: 40\n- Chunks: 104\n" in report
