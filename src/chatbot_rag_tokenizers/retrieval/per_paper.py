"""Per-paper retrieval (ADR 0076): a question that names two or more papers gets the Chunks of each.

A comparison reaches the embedder as one query, which lands on whichever paper restates both sides (#77). So the
wrapper asks for the papers, methods and models the question names, as it words them, and finds the Works each
could be among the indexed Chunks' Editions:

    "<Surname> et al. …"   the Works whose Edition's first author has that surname
    any other name         the Works whose Edition's title holds every word of the name

A name no Work matches is dropped. When two or more names find different Works, the retriever's whole ranking for
the question is split into one stream per name, the Chunks of that name's Works in the order the ranking gives them,
and the streams fill the slots in rotation, in the order the names were given, each Chunk once, then the rest of the
ranking. Otherwise the question is ranked as it is. No retriever's code or index changes; a Collapsed ranking (collapse.py) wraps this one as it wraps any other.
"""

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from ..parsing.chunker import Chunk
from .bm25 import tokenise
from .retriever import Retriever

SUFFIX = "+per-paper"
_POSSESSIVE = re.compile(r"['’]s\b")  # "MEGABYTE's" names MEGABYTE
_ET_AL = re.compile(r"([^\W\d_][\w'’-]*)\s+et\s+al\b", re.IGNORECASE)  # "Goldman et al.'s Unpacking Tokenization"


class NamedWorks:
    """The Works a name could be, among the Works of the indexed Chunks."""

    def __init__(self, chunks: Mapping[str, Chunk], manifest: Iterable[Mapping[str, str]]) -> None:
        # An Edition without a work_id, or without a manifest row, is its own Work, as in the Collapsed ranking.
        rows = {row["edition_id"]: row for row in manifest}
        works = {edition_id: rows.get(edition_id, {}).get("work_id") or f"edition:{edition_id}" for edition_id in {c.edition_id for c in chunks.values()}}
        self.of_chunk = {chunk_id: works[chunk.edition_id] for chunk_id, chunk in chunks.items()}
        self._titles: dict[str, list[set[str]]] = {}  # the words of each title of a Work's indexed Editions
        self._first_authors: dict[str, set[str]] = {}  # the lower-cased surname of each indexed Edition's first author
        for edition_id, work in works.items():
            row = rows.get(edition_id, {})
            self._titles.setdefault(work, []).append(set(tokenise(row.get("title", ""))))
            surnames = self._first_authors.setdefault(work, set())
            if first := row.get("authors", "").split(";")[0].split():
                surnames.add(first[-1].lower())

    def __call__(self, name: str) -> frozenset[str]:
        """The Works a name could be: by its first author's surname, or by the words of its title."""
        if author := _ET_AL.search(name):
            surname = author[1].lower()
            return frozenset(work for work, surnames in self._first_authors.items() if surname in surnames)
        words = set(tokenise(_POSSESSIVE.sub("", name)))
        return frozenset(work for work, titles in self._titles.items() if words and any(words <= title for title in titles))


class PerPaper:
    """A retriever's ranking, taken a paper at a time when the question names two or more."""

    def __init__(self, retriever: Retriever, chunks: Mapping[str, Chunk], works: NamedWorks, names: Callable[[str], Sequence[str]]) -> None:
        self.retriever = retriever
        self.chunks = chunks
        self.works = works
        self.names = names

    @property
    def device(self) -> str:
        return self.retriever.device

    @property
    def parameters(self) -> int | None:
        return self.retriever.parameters

    @property
    def dimension(self) -> int | None:
        return self.retriever.dimension

    def save(self, directory: Path) -> None:
        self.retriever.save(directory)

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        works = list(dict.fromkeys(works for works in map(self.works, self.names(text)) if works))
        if len(works) < 2:
            return self.retriever.query(text, k)
        ranking = self.retriever.query(text, len(self.chunks))
        streams = [[hit for hit in ranking if self.works.of_chunk[hit[0]] in named] for named in works]
        merged: dict[str, float] = {}
        for place in range(max(map(len, streams))):
            for stream in streams:
                if place < len(stream):
                    merged.setdefault(*stream[place])
        for chunk_id, score in ranking:  # once the named Works' Chunks run out, the rest in the raw order
            merged.setdefault(chunk_id, score)
        return list(merged.items())[:k]
