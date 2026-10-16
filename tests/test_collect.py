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
    # The BPE paper appears on both arXiv pages, revised in between: one Edition, pinned to the
    # newer Version. Semantic Scholar's query adds one preprint and three venue Editions, and
    # expansion from the Seed adds two preprints and one venue Edition.
    assert sorted(rows) == [
        "10.1162/TACL_A_00999",
        "1508.07909v5",
        "1804.10959v1",
        "1808.06226v2",
        "2004.03720v3",
        "2022.findings-acl.99",
        "2210.09461v3",
        "2301.00001",
        "2402.00001v1",
        "2403.00002v2",
        "2410.20771v3",
        "708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3",
        "D18-2012",
        "hep-th/9901001v1",
    ]

    bpe = rows["2004.03720v3"]
    assert bpe["edition_kind"] == "arxiv-preprint"
    assert bpe["title"] == "Byte Pair Encoding is Suboptimal for Language Model Pretraining"
    assert bpe["authors"] == "Kaj Bostrom; Greg Durrett"
    assert bpe["year"] == "2020"
    assert bpe["arxiv_id"] == "2004.03720"
    assert bpe["source_link"] == "https://arxiv.org/abs/2004.03720v3"
    assert bpe["discovery_channels"] == (
        "arxiv:tokenizer-titles|seed-citations:sentencepiece|semantic-scholar:subword-phrases"
    )
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

    # Rule-rejected Editions never get their record: they keep the Version their source reported.
    old = rows["hep-th/9901001v1"]
    assert old["versions"] == ""
    assert old["licence"] == "unknown"
    assert old["arxiv_comments"] == ""
    assert old["source_link"] == "https://arxiv.org/abs/hep-th/9901001v1"


