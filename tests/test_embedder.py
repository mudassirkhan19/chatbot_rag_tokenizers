"""The opt-in test of the real embedder (#35, ADR 0042): the pinned bge-small on the CPU and on MPS.

Skipped unless RUN_EMBEDDER_TESTS=1. The first run downloads the pinned model (~130 MB) from Hugging Face:

    RUN_EMBEDDER_TESTS=1 just test tests/test_embedder.py

It embeds the Chunks of the two CC BY fixture papers on each device and checks that every question of the
fixture Evaluation set gets the same top 10 on both.
"""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from chatbot_rag_tokenizers.retrieval.dense import Dense
from chatbot_rag_tokenizers.retrieval.embedder import BgeEmbedder, default_device
from chatbot_rag_tokenizers.retrieval.retriever import indexed_text
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from parse_support import REPO_CONFIG, FakeGrobid, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
DENSE = load_retrieval_config(ROOT / "config" / "retrieval.toml").dense
EVALUATION_SET = Path(__file__).parent / "fixtures" / "eval" / "evaluation-set.jsonl"

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EMBEDDER_TESTS") != "1", reason="loads the embedding model; set RUN_EMBEDDER_TESTS=1"
)


@pytest.fixture(scope="module")
def embedders() -> dict[str, BgeEmbedder]:
    """The real embedder on each device, made before the parse fixtures shut the network off."""
    if default_device() != "mps":
        pytest.skip("this machine has no MPS")
    return {device: BgeEmbedder(DENSE.pin, device) for device in ("cpu", "mps")}


@pytest.fixture
def chunks(embedders, tmp_path: Path, grobid: FakeGrobid):
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return load_corpus(load_parse_config(REPO_CONFIG), tmp_path / "cache", tmp_path / "parse-report.md").chunks


def test_cpu_and_mps_give_the_same_top_10(embedders, chunks):
    texts = [indexed_text(chunk) for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]
    retrievers = {device: Dense(DENSE, ids, model.embed(texts), model) for device, model in embedders.items()}
    questions = [json.loads(line)["question"] for line in EVALUATION_SET.read_text().splitlines()]

    cpu, mps = retrievers["cpu"], retrievers["mps"]
    assert cpu.vectors.shape == (len(chunks), 384)
    assert np.abs(cpu.vectors - mps.vectors).max() < 1e-6
    for question in questions:
        assert [chunk_id for chunk_id, _ in cpu.query(question, 10)] == [chunk_id for chunk_id, _ in mps.query(question, 10)]


def test_the_model_counts_with_the_chunkers_vocabulary(embedders):
    chunking = json.loads(load_parse_config(REPO_CONFIG).chunking.tokenizer_file.read_text())

    assert embedders["cpu"].tokenizer.get_vocab() == chunking["model"]["vocab"]
