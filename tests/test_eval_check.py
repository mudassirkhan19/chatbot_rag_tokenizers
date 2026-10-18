"""Offline runs of `eval-check`, and of `evaluate`'s gate, on Chunks parsed from the CC BY TEI fixtures.

The corpus is WECHSEL v2 (arXiv 2112.06598v2) and two Versions of a trimmed BPE paper: v5 (1508.07909v5) and a
v1 made from it by hand, with a reworded sentence, a changed number and a removed sentence in Section 5.1
(fixtures/tei/missed-table-v1.tei.xml). Each test writes its own Evaluation set.
"""

import json
import re
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from parse_support import REPO_CONFIG, FakeGrobid, run_parse, seed_pdf

UNIGRAM = "5.1 Unigram accuracy"
ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "data" / "manifest.csv"  # links the BPE paper's arXiv and ACL Editions
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path/cache, with the parse report in tmp_path/parse-report.md."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v1.pdf", "missed-table-v1.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return tmp_path


def passage(quote: str, section: str = UNIGRAM, edition_id: str = "1508.07909v5") -> dict:
    return {"edition_id": edition_id, "section": section, "quote": quote}


def question(id: str, *passages: dict, type: str = "single-paper", **fields) -> dict:
    return {"id": id, "type": type, "question": f"What does {id} say?", "passages": list(passages), **fields}


def write_set(tmp_path: Path, *questions: dict) -> Path:
    path = tmp_path / "evaluation-set.jsonl"
    path.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8")
    return path


def corpus_arguments(tmp_path: Path) -> list[str]:
    return [
        "--parse-config", str(REPO_CONFIG),
        "--cache", str(tmp_path / "cache"),
        "--parse-report", str(tmp_path / "parse-report.md"),
        "--index-cache", str(tmp_path / "index-cache"),
    ]  # fmt: skip


def run_eval_check(tmp_path: Path, evaluation_set: Path) -> None:
    """Run `eval-check` on the corpus in tmp_path; it prints its report."""
    main(
        [
            "eval-check",
            *corpus_arguments(tmp_path)[:6],
            "--evaluation-set", str(evaluation_set),
            "--manifest", str(MANIFEST),
        ]
    )  # fmt: skip


def held(out: str, question_id: str, number: int = 1) -> dict[str, int]:
    """Where eval-check found a Passage: the Chunks holding it, counted by pinned id."""
    line = re.search(rf"^{re.escape(question_id)} Passage {number}: .* held by \d+ Chunks?(?:: (?P<where>.*))?$", out, re.M)
    assert line, f"no line for {question_id} Passage {number} in:\n{out}"
    return {pinned: int(count) for pinned, count in re.findall(r"(\S+) \((\d+)\)", line["where"] or "")}


def test_a_reworded_quote_is_held_by_its_v1_chunk(corpus, capsys):
    # v1 says "conceal a few qualitative differences between the systems".
    reworded = passage("The F 1 numbers hide some qualitative differences between systems. For English→German, WDict produces few OOVs")
    run_eval_check(corpus, write_set(corpus, question("reworded", reworded)))

    assert held(capsys.readouterr().out, "reworded") == {"1508.07909v1": 1, "1508.07909v5": 1}


def test_a_quote_whose_number_changed_is_not_held_by_its_v1_chunk(corpus, capsys):
    # v1 says "4.8% recall"; every other word is the same.
    changed = passage("Consequently, the WDict baseline performs more poorly for OOVs (9.2% precision; 5.2% recall)")
    run_eval_check(corpus, write_set(corpus, question("changed-number", changed)))

    assert held(capsys.readouterr().out, "changed-number") == {"1508.07909v5": 1}


SUBWORDS = "4.1 Subword statistics"


def test_a_quote_whose_citation_was_redated_is_held_by_its_v1_chunk(corpus, capsys):
    # v1 cites (Tiedemann, 2008): a citation's year or number is not a finding.
    cited = passage("At the other end of the spectrum, the character level is suboptimal for alignment (Tiedemann, 2009).", SUBWORDS)
    run_eval_check(corpus, write_set(corpus, question("redated", cited)))

    assert held(capsys.readouterr().out, "redated") == {"1508.07909v1": 1, "1508.07909v5": 1}


