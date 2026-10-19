"""`chat-eval` (spec #63, ADR 0059): the whole Evaluation set asked of the chatbot, through the same Conversation
code as the chat page, scored and written as the chat report and the answers.

Each question is a Conversation of its own. A single-paper, multi-paper or unanswerable question is one Turn. A
follow-up first asks its stored history as real Turns, the bot answering each, then the follow-up, so the
rewriter works from the bot's own answers as it would on the page. Only the question's own Turn is scored; the
history's Turns are in the answers file and the latency.

The answers file is JSON Lines, one Turn per line in the order asked, with what the report scored it on. It holds
no timings, so two runs that get the same replies write the same file.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..evaluation.evalset import Question
from ..evaluation.matching import MatchingRule, holds
from ..evaluation.pipeline import checked_questions
from ..evaluation.works import Works
from ..retrieval.corpus import Corpus
from .chat_report import write_chat_report
from .conversation import Chatbot, Turn
from .grounding import Grounding, ground


@dataclass(frozen=True)
class Asked:
    """One Turn of a question's Conversation, scored when it is the question's own."""

    question: Question
    number: int  # the Turn's place in its Conversation, from 1
    turn: Turn
    grounding: Grounding | None  # None for an Abstention, which is neither grounded nor not
    found: tuple[int, ...]  # the question's Passages held by a retrieved Chunk, numbered from 1; empty on a history Turn

    @property
    def scored(self) -> bool:
        return self.number == len(self.question.history) + 1


def chat_eval(chatbot: Chatbot, corpus: Corpus, evaluation_set: Path, report: Path, answers: Path, rule: MatchingRule, works: Works) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check`, and AnswerModelUnavailable when the answer model
    can't answer, before any question is asked."""
    questions = checked_questions(evaluation_set, corpus, rule, works)
    pin = chatbot.model().pin
    asked = ask_all(questions, chatbot, rule)
    write_answers(answers, asked)
    write_chat_report(report, evaluation_set, questions, corpus, chatbot.config, pin, asked)
    turns = sum(1 for item in asked if not item.scored)
    print(f"chat-eval: {len(questions)} questions, {len(asked)} Turns ({turns} of them follow-ups' history); report in {report}, answers in {answers}")


def ask_all(questions: Sequence[Question], chatbot: Chatbot, rule: MatchingRule) -> list[Asked]:
    """Every question as its own Conversation, each Turn of each in the order asked. Raises AnswerModelUnavailable."""
    asked = []
    for question in questions:
        chatbot.reset()
        for number, text in enumerate([*question.history, question.question], start=1):
            turn = chatbot.ask(text)
            own = number == len(question.history) + 1
            found = tuple(
                number
                for number, passage in enumerate(question.passages, start=1)
                if own and any(holds(chunk.text, passage.quote, rule) for chunk in turn.retrieved)
            )
            asked.append(Asked(question, number, turn, ground(turn.answer, turn.retrieved), found))
    return asked


def write_answers(path: Path, asked: Sequence[Asked]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(_answer(item), ensure_ascii=False) for item in asked]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8", newline="\n")


def _answer(item: Asked) -> dict[str, Any]:
    turn, grounding = item.turn, item.grounding
    return {
        "question_id": item.question.id,
        "type": item.question.type,
        "turn": item.number,
        "scored": item.scored,
        "question": turn.question,
        "rewrite": turn.rewrite,
        "retrieved": [chunk.chunk_id for chunk in turn.retrieved],
        "reply": turn.reply,
        "abstention": turn.answer.abstention,
        "cited": [turn.retrieved[number - 1].chunk_id for number in turn.answer.cited],
        "invalid": turn.answer.invalid,
        "grounded": None if grounding is None else grounding.grounded,
        "numbers_not_cited": [] if grounding is None else list(grounding.missing),
        "passages_found": list(item.found) if item.scored else None,
    }
