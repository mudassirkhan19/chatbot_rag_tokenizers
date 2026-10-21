"""The embedder boundary (ADR 0042): the one way the dense retriever gets vectors.

An embedder turns texts into L2-normalised float32 vectors, one row per text, and names the model pin and
device it runs with. `load_embedder` makes the real one; the tests put a hashed bag of words in its place,
so they never download or load a model.

The real one runs a Hugging Face model at a pinned revision, with its weights checked against a pinned
sha256, pooled and cut as its table in the retrieval config says (ADR 0050). For BAAI/bge-small-en-v1.5
that is what its model card specifies: the [CLS] vector of the last layer, normalised, at most 512 tokens.
torch and transformers are imported only when it is made.
"""

import hashlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..config import ConfigError

# Each pooling a dense table can name, worded as the eval report and the index key give it.
POOLINGS = {
    "cls": "[CLS] vector of the last layer, L2-normalised",
    "mean": "mean of the last layer over non-padding tokens, L2-normalised",
}
# The files a pin's sha256 can be checked against, in the order they are looked for: a repo without
# model.safetensors (OpenScholar_Retriever has only pytorch_model.bin) is checked on the file it has (ADR 0052).
WEIGHTS = ("model.safetensors", "pytorch_model.bin")
_BATCH = 32
_PROGRESS_EVERY = 100  # batches


@dataclass(frozen=True)
class EmbeddingModel:
    model: str  # the Hugging Face repo
    revision: str  # the commit of that repo
    sha256: str  # of its weights file
    pooling: str  # a key of POOLINGS
    max_tokens: int  # a longer text is cut to its first max_tokens tokens


class Embedder(Protocol):
    model: str
    revision: str
    device: str  # "mps" or "cpu"
    parameters: int  # the model's, as the eval report gives its size

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """One L2-normalised float32 row per text, in the texts' order."""
        ...


def default_device() -> str:
    """MPS when this machine has it, otherwise the CPU."""
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def load_embedder(settings: EmbeddingModel, device: str | None = None) -> Embedder:
    return TransformersEmbedder(settings, device or default_device())


class TransformersEmbedder:
    def __init__(self, settings: EmbeddingModel, device: str) -> None:
        import torch
        from transformers import AutoModel

        self._torch = torch
        self.model, self.revision, self.device = settings.model, settings.revision, device
        self._pooling, self._max_tokens = settings.pooling, settings.max_tokens
        self.tokenizer, self._network, self.weights_file = load_pinned("embedder", AutoModel, settings.model, settings.revision, settings.sha256, device)
        self.parameters = sum(parameter.numel() for parameter in self._network.parameters())
        # The first pass on MPS compiles its kernels; doing it here keeps that out of the first query's latency.
        self.embed(["warm-up"])

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        torch = self._torch
        vectors = np.empty((len(texts), self._network.config.hidden_size), dtype=np.float32)
        # Texts of similar length share a batch, so little of it is padding.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        batches = range(0, len(order), _BATCH)
        cut = 0
        with torch.inference_mode():
            for number, start in enumerate(batches, start=1):
                rows = order[start : start + _BATCH]
                batch = [texts[i] for i in rows]
                cut += sum(len(ids) > self._max_tokens for ids in self.tokenizer(batch)["input_ids"])
                encoded = self.tokenizer(batch, padding=True, truncation=True, max_length=self._max_tokens, return_tensors="pt").to(self.device)
                hidden = self._network(**encoded).last_hidden_state
                if self._pooling == "cls":
                    pooled = hidden[:, 0]
                elif self._pooling == "mean":
                    # Padding positions are masked out, so a text's vector doesn't depend on its batch.
                    mask = encoded["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
                else:
                    raise ConfigError(f"pooling {self._pooling!r} is not one of {', '.join(POOLINGS)}")
                vectors[rows] = torch.nn.functional.normalize(pooled, dim=-1).cpu().numpy()
                if number % _PROGRESS_EVERY == 0:
                    print(f"embedder: {min(start + _BATCH, len(texts))}/{len(texts)} texts", file=sys.stderr)
        if cut:
            print(f"embedder: {cut} of {len(texts)} texts were cut to their first {self._max_tokens} tokens", file=sys.stderr)
        return vectors


def load_pinned(role: str, auto_class, model: str, revision: str, model_sha256: str, device: str) -> tuple[Any, Any, str]:
    """The tokenizer and network of a model at a pinned revision, in eval mode on the device, and the name of the
    weights file its sha256 was checked against. ``auto_class`` is the transformers class that loads it, such as
    AutoModel; ``role`` names it in the progress line. Raises ConfigError when the weights don't match the pin or
    don't fill the network exactly."""
    import torch
    from transformers import AutoTokenizer

    weights = weights_file(model, revision)
    if (found := sha256(weights)) != model_sha256:
        raise ConfigError(f"the weights of {model}@{revision} have sha256 {found[:12]}, not the pinned {model_sha256[:12]}")
    print(f"{role}: loading {model}@{revision[:12]} on {device}", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(model, revision=revision)
    # Loaded from the file whose hash was checked, never from another format the repo also holds.
    network, loading = auto_class.from_pretrained(
        model, revision=revision, dtype=torch.float32, use_safetensors=weights.name == WEIGHTS[0], output_loading_info=True
    )
    check_loading(model, loading)
    return tokenizer, network.to(device).eval(), weights.name


def weights_file(model: str, revision: str) -> Path:
    """The weights file of the repo at that revision, downloaded: the first of WEIGHTS it holds. Offline, a file
    Hugging Face hasn't cached counts as not held, so a wrong one stops at the hash check instead."""
    import huggingface_hub
    from huggingface_hub.errors import EntryNotFoundError

    for name in WEIGHTS:
        try:
            return Path(huggingface_hub.hf_hub_download(model, name, revision=revision))
        except EntryNotFoundError:
            continue
    raise ConfigError(f"found neither {' nor '.join(WEIGHTS)} of {model}@{revision[:12]}, on Hugging Face or, offline, in its cache")


def check_loading(model: str, loading: dict) -> None:
    """Refuse a checkpoint that doesn't fill the encoder exactly, as transformers reports its loading.

    Only the pooling layer may be missing: no pooling uses it, and a Contriever such as OpenScholar_Retriever
    is saved without it. Any other missing weight would be left at random, and the vectors would mean nothing.
    """

    def named(key) -> str:  # a mismatched key may come with the two shapes
        return key[0] if isinstance(key, tuple) else key

    if missing := sorted(key for key in loading["missing_keys"] if not key.startswith("pooler.")):
        raise ConfigError(f"{model} left {', '.join(missing)} untrained: its checkpoint does not hold them")
    if unexpected := sorted(loading["unexpected_keys"]):
        raise ConfigError(f"{model} did not use {', '.join(unexpected)} from its checkpoint")
    if mismatched := sorted(named(key) for key in loading["mismatched_keys"]):
        raise ConfigError(f"{model}: {', '.join(mismatched)} has the wrong shape in its checkpoint")
    if loading.get("error_msgs"):
        raise ConfigError(f"{model} did not load: {'; '.join(loading['error_msgs'])}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
