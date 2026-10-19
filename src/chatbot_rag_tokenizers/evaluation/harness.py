"""The harness (ADR 0039): runs every question through a retriever and scores the raw ranking against its Passages.

- Recall@5: the share of a question's Passages held by a Chunk in the top 5, averaged over questions.
- MRR@10: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top 10.
- Hit@5: the share of questions with a Passage held in the top 5.

Unanswerable questions are run, so they get a line and a latency, but are left out of the metrics. A
follow-up is run three ways: alone, after its history, and as its reference rewrite. Each query keeps its
top 5, for measuring what crowds it (crowding.py). A Collapsed ranking (ADR 0053) is scored the same way, and
its query also keeps the Editions merged into each slot and how many Works its pool held.
"""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..parsing.chunker import Chunk
from ..parsing.report import is_mostly_numeric
from ..retrieval.collapse import Collapsed
from ..retrieval.retriever import Retriever
from .evalset import Question
from .matching import MatchingRule, holds

RECALL_DEPTH = HIT_DEPTH = CROWDING_DEPTH = 5
MRR_DEPTH = 10

# How a question is put to the retriever: as asked, or, for a follow-up, in each of three ways.
AS_ASKED = "as asked"
FOLLOW_UP_ALONE = "follow-up alone"
WITH_HISTORY = "history + follow-up"
REWRITE = "reference rewrite"
FOLLOW_UP_QUERIES = (FOLLOW_UP_ALONE, WITH_HISTORY, REWRITE)


@dataclass(frozen=True)
class Slot:
    """One place in the top 5, for measuring what crowds it (ADR 0044)."""

    edition_id: str
    pinned_id: str  # the file the Chunk is from
    mostly_numeric: bool  # a text Chunk that is mostly numbers, as the parse report counts them (ADR 0035)
    holds_passage: bool
    merged: tuple[str, ...] = ()  # in a Collapsed ranking, the pinned ids of the Work's other files in the pool


@dataclass(frozen=True)
class Scored:
    """One query of one question, scored."""

    question: Question
    query_kind: str  # AS_ASKED, or one of FOLLOW_UP_QUERIES
    first_hit: int | None  # the rank of the first Chunk holding any Passage, None when none is in the top 10
    found: int  # the Passages held by a Chunk in the top 5
    top: tuple[Slot, ...]  # the top 5, best first; fewer when the retriever ranked fewer Chunks
    seconds: float  # how long the retriever took to answer
    pool_works: int | None = None  # in a Collapsed ranking, the Works its pool held


@dataclass(frozen=True)
class Metrics:
    questions: int
    recall: float
    mrr: float
    hit: float


def queries(question: Question) -> list[tuple[str, str]]:
    """Each query a question is run as, named."""
    if question.type != "follow-up":
        return [(AS_ASKED, question.question)]
    return [
        (FOLLOW_UP_ALONE, question.question),
        (WITH_HISTORY, " ".join([*question.history, question.question])),
        (REWRITE, question.rewrite),
    ]


def score(questions: Sequence[Question], retriever: Retriever, chunks: Mapping[str, Chunk], rule: MatchingRule) -> list[Scored]:
    scored = []
    for question in questions:
        for query_kind, text in queries(question):
            started = time.perf_counter()
            if isinstance(retriever, Collapsed):
                collapse = retriever.collapse(text, MRR_DEPTH)
                hits, merged, pool_works = collapse.ranking, {i: m.editions for i, m in collapse.merged.items()}, collapse.works
            else:
                hits, merged, pool_works = retriever.query(text, MRR_DEPTH), {}, None
            seconds = time.perf_counter() - started
            ranking = [chunks[chunk_id] for chunk_id, _ in hits]
            held = [[holds(chunk.text, passage.quote, rule) for passage in question.passages] for chunk in ranking]
            first_hit = next((rank for rank, row in enumerate(held, start=1) if any(row)), None)
            found = sum(1 for column in zip(*held[:RECALL_DEPTH]) if any(column))
            top = tuple(
                Slot(chunk.edition_id, chunk.pinned_id, is_mostly_numeric(chunk), any(row), merged.get(chunk.chunk_id, ()))
                for chunk, row in zip(ranking[:CROWDING_DEPTH], held)
            )
            scored.append(Scored(question, query_kind, first_hit, found, top, seconds, pool_works))
    return scored


def all_answerable(scored: Sequence[Scored]) -> list[Scored]:
    """Every answerable question once, as a user would type it: a follow-up alone, without its history."""
    return [s for s in scored if s.question.answerable and s.query_kind in (AS_ASKED, FOLLOW_UP_ALONE)]


def metrics(scored: Sequence[Scored]) -> Metrics | None:
    """The metrics over these queries, or None when there are none."""
    if not scored:
        return None
    count = len(scored)
    return Metrics(
        questions=count,
        recall=sum(s.found / len(s.question.passages) for s in scored) / count,
        mrr=sum(1 / s.first_hit if s.first_hit else 0.0 for s in scored) / count,
        hit=sum(1 for s in scored if s.found) / count,
    )
