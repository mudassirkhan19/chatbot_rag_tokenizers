"""Offline runs of `index` and `evaluate` on Chunks parsed from the CC BY TEI fixtures through the fake GROBID service.

The corpus is WECHSEL v2 (arXiv 2112.06598v2) and a trimmed BPE paper (1508.07909v5), both CC BY 4.0. The
fixture Evaluation set (fixtures/eval/evaluation-set.jsonl) has a question of each type, with Passages quoted
from those two papers.
"""

import csv
import json
import shutil
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from parse_support import REPO_CONFIG, FakeGrobid, config_with_budget, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"
EVALUATION_SET = Path(__file__).parent / "fixtures" / "eval" / "evaluation-set.jsonl"
# Both fixture papers, each grouped with its venue Edition into one Work, neither of them a Survey.
WORK_GROUPS = Path(__file__).parent / "fixtures" / "eval" / "work-groups.csv"


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path/cache, with the parse report in tmp_path/parse-report.md."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return tmp_path


def run_index(tmp_path: Path, parse_config: Path = REPO_CONFIG, retrieval_config: Path = RETRIEVAL_CONFIG) -> None:
    main(
        [
            "index",
            "--parse-config", str(parse_config),
            "--config", str(retrieval_config),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
        ]
    )  # fmt: skip


def cache_files(tmp_path: Path) -> dict[Path, int]:
    """Every file in the index cache, with the time it was last written."""
    return {path: path.stat().st_mtime_ns for path in sorted((tmp_path / "index-cache").rglob("*")) if path.is_file()}


def test_index_builds_bm25_and_dense_and_a_rerun_with_nothing_changed_does_not_rebuild(corpus, capsys):
    run_index(corpus)
    built = cache_files(corpus)
    [chunking] = {path.parent.parent.name for path in built}
    assert chunking.startswith("chunking-")
    assert sorted(path.parent.name.split("-")[0] for path in built if path.name == "index.json") == ["bm25", "dense"]

    run_index(corpus)

    assert cache_files(corpus) == built
    assert "up to date" in capsys.readouterr().out


def with_revision(tmp_path: Path, revision: str) -> Path:
    """The repo's retrieval config with the dense model at another revision."""
    config = RETRIEVAL_CONFIG.read_text()
    pinned = load_retrieval_config(RETRIEVAL_CONFIG).dense.revision
    other = tmp_path / "retrieval-other-revision.toml"
    other.write_text(config.replace(pinned, revision))
    return other


def test_a_model_revision_change_rebuilds_the_dense_index_and_leaves_bm25_alone(corpus, tmp_path, capsys):
    run_index(corpus)
    before = cache_files(corpus)
    capsys.readouterr()

    run_index(corpus, retrieval_config=with_revision(tmp_path, "0" * 40))

    out = capsys.readouterr().out
    assert "bm25 is up to date" in out and "built dense" in out
    after = cache_files(corpus)
    assert {path: after[path] for path in before} == before
    assert len({path.parent for path in after} - {path.parent for path in before}) == 1


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


def test_chunks_rebuilt_differently_under_the_same_config_rebuild_the_index(corpus, capsys):
    # A change to the TEI reader or the Chunker (ADR 0043) re-chunks every file under the same cache keys.
    run_index(corpus)
    [chunks] = [path for path in (corpus / "cache").glob("*/*.chunks.jsonl") if "WECHSEL" in path.read_text(encoding="utf-8")]
    chunks.write_text(chunks.read_text(encoding="utf-8").replace("WECHSEL", "WECHSEL method", 1), encoding="utf-8")
    capsys.readouterr()

    run_index(corpus)

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


