"""The element rules of `parse` (#19, ADR 0026), run through the CLI against a fake GROBID service.

`wechsel-elements.tei.xml` is the WECHSEL v2 TEI (CC BY 4.0) trimmed by hand to a few body Sections,
one figure and one table in the body, the acknowledgements, two annex Sections with a table, and three
references. `appendix-in-body.tei.xml` is a smaller hand-made rearrangement of the same paper, with the
appendices and acknowledgements in the body, as GROBID gives them for some Seeds.
"""

import json
from pathlib import Path

import httpx
import pytest

from test_parse import WECHSEL_TITLE, FakeGrobid, config_with_budget, fake_pdf, read_chunks, run_parse, sha256


@pytest.fixture
def grobid(monkeypatch: pytest.MonkeyPatch, no_network) -> FakeGrobid:
    fake = FakeGrobid()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: fake.handle(request))
    return fake


def serve(tmp_path: Path, grobid: FakeGrobid, fixture: str) -> Path:
    pdf = tmp_path / "pdfs" / "wechsel_2112.06598v2.pdf"
    pdf.parent.mkdir(exist_ok=True)
    pdf.write_bytes(fake_pdf(fixture))
    grobid.serve(pdf.read_bytes(), fixture)
    return pdf


@pytest.fixture
def elements(tmp_path: Path, grobid: FakeGrobid) -> Path:
    return serve(tmp_path, grobid, "wechsel-elements.tei.xml")


def small_paper_config(tmp_path: Path, token_budget: int = 350) -> Path:
    """The repo's parse config with a quality gate that lets the small hand-made paper through."""
    path = config_with_budget(tmp_path, token_budget)
    path.write_text(path.read_text().replace("min_body_characters = 2000", "min_body_characters = 500"))
    return path


def of_kind(chunks: list[dict], kind: str) -> list[dict]:
    return [c for c in chunks if c["kind"] == kind]


def test_each_table_is_one_chunk_linearised_row_by_row_after_its_caption_and_section(tmp_path, elements):
    run_parse(tmp_path, elements, config=config_with_budget(tmp_path, 1000))

    tables = of_kind(read_chunks(tmp_path, elements), "table")
    assert [(t["section_number"], t["section_title"]) for t in tables] == [
        ("5.1", "Transferring RoBERTa"),  # no ref names Table 2's id: it goes by its page
        ("A", "Grid search over k and τ"),  # Table 7 is cited from Appendix A by its id
    ]
    table_2 = tables[0]
    lines = table_2["text"].split("\n")
    assert lines[0] == (
        "Table 2 (5.1 Transferring RoBERTa): Results from fine-tuning RoBERTa models. "
        "We report accuracy for NLI on XNLI and micro F1 score for NER on WikiANN."
    )
    # One line per row, cells in order and separated by " | ", empty cells kept so columns line up.
    assert lines[1].startswith("Lang | Model | Score@0 NLI NER Avg")
    assert lines[2] == " | WECHSEL-RoBERTa 78.25 86.93 82.59 81.63 90.26 85.95 82.43 90.88 86.65 | - | - | -"
    assert lines[4].startswith("French | FullRand-RoBERTa | 55.71")
    assert len(lines) == 1 + 19
    assert (table_2["page_start"], table_2["page_end"]) == (6, 6)
    assert table_2["header"] == f"{WECHSEL_TITLE} › 5 Results › 5.1 Transferring RoBERTa"


def test_a_table_over_the_budget_is_cut_between_rows_and_each_part_names_the_table(tmp_path, elements):
    run_parse(tmp_path, elements)  # the repo's budget of 350 tokens: Table 2's 19 rows don't fit in one Chunk

    parts = [t for t in of_kind(read_chunks(tmp_path, elements), "table") if t["section_number"] == "5.1"]
    assert len(parts) > 1
    first_line = parts[0]["text"].split("\n")[0]
    assert first_line.startswith("Table 2 (5.1 Transferring RoBERTa): Results from fine-tuning")
    rows = []
    for part in parts:
        assert part["token_count"] <= 350
        [line, *part_rows] = part["text"].split("\n")
        assert line == first_line
        rows += part_rows
    # Together the parts hold every row once, in order.
    assert len(rows) == 19
    assert rows[0].startswith("Lang | Model")
    assert rows[1].startswith(" | WECHSEL-RoBERTa 78.25")
    assert rows[-1] == " | XLM-RBase | - | - | - | - | - | - | - | - | -69.18 87.37 | 78.28"


