"""The chat report writer (spec #63, ADRs 0059 and 0062): the committed Markdown record of a `chat-eval` run, in the
eval report's style.

It names what was scored (the Evaluation set, the Chunks, the retriever, the answer model's pin and the prompts'
hashes), then gives the grounded, abstention and false-abstention rates with their Wilson intervals and Recall@k
per question type, a line per question, the grounding verdict's agreement with the developer's hand-checked
sample, the variation over the runs, the questions whose verdict changed from a
baseline when one is given, and the timings last. Everything above the timings depends only on the inputs and the
model's replies, so re-scoring the stored replies reproduces it exactly.
"""

import hashlib
import math
import statistics
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ..evaluation.evalset import QUESTION_TYPES, UNANSWERABLE_KINDS, Question
from ..evaluation.comparison import CONFIDENCE
from ..evaluation.report import NONE
from ..retrieval.corpus import Corpus
from .answers import Asked, Baseline, Run, asked_over
from .grounding_check import compare, read_check
from .config import ChatConfig
from .model import pin

# The normal quantile of the Wilson interval: 1.96 for 95%.
_Z = statistics.NormalDist().inv_cdf(1 - (1 - CONFIDENCE) / 2)


def write_chat_report(
    path: Path,
    evaluation_set: Path,
    questions: Sequence[Question],
    corpus: Corpus,
    config: ChatConfig,
    runs: Sequence[Run],
    baseline: Baseline | None,
    rescored_from: Path | None,
    check: Path | None = None,
) -> None:
    """The report on runs[0], the run reported, against ``baseline`` when one is given. ``rescored_from`` names the answers file a re-scored report was
    scored from, which holds no timings. ``check`` is the developer's hand-checked sample, compared when it exists."""
    k = config.k
    asked = runs[0]
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
        f"- Answer model: {pin(config.model)}, thinking {'on' if config.model.think else 'off'}, temperature {config.model.temperature}",
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
        "- An answer is an Abstention when it holds the Abstention sentence, or when its text, without its markers, is"
        " one sentence declining in the model's own words, such as \"The provided chunks do not contain …\". Both are"
        " compared after the Passage matcher's normalisation. A decline that goes on to answer (another sentence, or a"
        " clause after \";\", \"but\" or \"however\") or cites a Chunk after it is an answer. The abstention rate is the share of the questions answered with one: on the unanswerable"
        " questions it is the rate of correct Abstentions, on the answerable ones the false-abstention rate.",
        "- An answer that is not an Abstention is grounded when it cites at least one retrieved Chunk, every marker in"
        " it names a Chunk retrieved for its Turn, and every number in it, cut into words as the Passage matcher cuts"
        " them (a word that starts with a digit, such as 50k or 0.1, but not ByT5), appears in a cited Chunk's context header or text. An uncited answer is not"
        " grounded. Abstentions are left out of the grounded rate.",
        f"- Recall@{k}: the share of a question's Passages held by one of the {k} Chunks its Turn retrieved, averaged over"
        " the answerable questions, with the Passage matcher of `evaluate` (ADR 0041).",
        f"- Every rate has its {CONFIDENCE:.0%} Wilson interval, in the column beside it and in brackets in the lines below the table. It covers the"
        " sampling of the questions, not the answer model's run-to-run variation, which the Variation section measures."
        f" Recall@{k} is a mean of per-question shares, not a proportion, and has no interval here: it is the retriever's"
        " measure, and the eval report gives its bootstrap interval (ADR 0061).",
        "",
        "## Results",
        "",
        f"| Question type | Questions | Abstained | Abstention rate | {CONFIDENCE:.0%} interval | Answers | Grounded | Grounded rate"
        f" | {CONFIDENCE:.0%} interval | Recall@{k} |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        *[_row(name, chosen) for name, chosen in _groups(scored)],
        "",
        *_summary(scored),
        "",
        "## Questions",
        "",
        f"Grounded is yes, no, or {NONE} for an Abstention. Passages in its Chunks counts the question's Passages held by"
        f" one of its Turn's {k} Chunks, then names them by their place in the question (`1/2: 1` found the first of two);"
        " a follow-up's line is its own Turn, after its history.",
        "",
        "| Question | Type | Abstained | Grounded | Invalid Citations | Numbers not in cited Chunks | Passages in its Chunks |",
        "|---|---|---|---|---|---|---:|",
        *[_question(item) for item in scored],
        "",
        *_hand_check(scored, check),
        *_variation(runs, k),
        *([] if baseline is None else _against(scored, baseline, asked_over(corpus, config))),
        "## Timings",
        "",
        *(_timings(asked) if rescored_from is None else [
            f"Not measured: this report was re-scored from `{rescored_from}` (`chat-eval --from-answers`), which holds no timings."
        ]),
    ]  # fmt: skip
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _groups(scored: Sequence[Asked]) -> list[tuple[str, list[Asked]]]:
    def where(test: Callable[[Question], bool]) -> list[Asked]:
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


