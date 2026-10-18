"""The harness: runs every question through a retriever and scores the raw ranking against its Passages (ADR 0039).

- Recall@5: the share of a question's Passages held by a Chunk in the top 5, averaged over questions.
- MRR@10: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top 10.
- Hit@5: the share of questions with a Passage held in the top 5.

Unanswerable questions are run, so they get a line and a latency, but are left out of the metrics. A
follow-up is run three ways: alone, after its history, and as its reference rewrite.
"""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..retrieval.retriever import Retriever
from .evalset import Question
from .matching import holds

RECALL_DEPTH = HIT_DEPTH = 5
MRR_DEPTH = 10

AS_ASKED = "as asked"
FOLLOW_UP_QUERIES = ("follow-up alone", "history + follow-up", "reference rewrite")


@dataclass(frozen=True)
class Scored:
    """One query of one question, scored."""

    question: Question
    query: str  # AS_ASKED, or one of FOLLOW_UP_QUERIES
    first_hit: int | None  # the rank of the first Chunk holding any Passage, None when none is in the top 10
    found: int  # the Passages held by a Chunk in the top 5
    seconds: float  # how long the retriever took to answer


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
    alone, history, rewrite = FOLLOW_UP_QUERIES
    return [(alone, question.question), (history, " ".join([*question.history, question.question])), (rewrite, question.rewrite)]


def score(questions: Sequence[Question], retriever: Retriever, chunk_texts: Mapping[str, str]) -> list[Scored]:
    scored = []
    for question in questions:
        for query, text in queries(question):
            started = time.perf_counter()
            ranking = retriever.query(text, MRR_DEPTH)
            seconds = time.perf_counter() - started
            held = [[holds(chunk_texts[chunk_id], passage.quote) for passage in question.passages] for chunk_id, _ in ranking]
            first_hit = next((rank for rank, row in enumerate(held, start=1) if any(row)), None)
            found = sum(1 for column in zip(*held[:RECALL_DEPTH]) if any(column))
            scored.append(Scored(question, query, first_hit, found, seconds))
    return scored


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
