"""Offline runs of `collect` against the hand-built fixture Snapshot."""

import csv
import gzip
import json
from pathlib import Path

from chatbot_rag_tokenizers.cli import main
from conftest import FIXTURES


def run_collect(snapshot: Path, manifest: Path) -> None:
    main(
        [
            "collect",
            "--config", str(FIXTURES / "scope.toml"),
            "--snapshot", str(snapshot),
            "--manifest", str(manifest),
        ]
    )


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        return {row["edition_id"]: row for row in csv.DictReader(f)}


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_manifest_has_one_row_per_edition(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)

    rows = read_manifest(manifest)
    # The BPE paper appears on both pages but is one Edition.
    assert sorted(rows) == [
        "1808.06226v1",
        "2004.03720v2",
        "2210.09461v3",
        "2402.00001v1",
        "2403.00002v2",
        "2410.20771v3",
        "hep-th/9901001v1",
    ]

    bpe = rows["2004.03720v2"]
    assert bpe["edition_kind"] == "arxiv-preprint"
    assert bpe["title"] == "Byte Pair Encoding is Suboptimal for Language Model Pretraining"
    assert bpe["authors"] == "Kaj Bostrom; Greg Durrett"
    assert bpe["year"] == "2020"
    assert bpe["arxiv_id"] == "2004.03720"
    assert bpe["source_link"] == "https://arxiv.org/abs/2004.03720v2"
    assert bpe["discovery_channels"] == "arxiv:tokenizer-titles"
    assert bpe["rule_outcome"] == "pass"
    assert bpe["relevance_verdict"] == "pending"
    assert bpe["funnel_status"] == "discovered"
    assert bpe["licence"] == "unknown"
    assert bpe["work_id"] == ""

    spm = rows["1808.06226v1"]
    assert spm["arxiv_comments"] == "Accepted as a demo paper at EMNLP 2018"
    assert spm["journal_ref"] == "EMNLP 2018 System Demonstrations"
    assert spm["doi"] == "10.18653/v1/D18-2012"
    assert spm["title"].startswith("SentencePiece: A simple and language independent subword tokenizer and detokenizer")


def test_rule_rejected_candidates_keep_their_row(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

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
    for edition_id in ["1808.06226v1", "2004.03720v2", "2410.20771v3"]:
        assert rows[edition_id]["rule_outcome"] == "pass"
        assert rows[edition_id]["rule_pattern"] == ""
        assert rows[edition_id]["relevance_stage"] == ""


def test_rerun_from_snapshot_is_byte_identical(fixture_snapshot, no_network, tmp_path):
    before = snapshot_files(fixture_snapshot)

    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    run_collect(fixture_snapshot, first)
    run_collect(fixture_snapshot, second)

    assert first.read_bytes() == second.read_bytes()
    assert snapshot_files(fixture_snapshot) == before


def test_snapshot_entries_are_compressed_and_credential_free(fixture_snapshot):
    files = snapshot_files(fixture_snapshot)
    assert len(files) == 2
    for name, data in files.items():
        assert name.endswith(".json.gz")
        record = json.loads(gzip.decompress(data))
        assert record["collected_at"] == "2026-10-16"
        assert set(record["request"]) == {"source", "url", "params"}
        assert "<feed" in record["body"]