def _row(name: str, chosen: Sequence[Asked]) -> str:
    abstained = sum(1 for item in chosen if item.turn.answer.abstention)
    answers = [item.grounding for item in chosen if item.grounding is not None]
    grounded = sum(1 for grounding in answers if grounding.grounded)
    recall = _recall(chosen)
    cells = [
        len(chosen), abstained, _rate(abstained, len(chosen)), _interval(abstained, len(chosen)),
        len(answers), grounded, _rate(grounded, len(answers)), _interval(grounded, len(answers)),
        NONE if recall is None else f"{recall:.2f}",
    ]  # fmt: skip
    return f"| {name} | {' | '.join(str(cell) for cell in cells)} |"


def _recall(chosen: Sequence[Asked]) -> float | None:
    """Recall@k averaged over the answerable questions chosen, or None when there are none."""
    answerable = [item for item in chosen if item.question.answerable]
    return sum(len(item.found) / len(item.question.passages) for item in answerable) / len(answerable) if answerable else None


def _rate(count: int, of: int) -> str:
    return f"{count / of:.2f}" if of else NONE


def wilson(count: int, of: int) -> tuple[float, float]:
    """The Wilson score interval on the proportion count/of, at the report's confidence."""
    share, spread = count / of, _Z * _Z / of
    centre = (share + spread / 2) / (1 + spread)
    half = _Z * math.sqrt(share * (1 - share) / of + spread / (4 * of)) / (1 + spread)
    return max(0.0, centre - half), min(1.0, centre + half)


def _interval(count: int, of: int) -> str:
    if not of:
        return NONE
    low, high = wilson(count, of)
    return f"[{low:.2f}, {high:.2f}]"


def _counted(count: int, of: int) -> str:
    """A rate with its counts and interval, as the lines under the Results table give it."""
    return f"{count}/{of} ({_rate(count, of)} {_interval(count, of)})" if of else f"0/0 ({NONE})"


def _summary(scored: Sequence[Asked]) -> list[str]:
    def abstained(test: Callable[[Question], bool]) -> str:
        return _counted(*_abstained(scored, test))

    kinds = ", ".join(f"{kind} {abstained(_of_kind(kind))}" for kind in UNANSWERABLE_KINDS)
    answers = [item.grounding for item in scored if item.grounding is not None]
    return [
        f"- Abstention rate on the unanswerable questions: {abstained(lambda q: not q.answerable)}; {kinds}",
        f"- False-abstention rate on the answerable questions: {abstained(lambda q: q.answerable)}",
        f"- Grounded rate over every answer that is not an Abstention: {_counted(*_grounded(scored))}",
        f"- Not grounded: {sum(1 for g in answers if not g.cited)} uncited, {sum(1 for g in answers if g.invalid)} with an"
        f" invalid Citation, {sum(1 for g in answers if g.missing)} with a number in no cited Chunk (an answer may be counted"
        " under more than one)",
    ]


