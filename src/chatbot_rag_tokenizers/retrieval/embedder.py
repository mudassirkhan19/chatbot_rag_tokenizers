"""The embedder boundary (ADR 0042): the one way the dense retriever gets vectors.

An embedder turns texts into L2-normalised float32 vectors, one row per text, and names the model pin and
device it runs with. `load_embedder` makes the real one; the tests put a hashed bag of words in its place,
so they never download or load a model.

The real one runs BAAI/bge-small-en-v1.5 at a pinned revision, with its weights checked against a pinned
sha256, as the model card specifies: the [CLS] vector of the last layer, normalised, at most 512 tokens.
torch and transformers are imported only when it is made.
"""

import hashlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from ..config import ConfigError

MAX_TOKENS = 512  # bge-small's position limit; a longer text is cut to its first 512 tokens
POOLING = "[CLS] vector of the last layer, L2-normalised"
WEIGHTS = "model.safetensors"  # the file the pin's sha256 is checked against
_BATCH = 32
_PROGRESS_EVERY = 100  # batches


@dataclass(frozen=True)
class ModelPin:
    model: str  # the Hugging Face repo
    revision: str  # the commit of that repo
    sha256: str  # of its weights file


class Embedder(Protocol):
    model: str
    revision: str
    device: str  # "mps" or "cpu"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """One L2-normalised float32 row per text, in the texts' order."""
        ...


def default_device() -> str:
    """MPS when this machine has it, otherwise the CPU."""
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def load_embedder(pin: ModelPin, device: str | None = None) -> Embedder:
    return BgeEmbedder(pin, device or default_device())


class BgeEmbedder:
    def __init__(self, pin: ModelPin, device: str) -> None:
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.model, self.revision, self.device = pin.model, pin.revision, device
        weights = Path(hf_hub_download(pin.model, WEIGHTS, revision=pin.revision))
        if (found := _sha256(weights)) != pin.sha256:
            raise ConfigError(f"the weights of {pin.model}@{pin.revision} have sha256 {found[:12]}, not the pinned {pin.sha256[:12]}")
        print(f"embedder: loading {pin.model}@{pin.revision[:12]} on {device}", file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(pin.model, revision=pin.revision)
        network = AutoModel.from_pretrained(pin.model, revision=pin.revision, dtype=torch.float32)
        # transformers types .to() as taking a model, not a device.
        self._network = network.to(device).eval()  # type: ignore[arg-type]
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
                cut += sum(len(ids) > MAX_TOKENS for ids in self.tokenizer(batch)["input_ids"])
                encoded = self.tokenizer(batch, padding=True, truncation=True, max_length=MAX_TOKENS, return_tensors="pt").to(self.device)
                cls = self._network(**encoded).last_hidden_state[:, 0]
                vectors[rows] = torch.nn.functional.normalize(cls, dim=-1).cpu().numpy()
                if number % _PROGRESS_EVERY == 0:
                    print(f"embedder: {min(start + _BATCH, len(texts))}/{len(texts)} texts", file=sys.stderr)
        if cut:
            print(f"embedder: {cut} of {len(texts)} texts were cut to their first {MAX_TOKENS} tokens", file=sys.stderr)
        return vectors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
