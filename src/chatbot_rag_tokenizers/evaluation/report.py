"""The eval report writer (ADR 0039): the committed Markdown record of an `evaluate` run, in the style of the parse report.

It names what was scored (the Evaluation set, the chunking config and corpus, each retriever's settings),
then gives a results table per retriever and question type, what crowds the top 5 (ADR 0044) and a line per
question. Everything above the timings, which come last, depends only on the inputs, so two runs on the same index give the same report
up to that section.
"""

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..retrieval.corpus import Corpus
from ..retrieval.index import Index
from ..retrieval.retriever import RetrieverConfig
from ..parsing.report import NUMERIC_SHARE
from .crowding import Share, crowding, totals
from .evalset import QUESTION_TYPES, Question
from .matching import MIN_BLOCK, MatchingRule
from .harness import (
    AS_ASKED,
    CROWDING_DEPTH,
    FOLLOW_UP_ALONE,
    FOLLOW_UP_QUERIES,
    HIT_DEPTH,
    MRR_DEPTH,
    RECALL_DEPTH,
    REWRITE,
    WITH_HISTORY,
    Scored,
    all_answerable,
    metrics,
)
from .work_groups import WorkGroup, WorkGroups

NONE = "—"
ALL_ANSWERABLE = f"{AS_ASKED}, follow-ups alone"  # the all-answerable row: see harness.all_answerable


@dataclass(frozen=True)
class RetrieverRun:
    config: RetrieverConfig
    index: Index  # what was queried, with its build time and device
    scored: list[Scored]


