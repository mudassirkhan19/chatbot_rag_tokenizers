"""The reranker (#62): a cross-encoder reorders a retriever's top `pool` Chunks for the query.

The wrapper asks the retriever it wraps for at least `pool` Chunks, has the cross-encoder score each pair of the
query and a Chunk's context header plus text (what the retrievers index), and ranks the pool by that score, a tie
going to the Chunk the retriever ranked higher. Past the pool, the retriever's ranking follows as it was, with its
own scores, so a wrapper that asks for every Chunk (per_paper.py) still gets them all. No retriever's code or index
changes; a Collapsed ranking (collapse.py) wraps this one as it wraps any other.

The scorer is a boundary, as the embedder is (ADR 0042): `load_scorer` makes the real one, a Hugging Face sequence
classifier at a pinned revision with its weights checked against a pinned sha256, whose single logit is the score;
the tests put a fake in its place. torch and transformers are imported only when it is made.
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..config import ConfigError
from ..parsing.chunker import Chunk
from . import embedder
from .hybrid import devices
from .retriever import Retriever, indexed_text

SUFFIX = "+rerank"
INPUT = "the query, then the Chunk's context header and text, the Chunk cut to fit max_tokens"
SCORE = "the cross-encoder's logit; a tie goes to the retriever's order, and the Chunks past the pool follow in it"
_BATCH = 16


@dataclass(frozen=True)
class RerankConfig:
    model: str  # the Hugging Face repo of the cross-encoder
    revision: str  # the commit of that repo
    model_sha256: str  # of its weights file
    max_tokens: int  # a pair longer than this has its Chunk cut
    pool: int  # how many of the retriever's Chunks are scored for a query
    retrievers: tuple[str, ...]  # the retrievers `evaluate` scores reranked, by their `--retriever` names

    def describe(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "revision": self.revision,
            "model_sha256": self.model_sha256,
            "max_tokens": self.max_tokens,
            "pool": self.pool,
            "input": INPUT,
            "score": SCORE,
        }


class Scorer(Protocol):
    model: str
    revision: str
    device: str  # "mps" or "cpu"
    parameters: int

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        """One score per text, in the texts' order: higher is more relevant to the query."""
        ...


def load_scorer(config: RerankConfig, device: str | None = None) -> Scorer:
    return CrossEncoder(config, device or embedder.default_device())


class Reranked:
    """A retriever's top `pool` Chunks, reordered by a cross-encoder."""

    def __init__(self, retriever: Retriever, chunks: Mapping[str, Chunk], scorer: Scorer, pool: int) -> None:
        self.retriever = retriever
        self.chunks = chunks
        self.scorer = scorer
        self.pool = pool

    @property
    def device(self) -> str:
        return devices([self.retriever.device, self.scorer.device])

    @property
    def parameters(self) -> int:
        return (self.retriever.parameters or 0) + self.scorer.parameters

    @property
    def dimension(self) -> int | None:
        return self.retriever.dimension

    def save(self, directory: Path) -> None:
        self.retriever.save(directory)

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        ranking = self.retriever.query(text, max(self.pool, k))
        pool, rest = ranking[: self.pool], ranking[self.pool :]
        scores = self.scorer.score(text, [indexed_text(self.chunks[chunk_id]) for chunk_id, _ in pool])
        order = sorted(range(len(pool)), key=lambda position: -scores[position])  # stable, so a tie keeps the raw order
        return [(pool[position][0], scores[position]) for position in order][:k] + rest[: max(0, k - len(pool))]


class CrossEncoder:
    def __init__(self, config: RerankConfig, device: str) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.model, self.revision, self.device, self._max_tokens = config.model, config.revision, device, config.max_tokens
        weights = embedder.weights_file(config.model, config.revision)
        if (found := embedder.sha256(weights)) != config.model_sha256:
            raise ConfigError(f"the weights of {config.model}@{config.revision} have sha256 {found[:12]}, not the pinned {config.model_sha256[:12]}")
        print(f"reranker: loading {config.model}@{config.revision[:12]} on {device}", file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(config.model, revision=config.revision)
        network, loading = AutoModelForSequenceClassification.from_pretrained(
            config.model, revision=config.revision, dtype=torch.float32, use_safetensors=weights.name == embedder.WEIGHTS[0], output_loading_info=True
        )
        embedder.check_loading(config.model, loading)
        if network.config.num_labels != 1:
            raise ConfigError(f"{config.model} gives {network.config.num_labels} logits per pair, not the one score a cross-encoder gives")
        self.parameters = sum(parameter.numel() for parameter in network.parameters())
        # transformers types .to() as taking a model, not a device.
        self._network = network.to(device).eval()  # type: ignore[arg-type]
        # The first pass on MPS compiles its kernels; doing it here keeps that out of the first query's latency.
        self.score("warm-up", ["warm-up"])

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        torch = self._torch
        scores = [0.0] * len(texts)
        # Texts of similar length share a batch, so little of it is padding.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        with torch.inference_mode():
            for start in range(0, len(order), _BATCH):
                rows = order[start : start + _BATCH]
                encoded = self.tokenizer(
                    [query] * len(rows), [texts[i] for i in rows], padding=True, truncation="only_second", max_length=self._max_tokens, return_tensors="pt"
                ).to(self.device)
                logits = self._network(**encoded).logits[:, 0].float().cpu().tolist()
                for row, logit in zip(rows, logits):
                    scores[row] = logit
        return scores
