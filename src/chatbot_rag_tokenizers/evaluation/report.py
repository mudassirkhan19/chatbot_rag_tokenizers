"""The eval report writer (ADR 0039): the committed Markdown record of an `evaluate` run, in the style of the parse report.

It names what was scored (the Evaluation set, the chunking config and corpus, each retriever's settings),
then gives a results table per retriever and question type, each retriever's raw ranking followed by its
Collapsed ranking (ADR 0053), the Comparison against a baseline (ADR 0061), what crowds the top 5 (ADR 0044),
the two rankings side by side (ADR 0063), the grouping rule scored against the Work groups (ADR 0060), each
follow-up's Rewrite beside its reference rewrite (ADR 0067) and a line per question, then the Cost table. Everything above the Cost table, which comes last, depends only on the inputs, so two runs on the same index give the same
report up to that section, and the Cost table differs only in its times.
"""

import hashlib
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..retrieval.collapse import SUFFIX
from ..retrieval.config import ComparisonConfig
from ..retrieval.corpus import Corpus
from ..retrieval.index import Index
from ..retrieval.retriever import RetrieverConfig
from ..parsing.report import NUMERIC_SHARE
from .comparison import CONFIDENCE, compare, draws
from .crowding import Share, crowding, totals
from .evalset import QUESTION_TYPES, Question
from .grouping import GroupingScore
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
    REWRITER,
    WITH_HISTORY,
    Scored,
    all_answerable,
    metrics,
    recall,
    reciprocal_rank,
)
from .work_groups import WorkGroup, WorkGroups

NONE = "—"
ALL_ANSWERABLE = f"{AS_ASKED}, follow-ups alone"  # the all-answerable row: see harness.all_answerable


@dataclass(frozen=True)
class Rewriter:
    """What the rewriter wrote for the follow-ups (ADR 0067), or why it was skipped."""

    model: str  # the answer model and how it is run, as the chat report names them
    prompt: str
    rewrites: Mapping[str, str] = field(default_factory=dict)  # each follow-up's Rewrite, by question id
    skipped: str = ""  # why the answer model couldn't answer, when it couldn't
    chat_retriever: str = ""  # the retriever `[chat]` names, when the [chat] table could be read
    chat_k: int = 0  # the Chunks the chatbot retrieves per Turn

    @property
    def ran(self) -> bool:
        return not self.skipped


@dataclass(frozen=True)
class RetrieverRun:
    config: RetrieverConfig
    index: Index  # what was queried, with its build time and device
    scored: list[Scored]
    pool: int | None = None  # for a Collapsed ranking, the raw Chunks it merged copies in
    overlap: float | None = None  # for a Collapsed ranking, the share of word 5-grams that made two Chunks copies

    @property
    def name(self) -> str:
        return self.config.name + (SUFFIX if self.pool else "")


