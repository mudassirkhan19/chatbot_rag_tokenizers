"""Offline runs of `index` and `evaluate` on Chunks parsed from the CC BY TEI fixtures through the fake GROBID service.

The corpus is WECHSEL v2 (arXiv 2112.06598v2) and a trimmed BPE paper (1508.07909v5), both CC BY 4.0. The
fixture Evaluation set (fixtures/eval/evaluation-set.jsonl) has a question of each type, with Passages quoted
from those two papers.
"""

import csv
import json
import re
import shutil
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval import index
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed, Merged
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from parse_support import REPO_CONFIG, FakeGrobid, config_with_budget, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"
EVALUATION_SET = Path(__file__).parent / "fixtures" / "eval" / "evaluation-set.jsonl"
# Both fixture papers, each grouped with its venue Edition into one Work, neither of them a Survey.
WORK_GROUPS = Path(__file__).parent / "fixtures" / "eval" / "work-groups.csv"
# The manifest's rows for the fixture papers and their venue Editions, as `collect` grouped them: each paper's
# venue Edition is its Work's Canonical Edition, and neither Work is a Survey.
MANIFEST = Path(__file__).parent / "fixtures" / "eval" / "manifest.csv"


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path/cache, with the parse report in tmp_path/parse-report.md."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return tmp_path


