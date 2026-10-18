"""Which Editions are not papers, read from the metadata their sources recorded (ADR 0040)."""

import pytest

from chatbot_rag_tokenizers.collection.editions import Edition
from chatbot_rag_tokenizers.collection.papers import not_a_paper


def venue(edition_id: str = "10.5555/x.1", title: str = "Subword Units for Translation", **fields) -> Edition:
    return Edition(edition_id=edition_id, edition_kind="venue", title=title, abstract="", authors=[], year="2024", **fields)


def preprint(comments: str) -> Edition:
    return Edition(
        edition_id="2403.01580v1", edition_kind="arxiv-preprint", title="Low-Resource NMT", abstract="",
        authors=[], year="2024", arxiv_id="2403.01580", arxiv_comments=comments,
    )


def test_a_journal_paper_is_a_paper():
    assert not_a_paper(venue(doi="10.1162/tacl_a_00999", openalex_type="article")) == ""


def test_a_cran_package_manual_is_not_a_paper():
    edition = venue("10.32614/cran.package.tok", "tok: Fast Text Tokenization", doi="10.32614/cran.package.tok")
    assert not_a_paper(edition) == "not a paper: a CRAN package manual (DOI 10.32614/cran.package.tok)"


@pytest.mark.parametrize(
    "work_type",
    ["dissertation", "book", "paratext", "dataset", "software", "peer-review", "conference-abstract", "editorial", "erratum"],
)
def test_openalex_types_that_name_no_paper(work_type):
    assert not_a_paper(venue(openalex_type=work_type)) == f"not a paper: OpenAlex type {work_type}"


@pytest.mark.parametrize(
    "work_type",
    # A Springer LNCS paper is often a book-chapter, and "other" holds conference papers too.
    ["article", "preprint", "conference-paper", "book-chapter", "review", "report", "other", "", "data-paper"],
)
def test_openalex_types_that_can_be_papers(work_type):
    assert not_a_paper(venue(openalex_type=work_type)) == ""


def test_a_thesis_whose_repository_record_names_the_degree_is_not_a_paper():
    # W7135572887: OpenAlex types it "other", but UvA-DARE's record names the PhD.
    edition = venue(
        "W7135572887",
        "Exploring solutions for low-resource neural machine translation",
        openalex_type="other",
        openalex_raw_type="info:eu-repo/semantics/other",
        openalex_raw_source_name="Araabi, A 2024, 'Exploring solutions for low-resource neural machine translation',"
        " Doctor of Philosophy, Universiteit van Amsterdam.",
    )
    assert not_a_paper(edition) == "not a paper: a thesis, its repository record names a Doctor of Philosophy"


def test_a_talk_recording_is_not_a_paper():
    # Underline's DataCite records of conference talks.
    edition = venue("10.48448/b8ks-2x15", "Which Pieces Does Unigram Tokenization Really Need?",
                    openalex_type="other", openalex_raw_type="Audiovisual")
    assert not_a_paper(edition) == "not a paper: a recording, its DataCite resource type is Audiovisual"


def test_a_workshop_paper_from_a_repository_is_a_paper():
    edition = venue(
        openalex_type="conference-paper",
        openalex_raw_type="proceedings-article",
        openalex_raw_source_name="10th ISCA Workshop on Speech Synthesis (SSW 10)",
    )
    assert not_a_paper(edition) == ""


@pytest.mark.parametrize("acl_id", ["2025.wnut-1.0", "W18-1200", "P16-1000"])
def test_acl_front_matter_is_not_a_paper(acl_id):
    assert not_a_paper(venue(acl_id, acl_id=acl_id)) == f"not a paper: {acl_id} is the front matter of an ACL volume"


@pytest.mark.parametrize("acl_id", ["2025.wnut-1.10", "2020.findings-emnlp.414", "W18-1201", "P16-1162", "P16-1100"])
def test_acl_papers_are_papers(acl_id):
    assert not_a_paper(venue(acl_id, acl_id=acl_id)) == ""


@pytest.mark.parametrize(
    ("title", "reason"),
    [
        # Semantic Scholar records no type for these, so only the title tells.
        ("Text Tokenization using Byte Pair Encoding and Unigram Modelling [R package sentencepiece version 0.1.2]",
         "not a paper: an R package manual, by its title"),
        ("NAACL HLT 2018 Subword and Character LEvel Models in NLP Proceedings of the Second Workshop",
         "not a paper: a proceedings volume, by its title"),
        ("Proceedings of the Tenth Workshop on Noisy and User-generated Text",
         "not a paper: a proceedings volume, by its title"),
    ],
)
def test_titles_that_name_no_paper(title, reason):
    assert not_a_paper(venue("bc35cfb38ef0dce37f9b6ccf165f195ce6aa7817", title)) == reason


@pytest.mark.parametrize(
    "title",
    ["Package-Level Tokenizers for R Code", "Findings of the WMT 2018 Shared Task on Proceedings-Based Translation"],
)
def test_titles_of_papers(title):
    assert not_a_paper(venue(title=title)) == ""


@pytest.mark.parametrize(
    ("comments", "reason"),
    [
        ("PhD thesis", "not a paper: a thesis, by its arXiv comments: PhD thesis"),
        ("MSc Thesis, 44 pages", "not a paper: a thesis, by its arXiv comments: MSc Thesis, 44 pages"),
        ("Master's Thesis", "not a paper: a thesis, by its arXiv comments: Master's Thesis"),
        ("PhD Dissertation", "not a paper: a thesis, by its arXiv comments: PhD Dissertation"),
        ("Ph.D. Thesis Submitted in May 2020 in partial fulfilment of the requirements",
         "not a paper: a thesis, by its arXiv comments: Ph.D. Thesis Submitted in May 2020 in partial fulfilment of the requirements"),
        ("A dissertation submitted to the AASTMT on February 2019",
         "not a paper: a thesis, by its arXiv comments: A dissertation submitted to the AASTMT on February 2019"),
        ("136 pages, 12 practical works, preprint. Textbook for senior undergraduates and graduate students.",
         "not a paper: a textbook, by its arXiv comments: 136 pages, 12 practical works, preprint. Textbook for"
         " senior undergraduates and graduate students."),
    ],
)
def test_arxiv_comments_that_name_no_paper(comments, reason):
    assert not_a_paper(preprint(comments)) == reason


@pytest.mark.parametrize(
    "comments",
    [
        "Accepted to ACL 2023 Main Conference",
        # A report taken from a thesis is a paper of its own.
        "capstone work, technical report, 27 pages, extraction from PhD thesis https://doras.dcu.ie/26559/",
        "Submitted Manuscript/Preprint (accepted at EUSFLAT 2023, to be published in Lecture Notes in Computer Science (LNCS))",
        "18 pages. Code and data: https://github.com/Course-Correct-Labs/mirror-loop",
        "Adapted dissertation introduction",
    ],
)
def test_arxiv_comments_of_papers(comments):
    assert not_a_paper(preprint(comments)) == ""
