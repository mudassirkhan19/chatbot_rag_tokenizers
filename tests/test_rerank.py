"""The reranker on hand-built Chunks (#62): a cross-encoder scores the retriever's top `pool` against the query and
reorders them; the rest of the ranking follows as the retriever ranked it."""

from collections.abc import Sequence
from pathlib import Path

from chatbot_rag_tokenizers.parsing.chunker import Chunk
from chatbot_rag_tokenizers.retrieval.rerank import Reranked


def chunk(chunk_id: str, text: str, header: str = "") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        edition_id="1508.07909",
        pinned_id="1508.07909v5",
        version="v5",
        file_sha256="bpe",
        section_number="",
        section_title="Introduction",
        section_path=("Introduction",),
        appendix=False,
        kind="text",
        page_start=None,
        page_end=None,
        header=header,
        text=text,
        token_count=len(text.split()),
    )


class Ranked:
    """A retriever that ranks the Chunks in the order it was given them, and records the depth it was asked for."""

    def __init__(self, *chunk_ids: str) -> None:
        self.chunk_ids = chunk_ids
        self.asked: list[int] = []

    device, parameters, dimension = "cpu", None, None

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        self.asked.append(k)
        return [(chunk_id, 1.0 - rank / 100) for rank, chunk_id in enumerate(self.chunk_ids[:k])]

    def save(self, directory: Path) -> None: ...


class Overlap:
    """A cross-encoder that scores a text by how many of the query's words it holds, and records the pairs it saw."""

    model, revision, device, parameters = "fake-reranker", "0" * 40, "mps", 1000

    def __init__(self) -> None:
        self.seen: list[tuple[str, tuple[str, ...]]] = []

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        self.seen.append((query, tuple(texts)))
        words = set(query.lower().split())
        return [float(len(words & set(text.lower().split()))) for text in texts]


CHUNKS = [
    chunk("a", "subword units are segments"),
    chunk("b", "byte pair encoding merges the most frequent pair"),
    chunk("c", "a table of results"),
    chunk("d", "byte pair encoding of rare words"),
    chunk("e", "byte pair encoding merges the most frequent pair of symbols"),
    chunk("f", "conclusion"),
]
QUERY = "how does byte pair encoding merges work"


def reranked(pool: int) -> tuple[Reranked, Ranked, Overlap]:
    retriever, scorer = Ranked(*(c.chunk_id for c in CHUNKS)), Overlap()
    return Reranked(retriever, {c.chunk_id: c for c in CHUNKS}, scorer, pool), retriever, scorer


def test_the_top_pool_is_reordered_by_the_cross_encoder_and_the_rest_follows_in_the_raw_order():
    wrapper, _, _ = reranked(pool=4)

    ranking = wrapper.query(QUERY, 6)

    # b holds 4 of the query's words, d 3, a and c none (a before c, as ranked); e and f are outside the pool, so e,
    # which would score highest, stays where the retriever put it, with its raw score.
    assert ranking == [("b", 4.0), ("d", 3.0), ("a", 0.0), ("c", 0.0), ("e", 0.96), ("f", 0.95)]


def test_a_query_for_fewer_than_pool_chunks_still_reranks_the_whole_pool():
    wrapper, retriever, scorer = reranked(pool=5)

    # e is in the pool now and ties b at 4 words; the tie goes to b, which the retriever ranked higher.
    assert wrapper.query(QUERY, 1) == [("b", 4.0)]
    assert retriever.asked == [5] and len(scorer.seen[0][1]) == 5


def test_the_cross_encoder_sees_each_chunks_context_header_and_text_as_the_retrievers_index_it():
    headed = chunk("a", "subword units are segments", header="Neural Machine Translation of Rare Words with Subword Units > Introduction")
    scorer = Overlap()
    wrapper = Reranked(Ranked("a"), {"a": headed}, scorer, pool=1)

    wrapper.query(QUERY, 1)

    assert scorer.seen == [(QUERY, ("Neural Machine Translation of Rare Words with Subword Units > Introduction\nsubword units are segments",))]
