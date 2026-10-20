"""The answers file of `chat-eval` (ADRs 0059 and 0062): every Turn asked, with what the report scored it on, and
how a Turn is scored and scored again from it.

The file is JSON Lines. Its first line names what the Turns were asked over: the parser and chunking keys of the
Chunks, and the chatbot's retriever and collapse pool, k, model pin, settings and prompts' hashes. Then one Turn per line in the
order asked, with no timings, so two runs that get the same replies write the same file. A run of `--runs N`
writes runs 2..N to the runs file beside it, each Turn the same record with a `run` field.

Re-scoring rebuilds each Turn from its question, Rewrite, retrieved Chunk ids and raw reply, and recomputes every
verdict with the current code; the stored verdicts are never read back. It refuses a file asked over other Chunks
or another chatbot, or one that does not match the Evaluation set.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..evaluation.evalset import Question
from ..evaluation.matching import MatchingRule, holds
from ..retrieval.corpus import Corpus
from .answer import read_answer
from .config import ChatConfig
from .conversation import Turn
from .grounding import Grounding, ground


class AnswersMismatch(ValueError):
    """The answers file can't be re-scored here: other Chunks, another chatbot, or another Evaluation set."""


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

    @property
    def verdict(self) -> str:
        return verdict(self.turn.answer.abstention, None if self.grounding is None else self.grounding.grounded)


def verdict(abstention: bool, grounded: bool | None) -> str:
    """A scored Turn's verdict in a word or two, as the report compares runs and baselines on it."""
    return "abstained" if abstention else ("grounded" if grounded else "not grounded")


Run = Sequence[Asked]  # every Turn of one pass over the Evaluation set, in the order asked


def score(question: Question, number: int, turn: Turn, rule: MatchingRule) -> Asked:
    unfound = Asked(question, number, turn, ground(turn.answer, turn.retrieved), ())
    if not unfound.scored:
        return unfound
    found = tuple(
        place for place, passage in enumerate(question.passages, start=1) if any(holds(chunk.text, passage.quote, rule) for chunk in turn.retrieved)
    )
    return Asked(question, number, turn, unfound.grounding, found)


def runs_path(answers: Path) -> Path:
    """The runs file beside the answers file: `chat-answers.jsonl` keeps its runs 2..N in `chat-answers-runs.jsonl`."""
    return answers.with_name(f"{answers.stem}-runs{answers.suffix}")


def asked_over(corpus: Corpus, config: ChatConfig) -> dict[str, Any]:
    """The answers file's first line: what its Turns were asked over."""
    return {
        "parser": corpus.parser_key,
        "chunking": corpus.chunking_key,
        "retriever": config.retriever.key,
        "collapse_pool": config.collapse_pool,  # None for the raw ranking, as files written before the collapse read
        "k": config.k,
        "model": config.model.model,
        "revision": config.model.revision,
        "think": config.model.think,
        "temperature": config.model.temperature,
        "system_prompt_sha256": _sha256(config.system_prompt),
        "rewrite_prompt_sha256": _sha256(config.rewrite_prompt),
        "history": config.history,
    }


def write_answers(answers: Path, corpus: Corpus, config: ChatConfig, runs: Sequence[Run]) -> None:
    """Run 1 to the answers file and runs 2..N to the runs file beside it, which is removed for a single run."""
    first, *rest = runs
    _write(answers, [asked_over(corpus, config), *(_record(item) for item in first)])
    if rest:
        _write(runs_path(answers), [{**_record(item), "run": number} for number, run in enumerate(rest, start=2) for item in run])
    else:
        runs_path(answers).unlink(missing_ok=True)


def read_answers(answers: Path) -> tuple[dict[str, Any], list[list[dict[str, Any]]]]:
    """The answers file's first line and its runs' records, run 1 first, as stored."""
    lines = [json.loads(line) for line in answers.read_text(encoding="utf-8").splitlines()]
    if not lines or "parser" not in lines[0]:
        raise AnswersMismatch(f"{answers} has no first line naming the Chunks it was asked over; rerun `chat-eval`")
    runs: dict[int, list[dict[str, Any]]] = {1: lines[1:]}
    if runs_path(answers).exists():
        for line in runs_path(answers).read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            runs.setdefault(record.pop("run"), []).append(record)
    return lines[0], [runs[number] for number in sorted(runs)]


@dataclass(frozen=True)
class Baseline:
    """Another answers file's verdicts, as stored, to compare a run against question by question."""

    path: Path
    runs: int
    verdicts: dict[str, list[str]]  # question id to its scored Turn's verdict in each run, run 1 first
    asked_over: dict[str, Any]  # its first line


def read_baseline(answers: Path) -> Baseline:
    """The answers file and its runs file read whole, so a run may overwrite the file it is compared with."""
    stored, runs = read_answers(answers)
    verdicts: dict[str, list[str]] = {}
    for records in runs:
        for record in records:
            if record["scored"]:
                verdicts.setdefault(record["question_id"], []).append(verdict(record["abstention"], record["grounded"]))
    return Baseline(answers, len(runs), verdicts, stored)


def rescore(answers: Path, questions: Sequence[Question], corpus: Corpus, config: ChatConfig, rule: MatchingRule) -> list[list[Asked]]:
    """Every run of the answers file scored again with the current code. Raises AnswersMismatch."""
    stored, runs = read_answers(answers)
    expected = asked_over(corpus, config)
    differ = [f"{key} {stored.get(key)!r}, not {value!r}" for key, value in expected.items() if stored.get(key) != value]
    if differ:
        raise AnswersMismatch(f"{answers} was asked over other Chunks or another chatbot than these: {'; '.join(differ)}")
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    asked = [(question, number, text) for question in questions for number, text in enumerate([*question.history, question.question], start=1)]
    rescored = []
    for run, records in enumerate(runs, start=1):
        turns = [(record["question_id"], record["turn"], record["question"]) for record in records]
        if turns != [(question.id, number, text) for question, number, text in asked]:
            raise AnswersMismatch(f"run {run} of {answers} does not ask the Evaluation set's questions in its order")
        rescored.append([_rebuilt(record, question, number, chunks, config, rule, answers) for record, (question, number, _) in zip(records, asked)])
    return rescored


def _rebuilt(record: dict[str, Any], question: Question, number: int, chunks: dict, config: ChatConfig, rule: MatchingRule, answers: Path) -> Asked:
    missing = [chunk_id for chunk_id in record["retrieved"] if chunk_id not in chunks]
    if missing:
        raise AnswersMismatch(f"{answers}: {question.id} Turn {number} retrieved {', '.join(missing)}, which this corpus lacks")
    retrieved = tuple(chunks[chunk_id] for chunk_id in record["retrieved"])
    answer = read_answer(record["reply"], len(retrieved), config.abstention)
    return score(question, number, Turn(record["question"], record["rewrite"], retrieved, record["reply"], answer, {}), rule)


def _record(item: Asked) -> dict[str, Any]:
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


def _write(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8", newline="\n")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