def test_each_figure_caption_is_one_chunk_in_the_section_that_cites_it(tmp_path, elements):
    run_parse(tmp_path, elements)

    [caption] = of_kind(read_chunks(tmp_path, elements), "caption")
    # Figure 2 is cited by its id from Section 5.1; GROBID kept the label in the caption text.
    assert (caption["section_number"], caption["section_title"], caption["appendix"]) == ("5.1", "Transferring RoBERTa", False)
    assert caption["text"] == (
        "Figure2: Test scores over training steps from fine-tuning RoBERTa models on NLI (using XNLI) and NER "
        "(using WikiANN). Perplexity on the held-out set over training steps of GPT-2 models. We evaluate every 12.5k steps."
    )
    assert (caption["page_start"], caption["page_end"]) == (7, 7)
    assert caption["header"] == f"{WECHSEL_TITLE} › 5 Results › 5.1 Transferring RoBERTa"
    # A Section's text Chunks come first, then its tables, then its captions.
    kinds = [c["kind"] for c in read_chunks(tmp_path, elements) if c["section_number"] == "5.1"]
    assert kinds == sorted(kinds, key=["text", "table", "caption"].index)


def read_bibliography(tmp_path: Path, pdf: Path) -> list[dict]:
    """The bibliography the parse cache holds for one file."""
    [path] = (tmp_path / "cache" / sha256(pdf.read_bytes())).glob("*.bibliography.jsonl")
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_the_reference_list_gives_no_chunks_and_is_stored_as_a_structured_bibliography(tmp_path, elements):
    run_parse(tmp_path, elements)

    texts = " ".join(c["text"] for c in read_chunks(tmp_path, elements))
    assert "AraBERT: Transformer-based model" not in texts
    assert not any("Reference" in c["section_title"] for c in read_chunks(tmp_path, elements))
    bibliography = read_bibliography(tmp_path, elements)
    assert [entry["key"] for entry in bibliography] == ["b0", "b1", "b14"]
    assert bibliography[0] == {
        "key": "b0",
        "title": "AraBERT: Transformer-based model for Arabic language understanding",
        "authors": ["Fady Wissam Antoun", "Hazem Baly", "Hajj"],  # GROBID's split of the names, kept as given
        "year": "2020",
        "identifiers": {},
        "raw": (
            "Wissam Antoun, Fady Baly, and Hazem Hajj. 2020. AraBERT: Transformer-based model for Arabic lan- guage "
            "understanding. In Proceedings of the 4th Workshop on Open-Source Arabic Corpora and Pro- cessing Tools, "
            "with a Shared Task on Offensive Lan- guage Detection, pages 9-15, Marseille, France. Eu- ropean Language "
            "Resource Association."
        ),
    }
    assert bibliography[1]["identifiers"] == {"DOI": "10.18653/v1/D16-1250"}
    # A report with no analytic part: title and authors come from the monograph.
    preprint = bibliography[2]
    assert (preprint["title"], preprint["year"], preprint["identifiers"]) == (
        "Word translation without parallel data",
        "2017",
        {"arXiv": "arXiv:1710.04087"},
    )
    assert preprint["authors"][:2] == ["Alexis Conneau", "Guillaume Lample"]


def test_acknowledgements_are_dropped_and_annex_sections_are_marked_as_appendices(tmp_path, elements):
    run_parse(tmp_path, elements)
    chunks = read_chunks(tmp_path, elements)

    texts = " ".join(c["text"] for c in chunks)
    assert "TPU Research Cloud" not in texts
    assert not any("Acknowledg" in c["section_title"] for c in chunks)
    sections = list(dict.fromkeys((c["section_number"], c["section_title"], tuple(c["section_path"]), c["appendix"]) for c in chunks))
    assert sections == [
        ("", "Abstract", ("Abstract",), False),
        ("1", "Introduction", ("1 Introduction",), False),
        ("3.1", "Subword Embedding Computation", ("3.1 Subword Embedding Computation",), False),
        ("5", "Results", ("5 Results",), False),
        ("5.1", "Transferring RoBERTa", ("5 Results", "5.1 Transferring RoBERTa"), False),
        ("A", "Grid search over k and τ", ("A Grid search over k and τ",), True),
        ("B", "Hyperparameters", ("B Hyperparameters",), True),
    ]
    # Every Chunk of an appendix Section is marked, its table too.
    assert all(c["appendix"] for c in chunks if c["section_number"] in ("A", "B"))
    assert any(c["kind"] == "table" and c["appendix"] for c in chunks)