def run_evaluate(
    tmp_path: Path,
    evaluation_set: Path = EVALUATION_SET,
    report: str = "eval-report.md",
    work_groups: Path = WORK_GROUPS,
    options: tuple[str, ...] = (),
) -> str:
    """Run `evaluate` on the corpus in tmp_path and return the eval report."""
    main(
        [
            "evaluate",
            "--parse-config", str(REPO_CONFIG),
            "--config", str(RETRIEVAL_CONFIG),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
            "--evaluation-set", str(evaluation_set),
            "--manifest", str(ROOT / "data" / "manifest.csv"),
            "--work-groups", str(work_groups),
            "--report", str(tmp_path / report),
            *options,
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
    return {(row[0], row[2]): [row[1], row[3], row[4]] for row in table(report, "### Questions: bm25")}


def slots(report: str) -> dict[tuple[str, str], list[str]]:
    """BM25's line per question: (question id, query) to its [duplicate, restatement, mostly-numeric] top-5 slots."""
    return {(row[0], row[2]): row[5:] for row in table(report, "### Questions: bm25")}


def crowding(report: str) -> dict[str, list[str]]:
    """BM25's crowding table: measure to [top-5 slots, share of slots, questions, share of questions]."""
    return {row[0]: row[1:] for row in table(report, "### Crowding: bm25")}


def listed(report: str, heading: str) -> list[str]:
    """The last paragraph of a section: its list, or "None."."""
    return report.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].strip().split("\n\n")[-1].splitlines()


def as_a_user_asks(lines: dict[tuple[str, str], list[str]]) -> list[list[str]]:
    """The lines of every answerable question as a user would ask it: the all-answerable row's queries."""
    return [line for (_, query), line in lines.items() if query in ("as asked", "follow-up alone") and line[2] != "—"]


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


def test_the_report_records_the_dense_model_pin_and_each_retrievers_device(indexed):
    report = run_evaluate(indexed)

    retrievers = report.split("## Retrievers\n", 1)[1].split("\n## ", 1)[0]
    assert "  - model: `BAAI/bge-small-en-v1.5`" in retrievers
    assert "  - revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`" in retrievers
    assert "  - model_sha256: `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`" in retrievers
    timings = report.split("## Timings\n", 1)[1]
    # The fake embedder runs on the CPU, as BM25 does.
    for name in ("bm25", "dense"):
        [line] = [line for line in timings.splitlines() if line.startswith(f"- {name}:")]
        assert "index built on cpu in " in line and " queries on cpu, latency p50 " in line and ", p95 " in line


# BM25's top 5 for vocabulary-sizes: the BPE paper, the BPE paper, WECHSEL, then two mostly-numeric BPE Chunks
# (Section 4.1's last Chunk, mostly Table 1's cells, and Section 5.1's, the cells of Figure 2's table).


def test_a_second_chunk_from_the_same_work_counts_as_a_duplicate_slot(indexed):
    report = run_evaluate(indexed)

    # Ranks 2, 4 and 5 hold the BPE paper again; WECHSEL at rank 3 is a Work not ranked higher.
    assert slots(report)["vocabulary-sizes", "as asked"] == ["3", "0", "2"]
    # metrics-miss ranks only WECHSEL's Chunks: four repeat the first.
    assert slots(report)["metrics-miss", "as asked"] == ["4", "0", "0"]


@pytest.fixture
def with_venue_edition(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture corpus plus the BPE paper's ACL Edition (P16-1162), parsed from the same TEI as its preprint and
    indexed: another Edition of the same Work, with the same text."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
        seed_pdf(tmp_path, grobid, "P16-1162.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    run_index(tmp_path)
    return tmp_path


def test_a_chunk_from_another_edition_of_a_work_ranked_higher_counts_as_a_duplicate_slot(with_venue_edition, tmp_path):
    # The fixture Work groups join P16-1162 with the preprint; here it is its own Work instead.
    apart = tmp_path / "work-groups-venue-apart.csv"
    apart.write_text(WORK_GROUPS.read_text().replace("P16-1162,sennrich-2016-bpe,", "P16-1162,sennrich-2016-bpe-acl,"))

    joined = slots(run_evaluate(with_venue_edition, report="joined.md"))
    separate = slots(run_evaluate(with_venue_edition, work_groups=apart, report="apart.md"))

    # BM25's top 5: the preprint's Section 5.1 Chunk, the ACL Edition's copy of it, WECHSEL, then the preprint's and
    # the ACL Edition's Section 4.1 Chunk. Joined, ranks 2, 4 and 5 repeat the BPE Work; apart, the ACL Edition's
    # first Chunk at rank 2 is a new Work, and only ranks 4 and 5 repeat one.
    assert joined["vocabulary-sizes", "as asked"] == ["3", "0", "0"]
    assert separate["vocabulary-sizes", "as asked"] == ["2", "0", "0"]


def with_survey(tmp_path: Path, work_id: str) -> Path:
    """The fixture Work groups with one Work flagged as a Survey."""
    groups = tmp_path / "work-groups-survey.csv"
    groups.write_text(WORK_GROUPS.read_text().replace(f",{work_id},no,", f",{work_id},yes,"))
    return groups


def test_a_surveys_chunk_counts_as_restatement_not_as_a_duplicate(indexed, tmp_path):
    report = run_evaluate(indexed, work_groups=with_survey(tmp_path, "sennrich-2016-bpe"))

    # All four BPE Chunks restate; none of them, nor WECHSEL's, repeats a Work that isn't a Survey.
    assert slots(report)["vocabulary-sizes", "as asked"] == ["0", "4", "2"]


def test_the_crowding_totals_count_every_answerable_question_as_a_user_would_ask_it(indexed):
    report = run_evaluate(indexed)

    asked = as_a_user_asks(slots(report))
    assert len(asked) == 4
    totals = crowding(report)
    for measure, column in (("duplicate", 0), ("restatement", 1), ("mostly numeric", 2)):
        found = sum(int(line[column]) for line in asked)
        crowded = sum(1 for line in asked if int(line[column]))
        assert totals[measure] == [f"{found}/20", f"{found / 20:.2f}", f"{crowded}/4", f"{crowded / 4:.2f}"]
    assert "- Mostly-numeric slots holding a Passage: 0 of " in report.split("### Crowding: bm25", 1)[1]


def write_question(tmp_path: Path, record: dict) -> Path:
    """Write the question as the developer had checked it."""
    path = tmp_path / f"{record['id']}.jsonl"
    path.write_text(json.dumps({**record, "checked_by": "developer"}, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def test_a_mostly_numeric_chunk_is_counted_in_the_numeric_share_and_when_it_holds_a_passage(indexed, tmp_path):
    # The quote is in Section 4.1's last Chunk, between a footnote and Table 1's cells.
    alignment = {
        "id": "alignment",
        "type": "single-paper",
        "question": "Why is the character level suboptimal at the other end of the spectrum?",
        "passages": [
            {
                "edition_id": "1508.07909v5",
                "section": "4.1 Subword statistics",
                "quote": "At the other end of the spectrum, the character level is suboptimal for alignment",
            }
        ],
    }

    report = run_evaluate(indexed, write_question(tmp_path, alignment))

    assert questions(report)["alignment", "as asked"] == ["single-paper", "1", "1/1"]
    numeric = slots(report)["alignment", "as asked"][2]
    assert int(numeric) >= 1
    assert f"- Mostly-numeric slots holding a Passage: 1 of {numeric}\n" in report.split("### Crowding: bm25", 1)[1]


def without_bpe(tmp_path: Path) -> Path:
    """The fixture Work groups without the BPE paper's Work."""
    groups = tmp_path / "work-groups-wechsel-only.csv"
    groups.write_text("".join(line + "\n" for line in WORK_GROUPS.read_text().splitlines() if "sennrich" not in line))
    return groups


def test_evaluate_names_the_editions_without_a_work_group_and_leaves_their_questions_out(indexed, tmp_path, capsys):
    report = run_evaluate(indexed, work_groups=without_bpe(tmp_path))

    assert "1 Edition in the top 5 has no Work group: 1508.07909v5" in capsys.readouterr().out
    assert listed(report, "## Editions without a Work group") == ["- 1508.07909v5"]
    lines = slots(report)
    assert lines["vocabulary-sizes", "as asked"] == ["ungrouped", "ungrouped", "2"]
    assert lines["metrics-miss", "as asked"] == ["4", "0", "0"]
    # The duplicate rate counts only the questions whose top 5 are all grouped; the numeric share counts them all.
    grouped = [line for line in as_a_user_asks(lines) if line[0] != "ungrouped"]
    assert 0 < len(grouped) < 4
    totals = crowding(report)
    assert totals["duplicate"][0] == f"{sum(int(line[0]) for line in grouped)}/{5 * len(grouped)}"
    assert totals["duplicate"][2].endswith(f"/{len(grouped)}")
    assert totals["mostly numeric"][2].endswith("/4")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_the_export_lists_exactly_the_editions_in_the_top_5_without_a_work_group(indexed, tmp_path):
    export = tmp_path / "ungrouped.csv"

    run_evaluate(indexed, work_groups=without_bpe(tmp_path), options=("--export-ungrouped", str(export)))

    assert read_csv(export) == [
        {
            "edition_id": "1508.07909v5",
            "work_id": "",
            "survey": "",
            "title": "Neural Machine Translation of Rare Words with Subword Units",
            "authors": "Rico Sennrich; Barry Haddow; Alexandra Birch",
            "year": "2015",
            "venue": "",
        }
    ]


def test_the_export_is_empty_when_every_edition_in_the_top_5_has_a_work_group(indexed, tmp_path, capsys):
    export = tmp_path / "ungrouped.csv"

    report = run_evaluate(indexed, options=("--export-ungrouped", str(export)))

    assert export.read_text().splitlines() == ["edition_id,work_id,survey,title,authors,year,venue"]
    assert listed(report, "## Editions without a Work group") == ["None."]
    assert "no Work group" not in capsys.readouterr().out


def test_evaluate_stops_on_a_malformed_work_groups_file(indexed, tmp_path):
    groups = tmp_path / "bad.csv"
    groups.write_text(WORK_GROUPS.read_text().replace("sennrich-2016-bpe,no,", "sennrich-2016-bpe,maybe,", 1))

    with pytest.raises(SystemExit) as stopped:
        run_evaluate(indexed, work_groups=groups)

    assert str(groups) in str(stopped.value) and "survey" in str(stopped.value)
