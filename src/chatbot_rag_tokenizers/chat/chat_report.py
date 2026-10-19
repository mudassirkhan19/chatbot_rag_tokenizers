"""The chat report writer (spec #63, ADR 0058): the committed Markdown record of a `chat-eval` run, in the eval
report's style.

It names what was scored (the Evaluation set, the Chunks, the retriever, the answer model's pin and the prompts'
hashes), then gives the grounded, abstention and false-abstention rates and Recall@k per question type, a line
per question, and the timings last. Everything above the timings depends only on the inputs and the model's
replies, so two runs on the same index and model give the same report up to that section.
"""

import hashlib
import statistics
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ..evaluation.evalset import QUESTION_TYPES, UNANSWERABLE_KINDS, Question
from ..evaluation.report import NONE
from ..retrieval.corpus import Corpus
from .config import ChatConfig

if TYPE_CHECKING:
    from .chat_eval import Asked

def write_chat_report(
    path: Path,
    evaluation_set: Path,
    questions: Sequence[Question],
    corpus: Corpus,
    config: ChatConfig,
    model_pin: str,
    asked: Sequence["Asked"],
) -> None:
    k = config.k
    scored = [item for item in asked if item.scored]
    counts = ", ".join(f"{sum(1 for q in questions if q.type == kind)} {kind}" for kind in QUESTION_TYPES)
    unanswerable = ", ".join(f"{sum(1 for q in questions if q.unanswerable_kind == kind)} {kind}" for kind in UNANSWERABLE_KINDS)
    lines = [
        "# Chat report",
        "",
        "Written by `chat-eval`. Every question of the Evaluation set is asked of the chatbot through the same"
        " Conversation code as the chat page, and each answer is checked for grounding, Abstention and the Passages in"
        " the Chunks its Turn retrieved.",
        "",
        "## Evaluation set",
        "",
        f"- File: `{evaluation_set}`",
        f"- sha256: `{hashlib.sha256(evaluation_set.read_bytes()).hexdigest()}`",
        f"- Questions: {len(questions)} ({counts}; of the unanswerable, {unanswerable})",
        "",
        "## Chunks",
        "",
        f"- Parser: `{corpus.parser_key}`",
        f"- Chunking config: `{corpus.chunking_key}`",
        f"- Files: {len(corpus.files)}",
        f"- Chunks: {len(corpus.chunks)}",
        "",
        "## Chatbot",
        "",
        f"- Retriever: {config.retriever.name} (`{config.retriever.key}`), {k} Chunks per Turn",
        f"- Answer model: {model_pin}, thinking {'on' if config.model.think else 'off'}, temperature {config.model.temperature}",
        f"- System prompt sha256: `{_sha256(config.system_prompt)}` (with the Abstention sentence filled in)",
        f"- Rewrite prompt sha256: `{_sha256(config.rewrite_prompt)}`",
        f"- Abstention sentence: \"{config.abstention}\"",
        f"- Earlier Turns shown on a follow-up: {config.history}",
        "",
        "## Measures",
        "",
        "- Each single-paper, multi-paper and unanswerable question is a Conversation of one Turn. A follow-up is a"
        " Conversation that first asks its stored history, the bot answering each, then the follow-up. Only the"
        " question's own Turn is scored.",
        "- An answer is an Abstention when it holds the Abstention sentence, compared after the Passage matcher's"
        " normalisation. The abstention rate is the share of the questions answered with one: on the unanswerable"
        " questions it is the rate of correct Abstentions, on the answerable ones the false-abstention rate.",
        "- An answer that is not an Abstention is grounded when it cites at least one retrieved Chunk, every marker in"
        " it names a Chunk retrieved for its Turn, and every number in it, cut into words as the Passage matcher cuts"
        " them (a word that starts with a digit, such as 50k or 0.1, but not ByT5), appears in a cited Chunk's context header or text. An uncited answer is not"
        " grounded. Abstentions are left out of the grounded rate.",
        f"- Recall@{k}: the share of a question's Passages held by one of the {k} Chunks its Turn retrieved, averaged over"
        " the answerable questions, with the Passage matcher of `evaluate` (ADR 0041).",
        "",
        "## Results",
        "",
        f"| Question type | Questions | Abstained | Abstention rate | Answers | Grounded | Grounded rate | Recall@{k} |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *[_row(name, chosen) for name, chosen in _groups(scored)],
        "",
        *_summary(scored),
        "",
        "## Questions",
        "",
        f"Grounded is yes, no, or {NONE} for an Abstention. Passages in its Chunks counts the question's Passages held by"
        f" one of its Turn's {k} Chunks; a follow-up's line is its own Turn, after its history.",
        "",
        "| Question | Type | Abstained | Grounded | Invalid Citations | Numbers not in cited Chunks | Passages in its Chunks |",
        "|---|---|---|---|---|---|---:|",
        *[_question(item) for item in scored],
        "",
        "## Timings",
        "",
        "These depend on the machine and change from run to run. They count every Turn asked, a follow-up's history"
        " included; rewriting counts only the Turns that were rewritten, as a Conversation's first Turn is not.",
        "",
        "| Step | Turns | p50 | p95 |",
        "|---|---:|---:|---:|",
        *_timings(asked),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _groups(scored: Sequence["Asked"]) -> list[tuple[str, list["Asked"]]]:
    def where(test: Callable[[Question], bool]) -> list["Asked"]:
        return [item for item in scored if test(item.question)]

    return [
        *[(kind, where(_of_type(kind))) for kind in QUESTION_TYPES if kind != "unanswerable"],
        ("all answerable", where(lambda q: q.answerable)),
        *[(f"unanswerable: {kind}", where(_of_kind(kind))) for kind in UNANSWERABLE_KINDS],
        ("all unanswerable", where(lambda q: not q.answerable)),
        ("all", list(scored)),
    ]


def _of_type(kind: str) -> Callable[[Question], bool]:
    return lambda question: question.type == kind


def _of_kind(kind: str) -> Callable[[Question], bool]:
    return lambda question: question.unanswerable_kind == kind


def _row(name: str, chosen: Sequence["Asked"]) -> str:
    abstained = sum(1 for item in chosen if item.turn.answer.abstention)
    answers = [item.grounding for item in chosen if item.grounding is not None]
    grounded = sum(1 for grounding in answers if grounding.grounded)
    answerable = [item for item in chosen if item.question.answerable]
    recall = (
        f"{sum(len(item.found) / len(item.question.passages) for item in answerable) / len(answerable):.2f}" if answerable else NONE
    )
    cells = [len(chosen), abstained, _rate(abstained, len(chosen)), len(answers), grounded, _rate(grounded, len(answers)), recall]
    return f"| {name} | {' | '.join(str(cell) for cell in cells)} |"


def _rate(count: int, of: int) -> str:
    return f"{count / of:.2f}" if of else NONE


def _summary(scored: Sequence["Asked"]) -> list[str]:
    def abstained(test: Callable[[Question], bool]) -> str:
        chosen = [item for item in scored if test(item.question)]
        count = sum(1 for item in chosen if item.turn.answer.abstention)
        return f"{count}/{len(chosen)} ({_rate(count, len(chosen))})"

    kinds = ", ".join(f"{kind} {abstained(_of_kind(kind))}" for kind in UNANSWERABLE_KINDS)
    answers = [item.grounding for item in scored if item.grounding is not None]
    grounded = sum(1 for grounding in answers if grounding.grounded)
    return [
        f"- Abstention rate on the unanswerable questions: {abstained(lambda q: not q.answerable)}; {kinds}",
        f"- False-abstention rate on the answerable questions: {abstained(lambda q: q.answerable)}",
        f"- Grounded rate over every answer that is not an Abstention: {grounded}/{len(answers)} ({_rate(grounded, len(answers))})",
        f"- Not grounded: {sum(1 for g in answers if not g.cited)} uncited, {sum(1 for g in answers if g.invalid)} with an"
        f" invalid Citation, {sum(1 for g in answers if g.missing)} with a number in no cited Chunk (an answer may be counted"
        " under more than one)",
    ]


def _question(item: "Asked") -> str:
    grounding = item.grounding
    grounded = NONE if grounding is None else ("yes" if grounding.grounded else "no")
    invalid = ", ".join(f"[{number}]" for number in item.turn.answer.invalid) or NONE
    missing = NONE if grounding is None else (", ".join(grounding.missing) or NONE)
    found = f"{len(item.found)}/{len(item.question.passages)}" if item.question.answerable else NONE
    abstained = "yes" if item.turn.answer.abstention else "no"
    return f"| {item.question.id} | {item.question.type} | {abstained} | {grounded} | {invalid} | {missing} | {found} |"


def _timings(asked: Sequence["Asked"]) -> list[str]:
    steps: list[tuple[str, list[float]]] = [
        ("retrieval", [item.turn.seconds["retrieval"] for item in asked]),
        ("rewriting", [item.turn.seconds["rewriting"] for item in asked if item.turn.rewrite is not None]),
        ("answering", [item.turn.seconds["answering"] for item in asked]),
        ("whole Turn", [sum(item.turn.seconds.values()) for item in asked]),
    ]
    return [f"| {step} | {len(seconds)} | {_percentile(seconds, 50)} | {_percentile(seconds, 95)} |" for step, seconds in steps]


def _percentile(seconds: Sequence[float], percent: int) -> str:
    if not seconds:
        return NONE
    ordered = sorted(seconds)
    value = statistics.quantiles(ordered, n=100, method="inclusive")[percent - 1] if len(ordered) > 1 else ordered[0]
    return f"{value:.2f} s"
