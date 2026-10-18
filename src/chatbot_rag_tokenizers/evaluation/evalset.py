"""The Evaluation set store: a committed JSON Lines file, one question per line (ADR 0039).

    {"id": "freezing", "type": "single-paper", "question": "...",
     "passages": [{"edition_id": "2112.06598v2", "section": "5 Results › 5.3 Is freezing necessary?", "quote": "..."}]}

A follow-up also has "history", the prior turns in order, and "rewrite", a hand-written standalone question.
An unanswerable question has no Passages. A Passage's Section is its path as the context header gives it.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

QuestionType = Literal["single-paper", "multi-paper", "follow-up", "unanswerable"]
QUESTION_TYPES: tuple[QuestionType, ...] = get_args(QuestionType)


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

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


def load_evaluation_set(path: Path) -> list[Question]:
    questions = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            questions.append(_question(json.loads(line), f"{path}:{number}"))
    ids = [question.id for question in questions]
    if duplicates := sorted({id for id in ids if ids.count(id) > 1}):
        raise EvaluationSetError(f"{path}: question ids are used more than once: {', '.join(duplicates)}")
    return questions


def _question(record: dict, where: str) -> Question:
    expected = {"id", "type", "question", "passages", "history", "rewrite"}
    if unknown := sorted(set(record) - expected):
        raise EvaluationSetError(f"{where}: unknown fields {', '.join(unknown)}")
    if record.get("type") not in QUESTION_TYPES:
        raise EvaluationSetError(f"{where}: type {record.get('type')!r} is not one of {', '.join(QUESTION_TYPES)}")
    try:
        passages = tuple(Passage(p["edition_id"], p["section"], p["quote"]) for p in record["passages"])
        question = Question(
            record["id"], record["type"], record["question"], passages, tuple(record.get("history", ())), record.get("rewrite", "")
        )
    except (KeyError, TypeError) as error:
        raise EvaluationSetError(f"{where}: missing or malformed field {error}") from error
    if question.answerable != bool(question.passages):
        raise EvaluationSetError(f"{where}: {question.id} is {question.type} but has {len(question.passages)} Passages")
    if (question.type == "follow-up") != bool(question.history and question.rewrite):
        raise EvaluationSetError(f"{where}: {question.id}: a follow-up, and only a follow-up, has a history and a rewrite")
    return question