def test_a_v1_chunk_with_list_numbers_the_quote_lacks_still_holds_it(corpus, capsys):
    # v1 numbers the techniques: "including (1) frequency-based compound splitting".
    listed = passage(
        "We report statistics for several word segmentation techniques that have proven useful in previous SMT research,"
        " including frequency-based compound splitting",
        SUBWORDS,
    )
    run_eval_check(corpus, write_set(corpus, question("list-numbers", listed)))

    assert held(capsys.readouterr().out, "list-numbers") == {"1508.07909v1": 1, "1508.07909v5": 1}


def test_a_number_left_alone_by_rewording_around_it_still_matches(corpus, capsys):
    # v1 says "rare (about 0.05% in the test set)": the number matches on its own, between reworded words.
    alone = passage(
        "Joint BPE can produce segments that are unknown because they only occur in the English training text, but these"
        " are rare (0.05% of test tokens).",
        SUBWORDS,
    )
    run_eval_check(corpus, write_set(corpus, question("lone-number", alone)))

    assert held(capsys.readouterr().out, "lone-number") == {"1508.07909v1": 1, "1508.07909v5": 1}


def test_word_pairs_scattered_across_a_chunk_do_not_hold_a_quote(corpus, capsys):
    # Each pair is in Section 4.1's first Chunk, in this order, but sentences apart.
    scattered = passage("Our main objective is the parallel data and translation results on the test set.", SUBWORDS)
    failures(corpus, question("scattered", scattered))

    assert held(capsys.readouterr().out, "scattered") == {}


def test_a_quote_spanning_two_chunks_is_held_by_both(corpus, capsys):
    # The first sentence ends one Chunk and the second starts the next, in both Versions; v1 rewords the second.
    spanning = passage(
        "reducing the size of the network vocabulary, and representing more words via subword units, can lead to"
        " better performance. The F 1 numbers hide some qualitative differences between systems."
    )
    run_eval_check(corpus, write_set(corpus, question("spanning", spanning)))

    assert held(capsys.readouterr().out, "spanning") == {"1508.07909v1": 2, "1508.07909v5": 2}


def test_eval_check_reports_each_questions_lexical_overlap_with_its_passages(corpus, capsys):
    # 5 of the question's 6 words are in the quote: all but "which".
    close = question("close", passage("The F 1 numbers hide some qualitative differences between systems."))
    close["question"] = "Which numbers hide differences between systems?"
    follow_up = question(
        "follow-up",
        passage("The F 1 numbers hide some qualitative differences between systems."),
        type="follow-up",
        history=["Do the systems differ?"],
        rewrite="Do F 1 numbers show every difference between systems?",
    )
    follow_up["question"] = "How so?"
    run_eval_check(corpus, write_set(corpus, close, follow_up))

    out = capsys.readouterr().out
    assert "close: lexical overlap 0.83 (5 of 6 question words are in its Passages)" in out
    # As asked, the follow-up shares no word; its rewrite shares f, 1, numbers, between and systems of 9.
    assert "follow-up: lexical overlap 0.00 (0 of 2 question words are in its Passages); rewrite 0.56 (5 of 9)" in out


def failures(tmp_path: Path, *questions: dict) -> str:
    """What eval-check says when it fails the set, which it must."""
    with pytest.raises(SystemExit) as stopped:
        run_eval_check(tmp_path, write_set(tmp_path, *questions))
    assert stopped.value.code not in (0, None)
    return str(stopped.value.code)


GOOD = question("good", passage("The F 1 numbers hide some qualitative differences between systems."))


def test_eval_check_fails_a_quote_that_is_not_in_its_edition_and_section(corpus):
    # v1 rewords this sentence, so the quote is only in v5; and it is in Section 5.1, not 4.1.
    in_v1 = passage("The F 1 numbers hide some qualitative differences between systems.", edition_id="1508.07909v1")
    other_section = passage("The F 1 numbers hide some qualitative differences between systems.", section="4.1 Subword statistics")
    out = failures(corpus, GOOD, question("in-v1", in_v1), question("other-section", other_section))

    assert "in-v1 Passage 1: the quote isn't in 1508.07909v1 › 5.1 Unigram accuracy" in out
    assert "other-section Passage 1: the quote isn't in 1508.07909v5 › 4.1 Subword statistics" in out
    assert "good" not in out


