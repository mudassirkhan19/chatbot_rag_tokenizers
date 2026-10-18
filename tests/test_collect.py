"""Offline runs of `collect` against the hand-built fixture Snapshot."""

import csv
import gzip
import json
import shutil
import time
from pathlib import Path

import httpx
import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.collection import judge, snapshot
from chatbot_rag_tokenizers.collection.openalex import OpenAlexError
from chatbot_rag_tokenizers.collection.snapshot import SnapshotStore
from conftest import FIXTURES, acl_request, arxiv_record_request, openalex_request, s2_seed_request


def run_collect(snapshot: Path, manifest: Path, config: Path = FIXTURES / "scope.toml", *flags: str) -> None:
    """Run `collect`, writing its report next to the manifest unless ``flags`` name another path."""
    report = [] if "--report" in flags else ["--report", str(manifest.with_name("report.md"))]
    main(
        [
            "collect",
            "--config", str(config),
            "--snapshot", str(snapshot),
            "--manifest", str(manifest),
            *report,
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
    # newer Version. Semantic Scholar's query adds one preprint and three venue Editions,
    # expansion from the Seed adds two preprints and one venue Edition, and the ACL Anthology
    # three venue Editions for ACL IDs that only preprints reported. OpenAlex adds two
    # more venue Editions.
    assert sorted(rows) == [
        "10.1162/TACL_A_00999",
        "10.5555/lrm.2022.7",
        "1508.07909v5",
        "1804.10959v1",
        "1808.06226v2",
        "2004.03720v3",
        "2020.findings-emnlp.414",
        "2022.findings-acl.99",
        "2210.09461v3",
        "2301.00001",
        "2402.00001v1",
        "2403.00002v2",
        "2410.20771v3",
        "708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3",
        "D18-2012",
        "P16-1162",
        "P18-1007",
        "W4400000103",
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
        "arxiv:tokenizer-titles|openalex:keyword-phrases|seed-citations:sentencepiece|semantic-scholar:subword-phrases"
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


def test_preprint_and_its_acl_edition_are_two_rows(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    # Semantic Scholar reported the preprint's ACL ID; the ACL Anthology page makes it a venue
    # Edition of its own, linked to the preprint only by the identifiers both rows carry.
    preprint, venue = rows["1508.07909v5"], rows["P16-1162"]
    assert preprint["edition_kind"] == "arxiv-preprint"
    assert preprint["acl_id"] == venue["acl_id"] == "P16-1162"
    assert preprint["doi"] == venue["doi"] == "10.18653/v1/P16-1162"

    assert venue["edition_kind"] == "venue"
    assert venue["title"] == "Neural Machine Translation of Rare Words with Subword Units"
    assert venue["authors"] == "Rico Sennrich; Barry Haddow; Alexandra Birch"
    assert venue["venue"] == "Annual Meeting of the Association for Computational Linguistics"
    assert venue["year"] == "2016"
    assert venue["licence"] == "https://creativecommons.org/licenses/by/4.0/"
    assert venue["source_link"] == "https://aclanthology.org/P16-1162"
    assert venue["pdf_link"] == "https://aclanthology.org/P16-1162.pdf"
    assert venue["arxiv_id"] == ""
    assert venue["s2_id"] == ""
    assert venue["versions"] == ""
    assert venue["work_id"] == preprint["work_id"] == ""
    # Found through the preprint, so by the query and the Seed hop that found the preprint.
    assert venue["discovery_channels"] == "seed-references:sentencepiece|semantic-scholar:subword-phrases"

    # Semantic Scholar named the BPE paper's Findings Edition only by an upper-cased ACL DOI; the
    # venue row still gets the ACL ID in the Anthology's own case.
    bpe = rows["2004.03720v3"]
    assert bpe["acl_id"] == ""
    assert bpe["doi"] == "10.18653/V1/2020.FINDINGS-EMNLP.414"
    findings = rows["2020.findings-emnlp.414"]
    assert findings["acl_id"] == "2020.findings-emnlp.414"
    assert findings["doi"] == "10.18653/v1/2020.findings-emnlp.414"
    assert findings["venue"] == "Findings of the Association for Computational Linguistics"

    # An ACL ID the Anthology doesn't have leaves the row as its source reported it.
    unknown = rows["2022.findings-acl.99"]
    assert unknown["edition_kind"] == "venue"
    assert unknown["venue"] == "Findings"
    assert unknown["licence"] == "unknown"
    assert unknown["pdf_link"] == ""


def test_openalex_finds_a_venue_edition_no_other_channel_found(fixture_snapshot, no_network, tmp_path):
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    journal = rows["10.5555/lrm.2022.7"]
    assert journal["edition_kind"] == "venue"
    assert journal["title"] == "Unigram Tokenization for Morphologically Rich Languages"
    assert journal["authors"] == "Ayşe Yılmaz; Juan Pérez"
    assert journal["year"] == "2022"
    assert journal["venue"] == "Journal of Low-Resource Morphology"
    assert journal["source_link"] == "https://doi.org/10.5555/lrm.2022.7"
    assert journal["doi"] == "10.5555/lrm.2022.7"
    assert journal["openalex_id"] == "W4200000100"
    assert journal["arxiv_id"] == journal["acl_id"] == journal["s2_id"] == ""
    # Every open-access PDF OpenAlex lists, its best one first; the paywalled copy is left out.
    assert journal["oa_pdf_urls"] == "https://repo.example.edu/1234/lrm-7.pdf|https://lrm.example.org/articles/7.pdf"
    assert journal["discovery_channels"] == "openalex:keyword-phrases"
    # The abstract, rebuilt from OpenAlex's inverted index, is what the rules and judge see.
    assert journal["rule_outcome"] == "pass"
    assert journal["relevance_verdict"] == "included"

    # Without a DOI, an OpenAlex venue Edition is named by its OpenAlex id.
    ledger = rows["W4400000103"]
    assert ledger["source_link"] == "https://openalex.org/W4400000103"
    assert ledger["oa_pdf_urls"] == ""
    assert ledger["rule_pattern"] == "crypto-assets"


def test_openalex_can_be_switched_off(fixture_snapshot, no_network, no_model, tmp_path, capsys):
    config = edited_config(tmp_path, "[sources.openalex]\nenabled = true", "[sources.openalex]\nenabled = false")
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest, config)
    rows = read_manifest(manifest)

    assert "10.5555/lrm.2022.7" not in rows
    assert "W4400000103" not in rows
    assert not any("openalex" in row["discovery_channels"] for row in rows.values())
    assert rows["10.1162/TACL_A_00999"]["openalex_id"] == ""
    assert rows["10.1162/TACL_A_00999"]["oa_pdf_urls"] == ""
    assert "discover: 17 Editions" in capsys.readouterr().err


def test_semantic_scholar_waits_out_a_half_hour_throttle(fixture_snapshot, no_network, tmp_path, monkeypatch):
    # Without an API key the shared pool can refuse every request for many minutes on end.
    SnapshotStore(fixture_snapshot)._path(s2_seed_request()).unlink()
    record = (FIXTURES / "seeds" / "sentencepiece-paper.json").read_bytes()
    clock = [0.0]

    def answer(transport, request: httpx.Request) -> httpx.Response:
        if clock[0] < 30 * 60:
            return httpx.Response(429, request=request)
        return httpx.Response(200, content=record, request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", answer)
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)

    assert "seed:sentencepiece" in read_manifest(manifest)["1808.06226v2"]["discovery_channels"]


def test_acl_id_of_a_volume_counts_as_no_paper(fixture_snapshot, no_network, tmp_path, monkeypatch, capsys):
    # Semantic Scholar has records for whole proceedings volumes, whose ACL ID the Anthology
    # redirects to the volume's page.
    paper_page = acl_request("2022.findings-acl.99")
    SnapshotStore(fixture_snapshot)._path(paper_page).unlink()
    volume_page = "https://aclanthology.org/volumes/2022.findings-acl.99/"
    volume_html = "<html><title>Findings of ACL 2022 - ACL Anthology</title><dl><dt>Anthology ID:</dt></dl></html>"

    def answer(transport, request: httpx.Request) -> httpx.Response:
        if str(request.url) == paper_page["url"]:
            return httpx.Response(301, headers={"Location": volume_page}, request=request)
        assert str(request.url) == volume_page
        return httpx.Response(200, text=volume_html, request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", answer)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)

    assert "acl-anthology: 2022.findings-acl.99 is a volume, not a paper" in capsys.readouterr().err
    unknown = read_manifest(manifest)["2022.findings-acl.99"]
    assert unknown["venue"] == "Findings"
    assert unknown["pdf_link"] == ""
    # Remembered like a 404, so a replay stays offline.
    assert SnapshotStore(fixture_snapshot).load(paper_page).body == ""


def test_openalex_without_a_key_explains_what_to_do(fixture_snapshot, no_network, tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    shutil.rmtree(fixture_snapshot / "responses" / "openalex")

    # Without a key OpenAlex can't page past the first results, so a fetch never starts.
    with pytest.raises(OpenAlexError, match="OPENALEX_API_KEY is not set"):
        run_collect(fixture_snapshot, tmp_path / "manifest.csv")


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
    # is a different Edition of the Work: its own row, left for the dedup stage to link. Semantic
    # Scholar found it; its ACL Anthology page is the authority for its metadata.
    venue = rows["D18-2012"]
    assert venue["edition_kind"] == "venue"
    assert venue["venue"] == "Conference on Empirical Methods in Natural Language Processing"
    assert venue["year"] == "2018"
    assert venue["licence"] == "https://creativecommons.org/licenses/by/4.0/"
    assert venue["source_link"] == "https://aclanthology.org/D18-2012"
    assert venue["pdf_link"] == "https://aclanthology.org/D18-2012.pdf"
    assert venue["acl_id"] == "D18-2012"
    assert venue["doi"] == "10.18653/v1/D18-2012"  # as the ACL Anthology reports it
    assert venue["arxiv_id"] == ""
    assert venue["s2_id"] == "4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f70"
    # The preprints that arXiv and the Seed record found reported this Edition's DOI or ACL ID,
    # so those channels found it too.
    assert venue["discovery_channels"] == "arxiv:tokenizer-titles|seed:sentencepiece|semantic-scholar:subword-phrases"
    assert venue["work_id"] == ""

    # Venue Editions without an ACL ID are named by their DOI, else by their Semantic Scholar id.
    journal = rows["10.1162/TACL_A_00999"]
    assert journal["edition_kind"] == "venue"
    assert journal["source_link"] == "https://doi.org/10.1162/TACL_A_00999"

    # OpenAlex reports the TACL paper under the same DOI in lower case: one row, which OpenAlex
    # enriches with its id and open-access PDF while the first Candidate's fields stay.
    assert journal["discovery_channels"] == "openalex:keyword-phrases|semantic-scholar:subword-phrases"
    assert journal["openalex_id"] == "W4300000102"
    assert journal["oa_pdf_urls"] == "https://direct.mit.edu/tacl/article-pdf/doi/10.1162/tacl_a_00999/tacl_a_00999.pdf"
    assert journal["venue"] == "Transactions of the Association for Computational Linguistics"

    # An OpenAlex work with an arXiv location is the preprint; its venue and PDFs aren't recorded.
    bpe = rows["2004.03720v3"]
    assert bpe["openalex_id"] == "W3000000101"
    assert bpe["oa_pdf_urls"] == ""
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

    # Found on the second citations page and by every keyword query: one row, every channel.
    assert rows["2004.03720v3"]["discovery_channels"] == (
        "arxiv:tokenizer-titles|openalex:keyword-phrases|seed-citations:sentencepiece|semantic-scholar:subword-phrases"
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


def test_seed_whose_references_the_publisher_withheld_expands_by_citations_only(fixture_snapshot, no_network, tmp_path):
    # Semantic Scholar answers with null data when the publisher elides a paper's references.
    elided = json.dumps({"data": None, "citingPaperInfo": {"openAccessPdf": {"disclaimer": "elided by the publisher"}}})
    SnapshotStore(fixture_snapshot).save(s2_seed_request("/references", 0), elided, collected_at="2026-10-16")
    manifest = tmp_path / "manifest.csv"
    run_collect(fixture_snapshot, manifest)
    rows = read_manifest(manifest)

    assert not any("seed-references:" in row["discovery_channels"] for row in rows.values())
    assert any("seed-citations:sentencepiece" in row["discovery_channels"] for row in rows.values())


def test_report_counts_editions_per_discovery_channel(fixture_snapshot, no_network, tmp_path, capsys):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    report = capsys.readouterr().err

    # Three preprints are found by both keyword queries: SentencePiece, the BPE paper and MrT5. The
    # Seed's references also reach the Sennrich paper, which only Semantic Scholar's query found.
    # OpenAlex also finds the BPE paper and the TACL paper, and two venue Editions nothing else
    # finds. An ACL Edition counts for every channel that found a preprint reporting its ACL ID.
    assert "discover: 19 Editions" in report
    assert "  arxiv:tokenizer-titles: 9 Editions, 4 found by no other channel" in report
    assert "  semantic-scholar:subword-phrases: 9 Editions, 1 found by no other channel" in report
    assert "  seed:sentencepiece: 2 Editions, 0 found by no other channel" in report
    assert "  seed-references:sentencepiece: 4 Editions, 2 found by no other channel" in report
    assert "  seed-citations:sentencepiece: 4 Editions, 2 found by no other channel" in report
    assert "  openalex:keyword-phrases: 5 Editions, 2 found by no other channel (1 pass the rules, 1 included, 0 pending)" in report
    # The same counts by source, so a source with several queries is measured as a whole. A Seed
    # and its citation hops count as one source.
    assert "  arxiv: 9 Editions, 4 found by no other source (0 pass the rules, 0 included, 0 pending)" in report
    assert "  semantic-scholar: 9 Editions, 1 found by no other source (1 pass the rules, 0 included, 0 pending)" in report
    assert "  openalex: 5 Editions, 2 found by no other source (1 pass the rules, 1 included, 0 pending)" in report
    assert "  seeds: 10 Editions, 4 found by no other source (3 pass the rules, 3 included, 0 pending)" in report
    assert "acl-anthology: 5 ACL IDs, 3 new venue Editions" in report


def test_report_shows_what_citation_expansion_adds_beyond_keyword_search(fixture_snapshot, no_network, tmp_path, capsys):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    report = capsys.readouterr().err

    # The Seed's own record isn't a citation hop, so expansion reaches eight Editions, three of
    # them ACL Editions of preprints it reached. Four of them no keyword query found: subword
    # regularization's preprint and ACL Edition and the Findings paper are included, the legal-MT
    # citer is rule-rejected.
    assert "  keyword search: 15 Editions, 9 included" in report
    assert "  citation expansion: 8 Editions, 4 found by no keyword query, 3 of those included" in report


def test_report_counts_pending_verdicts_apart_from_exclusions(fixture_snapshot, no_network, no_model, tmp_path, capsys):
    # A new model invalidates every cached verdict; without the judge they stay pending.
    config = edited_config(tmp_path, 'model = "example/judge-model"', 'model = "example/other-model"')
    run_collect(fixture_snapshot, tmp_path / "manifest.csv", config, "--no-judge")
    report = capsys.readouterr().err

    assert "  openalex: 5 Editions, 2 found by no other source (1 pass the rules, 0 included, 1 pending)" in report


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
    monkeypatch.setenv("OPENALEX_API_KEY", "fixture-openalex-key")
    with_key = tmp_path / "with-key.csv"
    run_collect(fixture_snapshot, with_key)

    assert with_key.read_bytes() == without_key.read_bytes()
    assert snapshot_files(fixture_snapshot) == before
    for name, data in before.items():
        text = gzip.decompress(data) if name.endswith(".gz") else data
        assert b"fixture-secret-key" not in text, name
        assert b"fixture-openalex-key" not in text, name


def test_snapshot_entries_are_compressed_and_credential_free(fixture_snapshot):
    files = snapshot_files(fixture_snapshot / "responses")
    # Two results pages each from arXiv, Semantic Scholar and OpenAlex, the Seed's record,
    # references and two citations pages, one full record per arXiv Edition that passes the rules,
    # and one ACL Anthology page per reported ACL ID.
    assert len(files) == 2 + 2 + 2 + 4 + 5 + 5
    for name, data in files.items():
        assert name.endswith(".json.gz")
        record = json.loads(gzip.decompress(data))
        assert record["collected_at"] == "2026-10-16"
        assert set(record["request"]) == {"source", "url", "params"}
        assert name.startswith(f"{record['request']['source']}/")
        markers = ["<feed", "<OAI-PMH", '"paperId"', "citation_title", '"results"']
        stored_404 = record["request"]["source"] == "acl-anthology" and record["body"] == ""
        assert stored_404 or any(marker in record["body"] for marker in markers)


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
    "10.5555/lrm.2022.7",
    "1508.07909v5",
    "1804.10959v1",
    "1808.06226v2",
    "2004.03720v3",
    "2020.findings-emnlp.414",
    "2022.findings-acl.99",
    "2410.20771v3",
    "708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3",
    "D18-2012",
    "P16-1162",
    "P18-1007",
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


class RecordingJudge(FakeJudge):
    """A FakeJudge that also keeps the abstract each Edition was scored on."""

    def __init__(self) -> None:
        super().__init__()
        self.abstracts: dict[str, str] = {}

    def score(self, editions):
        self.abstracts |= {edition.edition_id: edition.abstract for edition in editions}
        return super().score(editions)


def test_acl_editions_are_judged_on_an_abstract(fixture_snapshot, no_network, monkeypatch, tmp_path):
    fake = RecordingJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    # The ACL Anthology's own abstract, where it has one.
    assert fake.abstracts["2020.findings-emnlp.414"].startswith(
        "The success of pretrained transformer language models (LMs) in natural language processing"
    )
    # It has none for this 2016 paper, so the abstract Semantic Scholar reported with the ACL ID is used.
    assert fake.abstracts["P16-1162"] == (
        "We introduce a simpler and more effective approach, making the NMT model capable of"
        " open-vocabulary translation by encoding rare and unknown words as sequences of subword units."
    )
    rows = read_manifest(manifest)
    assert rows["P16-1162"]["relevance_verdict"] == "included"
    assert rows["P16-1162"]["judge_probability"] == "0.9000"


def edit_arxiv_record(snapshot_dir: Path, arxiv_id: str, *replacements: tuple[str, str]) -> None:
    """Replace an arXiv Edition's fixture record in the Snapshot with an edited copy."""
    record = (FIXTURES / "arxiv-oai" / f"{arxiv_id}.xml").read_text()
    for old, new in replacements:
        assert old in record
        record = record.replace(old, new, 1)
    SnapshotStore(snapshot_dir).save(arxiv_record_request(arxiv_id), record, collected_at="2026-10-18")


def withdraw_latest_version_of_1804_10959(snapshot_dir: Path) -> None:
    """Add a v2 to 1804.10959 that is a withdrawal: arXiv lists it with a 0kb size and serves no PDF for it."""
    withdrawal = (
        '    <version version="v2">\n'
        "      <date>Tue, 01 May 2018 09:00:00 GMT</date>\n"
        "      <size>0kb</size>\n"
        "      <source_type>I</source_type>\n"
        "    </version>\n"
    )
    edit_arxiv_record(
        snapshot_dir,
        "1804.10959",
        ("    </version>\n", "    </version>\n" + withdrawal),
        ("Accepted as a long paper at ACL2018", "Incorrect results"),
    )


def test_withdrawn_preprint_is_excluded_without_the_judge(fixture_snapshot, no_network, monkeypatch, tmp_path):
    withdraw_latest_version_of_1804_10959(fixture_snapshot)
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    assert "1804.10959v2" not in fake.scored
    row = read_manifest(manifest)["1804.10959v2"]
    assert row["rule_outcome"] == "pass"
    assert row["relevance_verdict"] == "excluded"
    assert row["relevance_stage"] == "withdrawn"
    assert row["relevance_reason"] == "withdrawn: v2 is a withdrawal; arXiv comments: Incorrect results"
    assert row["judge_probability"] == ""
    assert row["funnel_status"] == "discovered"


def test_withdrawal_replaced_by_a_new_version_is_judged(fixture_snapshot, no_network, monkeypatch, tmp_path):
    # MrT5's v2 becomes a withdrawal, but v3 replaced it.
    edit_arxiv_record(
        fixture_snapshot,
        "2410.20771",
        ("<date>Fri, 01 Nov 2024 00:00:00 GMT</date>\n      <size>100kb</size>", "<date>Fri, 01 Nov 2024 00:00:00 GMT</date>\n      <size>0kb</size>"),
    )
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    assert "2410.20771v3" in fake.scored
    row = read_manifest(manifest)["2410.20771v3"]
    assert row["relevance_stage"] == "judge"
    assert row["relevance_verdict"] == "included"


def test_report_counts_withdrawn_preprints_apart_from_judge_exclusions(fixture_snapshot, no_network, no_model, tmp_path, capsys):
    withdraw_latest_version_of_1804_10959(fixture_snapshot)
    report_path = tmp_path / "report.md"

    run_collect(fixture_snapshot, tmp_path / "manifest.csv", FIXTURES / "scope.toml", "--report", str(report_path))

    # One of the twelve included Editions in the fixture is now withdrawn.
    report = report_path.read_text()
    assert "| Rejected by the judge | 1 |" in report
    assert "| Withdrawn from arXiv | 1 |" in report
    assert "| Included | 11 |" in report
    assert "| Still to fetch | 10 |" in report
    assert "withdrawn: 1 excluded, the latest arXiv Version is a withdrawal" in capsys.readouterr().err


def edit_openalex_page(snapshot_dir: Path, page: str, *replacements: tuple[str, str]) -> None:
    """Replace an OpenAlex fixture results page in the Snapshot with an edited copy."""
    cursor = {"page-0.json": "*", "page-1.json": "FIXTURE-CURSOR-1"}[page]
    body = (FIXTURES / "openalex" / page).read_text()
    for old, new in replacements:
        assert old in body
        body = body.replace(old, new, 1)
    SnapshotStore(snapshot_dir).save(openalex_request(cursor), body, collected_at="2026-10-18")


def test_dissertation_is_excluded_as_not_a_paper_without_the_judge(fixture_snapshot, no_network, monkeypatch, tmp_path):
    # OpenAlex records its Unigram paper, a venue Edition, as a dissertation.
    edit_openalex_page(fixture_snapshot, "page-0.json", ('"type": "article"', '"type": "dissertation"'))
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    assert "10.5555/lrm.2022.7" not in fake.scored
    row = read_manifest(manifest)["10.5555/lrm.2022.7"]
    assert row["rule_outcome"] == "pass"
    assert row["relevance_verdict"] == "excluded"
    assert row["relevance_stage"] == "not a paper"
    assert row["relevance_reason"] == "not a paper: OpenAlex type dissertation"
    assert row["judge_probability"] == ""
    assert row["funnel_status"] == "discovered"


def test_thesis_named_in_the_arxiv_comments_is_excluded_without_the_judge(fixture_snapshot, no_network, monkeypatch, tmp_path):
    # The comments come from the full arXiv record, fetched after the rules.
    edit_arxiv_record(fixture_snapshot, "1804.10959", ("Accepted as a long paper at ACL2018", "PhD thesis, 120 pages"))
    fake = FakeJudge()
    monkeypatch.setattr(judge, "load_judge", lambda config: fake)
    manifest = tmp_path / "manifest.csv"

    run_collect(fixture_snapshot, manifest, FIXTURES / "scope.toml", "--refresh")

    assert "1804.10959v1" not in fake.scored
    row = read_manifest(manifest)["1804.10959v1"]
    assert row["relevance_stage"] == "not a paper"
    assert row["relevance_reason"] == "not a paper: a thesis, by its arXiv comments: PhD thesis, 120 pages"


def test_report_counts_editions_that_are_not_papers_apart_from_judge_exclusions(
    fixture_snapshot, no_network, no_model, tmp_path, capsys
):
    edit_openalex_page(fixture_snapshot, "page-0.json", ('"type": "article"', '"type": "dissertation"'))
    report_path = tmp_path / "report.md"

    run_collect(fixture_snapshot, tmp_path / "manifest.csv", FIXTURES / "scope.toml", "--report", str(report_path))

    # One of the twelve included Editions in the fixture is now a dissertation.
    report = report_path.read_text()
    assert "| Rejected by the judge | 1 |" in report
    assert "| Not a paper | 1 |" in report
    assert "| Included | 11 |" in report
    assert "not a paper: 1 excluded on their source metadata" in capsys.readouterr().err


def test_collect_writes_the_funnel_and_channel_report(fixture_snapshot, no_network, tmp_path):
    report_path = tmp_path / "report.md"
    run_collect(fixture_snapshot, tmp_path / "manifest.csv", FIXTURES / "scope.toml", "--report", str(report_path))
    report = report_path.read_text()

    # Six Candidates fail the rules and the judge excludes one more (see the tests above). Of the
    # twelve included, the Findings volume has no open PDF and nothing is fetched yet.
    assert "| Discovered | 19 |" in report
    assert "| Rejected by the rules | 6 |" in report
    assert "| Rejected by the judge | 1 |" in report
    assert "| Pending a judge verdict | 0 |" in report
    assert "| Included | 12 |" in report
    assert "| With full text | 0 |" in report
    assert "| No open PDF | 1 |" in report
    assert "| Still to fetch | 11 |" in report
    assert "judge `example/judge-model@0123456789abcdef0123456789abcdef01234567` at threshold 0.5" in report
    # Per source: Editions found, how many of them are included, and what only that source found.
    # The Seed found ten, nine of them included; arXiv found nine, five included.
    assert "| seeds | 10 | 9 | 4 | 3 | 3 | 0 |" in report
    assert "| arxiv | 9 | 5 | 4 | 0 | 0 | 0 |" in report
    assert "| openalex:keyword-phrases | 5 | 4 | 2 | 1 | 1 | 0 |" in report
    assert "| missing-required-term | 2 |" in report
    assert "| Citation expansion | 8 | 7 | 4 | 3 |" in report


def test_the_report_is_the_same_on_every_rerun(fixture_snapshot, no_network, tmp_path):
    first, second = tmp_path / "first.md", tmp_path / "second.md"
    run_collect(fixture_snapshot, tmp_path / "manifest.csv", FIXTURES / "scope.toml", "--report", str(first))
    run_collect(fixture_snapshot, tmp_path / "manifest.csv", FIXTURES / "scope.toml", "--report", str(second))

    assert first.read_bytes() == second.read_bytes()


def test_collect_warns_when_the_snapshot_is_larger_than_the_limit(fixture_snapshot, no_network, tmp_path, monkeypatch, capsys):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    assert "warning" not in capsys.readouterr().err

    # The fixture Snapshot is a few kB; a 1 kB limit stands in for the real one of about 50 MB.
    monkeypatch.setattr(snapshot, "SIZE_WARNING_BYTES", 1000)
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    assert "snapshot: warning: the Snapshot is 0.0 MB, more than about 0.001 MB" in capsys.readouterr().err


def test_collect_refuses_a_snapshot_that_contains_an_api_key(fixture_snapshot, no_network, tmp_path, monkeypatch):
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")  # a key that appears nowhere is fine
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-openalex-key-123")
    run_collect(fixture_snapshot, tmp_path / "manifest.csv")

    leaked = {"source": "openalex", "url": "https://api.openalex.org/works", "params": {"page": "leak"}}
    SnapshotStore(fixture_snapshot).save(leaked, '{"echo": "api_key=secret-openalex-key-123"}', collected_at="2026-10-17")
    before = (tmp_path / "manifest.csv").read_bytes()
    (tmp_path / "manifest.csv").write_bytes(b"stale")
    with pytest.raises(SystemExit) as refused:
        run_collect(fixture_snapshot, tmp_path / "manifest.csv")
    assert before and (tmp_path / "manifest.csv").read_bytes() == b"stale"  # nothing was written

    message = str(refused.value)
    assert "OPENALEX_API_KEY" in message
    assert "responses/openalex/" in message
    assert "secret-openalex-key-123" not in message