def write_eval_report(
    path: Path,
    evaluation_set: Path,
    evaluation_set_sha256: str,
    questions: Sequence[Question],
    corpus: Corpus,
    runs: Sequence[RetrieverRun],
    rule: MatchingRule,
    groups: WorkGroups,
    ungrouped: Sequence[str],
) -> None:
    counts = ", ".join(f"{sum(1 for q in questions if q.type == kind)} {kind}" for kind in QUESTION_TYPES)
    lines = [
        "# Eval report",
        "",
        "Written by `evaluate`. Each retriever ranks the Chunks for every question of the Evaluation set, and the raw"
        " ranking is scored against the question's Passages.",
        "",
        "## Evaluation set",
        "",
        f"- File: `{evaluation_set}`",
        f"- sha256: `{evaluation_set_sha256}`",
        f"- Questions: {len(questions)} ({counts})",
        "",
        "## Chunks",
        "",
        f"- Parser: `{corpus.parser_key}`",
        f"- Chunking config: `{corpus.chunking_key}`",
        *[f"  - {name}: `{value}`" for name, value in corpus.chunking.describe().items()],
        f"- Files: {len(corpus.files)}",
        f"- Chunks: {len(corpus.chunks)}",
        "",
        "## Retrievers",
        "",
        *[line for run in runs for line in _retriever(run.config)],
        "",
        "## Metrics",
        "",
        f"- Recall@{RECALL_DEPTH}: the share of a question's Passages held by a Chunk in the top {RECALL_DEPTH}, averaged over questions.",
        f"- MRR@{MRR_DEPTH}: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top {MRR_DEPTH}.",
        f"- Hit@{HIT_DEPTH}: the share of questions with a Passage held by a Chunk in the top {HIT_DEPTH}.",
        f"- A Chunk holds a Passage when, after unicode, case, whitespace and hyphenation are normalised and citations"
        f" dropped, at least {rule.threshold:.0%} of the quote's words match the Chunk's in order, in blocks of at least"
        f" {MIN_BLOCK} words (a number may match alone) within twice the quote's length, and every number in the quote"
        f" matches (ADR 0041). A match running into the Chunk's first or last word counts only the quote's words on the"
        f" Chunk's side, and must cover at least {rule.edge_min_words} words. The Chunk may come from any Edition.",
        "- The ranking is scored raw: duplicates of one Work all take their slots.",
        "- Unanswerable questions are run but left out of the metrics.",
        f"- A follow-up is run three ways: {FOLLOW_UP_ALONE}, {WITH_HISTORY} (its prior turns, then the follow-up, joined by"
        f" spaces) and {REWRITE}. The *all answerable* row takes each follow-up alone, as a user would ask it.",
        "",
        "## Results",
        "",
        *[line for run in runs for line in _results(run)],
        "## Crowding",
        "",
        f"What takes the top {CROWDING_DEPTH} slots of each answerable question, as a user would ask it (the *all answerable*"
        " row's queries), on the raw ranking (ADR 0044).",
        "",
        f"- Work groups: `{groups.path}` (sha256 `{groups.sha256}`), {len(groups.editions)} Editions in"
        f" {len({group.work_id for group in groups.editions.values()})} Works, {groups.checked} of the Editions checked by hand"
        " (checked_by), never computed by the system being measured.",
        "- A duplicate slot holds a Chunk from a Work already ranked higher: another Edition or Version of it, or another"
        " Chunk of the same file.",
        "- A restatement slot holds a Chunk from a Survey. A Survey is always its own Work, and its Chunks are never duplicates.",
        "- Duplicates and restatement count only the questions whose top 5 Editions all have a Work group.",
        f"- A mostly-numeric slot holds a text Chunk with more than {NUMERIC_SHARE:.0%} of its words numbers, as the parse"
        " report counts them (ADR 0035). It counts every question.",
        "",
        *[line for run in runs for line in _crowding(run, groups.editions)],
        "## Editions without a Work group",
        "",
        f"Editions in any retriever's top {CROWDING_DEPTH} for an answerable question, in any query, with no Work group."
        " `evaluate --export-ungrouped` writes them, with their titles, for grouping.",
        "",
        *([f"- {edition_id}" for edition_id in ungrouped] or ["None."]),
        "",
        "## Questions",
        "",
        f"First hit is the rank of the first Chunk holding a Passage, within the top {MRR_DEPTH}; Passages found counts"
        f" those held in the top {RECALL_DEPTH}. The slot counts are within the top {CROWDING_DEPTH}; a question with an"
        " Edition there that has no Work group has its duplicates and restatements marked ungrouped.",
        "",
        *[line for run in runs for line in _questions(run, groups.editions)],
        "## Timings",
        "",
        "These depend on the machine and change from run to run.",
        "",
        *[_timings(run) for run in runs],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _retriever(config: RetrieverConfig) -> list[str]:
    return [f"- {config.name}: `{config.key}`", *[f"  - {name}: `{value}`" for name, value in config.describe().items()]]


def _results(run: RetrieverRun) -> list[str]:
    def chosen(kind: str, query: str) -> list[Scored]:
        return [s for s in run.scored if s.question.type == kind and s.query_kind == query]

    rows = [
        ("single-paper", AS_ASKED, chosen("single-paper", AS_ASKED)),
        ("multi-paper", AS_ASKED, chosen("multi-paper", AS_ASKED)),
        *[("follow-up", query, chosen("follow-up", query)) for query in FOLLOW_UP_QUERIES],
        ("all answerable", ALL_ANSWERABLE, all_answerable(run.scored)),
    ]
    unanswerable = sum(1 for s in run.scored if not s.question.answerable)
    lines = [
        f"### Results: {run.config.name}",
        "",
        f"| Question type | Query | Questions | Recall@{RECALL_DEPTH} | MRR@{MRR_DEPTH} | Hit@{HIT_DEPTH} |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for kind, query, scored in rows:
        m = metrics(scored)
        cells = [f"{m.recall:.2f}", f"{m.mrr:.3f}", f"{m.hit:.2f}"] if m else [NONE] * 3
        lines.append(f"| {kind} | {query} | {len(scored)} | {' | '.join(cells)} |")
    lines.append(f"| unanswerable | left out | {unanswerable} | {NONE} | {NONE} | {NONE} |")
    return [*lines, ""]


def _crowding(run: RetrieverRun, groups: Mapping[str, WorkGroup]) -> list[str]:
    total = totals(all_answerable(run.scored), groups)

    def row(measure: str, share: Share) -> str:
        cells = [f"{share.slots}/{share.of_slots}", _share(share.slots, share.of_slots)]
        cells += [f"{share.questions}/{share.of_questions}", _share(share.questions, share.of_questions)]
        return f"| {measure} | {' | '.join(cells)} |"

    return [
        f"### Crowding: {run.config.name}",
        "",
        f"| Measure | Top-{CROWDING_DEPTH} slots | Share of slots | Questions | Share of questions |",
        "|---|---:|---:|---:|---:|",
        row("duplicate", total.duplicate),
        row("restatement", total.restatement),
        row("mostly numeric", total.numeric),
        "",
        f"- Grouped: {total.grouped} of {total.queries} questions have a Work group for every Edition in their top {CROWDING_DEPTH}.",
        f"- Mostly-numeric slots holding a Passage: {total.numeric_holding} of {total.numeric.slots}",
        "",
    ]


def _share(count: int, of: int) -> str:
    return f"{count / of:.2f}" if of else NONE


def _questions(run: RetrieverRun, groups: Mapping[str, WorkGroup]) -> list[str]:
    lines = [
        f"### Questions: {run.config.name}",
        "",
        "| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for s in run.scored:
        if s.question.answerable:
            crowded = crowding(s, groups)
            hit, found = str(s.first_hit or "none"), f"{s.found}/{len(s.question.passages)}"
            slots = [_count_or_ungrouped(crowded.duplicates), _count_or_ungrouped(crowded.restatements), str(crowded.numeric)]
        else:
            hit, found, slots = "left out", NONE, [NONE] * 3
        lines.append(f"| {s.question.id} | {s.question.type} | {s.query_kind} | {hit} | {found} | {' | '.join(slots)} |")
    return [*lines, ""]


def _count_or_ungrouped(count: int | None) -> str:
    return "ungrouped" if count is None else str(count)


def _timings(run: RetrieverRun) -> str:
    milliseconds = sorted(s.seconds * 1000 for s in run.scored)
    p95 = statistics.quantiles(milliseconds, n=20, method="inclusive")[-1] if len(milliseconds) > 1 else milliseconds[0]
    return (
        f"- {run.config.name}: index built on {run.index.build_device} in {run.index.build_seconds:.2f} s; {len(milliseconds)}"
        f" queries on {run.index.retriever.device}, latency p50 {statistics.median(milliseconds):.2f} ms, p95 {p95:.2f} ms"
    )
