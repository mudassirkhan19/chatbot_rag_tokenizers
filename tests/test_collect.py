"""Offline runs of `collect` against the hand-built fixture Snapshot."""

import csv
import gzip
import json
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.collection import judge
from conftest import FIXTURES


def run_collect(snapshot: Path, manifest: Path, config: Path = FIXTURES / "scope.toml", *flags: str) -> None:
    main(
        [
            "collect",
            "--config", str(config),
            "--snapshot", str(snapshot),
            "--manifest", str(manifest),
            *flags,
        ]
    )


def edited_config(tmp_path: Path, old: str, new: str) -> Path:
    """The fixture scope config with one piece of text replaced."""
    text = (FIXTURES / "scope.toml").read_text()
    assert old in text
    path = tmp_path / "edited-scope.toml"
    path.write_text(text.replace(old, new))
    return path


@pytest.fixture
def no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything tries to load the judge model."""

    def refuse(config):
        raise AssertionError("the judge model was loaded")

    monkeypatch.setattr(judge, "load_judge", refuse)


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        return {row["edition_id"]: row for row in csv.DictReader(f)}


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_manifest_has_one_row_per_edition(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)

    rows = read_manifest(manifest)
    # The BPE paper appears on both pages, revised in between: one Edition, pinned to the newer Version.
    assert sorted(rows) == [
        "1808.06226v2",
        "2004.03720v3",
        "2210.09461v3",
        "2402.00001v1",
        "2403.00002v2",
        "2410.20771v3",
        "hep-th/9901001v1",
    ]

    bpe = rows["2004.03720v3"]
    assert bpe["edition_kind"] == "arxiv-preprint"
    assert bpe["title"] == "Byte Pair Encoding is Suboptimal for Language Model Pretraining"
    assert bpe["authors"] == "Kaj Bostrom; Greg Durrett"
    assert bpe["year"] == "2020"
    assert bpe["arxiv_id"] == "2004.03720"
    assert bpe["source_link"] == "https://arxiv.org/abs/2004.03720v3"
    assert bpe["discovery_channels"] == "arxiv:tokenizer-titles"
    assert bpe["rule_outcome"] == "pass"
    assert bpe["relevance_verdict"] == "included"
    assert bpe["funnel_status"] == "relevant"
    assert bpe["work_id"] == ""

    spm = rows["1808.06226v2"]
    assert spm["arxiv_comments"] == "Accepted as a demo paper at EMNLP 2018"
    assert spm["journal_ref"] == "EMNLP 2018 System Demonstrations"
    assert spm["doi"] == "10.18653/v1/D18-2012"
    assert spm["title"].startswith("SentencePiece: A simple and language independent subword tokenizer and detokenizer")


def test_arxiv_editions_carry_their_full_record(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Search only ever saw v2 and v3; the full record lists every Version, v1 included.
    bpe = rows["2004.03720v3"]
    assert bpe["versions"] == "v1 2020-04-07T21:21:06Z|v2 2020-10-05T17:35:44Z|v3 2021-01-10T09:00:00Z"
    assert bpe["arxiv_comments"] == "5 pages, 3 figures. To be published in Findings of EMNLP 2020"
    assert bpe["licence"] == "http://creativecommons.org/licenses/by/4.0/"

    # Revised after the search page was saved: the record's latest Version is the pinned one.
    spm = rows["1808.06226v2"]
    assert spm["versions"] == "v1 2018-08-19T00:00:00Z|v2 2018-09-03T12:30:00Z"
    assert spm["source_link"] == "https://arxiv.org/abs/1808.06226v2"
    assert spm["licence"] == "http://arxiv.org/licenses/nonexclusive-distrib/1.0/"

    # Rule-rejected Editions get their record too; an old preprint without a licence says so.
    old = rows["hep-th/9901001v1"]
    assert old["versions"] == "v1 1999-01-04T00:00:00Z"
    assert old["licence"] == "unknown"
    assert old["arxiv_comments"] == ""


def test_rule_rejected_candidates_keep_their_row(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Token Merging has no required term either; the exclusion that names it is reported.
    expected_rejections = {
        "2210.09461v3": "token-reduction",
        "2402.00001v1": "kv-cache",
        "2403.00002v2": "crypto-assets",
        "hep-th/9901001v1": "missing-required-term",
    }
    for edition_id, pattern in expected_rejections.items():
        row = rows[edition_id]
        assert row["rule_outcome"] == "reject", edition_id
        assert row["rule_pattern"] == pattern, edition_id
        assert row["relevance_verdict"] == "excluded", edition_id
        assert row["relevance_stage"] == "rules", edition_id
        assert pattern in row["relevance_reason"], edition_id
        assert row["funnel_status"] == "discovered", edition_id

    # "Token merging" is an exclusion, but a byte-level title keeps it in.
    for edition_id in ["1808.06226v2", "2004.03720v3", "2410.20771v3"]:
        assert rows[edition_id]["rule_outcome"] == "pass"
        assert rows[edition_id]["rule_pattern"] == ""
        assert rows[edition_id]["relevance_stage"] == "judge"


def test_rerun_from_snapshot_is_byte_identical(fixture_snapshot, no_network, no_model, tmp_path):
    before = snapshot_files(fixture_snapshot)

    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    run_collect(fixture_snapshot, first)
    run_collect(fixture_snapshot, second)

    assert first.read_bytes() == second.read_bytes()
    assert snapshot_files(fixture_snapshot) == before


def test_snapshot_entries_are_compressed_and_credential_free(fixture_snapshot):
    files = snapshot_files(fixture_snapshot / "responses")
    assert len(files) == 2 + 7  # two results pages, one full record per arXiv Edition
    for name, data in files.items():
        assert name.endswith(".json.gz")
        record = json.loads(gzip.decompress(data))
        assert record["collected_at"] == "2026-10-16"
        assert set(record["request"]) == {"source", "url", "params"}
        assert "<feed" in record["body"] or "<OAI-PMH" in record["body"]


def test_rule_passes_get_the_cached_judge_verdict(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Fixture verdicts 0.97, 0.91 and 0.62 all clear the 0.5 threshold.
    for edition_id, probability in [("1808.06226v2", "0.9700"), ("2004.03720v3", "0.9100"), ("2410.20771v3", "0.6200")]:
        row = rows[edition_id]
        assert row["relevance_verdict"] == "included", edition_id
        assert row["relevance_stage"] == "judge", edition_id
        assert row["judge_probability"] == probability, edition_id
        assert row["judge_threshold"] == "0.5", edition_id
        assert row["judge_model"] == "example/judge-model@0123456789abcdef0123456789abcdef01234567", edition_id
        assert row["funnel_status"] == "relevant", edition_id

    # Rule rejects never reach the judge.
    tokenmerge = rows["2210.09461v3"]
    assert tokenmerge["relevance_stage"] == "rules"
    assert tokenmerge["judge_probability"] == ""
    assert tokenmerge["judge_threshold"] == ""


def test_changing_the_threshold_changes_verdicts_without_loading_the_model(
    fixture_snapshot, no_network, no_model, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest, edited_config(tmp_path, "threshold = 0.5", "threshold = 0.7"))
    rows = read_manifest(manifest)

    mrt5 = rows["2410.20771v3"]  # fixture verdict 0.62
    assert mrt5["relevance_verdict"] == "excluded"
    assert mrt5["relevance_stage"] == "judge"
    assert mrt5["judge_probability"] == "0.6200"
    assert mrt5["judge_threshold"] == "0.7"
    assert "0.6200 < threshold 0.7" in mrt5["relevance_reason"]
    assert mrt5["funnel_status"] == "discovered"

    assert rows["2004.03720v3"]["relevance_verdict"] == "included"  # fixture verdict 0.91


RULE_PASSES = ["1808.06226v2", "2004.03720v3", "2410.20771v3"]


@pytest.mark.parametrize(
    "old, new",
    [
        ('model = "example/judge-model"', 'model = "example/other-model"'),
        ('revision = "0123456789abcdef0123456789abcdef01234567"', 'revision = "fedcba9876543210fedcba9876543210fedcba98"'),
        ("Answer Yes or No.", "Answer only Yes or No."),
    ],
    ids=["model", "revision", "prompt"],
)
def test_changing_model_revision_or_prompt_invalidates_cached_verdicts(
    fixture_snapshot, no_network, no_model, tmp_path, old, new
):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest, edited_config(tmp_path, old, new), "--no-judge")
    rows = read_manifest(manifest)

    for edition_id in RULE_PASSES:
        row = rows[edition_id]
        assert row["relevance_verdict"] == "pending", edition_id
        assert row["relevance_stage"] == "", edition_id
        assert row["judge_probability"] == "", edition_id
        assert row["funnel_status"] == "discovered", edition_id


class FakeJudge:
    """Stands in for the model: P("Yes") is fixed per Edition."""

    PROBABILITIES = {"1808.06226v2": 0.99, "2004.03720v3": 0.35, "2410.20771v3": 0.8}

    def __init__(self) -> None:
        self.scored: list[str] = []

    def score(self, editions):
        self.scored += [edition.edition_id for edition in editions]
        return [self.PROBABILITIES[edition.edition_id] for edition in editions]


def test_invalidated_verdicts_are_rescored_and_cached(fixture_snapshot, no_network, monkeypatch, tmp_path):
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    config = edited_config(tmp_path, 'model = "example/judge-model"', 'model = "example/other-model"')
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"

    run_collect(fixture_snapshot, first, config)
    assert sorted(fake.scored) == RULE_PASSES
    rows = read_manifest(first)
    assert rows["2004.03720v3"]["relevance_verdict"] == "excluded"
    assert rows["2004.03720v3"]["judge_probability"] == "0.3500"
    assert rows["2004.03720v3"]["judge_model"].startswith("example/other-model@")
    assert rows["2410.20771v3"]["relevance_verdict"] == "included"

    # The next run reuses the new verdicts from the Snapshot.
    fake.scored.clear()
    run_collect(fixture_snapshot, second, config)
    assert fake.scored == []
    assert first.read_bytes() == second.read_bytes()


def test_refresh_rescores_every_rule_pass(fixture_snapshot, no_network, monkeypatch, tmp_path):
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    assert sorted(fake.scored) == RULE_PASSES
    assert read_manifest(manifest)["2004.03720v3"]["judge_probability"] == "0.3500"
