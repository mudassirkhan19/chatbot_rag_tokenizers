"""Offline runs of `load_corpus` over the full-text record's corpus: each file's Chunks cite the pinned id the parse
report lists for it and that id's Edition in the manifest, whichever id filled the parse cache (ADR 0066).

The record, manifest and PDFs are fixtures in the shape `fetch` leaves them (parse_support.FetchedCorpus).
"""

from pathlib import Path

import pytest

from chatbot_rag_tokenizers.parsing.chunker import Chunk
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import Corpus, CorpusError, load_corpus
from parse_support import REPO_CONFIG, FakeGrobid, FetchedCorpus, run_parse, seed_pdf, sha256


@pytest.fixture
def corpus(tmp_path: Path, grobid: FakeGrobid) -> FetchedCorpus:
    return FetchedCorpus(tmp_path, grobid)


def loaded(corpus: FetchedCorpus, cache: Path | None = None) -> Corpus:
    return load_corpus(load_parse_config(REPO_CONFIG), cache or corpus.root / "cache", corpus.root / "parse-report.md", corpus.manifest)


def cited(chunks: tuple[Chunk, ...], pdf: bytes) -> list[tuple[str, str, str]]:
    """The (Edition id, pinned id, Version) of each Chunk of the file, in the corpus's order, each run of them once."""
    runs: list[tuple[str, str, str]] = []
    for chunk in chunks:
        if chunk.file_sha256 == sha256(pdf) and (not runs or runs[-1] != (chunk.edition_id, chunk.pinned_id, chunk.version)):
            runs.append((chunk.edition_id, chunk.pinned_id, chunk.version))
    return runs


def test_a_file_pinned_under_two_ids_gives_each_its_own_ids_though_the_cache_holds_one(corpus):
    # The same bytes, pinned by a venue Edition and by a preprint: the cache keeps one set of Chunks for them.
    pdf = corpus.fetched("2022.nsurl-1.1", "2022.nsurl-1.1.pdf", "syllable tokens")
    corpus.fetched("2301.06736v1", "2301.06736v1.pdf", "syllable tokens")
    corpus.parse()
    assert corpus.editions_and_anchors(pdf) == {("2301.06736v1", "2301.06736v1", "v1", sha256(pdf))}

    chunks = loaded(corpus).chunks

    assert cited(chunks, pdf) == [("2022.nsurl-1.1", "2022.nsurl-1.1", ""), ("2301.06736v1", "2301.06736v1", "v1")]


def test_chunks_cached_under_an_alias_another_checkout_parsed_cite_the_reports_id(corpus, tmp_path, grobid):
    # Another checkout parsed the file when the manifest still named its Edition by an alias, and filled the cache.
    (tmp_path / "elsewhere").mkdir()
    elsewhere = FetchedCorpus(tmp_path / "elsewhere", grobid)
    pdf = elsewhere.fetched("arXiv:2607.05691v1", "arXiv_2607.05691v1.pdf", "smiles")
    elsewhere.parse()
    assert elsewhere.anchors(pdf) == {("arXiv:2607.05691v1", "v1", sha256(pdf))}
    corpus.fetched("2607.05691v1", "2607.05691v1.pdf", "smiles")
    corpus.parse()

    from_elsewhere = loaded(corpus, cache=elsewhere.root / "cache")

    assert cited(from_elsewhere.chunks, pdf) == [("2607.05691v1", "2607.05691v1", "v1")]
    # Only the ids are restamped: the Chunks an index is built from are the same.
    assert [(c.chunk_id, c.text) for c in from_elsewhere.chunks] == [(c.chunk_id, c.text) for c in loaded(corpus).chunks]


def test_a_corpus_parsed_from_the_record_needs_the_manifest_that_names_its_editions(corpus):
    corpus.fetched("2607.05691v1", "2607.05691v1.pdf", "smiles")
    corpus.parse()
    corpus.manifest.unlink()

    with pytest.raises(CorpusError, match="no manifest at .*manifest.csv"):
        loaded(corpus)


def test_a_pinned_id_the_manifest_no_longer_includes_stops_the_load(corpus):
    corpus.fetched("2607.05691v1", "2607.05691v1.pdf", "smiles")
    corpus.parse()
    # The Edition was judged again and excluded after this parse.
    corpus.manifest.write_text(corpus.manifest.read_text().replace(",included,", ",excluded,"))

    with pytest.raises(CorpusError, match="includes no Edition pinned to 1 file .*: 2607.05691v1. Run `just parse`"):
        loaded(corpus)


def test_a_files_run_takes_each_edition_from_every_file_given_as_parse_did_failed_ones_too(tmp_path, grobid):
    v1 = seed_pdf(tmp_path, grobid, "wechsel_2112.06598v1.pdf", "wechsel_2112.06598v2.tei.xml")
    # The latest Version fails the quality gate, so it has no Chunks, but it still names the Edition.
    seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "scanned.tei.xml")
    with pytest.raises(SystemExit):
        run_parse(tmp_path, v1, tmp_path / "pdfs" / "wechsel_2112.06598v2.pdf")

    chunks = load_corpus(load_parse_config(REPO_CONFIG), tmp_path / "cache", tmp_path / "parse-report.md", tmp_path / "manifest.csv").chunks

    assert cited(chunks, v1.read_bytes()) == [("2112.06598v2", "2112.06598v1", "v1")]