def test_eval_check_fails_a_quote_over_300_characters(corpus):
    text = (
        "The F 1 numbers hide some qualitative differences between systems. For English→German, WDict produces few OOVs"
        " (26.5% recall), but with high precision (60.6%) , whereas the subword systems achieve higher recall, but lower"
        " precision. We note that the character bigram model C2-50k produces the most OOV words,"
    )
    too_long, at_limit = text.removesuffix(" words,"), text.removeprefix("The F 1 ")
    assert (len(too_long), len(at_limit)) == (301, 300)
    out = failures(corpus, question("at-limit", passage(at_limit)), question("too-long", passage(too_long)))

    assert "too-long Passage 1: the quote is 301 characters long; the limit is 300" in out
    assert "at-limit" not in out


def test_eval_check_fails_a_malformed_follow_up_and_an_answerable_question_without_passages(corpus):
    found = GOOD["passages"][0]
    out = failures(
        corpus,
        question("no-rewrite", found, type="follow-up", history=["What does the BPE paper report?"]),
        question("no-history", found, type="follow-up", rewrite="What does the BPE paper say about F 1?"),
        question("history-but-not-follow-up", found, history=["What does the BPE paper report?"]),
        question("no-passages", type="single-paper"),
        question("unanswerable-with-passage", found, type="unanswerable"),
        question(
            "well-formed", found, type="follow-up", history=["What does the BPE paper report?"], rewrite="What does the BPE paper say about F 1?"
        ),
    )

    assert "no-rewrite: a follow-up needs a history and a rewrite" in out
    assert "no-history: a follow-up needs a history and a rewrite" in out
    assert "history-but-not-follow-up: only a follow-up has a history or a rewrite" in out
    assert "no-passages: an answerable question needs a Passage" in out
    assert "unanswerable-with-passage: an unanswerable question has no Passages" in out
    assert "well-formed" not in out


def test_eval_check_fails_a_multi_paper_question_whose_passages_come_from_one_work(corpus, grobid, tmp_path):
    # The ACL Anthology Edition of the BPE paper (P16-1162), which the manifest links to its arXiv preprint.
    venue = seed_pdf(tmp_path, grobid, "P16-1162.pdf", "missed-table.tei.xml")
    run_parse(tmp_path, *sorted((tmp_path / "pdfs").iterdir()))
    unchanged = "Figure 2 shows results for the English-German ensemble systems on newstest2015."
    wechsel = passage(
        "We choose temperature τ = 0.1 and neighbors k = 10 for WECHSEL",
        section="3.2 Subword similarity-based Transfer",
        edition_id="2112.06598v2",
    )
    out = failures(
        corpus,
        question("two-versions", passage(unchanged), passage(unchanged, edition_id="1508.07909v1"), type="multi-paper"),
        question("two-editions", passage(unchanged), passage(unchanged, edition_id=venue.stem), type="multi-paper"),
        question("two-works", passage(unchanged), wechsel, type="multi-paper"),
    )

    assert "two-versions: a multi-paper question needs Passages from at least two Works" in out
    assert "two-editions: a multi-paper question needs Passages from at least two Works" in out
    assert "two-works" not in out


def test_evaluate_refuses_a_set_that_fails_eval_check(corpus):
    main(["index", *corpus_arguments(corpus), "--config", str(RETRIEVAL_CONFIG)])
    broken = write_set(corpus, GOOD, question("no-passages"))

    with pytest.raises(SystemExit) as stopped:
        main(
            [
                "evaluate",
                *corpus_arguments(corpus),
                "--config", str(RETRIEVAL_CONFIG),
                "--evaluation-set", str(broken),
                "--manifest", str(MANIFEST),
                "--report", str(corpus / "eval-report.md"),
            ]
        )  # fmt: skip

    assert "fails eval-check" in str(stopped.value) and "no-passages: an answerable question needs a Passage" in str(stopped.value)
    assert not (corpus / "eval-report.md").exists()
