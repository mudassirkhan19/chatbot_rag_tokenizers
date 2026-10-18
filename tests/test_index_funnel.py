"""Offline runs of `index` over the full-text record's corpus: it marks the included Editions whose pinned files
are all in the index as indexed, in the manifest and the funnel report, and records the indexed files in the
Snapshot so `collect` keeps the mark (ADR 0045).

The record, manifest and PDFs are fixtures in the shape `fetch` leaves them (parse_support.FetchedCorpus).
"""

import csv
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from parse_support import FakeGrobid, FetchedCorpus, run_parse, seed_pdf

RETRIEVAL_CONFIG = Path(__file__).parents[1] / "config" / "retrieval.toml"


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> FetchedCorpus:
    return FetchedCorpus(tmp_path, grobid)


def run_index(corpus: FetchedCorpus) -> None:
    main(
        [
            "index",
            "--config", str(RETRIEVAL_CONFIG),
            "--retriever", "bm25",
            "--cache", str(corpus.root / "cache"),
            "--parse-report", str(corpus.root / "parse-report.md"),
            "--index-cache", str(corpus.root / "index-cache"),
            "--snapshot", str(corpus.snapshot),
            "--manifest", str(corpus.manifest),
            "--funnel-report", str(corpus.root / "report.md"),
        ]
    )  # fmt: skip


def statuses(corpus: FetchedCorpus) -> dict[str, str]:
    with corpus.manifest.open(newline="") as f:
        return {row["edition_id"]: row["funnel_status"] for row in csv.DictReader(f)}


def test_index_marks_exactly_the_included_editions_whose_pinned_files_are_all_indexed(corpus):
    corpus.fetched("P16-1162", "P16-1162.pdf", "venue")
    corpus.fetched("2112.06598v2", "2112.06598v1.pdf", "wechsel v1")
    corpus.fetched("2112.06598v2", "2112.06598v2.pdf", "wechsel v2")
    # One of its two files fails the quality gate, so it has no Chunks and the Edition isn't wholly indexed.
    corpus.fetched("1508.07909v5", "1508.07909v1.pdf", "bpe v1")
    corpus.fetched("1508.07909v5", "1508.07909v5.pdf", "bpe v5", tei="scanned.tei.xml")
    corpus.fetched("2506.00291v2", "2506.00291v2.pdf", "withdrawn")
    corpus.excluded("2506.00291v2")
    corpus.no_open_pdf("2020.acl-main.1")
    with pytest.raises(SystemExit):
        corpus.parse()

    run_index(corpus)

    assert statuses(corpus) == {
        "P16-1162": "indexed",
        "2112.06598v2": "indexed",
        "1508.07909v5": "full text",
        "2506.00291v2": "discovered",
        "2020.acl-main.1": "no_fulltext",
    }
    report = (corpus.root / "report.md").read_text()
    assert "| With full text | 3 |" in report
    assert "| Indexed | 2 |" in report
    assert "| With full text, not indexed | 1 |" in report


def test_an_index_over_a_seed_files_run_leaves_the_marks_and_the_record_alone(corpus, grobid, capsys):
    corpus.fetched("P16-1162", "P16-1162.pdf", "venue")
    corpus.parse()
    run_index(corpus)
    record = corpus.snapshot / "index" / "files.jsonl"
    marked, recorded = corpus.manifest.read_bytes(), record.read_bytes()

    # The Seeds-only route parses other files into the same report; its corpus isn't the manifest's.
    run_parse(corpus.root, seed_pdf(corpus.root, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"))
    run_index(corpus)

    assert corpus.manifest.read_bytes() == marked
    assert record.read_bytes() == recorded
    assert "parse report comes from a `--files` run, so no Edition is marked indexed" in capsys.readouterr().err
