"""The real embedder's checks on a model's files, offline (#57, ADR 0052): which weights file the pin's
sha256 is checked against, and refusing a checkpoint that leaves part of the encoder untrained."""

from pathlib import Path

import huggingface_hub
import pytest
from huggingface_hub.errors import EntryNotFoundError

from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.retrieval.embedder import check_loading, weights_file


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A Hugging Face repo holding the files named, in place of the Hub."""
    held: set[str] = set()

    def download(model: str, filename: str, revision: str) -> str:
        if filename not in held:
            raise EntryNotFoundError(f"{filename} is not in {model}@{revision}")
        (path := tmp_path / filename).write_bytes(b"weights")
        return str(path)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", download)
    return held


def test_a_repo_with_model_safetensors_is_checked_on_it(repo):
    repo |= {"model.safetensors", "pytorch_model.bin"}

    assert weights_file("BAAI/bge-base-en-v1.5", "a" * 40).name == "model.safetensors"


def test_a_repo_without_model_safetensors_is_checked_on_its_pytorch_model_bin(repo):
    repo |= {"pytorch_model.bin"}

    assert weights_file("OpenScholar/OpenScholar_Retriever", "a" * 40).name == "pytorch_model.bin"


def test_a_repo_with_neither_weights_file_is_refused(repo):
    with pytest.raises(ConfigError, match=r"found neither model.safetensors nor pytorch_model.bin of OpenScholar/OpenScholar_Retriever@aaaaaaaaaaaa"):
        weights_file("OpenScholar/OpenScholar_Retriever", "a" * 40)


def loading(missing=(), unexpected=(), mismatched=()) -> dict:
    """What transformers reports on loading a checkpoint (from_pretrained with output_loading_info=True)."""
    return {"missing_keys": set(missing), "unexpected_keys": set(unexpected), "mismatched_keys": set(mismatched), "error_msgs": []}


def test_a_checkpoint_without_the_pooler_loads():
    # OpenScholar_Retriever is a Contriever, a BertModel saved without its pooling layer, which we never use.
    check_loading("OpenScholar/OpenScholar_Retriever", loading(missing=["pooler.dense.weight", "pooler.dense.bias"]))


def test_a_checkpoint_missing_an_encoder_weight_is_refused():
    with pytest.raises(ConfigError, match=r"OpenScholar/OpenScholar_Retriever left encoder.layer.0.output.dense.weight untrained"):
        check_loading("OpenScholar/OpenScholar_Retriever", loading(missing=["encoder.layer.0.output.dense.weight", "pooler.dense.bias"]))


def test_a_checkpoint_with_weights_the_model_does_not_use_is_refused():
    # e.g. every weight under a "bert." prefix the model doesn't expect
    with pytest.raises(ConfigError, match=r"did not use bert.embeddings.word_embeddings.weight"):
        check_loading("some/model", loading(unexpected=["bert.embeddings.word_embeddings.weight"]))


def test_a_checkpoint_with_a_weight_of_the_wrong_shape_is_refused():
    with pytest.raises(ConfigError, match=r"embeddings.word_embeddings.weight has the wrong shape"):
        check_loading("some/model", loading(mismatched=["embeddings.word_embeddings.weight"]))