@pytest.fixture
def appendix_in_body(tmp_path: Path, grobid: FakeGrobid) -> Path:
    return serve(tmp_path, grobid, "appendix-in-body.tei.xml")


def test_body_sections_headed_with_an_appendix_letter_start_the_appendix(tmp_path, appendix_in_body):
    run_parse(tmp_path, appendix_in_body, config=small_paper_config(tmp_path))
    chunks = read_chunks(tmp_path, appendix_in_body)

    sections = list(dict.fromkeys((c["section_number"], tuple(c["section_path"]), c["appendix"]) for c in chunks))
    assert sections == [
        ("", ("Abstract",), False),
        ("1", ("1 Introduction",), False),
        ("", ("1 Introduction", "A closer look."), False),  # a run-in heading, not Appendix A
        ("2", ("2 Conclusion",), False),
        # The acknowledgements in the body, and the headless div that continues them, are dropped.
        ("A", ("A Grid search over k and τ",), True),
        ("A.1", ("A Grid search over k and τ", "A.1 Probing tasks"), True),
        ("", ("A Grid search over k and τ", "A.1 Probing tasks", "Summary."), True),  # after the appendix began
        ("B", ("B Hyperparameters",), True),
        ("C", ("C Qualitative subword correspondence",), True),  # printed "C."
        # GROBID put 2.1 in the annex, but its number continues Section 2 of the body.
        ("2.1", ("2 Conclusion", "2.1 Limitations"), False),
    ]
    assert "Andy Koh" not in " ".join(c["text"] for c in chunks)
    # Figure 5 is cited only by its number, from Appendix A; GROBID left the label out of its caption.
    [caption] = of_kind(chunks, "caption")
    assert (caption["section_number"], caption["appendix"], caption["text"]) == ("A", True, "Figure 5: Linear probe scores over k and τ.")


def test_block_equations_stay_inline_in_the_paragraph_before_them(tmp_path, elements):
    run_parse(tmp_path, elements)

    [chunk] = [c for c in read_chunks(tmp_path, elements) if c["section_number"] == "3.1"]
    # GROBID's linearised formulas, as it renders them, right after the sentence that leads into them.
    assert "Subwords in which no known n-gram occurs are initialized to zero. u x = g∈G (x) w g G" in chunk["text"]
    assert chunk["kind"] == "text"


def test_front_matter_other_than_the_title_and_abstract_is_dropped(tmp_path, elements):
    run_parse(tmp_path, elements)
    chunks = read_chunks(tmp_path, elements)

    texts = " ".join(c["text"] for c in chunks)
    for front_matter in ("Minixhofer", "benjamin.minixhofer@jku.at", "Johannes Kepler University", "State of Upper Austria", "FFG-881064"):
        assert front_matter not in texts
    assert chunks[0]["section_title"] == "Abstract"
    assert all(c["header"].startswith(WECHSEL_TITLE) for c in chunks)
    # Footnotes sit outside every Section in GROBID's TEI, so they are not read either.
    assert "Word Embeddings Can Help initialize Subword Embeddings in a new Language." not in texts


def test_the_report_counts_table_and_caption_chunks_per_file(tmp_path, grobid, elements):
    other = tmp_path / "pdfs" / "sennrich-bpe_1508.07909v5.pdf"
    other.write_bytes(fake_pdf("appendix in body"))
    grobid.serve(other.read_bytes(), "appendix-in-body.tei.xml")

    run_parse(tmp_path, elements, other, config=small_paper_config(tmp_path, 1000))

    report = (tmp_path / "parse-report.md").read_text()
    assert "| Pinned id | sha256 | Status | Sections | Chunks | Tables | Captions |\n|---|---|---|---:|---:|---:|---:|\n" in report
    # 10 Sections of one short paragraph each and a caption; at 1,000 tokens WECHSEL's Introduction and
    # Section 5.1 take two text Chunks each, beside one Chunk for each of its 2 tables and 1 caption.
    assert (
        f"| 1508.07909v5 | `{sha256(other.read_bytes())}` | parsed | 10 | 11 | 0 | 1 |\n"
        f"| 2112.06598v2 | `{sha256(elements.read_bytes())}` | parsed | 7 | 12 | 2 | 1 |\n"
    ) in report
    assert "- Sections: 17\n- Chunks: 23\n- Table Chunks: 2\n- Caption Chunks: 2\n" in report
