"""The one interface every retriever has (ADRs 0039 and 0042): its config builds it from Chunks or loads it from the
index cache, and it answers a query with ranked Chunk ids and their scores."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from ..parsing.chunker import Chunk

# What a retriever indexes for a Chunk: its context header, so a lookup naming a paper matches its title,
# then its text. The Chunk itself keeps the two apart, so citations still quote clean text.
HEADER_BREAK = "\n"


def indexed_text(chunk: Chunk) -> str:
    return chunk.header + HEADER_BREAK + chunk.text


class Retriever(Protocol):
    @property
    def device(self) -> str:
        """Where it computes: "cpu", or "mps" for a model on Apple silicon."""
        ...

    @property
    def parameters(self) -> int | None:
        """Its model's parameter count; None for BM25, which has no model."""
        ...

    @property
    def dimension(self) -> int | None:
        """The length of its vectors; None for BM25, which has none."""
        ...

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        """The ids of at most k Chunks for the text, best first, with their scores."""
        ...

    def save(self, directory: Path) -> None: ...


class RetrieverConfig(Protocol):
    @property
    def name(self) -> str:
        """The name `index --retriever` and `evaluate --retriever` take, e.g. "bm25"."""
        ...

    @property
    def key(self) -> str:
        """Names the retriever's index in the index cache: its name and a short hash of its settings."""
        ...

    def describe(self) -> dict[str, Any]:
        """The settings that decide the rankings, as the eval report shows them."""
        ...

    def build(self, chunks: Sequence[Chunk]) -> Retriever: ...

    def load(self, directory: Path) -> Retriever: ...
