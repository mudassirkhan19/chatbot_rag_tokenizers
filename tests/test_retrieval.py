"""Offline runs of `index` and `evaluate` on Chunks parsed from the CC BY TEI fixtures through the fake GROBID service.

The corpus is WECHSEL v2 (arXiv 2112.06598v2) and a trimmed BPE paper (1508.07909v5), both CC BY 4.0. The
fixture Evaluation set (fixtures/eval/evaluation-set.jsonl) has a question of each type, with Passages quoted
from those two papers.
"""

import shutil
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from parse_support import REPO_CONFIG, FakeGrobid, config_with_budget, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"
EVALUATION_SET = Path(__file__).parent / "fixtures" / "eval" / "evaluation-set.jsonl"


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path/cache, with the parse report in tmp_path/parse-report.md."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return tmp_path


def run_index(tmp_path: Path, parse_config: Path = REPO_CONFIG) -> None:
    main(
        [
            "index",
            "--parse-config", str(parse_config),
            "--config", str(RETRIEVAL_CONFIG),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
        ]
    )  # fmt: skip


def cache_files(tmp_path: Path) -> dict[Path, int]:
    """Every file in the index cache, with the time it was last written."""
    return {path: path.stat().st_mtime_ns for path in sorted((tmp_path / "index-cache").rglob("*")) if path.is_file()}


def test_index_builds_bm25_and_a_rerun_with_nothing_changed_does_not_rebuild(corpus, capsys):
    run_index(corpus)
    built = cache_files(corpus)
    [index_dir] = {path.parent for path in built}
    assert index_dir.parent.name.startswith("chunking-") and index_dir.name.startswith("bm25-")

    run_index(corpus)

    assert cache_files(corpus) == built
    assert "up to date" in capsys.readouterr().out


def test_a_chunking_config_change_builds_a_new_index_and_leaves_the_old_one(corpus, tmp_path):
    run_index(corpus)
    before = cache_files(corpus)
    other = config_with_budget(tmp_path, 200)
    run_parse(tmp_path, *sorted((tmp_path / "pdfs").iterdir()), config=other)

    run_index(corpus, parse_config=other)

    after = cache_files(corpus)
    assert {path: after[path] for path in before} == before
    new = {path.parent.parent.name for path in after} - {path.parent.parent.name for path in before}
    assert len(new) == 1 and new.pop().startswith("chunking-")


def test_a_new_grobid_image_rebuilds_the_index_over_the_new_parse(corpus, tmp_path, capsys):
    run_index(corpus)
    other = tmp_path / "parse-new-grobid.toml"
    other.write_text(
        config_with_budget(tmp_path, 350).read_text().replace(load_parse_config(REPO_CONFIG).grobid.digest, "sha256:" + "0" * 64)
    )
    run_parse(tmp_path, *sorted((tmp_path / "pdfs").iterdir()), config=other)
    capsys.readouterr()

    run_index(corpus, parse_config=other)

    out = capsys.readouterr().out
    assert "built bm25" in out and "up to date" not in out


def test_index_says_when_the_parse_cache_is_empty(corpus, capsys):
    shutil.rmtree(corpus / "cache")

    with pytest.raises(SystemExit) as stopped:
        run_index(corpus)

    assert "holds no Chunks" in str(stopped.value) and "just parse" in str(stopped.value)
    assert not (corpus / "index-cache").exists()


def test_index_says_when_the_parse_cache_was_built_with_another_chunking_config(corpus, tmp_path):
    other = config_with_budget(tmp_path, 200)
    # The cache now holds Chunks under the other config only, while the report still names the repo's.
    for path in (tmp_path / "cache").rglob("*.chunks.jsonl"):
        path.unlink()
    report = (tmp_path / "parse-report.md").read_text()
    run_parse(tmp_path, *sorted((tmp_path / "pdfs").iterdir()), config=other)
    (tmp_path / "parse-report.md").write_text(report)

    with pytest.raises(SystemExit) as stopped:
        run_index(corpus)

    assert "another chunking config" in str(stopped.value)


def test_index_says_when_the_parse_report_was_written_with_another_chunking_config(corpus, tmp_path):
    run_parse(tmp_path, *sorted((tmp_path / "pdfs").iterdir()), config=config_with_budget(tmp_path, 200))

    with pytest.raises(SystemExit) as stopped:
        run_index(corpus)

    assert "another GROBID image or chunking config" in str(stopped.value)