def _variation(runs: Sequence[Run], k: int) -> list[str]:
    """How the runs after the first differ from it: each rate's range, the questions whose verdict changed, and the
    Turns whose wording or retrieved Chunks changed."""
    if len(runs) == 1:
        return ["## Variation", "", "One run: `chat-eval --runs N` asks the whole set N times and measures how much the answers vary.", ""]
    scored = [[item for item in run if item.scored] for run in runs]
    rates: list[tuple[str, list[tuple[int, int]]]] = [
        ("Abstention rate, unanswerable", [_abstained(run, lambda q: not q.answerable) for run in scored]),
        *[(f"Abstention rate, {kind}", [_abstained(run, _of_kind(kind)) for run in scored]) for kind in UNANSWERABLE_KINDS],
        ("False-abstention rate, answerable", [_abstained(run, lambda q: q.answerable) for run in scored]),
        ("Grounded rate", [_grounded(run) for run in scored]),
    ]
    recalls = [_recall(run) for run in scored]
    flaky = [items for items in zip(*scored) if len({item.verdict for item in items}) > 1]
    first, later = runs[0], runs[1:]
    worded = [item for place, item in enumerate(first) if any(run[place].turn.reply != item.turn.reply for run in later)]
    moved = [item for place, item in enumerate(first) if any(run[place].turn.retrieved != item.turn.retrieved for run in later)]
    return [
        "## Variation",
        "",
        f"{len(runs)} runs of the whole set, one after another in one process; the report above is run 1's, and the"
        " answers file's runs file holds the others. A range is the lowest and highest rate over the runs.",
        "",
        f"| Measure | {' | '.join(f'Run {number}' for number in range(1, len(runs) + 1))} | Range |",
        f"|---|{'---:|' * len(runs)}---:|",
        *[f"| {name} | {' | '.join(f'{count}/{of}' for count, of in values)} | {_range([count / of for count, of in values if of])} |" for name, values in rates],
        f"| Recall@{k}, answerable | {' | '.join(NONE if r is None else f'{r:.2f}' for r in recalls)} | {_range([r for r in recalls if r is not None])} |",
        "",
        "### Questions whose verdict changed",
        "",
        f"{len(flaky)} of {len(scored[0])} questions; each count is out of the {len(runs)} runs, and the verdicts are in run order.",
        "",
        "| Question | Type | Abstained | Grounded | Verdicts |",
        "|---|---|---:|---:|---|",
        *[
            f"| {items[0].question.id} | {items[0].question.type} | {sum(1 for item in items if item.turn.answer.abstention)}/{len(runs)}"
            f" | {sum(1 for item in items if item.verdict == 'grounded')}/{len(runs)} | {', '.join(item.verdict for item in items)} |"
            for items in flaky
        ],
        "",
        f"- Turns whose reply changed wording from run 1: {_turns(worded, len(first))}",
        f"- Turns whose retrieved Chunks changed from run 1: {_turns(moved, len(first))} (a follow-up's can move, as its"
        " history's replies feed the rewriter)",
        "",
    ]


def _against(scored: Sequence[Asked], baseline: Baseline, here: dict[str, Any]) -> list[str]:
    """The questions whose verdict differs from the baseline's run 1, each marked when the baseline's runs disagreed,
    after the settings the baseline was asked over that differ from this run's."""
    changed = [item for item in scored if item.question.id in baseline.verdicts and item.verdict != baseline.verdicts[item.question.id][0]]
    missing = [item.question.id for item in scored if item.question.id not in baseline.verdicts]
    lines = [
        "## Against the baseline",
        "",
        f"Baseline: `{baseline.path}`, {baseline.runs} run{'s' if baseline.runs > 1 else ''}, its verdicts as stored. Each question"
        " whose verdict here differs from the baseline's run 1 is listed, marked flaky in the baseline when its runs"
        " disagreed on it, so a change the baseline already varied on is not read as an effect.",
        "",
    ]
    differ = [f"{key} {baseline.asked_over.get(key)!r}, here {value!r}" for key, value in here.items() if baseline.asked_over.get(key) != value]
    if differ:
        lines += [f"The baseline was asked over other settings: {'; '.join(differ)}.", ""]
    if missing:
        lines += [f"Not in the baseline: {', '.join(missing)}.", ""]
    if not changed:
        return [*lines, "No question's verdict changed from the baseline's run 1.", ""]
    rows = []
    for item in changed:
        verdicts = baseline.verdicts[item.question.id]
        flaky = f"flaky in the baseline: {', '.join(verdicts)}" if len(set(verdicts)) > 1 else NONE
        rows.append(f"| {item.question.id} | {item.question.type} | {verdicts[0]} | {item.verdict} | {flaky} |")
    return [*lines, "| Question | Type | Baseline | Now | Note |", "|---|---|---|---|---|", *rows, ""]