def write_eval_report(
    path: Path,
    evaluation_set: Path,
    evaluation_set_sha256: str,
    questions: Sequence[Question],
    corpus: Corpus,
    runs: Sequence[RetrieverRun],
    rule: MatchingRule,
    groups: WorkGroups,
    grouping: GroupingScore | None,
    ungrouped: Sequence[str],
    comparison: ComparisonConfig,
    rewriter: Rewriter,
) -> None:
    counts = ", ".join(f"{sum(1 for q in questions if q.type == kind)} {kind}" for kind in QUESTION_TYPES)
    lines = [
        "# Eval report",
        "",
        "Written by `evaluate`. Each retriever ranks the Chunks for every question of the Evaluation set, and the raw"
        f" ranking and its Collapsed ranking (`<retriever>{SUFFIX}`, each passage once across a Work's files) are scored against the"
        " question's Passages.",
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
        *[line for run in runs for line in _retriever(run)],
        *([f"- The chatbot's retriever, from `[chat]`: {rewriter.chat_retriever}, {rewriter.chat_k} Chunks per Turn"] if rewriter.chat_retriever else []),
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
        "- A retriever's own ranking is scored raw: duplicates of one Work all take their slots.",
        f"- Its `{SUFFIX}` twin is scored on the Collapsed ranking (ADRs 0053, 0057 and 0072) over the same index: from"
        " the raw top *pool* Chunks, with Works from the manifest's work_id (an Edition with none is its own Work), in"
        " the raw order, it merges copies: the Chunks of a Work from different files that share at least *overlap* of"
        " their word 5-grams, counted on the smaller Chunk's, where one is the other's closest Chunk in its file"
        " (another Version's or Edition's copy of the passage, wherever its file puts it), into the slot of the best-ranked one, shown from the"
        " Canonical Edition's file when the pool holds a copy from it, else from an Edition's latest file, else as"
        " ranked. A Work's other Chunks keep their slots. Surveys are not demoted.",
        "- Unanswerable questions are run but left out of the metrics.",
        f"- A follow-up is run four ways: {FOLLOW_UP_ALONE}, {WITH_HISTORY} (its prior turns, then the follow-up, joined by"
        f" spaces), {REWRITE} and {REWRITER}, the chatbot's Rewrite: the answer model, given the `[chat]` rewrite prompt,"
        " the last `history` prior turns as earlier questions with no answers, and the follow-up (ADR 0067). The *all"
        " answerable* row takes each follow-up alone, as a user would ask it.",
        *_rewriter(rewriter),
        "",
        "## Results",
        "",
        *[line for run in runs for line in _results(run, rewriter)],
        *_comparison(runs, comparison),
        "## Crowding",
        "",
        f"What takes the top {CROWDING_DEPTH} slots of each answerable question, as a user would ask it (the *all answerable*"
        f" row's queries), on the raw ranking and on the Collapsed ranking (ADR 0044). Both are measured against the same"
        " Work groups, never the manifest's work_id the collapse uses.",
        "",
        f"- Work groups: `{groups.path}` (sha256 `{groups.sha256}`), {len(groups.editions)} Editions in"
        f" {len({group.work_id for group in groups.editions.values()})} Works, {groups.checked} of the Editions checked"
        " (who checked each is in checked_by), never computed by the system being measured.",
        "- A duplicate slot holds a Chunk from a Work already ranked higher: another Edition or Version of it, or another"
        " Chunk of the same file. The two are counted apart too: the first repeats a paper, the second is more of it."
        " A Collapsed ranking merges only copies, the first kind.",
        "- A restatement slot holds a Chunk from a Survey. A Survey is always its own Work, and its Chunks are never duplicates.",
        "- Duplicates and restatement count only the questions whose top 5 Editions all have a Work group.",
        f"- A mostly-numeric slot holds a text Chunk with more than {NUMERIC_SHARE:.0%} of its words numbers, as the parse"
        " report counts them (ADR 0035). It counts every question.",
        "",
        *[line for run in runs for line in _crowding(run, groups.editions)],
        *_before_and_after(runs, groups.editions),
        *_grouping(grouping, groups.editions),
        "## Editions without a Work group",
        "",
        f"Editions in any retriever's top {CROWDING_DEPTH} for an answerable question, in any query but the {REWRITER}'s,"
        " with no Work group."
        " `evaluate --export-ungrouped` writes them, with their titles, for grouping.",
        "",
        *([f"- {edition_id}" for edition_id in ungrouped] or ["None."]),
        "",
        "## Questions",
        "",
        f"First hit is the rank of the first Chunk holding a Passage, within the top {MRR_DEPTH}; Passages found counts"
        f" those held in the top {RECALL_DEPTH}. The slot counts are within the top {CROWDING_DEPTH}; a question with an"
        " Edition there that has no Work group has its duplicates and restatements marked ungrouped. A Collapsed"
        f" ranking's lines name the file of each top-{CROWDING_DEPTH} Chunk, with the other files of its Work in the pool"
        " after a +.",
        "",
        *_rewrites(questions, rewriter),
        *[line for run in runs for line in _questions(run, groups.editions)],
        "## Cost",
        "",
        "Each retriever's model and index, with how long the index took to build and each query took. A hybrid's"
        " parameters, dimension and index are its members' summed (BM25 has no model and no vectors), and its build"
        f" time is theirs; a `{SUFFIX}` twin uses its retriever's index. The times depend on the machine and change"
        " from run to run.",
        "",
        "| Retriever | Parameters | Dimension | Index on disk | Built on | Build time | Queries | Queried on | Latency p50 | Latency p95 |",
        "|---|---:|---:|---:|---|---:|---:|---|---:|---:|",
        *[_cost(run) for run in runs],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _retriever(run: RetrieverRun) -> list[str]:
    if run.pool:
        return [f"- {run.name}: {run.config.name}'s index, with copies from other files of a Work merged", f"  - pool: `{run.pool}`", f"  - overlap: `{run.overlap}`"]
    return [f"- {run.name}: `{run.config.key}`", *[f"  - {name}: `{value}`" for name, value in run.config.describe().items()]]


def _rewriter(rewriter: Rewriter) -> list[str]:
    if not rewriter.ran:
        return [f"- The {REWRITER} row is skipped: {rewriter.skipped}"]
    return [
        f"- Rewriter: {rewriter.model}, rewrite prompt sha256"
        f" `{hashlib.sha256(rewriter.prompt.encode()).hexdigest()}`"
    ]


def _rewrites(questions: Sequence[Question], rewriter: Rewriter) -> list[str]:
    lines = ["### Rewrites", "", f"Each follow-up's {REWRITE} and the {REWRITER}'s Rewrite, which are its last two queries below.", ""]
    if not rewriter.ran:
        return [*lines, f"None: the {REWRITER} row is skipped.", ""]
    rows = [
        f"| {q.id} | {q.question} | {q.rewrite} | {rewriter.rewrites[q.id]} |" for q in questions if q.id in rewriter.rewrites
    ]
    return [*lines, "| Question | Follow-up | Reference rewrite | Rewrite |", "|---|---|---|---|", *rows, ""]


def _results(run: RetrieverRun, rewriter: Rewriter) -> list[str]:
    def chosen(kind: str, query: str) -> list[Scored]:
        return [s for s in run.scored if s.question.type == kind and s.query_kind == query]

    rows = [
        ("single-paper", AS_ASKED, chosen("single-paper", AS_ASKED)),
        ("multi-paper", AS_ASKED, chosen("multi-paper", AS_ASKED)),
        *[("follow-up", query, chosen("follow-up", query)) for query in FOLLOW_UP_QUERIES if query != REWRITER or rewriter.ran],
        ("all answerable", ALL_ANSWERABLE, all_answerable(run.scored)),
    ]
    unanswerable = sum(1 for s in run.scored if not s.question.answerable)
    lines = [
        f"### Results: {run.name}",
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


def _comparison(runs: Sequence[RetrieverRun], config: ComparisonConfig) -> list[str]:
    by_name = {run.name: run for run in runs}

    def baseline(run: RetrieverRun) -> RetrieverRun:
        return by_name[config.baseline + (SUFFIX if run.pool else "")]

    questions = len(all_answerable(by_name[config.baseline].scored))
    lines = [
        "## Comparison",
        "",
        f"Each retriever against the baseline, {config.baseline}, and each `{SUFFIX}` twin against {config.baseline}{SUFFIX},"
        f" on the {questions} answerable questions as a user asks them (the *all answerable* row's queries). The report"
        " names no winner: the decision rule of spec #55 is applied in an ADR.",
        "",
        "- Wins, ties and losses count the questions where the retriever's Recall@5 (or reciprocal rank, for MRR@10) is"
        " higher than the baseline's, the same, or lower.",
        f"- The intervals are {CONFIDENCE:.0%} percentile bootstrap intervals: the questions drawn with replacement,"
        f" {config.resamples} times, by NumPy's default generator seeded with {config.seed}. Every retriever is scored on the"
        " same draws, so a difference is paired question by question.",
        "- A difference whose interval holds 0 is within noise.",
        "",
    ]
    if not questions:
        return [*lines, "No answerable questions to compare on.", ""]
    drawn = draws(questions, config.resamples, config.seed)
    for metric, measure, digits in ((f"Recall@{RECALL_DEPTH}", recall, 2), (f"MRR@{MRR_DEPTH}", reciprocal_rank, 3)):
        lines += [
            f"### Comparison: {metric}",
            "",
            f"| Retriever | Baseline | {metric} | {CONFIDENCE:.0%} interval | Difference | Difference's {CONFIDENCE:.0%} interval | Noise | Wins | Ties | Losses |",
            "|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
        ]
        for run in runs:
            compared = compare(run.scored, baseline(run).scored, measure, drawn)
            low, high = compared.difference_interval.low, compared.difference_interval.high
            cells = [
                baseline(run).name,
                f"{compared.mean:.{digits}f}",
                f"[{compared.interval.low:.{digits}f}, {compared.interval.high:.{digits}f}]",
                f"{compared.difference:+.{digits}f}",
                f"[{low:+.{digits}f}, {high:+.{digits}f}]",
                "within noise" if compared.within_noise else "beyond noise",
                str(compared.wins),
                str(compared.ties),
                str(compared.losses),
            ]
            lines.append(f"| {run.name} | {' | '.join(cells)} |")
        lines.append("")
    for ranking, chosen in (("raw ranking", [run for run in runs if not run.pool]), ("Collapsed ranking", [run for run in runs if run.pool])):
        columns = [all_answerable(run.scored) for run in chosen]
        lines += [
            f"### First hit: {ranking}",
            "",
            f"The rank of each question's first hit within the top {MRR_DEPTH}, by retriever.",
            "",
            "| " + " | ".join(["Question", "Type", *(run.name for run in chosen)]) + " |",
            "|---|---|" + "---:|" * len(chosen),
            *[
                f"| {row[0].question.id} | {row[0].question.type} | {' | '.join(str(s.first_hit or 'none') for s in row)} |"
                for row in zip(*columns)
            ],
            "",
        ]
    return lines


def _crowding(run: RetrieverRun, groups: Mapping[str, WorkGroup]) -> list[str]:
    total = totals(all_answerable(run.scored), groups)

    def row(measure: str, share: Share) -> str:
        cells = [f"{share.slots}/{share.of_slots}", _share(share.slots, share.of_slots)]
        cells += [f"{share.questions}/{share.of_questions}", _share(share.questions, share.of_questions)]
        return f"| {measure} | {' | '.join(cells)} |"

    queries = all_answerable(run.scored)
    short = [
        f"- Pool: the top {run.pool} raw Chunks held fewer than {CROWDING_DEPTH} distinct Chunks, once copies were merged,"
        f" for {sum(1 for s in queries if (s.pool_distinct or 0) < CROWDING_DEPTH)} of {len(queries)} questions, and fewer than"
        f" {MRR_DEPTH}, the depth each query asks for, for {sum(1 for s in queries if (s.pool_distinct or 0) < MRR_DEPTH)}."
    ]
    return [
        f"### Crowding: {run.name}",
        "",
        f"| Measure | Top-{CROWDING_DEPTH} slots | Share of slots | Questions | Share of questions |",
        "|---|---:|---:|---:|---:|",
        row("duplicate", total.duplicate),
        row("duplicate: another Edition or Version", total.other_file),
        row("duplicate: same file", total.same_file),
        row("restatement", total.restatement),
        row("mostly numeric", total.numeric),
        "",
        f"- Grouped: {total.grouped} of {total.queries} questions have a Work group for every Edition in their top {CROWDING_DEPTH}.",
        f"- Mostly-numeric slots holding a Passage: {total.numeric_holding} of {total.numeric.slots}",
        *(short if run.pool else []),
        "",
    ]


def _before_and_after(runs: Sequence[RetrieverRun], groups: Mapping[str, WorkGroup]) -> list[str]:
    """Each retriever's raw ranking beside its Collapsed ranking, with the duplicates and the metrics over the answerable
    questions as a user asks them: the figures of its Crowding and Results tables, in one table."""
    lines = [
        "## Before and after",
        "",
        f"Each retriever's raw ranking and its Collapsed ranking, over the answerable questions as a user asks them: the"
        f" duplicate slots in the top {CROWDING_DEPTH} as *Crowding* counts them, over the questions whose top"
        f" {CROWDING_DEPTH} is grouped, and the *all answerable* row of *Results*.",
        "",
        f"| Retriever | Ranking | Duplicate | Another Edition or Version | Same file | Grouped questions | Recall@{RECALL_DEPTH} | MRR@{MRR_DEPTH} | Hit@{HIT_DEPTH} |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in runs:
        scored = all_answerable(run.scored)
        total, m = totals(scored, groups), metrics(scored)
        cells = [
            *(f"{share.slots}/{share.of_slots}" for share in (total.duplicate, total.other_file, total.same_file)),
            f"{total.grouped}/{total.queries}",
            *([f"{m.recall:.2f}", f"{m.mrr:.3f}", f"{m.hit:.2f}"] if m else [NONE] * 3),
        ]
        lines.append(f"| {run.config.name} | {'collapsed' if run.pool else 'raw'} | {' | '.join(cells)} |")
    return [*lines, ""]


def _grouping(grouping: GroupingScore | None, groups: Mapping[str, WorkGroup]) -> list[str]:
    if grouping is None:
        return ["## Grouping", "", "The manifest has no work_id filled, so there is no grouping to score: `collect` fills it.", ""]
    lines = [
        "## Grouping",
        "",
        "The grouping rule (ADR 0051), as the manifest's work_id and survey columns hold it, scored against the Work"
        " groups. Over the Editions in the Work groups, a pair is two Editions one Work holds; an Edition the manifest"
        " gives no work_id is its own Work. Precision is the share of the rule's pairs the Work groups join too, recall"
        " the share of the Work groups' pairs the rule joins. A Work of the Work groups is named under *Surveys* when its"
        " Survey flag differs from the rule's survey column on any of its Editions (blank reads as no).",
        "",
    ]
    both = len(grouping.rule_pairs & grouping.checked_pairs)
    without = (
        f"{len(grouping.without_work_id)} without a work_id in the manifest: {', '.join(grouping.without_work_id)}"
        if grouping.without_work_id
        else "all with a work_id in the manifest"
    )

    def pairs(found: Sequence[tuple[str, str]]) -> list[str]:
        if not found:
            return ["None.", ""]
        rows = [
            f"| {first} | {grouping.titles[first]} | {second} | {grouping.titles[second]} |"
            f" {grouping.work_ids[first] or NONE} / {grouping.work_ids[second] or NONE} |"
            f" {groups[first].work_id} / {groups[second].work_id} |"
            for first, second in found
        ]
        return ["| Edition | Title | Edition | Title | work_id | Work groups |", "|---|---|---|---|---|---|", *rows, ""]

    return [
        *lines,
        f"- Editions: {len(grouping.titles)} in the Work groups, {without}",
        f"- Pairs the rule joins: {len(grouping.rule_pairs)}",
        f"- Pairs the Work groups join: {len(grouping.checked_pairs)}",
        f"- Pairs both join: {both}",
        f"- Precision: {both}/{len(grouping.rule_pairs)} = {_share(both, len(grouping.rule_pairs))}",
        f"- Recall: {both}/{len(grouping.checked_pairs)} = {_share(both, len(grouping.checked_pairs))}",
        "",
        "### Pairs the rule joins and the Work groups keep apart",
        "",
        *pairs(grouping.joined_apart),
        "### Pairs the Work groups join and the rule misses",
        "",
        *pairs(grouping.missed),
        "### Surveys",
        "",
        f"- Surveys: {grouping.surveys} of {grouping.works} Works in the Work groups, {grouping.rule_surveys} flagged by the rule;"
        f" the two agree on {grouping.works - len(grouping.survey_disagreements)} of {grouping.works} Works",
        "",
        *(
            [
                "| Work | Work groups | Rule | Editions |",
                "|---|---|---|---|",
                *[
                    f"| {d.work_id} | {'yes' if d.survey else 'no'} | {', '.join(d.rule_flags)} | {', '.join(d.editions)} |"
                    for d in grouping.survey_disagreements
                ],
            ]
            if grouping.survey_disagreements
            else ["None."]
        ),
        "",
    ]


def _share(count: int, of: int) -> str:
    return f"{count / of:.2f}" if of else NONE


def _questions(run: RetrieverRun, groups: Mapping[str, WorkGroup]) -> list[str]:
    merged = [f"Top-{CROWDING_DEPTH} files + merged"] if run.pool else []
    lines = [
        f"### Questions: {run.name}",
        "",
        "| " + " | ".join(["Question", "Type", "Query", "First hit", "Passages found", "Duplicate slots", "Restatement slots", "Numeric slots", *merged]) + " |",
        "|---|---|---|---:|---:|---:|---:|---:|" + ("---|" if run.pool else ""),
    ]
    for s in run.scored:
        if s.question.answerable:
            crowded = crowding(s, groups)
            hit, found = str(s.first_hit or "none"), f"{s.found}/{len(s.question.passages)}"
            slots = [_count_or_ungrouped(crowded.duplicates), _count_or_ungrouped(crowded.restatements), str(crowded.numeric)]
        else:
            hit, found, slots = "left out", NONE, [NONE] * 3
        if run.pool:
            slots.append("; ".join(" + ".join([slot.pinned_id, *slot.merged]) for slot in s.top) or NONE)
        lines.append(f"| {s.question.id} | {s.question.type} | {s.query_kind} | {hit} | {found} | {' | '.join(slots)} |")
    return [*lines, ""]


def _count_or_ungrouped(count: int | None) -> str:
    return "ungrouped" if count is None else str(count)


def _cost(run: RetrieverRun) -> str:
    retriever = run.index.retriever
    milliseconds = sorted(s.seconds * 1000 for s in run.scored)
    p95 = statistics.quantiles(milliseconds, n=20, method="inclusive")[-1] if len(milliseconds) > 1 else milliseconds[0]
    cells = [
        NONE if retriever.parameters is None else f"{retriever.parameters / 1e6:.1f}M",
        NONE if retriever.dimension is None else str(retriever.dimension),
        _size(run.index.disk_bytes),
        run.index.build_device,
        f"{run.index.build_seconds:.2f} s",
        str(len(milliseconds)),
        retriever.device,
        f"{statistics.median(milliseconds):.2f} ms",
        f"{p95:.2f} ms",
    ]
    return f"| {run.name} | {' | '.join(cells)} |"


def _size(count: int) -> str:
    return f"{count / 1e6:.1f} MB" if count >= 1e6 else f"{count / 1e3:.1f} kB"