def run_index(
    tmp_path: Path, parse_config: Path = REPO_CONFIG, retrieval_config: Path = RETRIEVAL_CONFIG, options: tuple[str, ...] = ()
) -> None:
    main(
        [
            "index",
            "--parse-config", str(parse_config),
            "--config", str(retrieval_config),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
            # A Seed run has no manifest, so no Edition is marked indexed; never the repo's own manifest.
            "--snapshot", str(tmp_path / "snapshot"),
            "--manifest", str(tmp_path / "manifest.csv"),
            "--funnel-report", str(tmp_path / "report.md"),
            *options,
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
    assert sorted(path.parent.name.split("-")[0] for path in built if path.name == "index.json") == ["bm25", "dense", "dense", "dense", "hybrid", "hybrid", "hybrid"]

    run_index(corpus)

    assert cache_files(corpus) == built
    assert "up to date" in capsys.readouterr().out


def with_revision(tmp_path: Path, revision: str) -> Path:
    """The repo's retrieval config with dense.bge-small at another revision."""
    config = RETRIEVAL_CONFIG.read_text()
    [pinned] = [dense.revision for dense in load_retrieval_config(RETRIEVAL_CONFIG).dense if dense.name == "dense.bge-small"]
    other = tmp_path / "retrieval-other-revision.toml"
    other.write_text(config.replace(pinned, revision))
    return other


def test_a_model_revision_change_rebuilds_that_dense_index_and_leaves_the_others_alone(corpus, tmp_path, capsys):
    run_index(corpus)
    before = cache_files(corpus)
    capsys.readouterr()

    run_index(corpus, retrieval_config=with_revision(tmp_path, "0" * 40))

    out = capsys.readouterr().out
    assert "bm25 is up to date" in out and "built dense.bge-small" in out
    assert "dense.bge-base is up to date" in out and "dense.openscholar is up to date" in out
    # bge-small's key is part of its hybrid's, so that hybrid gets a new folder too; the other hybrids don't.
    assert "built hybrid.bm25+bge-small" in out and "hybrid.bm25+bge-base is up to date" in out
    after = cache_files(corpus)
    assert {path: after[path] for path in before} == before
    new = {path.parent for path in after} - {path.parent for path in before}
    assert sorted(folder.name.split("-")[0] for folder in new) == ["dense", "hybrid"]


# A second dense table beside bge-small, as the embedding comparison adds them (ADR 0050).
OTHER_TABLE = """
[dense.other]
model = "example/other-embedder"
revision = "1111111111111111111111111111111111111111"
model_sha256 = "2222222222222222222222222222222222222222222222222222222222222222"
pooling = "mean"
max_tokens = 256
query_instruction = "Represent this sentence for searching relevant passages: "
"""


def with_two_dense_tables(tmp_path: Path, other_revision: str = "1" * 40) -> Path:
    """The repo's retrieval config plus [dense.other], at the revision given."""
    path = tmp_path / "retrieval-two-dense.toml"
    path.write_text(RETRIEVAL_CONFIG.read_text() + OTHER_TABLE.replace("1" * 40, other_revision))
    return path


def index_folders(tmp_path: Path) -> dict[str, Path]:
    """Each built index's folder, by the retriever its record names."""
    records = (tmp_path / "index-cache").rglob("index.json")
    return {json.loads(record.read_text())["retriever"]: record.parent for record in records}


def test_each_dense_table_gets_its_own_index_and_a_revision_change_rebuilds_only_that_table(corpus, tmp_path, capsys):
    run_index(corpus, retrieval_config=with_two_dense_tables(tmp_path))
    first = index_folders(corpus)
    dense = ["bm25", "dense.bge-base", "dense.bge-small", "dense.openscholar", "dense.other"]
    assert sorted(name for name in first if not name.startswith("hybrid.")) == dense
    assert len(set(first.values())) == len(first)
    before = cache_files(corpus)
    capsys.readouterr()

    run_index(corpus, retrieval_config=with_two_dense_tables(tmp_path, other_revision="3" * 40))

    out = capsys.readouterr().out
    for name in ("bm25", "dense.bge-small", "dense.bge-base", "dense.openscholar"):
        assert f"{name} is up to date" in out
    assert "built dense.other" in out
    after = cache_files(corpus)
    assert {path: after[path] for path in before} == before
    [new] = {path.parent for path in after} - {path.parent for path in before}
    assert new.name.startswith("dense-") and new != first["dense.other"]


def test_two_dense_models_rank_the_fixture_differently(corpus, tmp_path):
    # The two tables differ in model id and settings the fake embedder ignores, not in query instruction.
    config = with_two_dense_tables(tmp_path)
    run_index(corpus, retrieval_config=config)

    report = run_evaluate(corpus, retrieval_config=config)

    bge_small, other = table(report, "### Questions: dense.bge-small"), table(report, "### Questions: dense.other")
    assert [row[:3] for row in bge_small] == [row[:3] for row in other]
    assert bge_small != other


@pytest.mark.parametrize("name", ["dense.bge-small", "dense.bge-base", "dense.openscholar"])
def test_retriever_names_one_dense_model_and_only_that_one_is_built_and_scored(corpus, name):
    run_index(corpus, options=("--retriever", name))

    assert list(index_folders(corpus)) == [name]
    report = run_evaluate(corpus, options=("--retriever", name))
    assert f"### Results: {name}" in report and "### Results: bm25" not in report


def test_building_a_hybrid_alone_builds_its_members_first_and_stores_no_vectors(corpus, capsys):
    run_index(corpus, options=("--retriever", "hybrid.bm25+bge-small"))

    out = capsys.readouterr().out
    assert out.index("built bm25") < out.index("built dense.bge-small") < out.index("built hybrid.bm25+bge-small")
    folders = index_folders(corpus)
    assert sorted(folders) == ["bm25", "dense.bge-small", "hybrid.bm25+bge-small"]
    hybrid = folders["hybrid.bm25+bge-small"]
    assert [path.name for path in hybrid.iterdir()] == ["index.json"]
    record = json.loads((hybrid / "index.json").read_text())
    assert record["members"] == {name: folders[name].name for name in ("bm25", "dense.bge-small")}
    members = [json.loads((folders[name] / "index.json").read_text()) for name in ("bm25", "dense.bge-small")]
    assert record["build_seconds"] == round(sum(member["build_seconds"] for member in members), 3)
    built = cache_files(corpus)

    run_index(corpus, options=("--retriever", "hybrid.bm25+bge-small"))

    assert cache_files(corpus) == built
    assert "built" not in capsys.readouterr().out


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
    retrieval_config: Path = RETRIEVAL_CONFIG,
    manifest: Path = MANIFEST,
) -> str:
    """Run `evaluate` on the corpus in tmp_path and return the eval report."""
    main(
        [
            "evaluate",
            "--parse-config", str(REPO_CONFIG),
            "--config", str(retrieval_config),
            "--cache", str(tmp_path / "cache"),
            "--parse-report", str(tmp_path / "parse-report.md"),
            "--index-cache", str(tmp_path / "index-cache"),
            "--evaluation-set", str(evaluation_set),
            "--manifest", str(manifest),
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
    for name in ("bm25", "dense.bge-small"):
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
            "checked_by": "",
            "note": "",
        }
    ]


def test_the_export_is_empty_when_every_edition_in_the_top_5_has_a_work_group(indexed, tmp_path, capsys):
    export = tmp_path / "ungrouped.csv"

    report = run_evaluate(indexed, options=("--export-ungrouped", str(export)))

    assert export.read_text().splitlines() == ["edition_id,work_id,survey,title,authors,year,venue,checked_by,note"]
    assert listed(report, "## Editions without a Work group") == ["None."]
    assert "no Work group" not in capsys.readouterr().out


def test_the_report_counts_the_editions_a_person_checked(indexed, tmp_path):
    groups = tmp_path / "partly-checked.csv"
    lines = WORK_GROUPS.read_text().splitlines()
    groups.write_text(f"{lines[0]},checked_by\n{lines[1]},mudassir\n{lines[2]},\n{lines[3]},mudassir\n{lines[4]},\n")

    report = run_evaluate(indexed, work_groups=groups)

    assert "4 Editions in 2 Works, 2 of the Editions checked (who checked each is in checked_by)," in report


def test_evaluate_stops_on_a_malformed_work_groups_file(indexed, tmp_path):
    groups = tmp_path / "bad.csv"
    groups.write_text(WORK_GROUPS.read_text().replace("sennrich-2016-bpe,no,", "sennrich-2016-bpe,maybe,", 1))

    with pytest.raises(SystemExit) as stopped:
        run_evaluate(indexed, work_groups=groups)

    assert str(groups) in str(stopped.value) and "survey" in str(stopped.value)


# A hybrid small enough to fuse by hand: each member's top 3, and k = 1, so ranks 1, 2 and 3 score 1/2, 1/3 and 1/4.
TINY_HYBRID = """
[hybrid.tiny]
members = ["bm25", "dense.bge-small"]
k = 1
pool = 3
"""


def test_a_hybrid_ranks_by_the_sum_of_its_members_reciprocal_ranks(indexed, tmp_path):
    config = tmp_path / "retrieval-tiny.toml"
    config.write_text(RETRIEVAL_CONFIG.read_text() + TINY_HYBRID)
    run_index(indexed, retrieval_config=config, options=("--retriever", "hybrid.tiny"))
    corpus = load_corpus(load_parse_config(REPO_CONFIG), indexed / "cache", indexed / "parse-report.md")
    retrievers = load_retrieval_config(config).retrievers

    query = "byte pair encoding merges"

    def ranking(name: str) -> list[tuple[str, float]]:
        return index.load(indexed / "index-cache", corpus, retrievers[name]).retriever.query(query, 10)

    bpe, wechsel = "ca5dde4cb76ce13c", "6ac34dd4fce57e87"
    # The members disagree: they share only BPE's first Chunk, at rank 1 in BM25 and rank 3 in the dense model.
    assert [chunk_id for chunk_id, _ in ranking("bm25")[:3]] == [f"{bpe}-0000", f"{bpe}-0006", f"{wechsel}-0018"]
    assert [chunk_id for chunk_id, _ in ranking("dense.bge-small")[:3]] == [f"{wechsel}-0023", f"{wechsel}-0031", f"{bpe}-0000"]
    # 1/2 + 1/4 for the shared Chunk; 1/2 for the dense model's first; 1/3 for each member's second, BM25's first as
    # it is listed first; 1/4 for BM25's third. Each member's other Chunks are outside its pool of 3.
    expected = [(f"{bpe}-0000", 0.75), (f"{wechsel}-0023", 0.5), (f"{bpe}-0006", 1 / 3), (f"{wechsel}-0031", 1 / 3), (f"{wechsel}-0018", 0.25)]
    assert ranking("hybrid.tiny") == pytest.approx(expected)
    # Built in memory over the Chunks, as from the index cache.
    assert retrievers["hybrid.tiny"].build(corpus.chunks).query(query, 10) == ranking("hybrid.tiny")


def test_evaluate_scores_a_hybrid_in_every_table_and_records_its_members_k_and_pool(corpus):
    name = "hybrid.bm25+bge-small"
    run_index(corpus, options=("--retriever", name))
    folders = index_folders(corpus)

    report = run_evaluate(corpus, options=("--retriever", name))

    for heading in ("Results", "Crowding", "Questions"):
        assert len(table(report, f"### {heading}: {name}")) > 1
    retrievers = report.split("## Retrievers\n", 1)[1].split("\n## ", 1)[0]
    bm25, bge_small = folders["bm25"].name, folders["dense.bge-small"].name
    assert f"- {name}: `{folders[name].name}`" in retrievers
    assert f"  - members: `bm25 ({bm25}), dense.bge-small ({bge_small})`" in retrievers
    assert "  - k: `60`" in retrievers and "  - pool: `100`" in retrievers
    [timing] = [line for line in report.split("## Timings\n", 1)[1].splitlines() if line.startswith(f"- {name}:")]
    assert "index built on cpu in " in timing and " queries on cpu, latency p50 " in timing


def test_evaluate_says_when_a_member_of_a_hybrid_has_no_index(corpus):
    run_index(corpus, options=("--retriever", "hybrid.bm25+bge-small"))
    shutil.rmtree(index_folders(corpus)["dense.bge-small"])

    with pytest.raises(SystemExit) as stopped:
        run_evaluate(corpus, options=("--retriever", "hybrid.bm25+bge-small"))

    assert "no dense.bge-small index" in str(stopped.value) and "just index" in str(stopped.value)


# The Collapsed ranking (#52): every retriever's `+collapsed` twin, over the same index.


def headings(report: str) -> list[str]:
    return [line for line in report.splitlines() if line.startswith("### ")]


def test_every_retriever_gets_a_collapsed_twin_in_every_table(indexed):
    report = run_evaluate(indexed)

    names = ["bm25", "dense.bge-small", "dense.bge-base", "dense.openscholar"]
    names += ["hybrid.bm25+bge-small", "hybrid.bm25+bge-base", "hybrid.bm25+openscholar"]
    for section in ("Results", "Crowding", "Questions"):
        assert [h for h in headings(report) if h.startswith(f"### {section}: ")] == [
            f"### {section}: {name}{twin}" for name in names for twin in ("", "+collapsed")
        ]
    retrievers = report.split("## Retrievers\n", 1)[1].split("\n## ", 1)[0]
    timings = report.split("## Timings\n", 1)[1]
    for name in names:
        assert f"- {name}+collapsed: {name}'s index, with copies from other files of a Work merged" in retrievers
        assert f"- {name}+collapsed: index built on cpu" in timings


def collapsed_lines(report: str, retriever: str = "bm25") -> dict[tuple[str, str], list[str]]:
    """A Collapsed ranking's line per question: (question id, query) to its [duplicate, restatement, numeric] slots and
    its top-5 files, each with the merged ones after a +."""
    return {(row[0], row[2]): row[5:] for row in table(report, f"### Questions: {retriever}+collapsed")}


def test_the_collapse_merges_copies_from_other_files_and_keeps_a_works_other_chunks(with_venue_edition):
    report = run_evaluate(with_venue_edition)

    # Raw, as before: the preprint's Section 5.1 Chunk, the ACL Edition's copy of it, WECHSEL, then the preprint's and
    # the ACL Edition's copies of the last Chunk of Section 4.1: ranks 2, 4 and 5 repeat the BPE Work.
    assert slots(report)["vocabulary-sizes", "as asked"] == ["3", "0", "0"]
    # Collapsed: each copy pair is one slot, shown by the Canonical Edition with the preprint merged into it. Section
    # 4.1's Chunk is other text of the same paper, so it keeps its own slot, and counts as a same-file duplicate.
    [*counts, files] = collapsed_lines(report)["vocabulary-sizes", "as asked"]
    assert files.startswith("P16-1162 + 1508.07909v5; 2112.06598v2; P16-1162 + 1508.07909v5")
    assert counts[0] != "0"
    for retriever in ("bm25", "dense.bge-small"):
        raw = {row[0]: row[1:] for row in table(report, f"### Crowding: {retriever}")}
        collapsed = {row[0]: row[1:] for row in table(report, f"### Crowding: {retriever}+collapsed")}
        assert raw["duplicate: another Edition or Version"][0] != "0/20"
        assert collapsed["duplicate: another Edition or Version"][0].startswith("0/")
        assert collapsed["duplicate: same file"][0] == collapsed["duplicate"][0]


@pytest.fixture
def with_v1(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture corpus with the BPE paper's v1 beside its latest Version, both indexed under the Edition
    1508.07909v5. v1's Section 5.1 says the F1 numbers "conceal a few" differences where v5 says "hide some"."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v1.pdf", "missed-table-v1.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    run_index(tmp_path)
    return tmp_path


def qualitative_differences(tmp_path: Path) -> Path:
    """Two questions on BPE's Section 5.1: one worded as v1 words it, which BM25 ranks v1's Chunk first for and v5's
    after it, and one in a word only v1 has, which only v1's Chunk is ranked for."""
    questions = [
        {
            "id": "both-versions",
            "type": "single-paper",
            "question": "Which qualitative differences between the systems do the F1 numbers conceal?",
            "passages": [
                {"edition_id": "1508.07909v5", "section": "5.1 Unigram accuracy", "quote": "The F 1 numbers hide some qualitative differences between systems"}
            ],
        },
        {
            "id": "only-v1",
            "type": "single-paper",
            "question": "conceal",
            "passages": [
                {
                    "edition_id": "1508.07909v1",
                    "section": "5.1 Unigram accuracy",
                    "quote": "The F 1 numbers conceal a few qualitative differences between the systems",
                }
            ],
        },
    ]
    path = tmp_path / "versions.jsonl"
    path.write_text("".join(json.dumps({**q, "checked_by": "developer"}) + "\n" for q in questions), encoding="utf-8")
    return path


def test_the_latest_version_stands_for_its_work_when_it_is_in_the_pool_and_v1_only_when_it_is_not(with_v1, tmp_path):
    report = run_evaluate(with_v1, qualitative_differences(tmp_path))

    lines = collapsed_lines(report)
    assert lines["both-versions", "as asked"][3].startswith("1508.07909v5 + 1508.07909v1; ")
    assert lines["only-v1", "as asked"][3] == "1508.07909v1"


def manifest_with(tmp_path: Path, name: str, **columns: str) -> Path:
    """The fixture manifest with these columns set on the BPE paper's two Editions."""
    rows = read_csv(MANIFEST)
    for row in rows:
        if row["edition_id"] in ("1508.07909v5", "P16-1162"):
            row.update(columns)
    path = tmp_path / f"manifest-{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_an_edition_without_a_work_id_keeps_its_slot_as_its_own_work(with_venue_edition, tmp_path):
    report = run_evaluate(with_venue_edition, manifest=manifest_with(tmp_path, "ungrouped", work_id="", canonical="", survey=""))

    # Neither BPE Edition is dropped or joined: each is a Work of its own, so the ACL Edition's copies of the preprint's
    # Chunks are not merged into them and keep their slots.
    assert collapsed_lines(report)["vocabulary-sizes", "as asked"][3] == "1508.07909v5; P16-1162; 2112.06598v2; 1508.07909v5; P16-1162"


def test_a_survey_keeps_its_slot(with_venue_edition, tmp_path):
    report = run_evaluate(with_venue_edition, manifest=manifest_with(tmp_path, "survey", survey="yes"))

    # Collapsed as if it weren't a Survey: each copy pair is one slot.
    assert collapsed_lines(report)["vocabulary-sizes", "as asked"][3] == "P16-1162 + 1508.07909v5; 2112.06598v2; P16-1162 + 1508.07909v5; 2112.06598v2; 2112.06598v2"


def test_a_collapsed_hit_carries_its_work_merged_editions_and_copies_and_keeps_its_citation_anchor(with_venue_edition):
    corpus = load_corpus(load_parse_config(REPO_CONFIG), with_venue_edition / "cache", with_venue_edition / "parse-report.md")
    bm25 = load_retrieval_config(RETRIEVAL_CONFIG).bm25
    raw = index.load(with_venue_edition / "index-cache", corpus, bm25).retriever
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    collapsed = Collapsed(raw, chunks, read_csv(MANIFEST), pool=50)
    text = "What vocabulary size do the translation systems use?"

    collapse = collapsed.collapse(text, 5)

    # The ACL Edition was parsed from the same TEI as the preprint, so a copy of one of its Chunks has the same text.
    pool = [chunk_id for chunk_id, _ in raw.query(text, 50)]
    shown = next(chunk_id for chunk_id, _ in collapse.ranking if chunks[chunk_id].edition_id in ("1508.07909v5", "P16-1162"))
    assert chunks[shown].pinned_id == "P16-1162"
    copies = tuple(c for c in pool if chunks[c].pinned_id == "1508.07909v5" and chunks[c].text == chunks[shown].text)
    assert len(copies) == 1
    assert collapse.merged[shown] == Merged("sennrich-2016-neural-machine-translation", ("1508.07909v5",), copies)
    # The raw (chunk id, score) shape, and the Chunk itself with its citation anchor, as the raw ranking gives them.
    assert dict(collapse.ranking)[shown] == dict(raw.query(text, 50))[shown]
    assert collapsed.query(text, 5) == collapse.ranking


def test_the_report_records_the_pool_and_how_many_pools_held_fewer_distinct_chunks_than_asked_for(with_venue_edition, tmp_path):
    config = tmp_path / "retrieval-pool-10.toml"
    config.write_text(RETRIEVAL_CONFIG.read_text().replace("pool = 50", "pool = 10"))

    report = run_evaluate(with_venue_edition, retrieval_config=config)

    retrievers = report.split("## Retrievers\n", 1)[1].split("\n## ", 1)[0]
    assert "- bm25+collapsed: bm25's index, with copies from other files of a Work merged\n  - pool: `10`" in retrievers
    crowded = report.split("### Crowding: bm25+collapsed\n", 1)[1].split("\n### ", 1)[0]
    found = re.search(r"- Pool: the top 10 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for (\d+) of 4"
                      r" questions, and fewer than 10, the depth each query asks for, for (\d+)\.", crowded)
    assert found
    # vocabulary-sizes alone has two copy pairs in its raw top 5, so its pool of 10 holds at most 8 distinct Chunks.
    assert int(found[2]) >= 1
    assert "- Pool:" not in report.split("### Crowding: bm25\n", 1)[1].split("\n### ", 1)[0]


def test_a_hybrids_build_time_is_its_members_build_time_now_not_when_its_record_was_written(corpus):
    name = "hybrid.bm25+bge-small"
    run_index(corpus, options=("--retriever", name))
    # As if bge-small had since been deleted and rebuilt, taking 1000 s; the hybrid's own record is untouched.
    record = index_folders(corpus)["dense.bge-small"] / "index.json"
    record.write_text(json.dumps({**json.loads(record.read_text()), "build_seconds": 1000.0}))

    report = run_evaluate(corpus, options=("--retriever", name))

    bm25 = json.loads((index_folders(corpus)["bm25"] / "index.json").read_text())["build_seconds"]
    [timing] = [line for line in report.split("## Timings\n", 1)[1].splitlines() if line.startswith(f"- {name}:")]
    assert f"index built on cpu in {bm25 + 1000:.2f} s;" in timing


@pytest.fixture
def with_short_venue_edition(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture corpus plus a file standing in for the BPE paper's ACL Edition (P16-1162, its Work's Canonical
    Edition) with another paper's text, which has no Section 5.1: none of its Chunks is a copy of the preprint's."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
        seed_pdf(tmp_path, grobid, "P16-1162.pdf", "lost-heading.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    run_index(tmp_path)
    return tmp_path


def test_a_canonical_editions_other_text_never_stands_in_for_a_retrieved_chunk(with_short_venue_edition, tmp_path):
    question = {
        "id": "f1-differences",
        "type": "single-paper",
        "question": "Which qualitative differences between the translation systems do the F1 numbers hide?",
        "passages": [
            {"edition_id": "1508.07909v5", "section": "5.1 Unigram accuracy", "quote": "The F 1 numbers hide some qualitative differences between systems"}
        ],
    }

    report = run_evaluate(with_short_venue_edition, write_question(tmp_path, question))

    # The preprint's Section 5.1 Chunk holds the Passage and keeps its slot: the Canonical Edition holds no copy of it,
    # so none of its Chunks is shown in its place or merged into it.
    [line] = [row for row in table(report, "### Questions: bm25+collapsed") if row[0] == "f1-differences"]
    assert line[3] == "1"
    assert line[8].startswith("1508.07909v5; ") and "+" not in line[8].split(";")[0]