def _hand_check(scored: Sequence[Asked], check: Path | None) -> list[str]:
    """The automatic verdict's agreement with the developer's labels on the sample, and every disagreement (ADR 0066)."""
    lines = [
        "## Grounding checked by hand",
        "",
        "The developer's labels on a seeded sample of answered Turns (`chat-eval --export-check`, labelled on the"
        " `chat-label` page) against this run's automatic verdict. A row is compared when the developer gave it a label"
        " and this run asked its question with the same reply over the same Chunks.",
        "",
    ]
    if check is None or not check.exists():
        return [*lines, "No sample to compare with: `chat-eval --export-check` draws one, and `chat-label` serves the page to label it.", ""]
    rows = read_check(check)
    result = compare(scored, rows)
    by_hand = [d for d in result.disagreements if d.label == "grounded"]
    lines += [
        f"- Sample: `{check}`, {result.rows} Turns: {result.labelled} labelled by the developer, {result.unsure} left unsure,"
        f" {result.rows - result.labelled - result.unsure} not checked by the developer",
        f"- Agreement with the automatic verdict: {_counted(result.agreed, result.compared)}",
        f"- Grounded by the automatic check but not by hand: {len(result.disagreements) - len(by_hand)}; not grounded by the"
        f" check but grounded by hand: {len(by_hand)}",
    ]
    if result.stale:
        lines.append(f"- Not compared, as this run's reply or Chunks differ from the sample's, or its reply is now an Abstention: {', '.join(result.stale)}")
    lines.append("")
    if not result.disagreements:
        return [*lines, "No disagreements.", ""]
    return [
        *lines,
        "| Question | Type | Automatic | By hand | Note |",
        "|---|---|---|---|---|",
        *[f"| {d.item.question.id} | {d.item.question.type} | {d.item.verdict} | {d.label} | {d.note or NONE} |" for d in result.disagreements],
        "",
    ]


def _abstained(scored: Sequence[Asked], test: Callable[[Question], bool]) -> tuple[int, int]:
    chosen = [item for item in scored if test(item.question)]
    return sum(1 for item in chosen if item.turn.answer.abstention), len(chosen)


def _grounded(scored: Sequence[Asked]) -> tuple[int, int]:
    answers = [item.grounding for item in scored if item.grounding is not None]
    return sum(1 for grounding in answers if grounding.grounded), len(answers)


def _range(values: Sequence[float]) -> str:
    return f"{min(values):.2f}–{max(values):.2f}" if values else NONE


def _turns(changed: Sequence[Asked], of: int) -> str:
    named = ", ".join(item.question.id if item.question.history == () else f"{item.question.id} Turn {item.number}" for item in changed)
    return f"{len(changed)} of {of}" + (f" ({named})" if named else "")


def _question(item: Asked) -> str:
    grounding = item.grounding
    grounded = NONE if grounding is None else ("yes" if grounding.grounded else "no")
    invalid = ", ".join(f"[{number}]" for number in item.turn.answer.invalid) or NONE
    missing = NONE if grounding is None else (", ".join(grounding.missing) or NONE)
    found = NONE
    if item.question.answerable:
        found = f"{len(item.found)}/{len(item.question.passages)}" + (f": {', '.join(str(n) for n in item.found)}" if item.found else "")
    abstained = "yes" if item.turn.answer.abstention else "no"
    return f"| {item.question.id} | {item.question.type} | {abstained} | {grounded} | {invalid} | {missing} | {found} |"


def _timings(asked: Sequence[Asked]) -> list[str]:
    steps: list[tuple[str, list[float]]] = [
        ("retrieval", [item.turn.seconds["retrieval"] for item in asked]),
        ("rewriting", [item.turn.seconds["rewriting"] for item in asked if item.turn.rewrite is not None]),
        ("answering", [item.turn.seconds["answering"] for item in asked]),
        ("whole Turn", [sum(item.turn.seconds.values()) for item in asked]),
    ]
    return [
        "These depend on the machine and change from run to run. They count every Turn of the reported run, a follow-up's"
        " history included; rewriting counts only the Turns that were rewritten, as a Conversation's first Turn is not.",
        "",
        "| Step | Turns | p50 | p95 |",
        "|---|---:|---:|---:|",
        *[f"| {step} | {len(seconds)} | {_percentile(seconds, 50)} | {_percentile(seconds, 95)} |" for step, seconds in steps],
    ]


def _percentile(seconds: Sequence[float], percent: int) -> str:
    if not seconds:
        return NONE
    ordered = sorted(seconds)
    value = statistics.quantiles(ordered, n=100, method="inclusive")[percent - 1] if len(ordered) > 1 else ordered[0]
    return f"{value:.2f} s"