def run_evaluate(tmp_path: Path, evaluation_set: Path = EVALUATION_SET, report: str = "eval-report.md") -> str:
    """Run `evaluate` with BM25 on the corpus in tmp_path and return the eval report."""
    main(
        [
            "evaluate",
            "--parse-config", str(REPO_CONFIG),
            "--config", str(RETRIEVAL_CONFIG),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
            "--evaluation-set", str(evaluation_set),
            "--report", str(tmp_path / report),
        ]
    )  # fmt: skip
    return (tmp_path / report).read_text()


def table(report: str, heading: str) -> list[list[str]]:
    """The body rows of the Markdown table under a heading, each as its cells."""
    lines = report.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0].splitlines()
    rows = [line for line in lines if line.startswith("|")][2:]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]


def results(report: str) -> dict[tuple[str, str], list[str]]:
    """BM25's results table: (question type, query) to [questions, Recall@5, MRR@10, Hit@5]."""
    return {(row[0], row[1]): row[2:] for row in table(report, "### Results: bm25")}


def questions(report: str) -> dict[tuple[str, str], list[str]]:
    """BM25's line per question: (question id, query) to [type, rank of first hit, Passages found]."""
    return {(row[0], row[2]): [row[1], *row[3:]] for row in table(report, "### Questions: bm25")}


@pytest.fixture
def indexed(corpus: Path) -> Path:
    run_index(corpus)
    return corpus


def test_recall_at_5_counts_each_passage_of_a_question(indexed):
    report = run_evaluate(indexed)

    # WECHSEL's Passage is held at rank 3 and the BPE paper's only at rank 8: one of two Passages in the top 5.
    assert questions(report)["vocabulary-sizes", "as asked"] == ["multi-paper", "3", "1/2"]
    assert results(report)["multi-paper", "as asked"] == ["1", "0.50", "0.333", "1.00"]


def test_mrr_at_10_is_zero_when_no_chunk_in_the_top_10_holds_a_passage(indexed):
    report = run_evaluate(indexed)

    assert questions(report)["metrics-miss", "as asked"] == ["single-paper", "none", "0/1"]
    # Averaged with the other single-paper question, whose Passage is held at rank 2: (1/2 + 0) / 2.
    assert questions(report)["freezing", "as asked"][1] == "2"
    assert results(report)["single-paper", "as asked"] == ["2", "0.50", "0.250", "0.50"]


def test_a_passage_quoted_from_another_edition_counts_when_a_chunk_holds_its_text(indexed):
    # The freezing question's Passage names WECHSEL's venue Edition, which isn't in the corpus; v2 holds its text.
    # (Figure 6's caption, which repeats "freeze" and "TransInner", ranks first.)
    report = run_evaluate(indexed)

    assert questions(report)["freezing", "as asked"] == ["single-paper", "2", "1/1"]


def test_unanswerable_questions_are_left_out_of_the_metrics(indexed, tmp_path):
    answerable = tmp_path / "answerable.jsonl"
    lines = EVALUATION_SET.read_text().splitlines()
    answerable.write_text("".join(line + "\n" for line in lines if '"unanswerable"' not in line))

    with_unanswerable = results(run_evaluate(indexed))
    without = results(run_evaluate(indexed, answerable, report="answerable-report.md"))

    assert with_unanswerable.pop(("unanswerable", "left out")) == ["1", "—", "—", "—"]
    assert without.pop(("unanswerable", "left out")) == ["0", "—", "—", "—"]
    assert with_unanswerable == without
    assert with_unanswerable["all answerable", "as asked, follow-ups alone"][0] == "4"


def test_a_follow_up_is_scored_alone_with_its_history_and_as_its_reference_rewrite(indexed):
    report = run_evaluate(indexed)

    lines = {query: line for (question, query), line in questions(report).items() if question == "neighbours"}
    assert list(lines) == ["follow-up alone", "history + follow-up", "reference rewrite"]
    # Alone, the follow-up names nothing to search for; its history and its rewrite name WECHSEL's settings.
    assert lines["follow-up alone"] == ["follow-up", "none", "0/1"]
    assert lines["history + follow-up"] == ["follow-up", "3", "1/1"]
    assert lines["reference rewrite"] == ["follow-up", "2", "1/1"]
    assert [query for kind, query in results(report) if kind == "follow-up"] == list(lines)


def test_two_runs_give_the_same_report_apart_from_timings(indexed):
    first = run_evaluate(indexed, report="first.md")
    second = run_evaluate(indexed, report="second.md")

    assert "## Timings" in first
    assert first.split("## Timings")[0] == second.split("## Timings")[0]


def test_evaluate_says_when_the_index_has_not_been_built(corpus):
    with pytest.raises(SystemExit) as stopped:
        run_evaluate(corpus)

    assert "just index" in str(stopped.value)
