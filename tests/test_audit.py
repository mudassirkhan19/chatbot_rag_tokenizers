"""Offline runs of `audit export` and `audit report`: building the Audit set and measuring the Relevance verdict on it."""

import csv
from collections import Counter
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.collection import judge
from conftest import FIXTURES

# The fixture Snapshot's Editions by stratum, as the fixture verdicts and threshold 0.5 place them.
RULE_REJECTS = {"2210.09461v3", "2301.00001", "2402.00001v1", "2403.00002v2", "W4400000103", "hep-th/9901001v1"}
JUDGE_REJECTS = {"708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3"}
JUDGE_ACCEPTS = {
    "10.1162/TACL_A_00999",
    "10.5555/lrm.2022.7",
    "1508.07909v5",
    "1804.10959v1",
    "1808.06226v2",
    "2004.03720v3",
    "2020.findings-emnlp.414",
    "2022.findings-acl.99",
    "2410.20771v3",
    "D18-2012",
    "P16-1162",
    "P18-1007",
}


@pytest.fixture
def no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything tries to load the judge model."""

    def refuse(config):
        raise AssertionError("the judge model was loaded")

    monkeypatch.setattr(judge, "load_judge", refuse)


def run_export(snapshot: Path, output: Path, *flags: str) -> None:
    main(
        [
            "audit", "export",
            "--config", str(FIXTURES / "scope.toml"),
            "--snapshot", str(snapshot),
            "--output", str(output),
            *flags,
        ]
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_export_samples_every_stratum_with_draft_labels(fixture_snapshot, no_network, no_model, tmp_path):
    output = tmp_path / "audit-set.csv"
    run_export(fixture_snapshot, output, "--size", "5")
    rows = {row["edition_id"]: row for row in read_rows(output)}

    # Five rows shared out evenly: the single judge reject, then two each of the larger strata.
    assert Counter(row["stratum"] for row in rows.values()) == {"rules-rejected": 2, "judge-excluded": 1, "judge-included": 2}
    for row in rows.values():
        expected = {"rules-rejected": RULE_REJECTS, "judge-excluded": JUDGE_REJECTS, "judge-included": JUDGE_ACCEPTS}
        assert row["edition_id"] in expected[row["stratum"]]
        # The size of the stratum it was drawn from, so the report can weight it.
        assert row["stratum_size"] == str(len(expected[row["stratum"]]))
        assert row["title"] and row["source_link"]
        # The draft is the pipeline's verdict, copied into the label for the developer to correct.
        assert row["draft_label"] == ("yes" if row["stratum"] == "judge-included" else "no")
        assert (row["label"], row["reason"]) == (row["draft_label"], row["draft_reason"])

    bare = rows["708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3"]
    assert bare["draft_reason"] == "judge: P(Yes) 0.3000 < threshold 0.5"
    assert rows.keys() & JUDGE_ACCEPTS
    accepted = rows[min(rows.keys() & JUDGE_ACCEPTS)]
    assert accepted["abstract"]  # the labeller reads the abstract the judge read
    for row in rows.values():
        if row["stratum"] == "rules-rejected":
            assert row["draft_reason"].split(":")[0] in {"token-reduction", "kv-cache", "crypto-assets", "missing-required-term"}


def test_export_is_reproducible_and_never_overwrites_labels(fixture_snapshot, no_network, no_model, tmp_path):
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    run_export(fixture_snapshot, first, "--size", "5")
    run_export(fixture_snapshot, second, "--size", "5")
    assert first.read_bytes() == second.read_bytes()

    # The file holds hand-corrected labels, so a second export must not replace it.
    labelled = first.read_text().replace(",yes,", ",no,")
    first.write_text(labelled)
    with pytest.raises(SystemExit, match="already exists"):
        run_export(fixture_snapshot, first, "--size", "5")
    assert first.read_text() == labelled

    run_export(fixture_snapshot, first, "--size", "5", "--force")
    assert first.read_bytes() == second.read_bytes()


def test_export_larger_than_the_candidates_takes_them_all(fixture_snapshot, no_network, no_model, tmp_path):
    output = tmp_path / "audit-set.csv"
    run_export(fixture_snapshot, output, "--size", "100")
    assert {row["edition_id"] for row in read_rows(output)} == RULE_REJECTS | JUDGE_REJECTS | JUDGE_ACCEPTS


def run_report(output: Path, *flags: str, config: Path = FIXTURES / "scope.toml") -> str:
    main(
        [
            "audit", "report",
            "--config", str(config),
            "--audit-set", str(FIXTURES / "audit" / "audit-set.csv"),
            "--verdicts", str(FIXTURES / "audit" / "verdicts.jsonl"),
            "--output", str(output),
            *flags,
        ]
    )
    return output.read_text()


# The fixture Audit set (tests/fixtures/audit/audit-set.csv), worked by hand. Each labelled row
# stands for stratum_size / labelled-in-stratum Candidates: 20 for the two rule rejects, 5 for each
# of the six rule passes. "yes" labels: r2 (20), e2, i1, i2, i3 (5 each), so 40 of 70 Candidates.


def test_report_weights_each_stratum_and_scores_the_rule_stage(no_model, tmp_path):
    report = run_report(tmp_path / "report.md", "--thresholds", "0.5,0.65", "--no-judge")

    assert "8 labelled Candidates (3 labels changed from the draft, 0 unlabelled)" in report
    assert "| rules-rejected | 40 | 2 | 1 |" in report
    assert "| judge-excluded | 10 | 2 | 1 |" in report
    assert "| judge-included | 20 | 4 | 3 |" in report

    # All six rule passes are predicted relevant: 20 of their 30 are, out of 40 relevant overall.
    # Precision 20/30, recall 20/40, F1 4/7.
    rules = report.split("## Rule stage alone")[1].split("##")[0]
    assert "| 0.667 | 0.500 | 0.571 |" in rules


def test_report_gives_each_model_its_metrics_by_threshold_and_run_time(no_model, tmp_path):
    report = run_report(tmp_path / "report.md", "--thresholds", "0.5,0.65", "--no-judge")
    model_a = report.split("## Rules and judge: example/model-a@")[1].split("##")[0]
    model_b = report.split("## Rules and judge: example/model-b@")[1].split("##")[0]

    # Model A at 0.5 includes i1–i4 (15 of 20 relevant), at 0.65 i1–i3 (15 of 15). Its stale
    # verdict for i4, made with another prompt, is ignored.
    assert "| 0.5 | 0.750 | 0.375 | 0.500 |" in model_a
    assert "| 0.65 | 1.000 | 0.375 | 0.545 |" in model_a
    assert "Best F1 0.545 at threshold 0.65" in model_a
    # 1 s per Candidate, for the 30 Candidates that passed the rules.
    assert "1.00 s per Candidate" in model_a
    assert "about 0.5 min for the 30 rule passes" in model_a

    # Model B at 0.5 includes e2, i1, i2, i3 (all relevant, 20 of 40); at 0.65 it drops i3.
    assert "| 0.5 | 1.000 | 0.500 | 0.667 |" in model_b
    assert "| 0.65 | 1.000 | 0.375 | 0.545 |" in model_b
    assert "Best F1 0.667 at threshold 0.5" in model_b
    assert "3.00 s per Candidate" in model_b
    assert "about 1.5 min for the 30 rule passes" in model_b


def test_report_without_the_judge_names_models_missing_verdicts(no_model, tmp_path):
    text = (FIXTURES / "scope.toml").read_text()
    config = tmp_path / "scope.toml"
    config.write_text(text + '\n[[audit.models]]\nmodel = "example/model-c"\nrevision = "cccccccccccccccccccccccccccccccccccccccc"\n')

    report = run_report(tmp_path / "report.md", "--no-judge", config=config)

    model_c = report.split("## Rules and judge: example/model-c@")[1]
    assert "No verdicts for 6 of the 6 rule passes" in model_c
    assert "| threshold |" not in model_c
    # The other models are unaffected, and the default thresholds include the configured one.
    assert "| 0.5 | 0.750 | 0.375 | 0.500 |" in report
    assert "| 0.9 |" in report