def test_semantic_scholar_finds_editions_the_arxiv_query_missed(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Found only by Semantic Scholar, which reports no Version; its arXiv record pins it.
    nmt = rows["1508.07909v5"]
    assert nmt["edition_kind"] == "arxiv-preprint"
    assert nmt["title"] == "Neural Machine Translation of Rare Words with Subword Units"
    assert nmt["authors"] == "Rico Sennrich; Barry Haddow; Alexandra Birch"
    assert nmt["year"] == "2015"
    assert nmt["source_link"] == "https://arxiv.org/abs/1508.07909v5"
    assert nmt["versions"].startswith("v1 2015-08-31T16:37:31Z|v2 ")
    assert nmt["arxiv_comments"] == "accepted at ACL 2016"
    assert nmt["discovery_channels"] == "seed-references:sentencepiece|semantic-scholar:subword-phrases"
    # External identifiers as Semantic Scholar reported them.
    assert nmt["arxiv_id"] == "1508.07909"
    assert nmt["acl_id"] == "P16-1162"
    assert nmt["doi"] == "10.18653/v1/P16-1162"
    assert nmt["s2_id"] == "2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e"
    assert nmt["rule_outcome"] == "pass"
    assert nmt["relevance_verdict"] == "included"


def test_same_edition_from_two_channels_is_one_row_with_both_identifiers(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Both sources report arXiv 1808.06226: one row, arXiv's pinned record, every channel, and
    # the identifiers only Semantic Scholar knows.
    spm = rows["1808.06226v2"]
    assert spm["discovery_channels"] == "arxiv:tokenizer-titles|seed:sentencepiece|semantic-scholar:subword-phrases"
    assert spm["source_link"] == "https://arxiv.org/abs/1808.06226v2"
    assert spm["arxiv_comments"] == "Accepted as a demo paper at EMNLP 2018"
    assert spm["doi"] == "10.18653/v1/D18-2012"  # as arXiv reported it
    assert spm["acl_id"] == "D18-2012"
    assert spm["s2_id"] == "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
    assert spm["venue"] == ""

    # Semantic Scholar knew MrT5 only by its arXiv DOI, which is still an exact arXiv match.
    mrt5 = rows["2410.20771v3"]
    assert mrt5["discovery_channels"] == "arxiv:tokenizer-titles|semantic-scholar:subword-phrases"
    assert mrt5["s2_id"] == "5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f7081"

    # The EMNLP Edition of SentencePiece shares its DOI and ACL ID with the preprint row, but it
    # is a different Edition of the Work: its own row, left for the dedup stage to link.
    venue = rows["D18-2012"]
    assert venue["edition_kind"] == "venue"
    assert venue["venue"] == "Conference on Empirical Methods in Natural Language Processing"
    assert venue["year"] == "2018"
    assert venue["source_link"] == "https://aclanthology.org/D18-2012"
    assert venue["acl_id"] == "D18-2012"
    assert venue["doi"] == "10.18653/V1/D18-2012"
    assert venue["arxiv_id"] == ""
    assert venue["s2_id"] == "4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f70"
    assert venue["discovery_channels"] == "semantic-scholar:subword-phrases"
    assert venue["work_id"] == ""

    # Venue Editions without an ACL ID are named by their DOI, else by their Semantic Scholar id.
    journal = rows["10.1162/TACL_A_00999"]
    assert journal["edition_kind"] == "venue"
    assert journal["source_link"] == "https://doi.org/10.1162/TACL_A_00999"
    bare = rows["708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3"]
    assert bare["edition_kind"] == "venue"
    assert bare["year"] == ""
    assert bare["source_link"] == "https://www.semanticscholar.org/paper/708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3"
    assert bare["s2_id"] == "708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3"

    # Venue Editions go through the same relevance stages.
    assert venue["relevance_verdict"] == "included"
    assert bare["rule_outcome"] == "pass"
    assert bare["relevance_verdict"] == "excluded"
    assert bare["relevance_stage"] == "judge"


def test_citation_expansion_finds_candidates_keyword_search_missed(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Cited by the SentencePiece Seed and found by no keyword query; it goes through the same
    # stages as any other Candidate: arXiv record, rules, judge.
    regularization = rows["1804.10959v1"]
    assert regularization["discovery_channels"] == "seed-references:sentencepiece"
    assert regularization["title"].startswith("Subword Regularization")
    assert regularization["acl_id"] == "P18-1007"
    assert regularization["arxiv_comments"] == "Accepted as a long paper at ACL2018"
    assert regularization["rule_outcome"] == "pass"
    assert regularization["relevance_verdict"] == "included"
    assert regularization["judge_probability"] == "0.9300"

    # A venue Edition that cites the Seed, on the first citations page.
    segmentation = rows["2022.findings-acl.99"]
    assert segmentation["discovery_channels"] == "seed-citations:sentencepiece"
    assert segmentation["edition_kind"] == "venue"
    assert segmentation["relevance_verdict"] == "included"

    # Found on the second citations page and by both keyword queries: one row, every channel.
    assert rows["2004.03720v3"]["discovery_channels"] == (
        "arxiv:tokenizer-titles|seed-citations:sentencepiece|semantic-scholar:subword-phrases"
    )
    # The Seed's own record is a Candidate too, and the Seed's references reach a keyword Candidate.
    assert rows["1808.06226v2"]["discovery_channels"] == (
        "arxiv:tokenizer-titles|seed:sentencepiece|semantic-scholar:subword-phrases"
    )
    assert rows["1508.07909v5"]["discovery_channels"] == (
        "seed-references:sentencepiece|semantic-scholar:subword-phrases"
    )

    # A citer the rules reject keeps its row, but its arXiv record is never fetched.
    legal = rows["2301.00001"]
    assert legal["discovery_channels"] == "seed-citations:sentencepiece"
    assert legal["rule_outcome"] == "reject"
    assert legal["rule_pattern"] == "missing-required-term"
    assert legal["versions"] == ""
    assert legal["licence"] == "unknown"

    # A reference Semantic Scholar could not resolve to a paper is skipped.
    assert not any(row["title"].startswith("A reference Semantic Scholar") for row in rows.values())


def test_report_counts_editions_per_discovery_channel(fixture_snapshot, no_network, tmp_path, capsys):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    report = capsys.readouterr().err

    # Three Editions are found by both keyword queries: SentencePiece, the BPE paper and MrT5.
    # The Seed's references also reach the Sennrich paper, which only Semantic Scholar's query found.
    assert "discover: 14 Editions" in report
    assert "  arxiv:tokenizer-titles: 7 Editions, 4 found by no other channel" in report
    assert "  semantic-scholar:subword-phrases: 7 Editions, 3 found by no other channel" in report
    assert "  seed:sentencepiece: 1 Editions, 0 found by no other channel" in report
    assert "  seed-references:sentencepiece: 2 Editions, 1 found by no other channel" in report
    assert "  seed-citations:sentencepiece: 3 Editions, 2 found by no other channel" in report


def test_report_shows_what_citation_expansion_adds_beyond_keyword_search(fixture_snapshot, no_network, tmp_path, capsys):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    report = capsys.readouterr().err

    # The Seed's own record isn't a citation hop, so expansion reaches five Editions. Three of
    # them no keyword query found: subword regularization and the Findings paper are included,
    # the legal-MT citer is rule-rejected.
    assert "  keyword search: 11 Editions, 6 included" in report
    assert "  citation expansion: 5 Editions, 3 found by no keyword query, 2 of those included" in report


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


def test_api_key_changes_nothing_and_is_never_stored(fixture_snapshot, no_network, tmp_path, monkeypatch):
    without_key = tmp_path / "without-key.csv"
    run_collect(fixture_snapshot, without_key)
    before = snapshot_files(fixture_snapshot)

    monkeypatch.setenv("S2_API_KEY", "fixture-secret-key")
    with_key = tmp_path / "with-key.csv"
    run_collect(fixture_snapshot, with_key)

    assert with_key.read_bytes() == without_key.read_bytes()
    assert snapshot_files(fixture_snapshot) == before
    for name, data in before.items():
        text = gzip.decompress(data) if name.endswith(".gz") else data
        assert b"fixture-secret-key" not in text, name


def test_snapshot_entries_are_compressed_and_credential_free(fixture_snapshot):
    files = snapshot_files(fixture_snapshot / "responses")
    # Two arXiv and two Semantic Scholar results pages, the Seed's record, references and two
    # citations pages, and one full record per arXiv Edition that passes the rules.
    assert len(files) == 2 + 2 + 4 + 5
    for name, data in files.items():
        assert name.endswith(".json.gz")
        record = json.loads(gzip.decompress(data))
        assert record["collected_at"] == "2026-10-16"
        assert set(record["request"]) == {"source", "url", "params"}
        assert name.startswith(f"{record['request']['source']}/")
        assert "<feed" in record["body"] or "<OAI-PMH" in record["body"] or '"paperId"' in record["body"]


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


RULE_PASSES = [
    "10.1162/TACL_A_00999",
    "1508.07909v5",
    "1804.10959v1",
    "1808.06226v2",
    "2004.03720v3",
    "2022.findings-acl.99",
    "2410.20771v3",
    "708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3",
    "D18-2012",
]


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

    PROBABILITIES = dict.fromkeys(RULE_PASSES, 0.9) | {"1808.06226v2": 0.99, "2004.03720v3": 0.35, "2410.20771v3": 0.8}

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
