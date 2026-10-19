"""The Evaluation set store: a committed JSON Lines file, one question per line (ADR 0039).

    {"id": "freezing", "type": "single-paper", "question": "...",
     "passages": [{"edition_id": "2112.06598v2", "section": "5 Results › 5.3 Is freezing necessary?", "quote": "..."}]}

A follow-up also has "history", the prior turns in order, and "rewrite", a hand-written standalone question.
"checked_by" names who checked the question; a question without it is unchecked (ADR 0046).
An unanswerable question has no Passages, and "unanswerable_kind" says how far the corpus is from answering it:
"near-miss" (on topic, and the corpus holds the paper or the measure, just not this answer) or "out-of-topic". A Passage's Section is its path as the context header gives it.

Loading checks only that each line can be read as a question: JSON, known fields and types, unique ids.
Whether the questions are well formed, and their quotes right, is `eval-check`'s job (ADR 0041).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

QuestionType = Literal["single-paper", "multi-paper", "follow-up", "unanswerable"]
QUESTION_TYPES: tuple[QuestionType, ...] = get_args(QuestionType)
UnanswerableKind = Literal["near-miss", "out-of-topic"]
UNANSWERABLE_KINDS: tuple[UnanswerableKind, ...] = get_args(UnanswerableKind)


class EvaluationSetError(ValueError):
    """A line of the Evaluation set is malformed, worded for the person editing it."""


@dataclass(frozen=True)
class Passage:
    edition_id: str  # the pinned Edition the quote was taken from
    section: str
    quote: str  # verbatim


@dataclass(frozen=True)
class Question:
    id: str
    type: QuestionType
    question: str
    passages: tuple[Passage, ...]
    history: tuple[str, ...] = ()  # a follow-up's prior turns, oldest first
    rewrite: str = ""  # a follow-up's reference rewrite
    checked_by: str = ""  # who checked it by hand; empty until someone has
    unanswerable_kind: str = ""  # an unanswerable question's: one of UNANSWERABLE_KINDS once eval-check passes

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


def load_evaluation_set(path: Path) -> list[Question]:
    questions = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise EvaluationSetError(f"{path}:{number}: not valid JSON: {error}") from error
            questions.append(_question(record, f"{path}:{number}"))
    ids = [question.id for question in questions]
    if duplicates := sorted({id for id in ids if ids.count(id) > 1}):
        raise EvaluationSetError(f"{path}: question ids are used more than once: {', '.join(duplicates)}")
    return questions


def _question(record: object, where: str) -> Question:
    if not isinstance(record, dict):
        raise EvaluationSetError(f"{where}: not a JSON object")
    expected = {"id", "type", "question", "passages", "history", "rewrite", "checked_by", "unanswerable_kind"}
    if unknown := sorted(set(record) - expected):
        raise EvaluationSetError(f"{where}: unknown fields {', '.join(unknown)}")
    if record.get("type") not in QUESTION_TYPES:
        raise EvaluationSetError(f"{where}: type {record.get('type')!r} is not one of {', '.join(QUESTION_TYPES)}")
    try:
        passages = tuple(Passage(p["edition_id"], p["section"], p["quote"]) for p in record["passages"])
        question = Question(
            record["id"],
            record["type"],
            record["question"],
            passages,
            tuple(record.get("history", ())),
            record.get("rewrite", ""),
            record.get("checked_by", ""),
            record.get("unanswerable_kind", ""),
        )
    except (KeyError, TypeError) as error:
        raise EvaluationSetError(f"{where}: missing or malformed field {error}") from error
    return question
