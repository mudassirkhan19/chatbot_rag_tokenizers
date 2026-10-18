"""Numbered headings GROBID left inside a paragraph (#41), run through the CLI against a fake GROBID service.

`lost-heading.tei.xml` is the TEI of arXiv 2604.14053v1 (CC BY 4.0), trimmed by hand. GROBID didn't recognise
the head "2 Related Work" and left it as the first words of an Introduction paragraph, on boxes taller than the
body lines. The file's opening comment lists what was made up for the tests. `lost-heading-at-sentence-end.tei.xml`
is the TEI of ACL Anthology D18-1278 (CC BY 4.0), trimmed by hand: GROBID left "3 Experiments" at the start of a
paragraph of Section 2.3 and "4 Analysis" at the end of that paragraph's last sentence.
"""

from pathlib import Path

import pytest

from parse_support import FakeGrobid, config_with_budget, fake_pdf, read_chunks, run_parse

INTRODUCTION = ("1 Introduction",)
RELATED_WORK = ("2 Related Work",)
ANALYSIS = ("3 Analysis",)


def parse(tmp_path: Path, grobid: FakeGrobid, name: str, fixture: str) -> list[dict]:
    pdf = tmp_path / "pdfs" / f"{name}.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(fake_pdf(fixture))
    grobid.serve(pdf.read_bytes(), fixture)
    config = config_with_budget(tmp_path, 350)
    config.write_text(config.read_text().replace("min_body_characters = 2000", "min_body_characters = 500"))
    run_parse(tmp_path, pdf, config=config)
    return read_chunks(tmp_path, pdf)


@pytest.fixture
def chunks(tmp_path: Path, grobid: FakeGrobid) -> list[dict]:
    return parse(tmp_path, grobid, "2604.14053v1", "lost-heading.tei.xml")


def text_of(chunks: list[dict], path: tuple[str, ...]) -> str:
    return " ".join(c["text"] for c in chunks if tuple(c["section_path"]) == path)


def test_a_numbered_heading_left_at_the_start_of_a_paragraph_starts_its_own_section(chunks):
    sections = list(dict.fromkeys((c["section_number"], c["section_title"], tuple(c["section_path"])) for c in chunks))
    assert sections == [
        ("", "Abstract", ("Abstract",)),
        ("1", "Introduction", INTRODUCTION),
        ("2", "Related Work", RELATED_WORK),
        ("3", "Analysis", ANALYSIS),
    ]
    related = [c for c in chunks if tuple(c["section_path"]) == RELATED_WORK]
    # The heading leaves the text for the path and the context header, and the paragraphs after it follow it.
    assert related[0]["text"].startswith("Tokenization and Regularization. Typical alternatives to BPE")
    assert "Under-Trained Tokens." in text_of(chunks, RELATED_WORK)
    assert related[0]["header"].endswith("› 2 Related Work")
    assert (related[0]["page_start"], related[-1]["page_end"]) == (2, 3)
    introduction = text_of(chunks, INTRODUCTION)
    assert "Related Work" not in introduction and "Typical alternatives to BPE" not in introduction


def test_a_sentence_that_starts_with_a_number_on_body_lines_stays_text(chunks):
    analysis = text_of(chunks, ANALYSIS)
    assert "3 models are studied here, all of them coding language models:" in analysis
    assert "4 Of the three, CodeGemma and Qwen have larger vocabularies," in analysis
    assert not any(c["section_number"] == "4" for c in chunks)


def test_a_heading_whose_number_does_not_continue_the_sections_stays_text(chunks):
    # A copy of the "2 Related Work" paragraph after Section 3, on the same tall boxes: Section 2 can't come again.
    assert "2 Related Work Tokenization and Regularization. Typical alternatives to BPE" in text_of(chunks, ANALYSIS)
    assert [c["section_number"] for c in chunks if c["section_number"] == "2"] == [
        c["section_number"] for c in chunks if tuple(c["section_path"]) == RELATED_WORK
    ]


def test_a_numbered_heading_left_at_the_end_of_a_sentence_starts_its_own_section(tmp_path, grobid):
    chunks = parse(tmp_path, grobid, "D18-1278", "lost-heading-at-sentence-end.tei.xml")

    sections = list(dict.fromkeys((c["section_number"], tuple(c["section_path"])) for c in chunks))
    assert sections == [
        ("", ("Abstract",)),
        ("1", ("1 Introduction",)),
        ("2", ("2 Dependency parsing model",)),
        ("2.3", ("2 Dependency parsing model", "2.3 Computing word representations")),
        ("3", ("3 Experiments",)),
        ("4.1", ("4 Analysis", "4.1 Why do characters beat words?")),
    ]
    experiments = text_of(chunks, ("3 Experiments",))
    assert experiments.startswith("Data We experiment on twelve languages")
    assert experiments.endswith("This reinforces a finding of")
    assert "4 Analysis" not in experiments
