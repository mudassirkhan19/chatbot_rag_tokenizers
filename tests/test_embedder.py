"""The opt-in test of the real embedder (#35, #57, ADRs 0042, 0050 and 0051): every dense table's model on the CPU and on MPS.

Skipped unless RUN_EMBEDDER_TESTS=1. The first run downloads the pinned models (~1 GB) from Hugging Face:

    RUN_EMBEDDER_TESTS=1 just test tests/test_embedder.py -s

For each model it checks the weights against the pin, the vocabulary against the chunker's, and that every
question of the fixture Evaluation set gets the same top 10 on both devices, over the Chunks of the two CC BY
fixture papers. For OpenScholar_Retriever it also checks our vectors against vectors made the way Contriever's
reference code makes them, and prints whether Contriever's raw inner product ranks the fixture as our
normalised vectors do (`-s` shows it).
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from chatbot_rag_tokenizers.retrieval.dense import Dense
from chatbot_rag_tokenizers.retrieval.embedder import TransformersEmbedder, default_device
from chatbot_rag_tokenizers.retrieval.retriever import indexed_text
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from parse_support import REPO_CONFIG, FakeGrobid, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
DENSE = {config.name: config for config in load_retrieval_config(ROOT / "config" / "retrieval.toml").dense}
EVALUATION_SET = Path(__file__).parent / "fixtures" / "eval" / "evaluation-set.jsonl"
# Each model's vector size and the weights file its repo holds, from its model card and repo.
DIMENSIONS = {"dense.bge-small": 384, "dense.bge-base": 768, "dense.openscholar": 768}
WEIGHTS_FILES = {"dense.bge-small": "model.safetensors", "dense.bge-base": "model.safetensors", "dense.openscholar": "pytorch_model.bin"}

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EMBEDDER_TESTS") != "1", reason="loads the embedding models; set RUN_EMBEDDER_TESTS=1"
)


@pytest.fixture(scope="module", params=sorted(DENSE), ids=str)
def table(request) -> str:
    return request.param


@pytest.fixture(scope="module")
def embedders(table: str) -> dict[str, TransformersEmbedder]:
    """The real embedder of a table on each device, made before the parse fixtures shut the network off."""
    if default_device() != "mps":
        pytest.skip("this machine has no MPS")
    return {device: TransformersEmbedder(DENSE[table].embedding_model, device) for device in ("cpu", "mps")}


@pytest.fixture
def chunks(embedders, tmp_path: Path, grobid: FakeGrobid):
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    return load_corpus(load_parse_config(REPO_CONFIG), tmp_path / "cache", tmp_path / "parse-report.md").chunks


def questions() -> list[str]:
    return [json.loads(line)["question"] for line in EVALUATION_SET.read_text().splitlines()]


def test_the_weights_are_the_pinned_file(table, embedders):
    from huggingface_hub import hf_hub_download

    model = embedders["cpu"]
    weights = Path(hf_hub_download(model.model, model.weights_file, revision=model.revision))

    assert model.weights_file == WEIGHTS_FILES[table]
    assert hashlib.sha256(weights.read_bytes()).hexdigest() == DENSE[table].model_sha256


def test_cpu_and_mps_give_the_same_top_10(table, embedders, chunks):
    texts = [indexed_text(chunk) for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]
    retrievers = {device: Dense(DENSE[table], ids, model.embed(texts), model) for device, model in embedders.items()}

    cpu, mps = retrievers["cpu"], retrievers["mps"]
    assert cpu.vectors.shape == (len(chunks), DIMENSIONS[table])
    print(f"\n{table}: CPU and MPS vectors differ by at most {np.abs(cpu.vectors - mps.vectors).max():.1e} per dimension")
    assert np.abs(cpu.vectors - mps.vectors).max() < 1e-6
    for question in questions():
        assert [chunk_id for chunk_id, _ in cpu.query(question, 10)] == [chunk_id for chunk_id, _ in mps.query(question, 10)]


def test_the_model_counts_with_the_chunkers_vocabulary(embedders):
    chunking = json.loads(load_parse_config(REPO_CONFIG).chunking.tokenizer_file.read_text())

    assert embedders["cpu"].tokenizer.get_vocab() == chunking["model"]["vocab"]


@pytest.fixture(scope="module")
def contriever(table: str):
    """A function giving OpenScholar_Retriever's vectors as Contriever's reference code makes them
    (src/contriever.py in facebookresearch/contriever): a BertModel without its pooling layer, the last layer
    with padding zeroed, summed and divided by the number of tokens, not normalised. It embeds one text at a
    time, so nothing is padded. Loaded, like the embedders, before the network is shut off."""
    if table != "dense.openscholar":
        pytest.skip("the reference vectors are OpenScholar_Retriever's")
    import torch
    from transformers import AutoTokenizer, BertModel

    config = DENSE[table]
    tokenizer = AutoTokenizer.from_pretrained(config.model, revision=config.revision)
    model = BertModel.from_pretrained(config.model, revision=config.revision, add_pooling_layer=False, use_safetensors=False).eval()

    def vectors(texts: list[str]) -> np.ndarray:
        rows = []
        with torch.inference_mode():
            for text in texts:
                encoded = tokenizer([text], max_length=config.max_tokens, truncation=True, return_tensors="pt")
                mask = encoded["attention_mask"]
                last_hidden = model(**encoded)["last_hidden_state"].masked_fill(~mask[..., None].bool(), 0.0)
                rows.append((last_hidden.sum(dim=1) / mask.sum(dim=1)[..., None])[0].numpy())
        return np.stack(rows)

    return vectors


def test_openscholar_pools_as_contrievers_reference_code(contriever, embedders, chunks):
    # The shortest and longest Chunks, two between, and a question: batched with each other, so most are padded.
    texts = sorted((indexed_text(chunk) for chunk in chunks), key=len)
    sample = [texts[0], texts[len(texts) // 3], texts[2 * len(texts) // 3], texts[-1], questions()[0]]

    reference = contriever(sample)
    reference /= np.linalg.norm(reference, axis=1, keepdims=True)

    difference = np.abs(embedders["cpu"].embed(sample) - reference).max()
    print(f"\ndense.openscholar: the embedder's vectors differ from the reference's by at most {difference:.1e} per dimension")
    assert difference < 1e-5


def test_openscholar_normalised_and_raw_inner_product_top_10(contriever, chunks):
    """Measures, and prints, which fixture questions' top 10 change when the vectors are normalised (cosine)
    rather than scored by Contriever's raw inner product."""
    raw_chunks = contriever([indexed_text(chunk) for chunk in chunks])
    asked = questions()
    raw_questions = contriever(asked)

    def top_10(chunk_vectors: np.ndarray, question_vectors: np.ndarray) -> list[list[int]]:
        return [list(np.argsort(-(chunk_vectors @ vector), kind="stable")[:10]) for vector in question_vectors]

    def normalised(vectors: np.ndarray) -> np.ndarray:
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    raw, cosine = top_10(raw_chunks, raw_questions), top_10(normalised(raw_chunks), normalised(raw_questions))
    changed = [(question, a, b) for question, a, b in zip(asked, raw, cosine) if a != b]
    print(f"\ndense.openscholar: normalising changes the top 10 of {len(changed)} of {len(asked)} fixture questions")
    for question, a, b in changed:
        print(f"  {question!r}: same set {set(a) == set(b)}, {sum(x != y for x, y in zip(a, b))} of 10 ranks differ")
    assert len(raw) == len(asked)
