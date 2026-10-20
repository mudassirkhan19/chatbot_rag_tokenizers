"""`evaluate` (ADR 0039): score each retriever's index on the Evaluation set and write the eval report, with what
crowds the top 5 measured against the Work groups (ADR 0044). Every retriever is scored twice: raw, and as its
Collapsed ranking over the same index (ADR 0053). A follow-up is scored a fourth way, as the chatbot's Rewrite of its
stored history and itself, when the [chat] answer model answers at its pin; otherwise that row is skipped (ADR 0067)."""

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ..chat import model as answer_model
from ..chat.config import load_chat_config
from ..config import ConfigError
from ..chat.model import AnswerModelUnavailable
from ..chat.rewrite import rewrite
from ..retrieval import index
from ..retrieval.collapse import Collapsed
from ..retrieval.config import ComparisonConfig
from ..retrieval.corpus import Corpus
from ..retrieval.retriever import RetrieverConfig
from .check import check
from .comparison import check_baseline
from .crowding import ungrouped
from .evalset import EvaluationSetError, Question, load_evaluation_set
from .grouping import score_grouping
from .harness import CROWDING_DEPTH, REWRITER, all_answerable, metrics, score
from .matching import MatchingRule
from .report import Rewriter, RetrieverRun, write_eval_report
from .work_groups import load_work_groups, write_export
from .works import Works


def checked_questions(evaluation_set: Path, corpus: Corpus, rule: MatchingRule, works: Works) -> list[Question]:
    """The Evaluation set's questions. Raises EvaluationSetError for an empty set or one that fails `eval-check`
    (ADR 0041), so nothing is scored on a broken set."""
    questions = load_evaluation_set(evaluation_set)
    if not questions:
        raise EvaluationSetError(f"{evaluation_set} holds no questions")
    checked = check(questions, corpus, rule, works)
    if checked.problems:
        raise EvaluationSetError(f"{checked.failure(evaluation_set)}\nFix the set; `just eval-check` gives every Passage's matches too.")
    return questions


def rewrite_follow_ups(questions: Sequence[Question], chat_config: Path) -> Rewriter:
    """The rewriter's Rewrite of every follow-up, from its stored history's questions, the last `history` of them,
    as a Conversation's earlier Turns with no answers, by the answer model of the [chat] table in ``chat_config``.
    Skipped, with the reason, when that table can't be read or the answer model can't answer, so the other rows are
    scored without it."""
    try:
        chat = load_chat_config(chat_config)
    except ConfigError as error:
        return Rewriter("", "", skipped=str(error))
    settings = f"thinking {'on' if chat.model.think else 'off'}, temperature {chat.model.temperature}"
    try:
        model = answer_model.load_answer_model(chat.model)
        written = {
            question.id: rewrite(model, chat.rewrite_prompt, [(asked, "") for asked in question.history[-chat.history :]], question.question)
            for question in questions
            if question.type == "follow-up"
        }
    except AnswerModelUnavailable as error:
        return Rewriter(f"{answer_model.pin(chat.model)}, {settings}", chat.rewrite_prompt, skipped=str(error))
    return Rewriter(f"{model.pin}, {settings}", chat.rewrite_prompt, written)


def evaluate(
    corpus: Corpus,
    configs: Sequence[RetrieverConfig],
    index_root: Path,
    evaluation_set: Path,
    report: Path,
    rule: MatchingRule,
    manifest: Iterable[Mapping[str, str]],
    work_groups: Path,
    pool: int,
    comparison: ComparisonConfig,
    chat_config: Path,
    export: Path | None = None,
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check` (ADR 0041), WorkGroupsError for a malformed Work
    groups file, BaselineMissing when the Comparison's baseline isn't one of `configs` and index.IndexMissing when a
    retriever isn't built. `pool` is the raw Chunks each Collapsed ranking
    merges copies in, and `chat_config` holds the [chat] table of the rewriter's model and prompt. With `export`, also writes there every Edition in a top 5 that has no Work group."""
    check_baseline(comparison.baseline, [config.name for config in configs])
    rows = {row["edition_id"]: row for row in manifest}
    works = Works(rows.values())
    groups = load_work_groups(work_groups)
    questions = checked_questions(evaluation_set, corpus, rule, works)
    indexes = [(config, index.load(index_root, corpus, config)) for config in configs]
    rewriter = rewrite_follow_ups(questions, chat_config)
    if not rewriter.ran:
        print(f"evaluate: the rewriter row is skipped: {rewriter.skipped}")
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    runs = []
    for config, built in indexes:
        collapsed = Collapsed(built.retriever, chunks, rows.values(), pool)
        for run in (
            RetrieverRun(config, built, score(questions, built.retriever, chunks, rule, rewriter.rewrites)),
            RetrieverRun(config, built, score(questions, collapsed, chunks, rule, rewriter.rewrites), pool),
        ):
            runs.append(run)
            if overall := metrics(all_answerable(run.scored)):
                print(f"evaluate: {run.name}: Recall@5 {overall.recall:.2f}, MRR@10 {overall.mrr:.3f}, Hit@5 {overall.hit:.2f}")
    # The rewriter's queries are left out, so the Editions to group don't depend on whether the answer model answered.
    grouped_queries = (s for run in runs for s in run.scored if s.question.answerable and s.query_kind != REWRITER)
    missing = sorted(ungrouped(grouped_queries, groups.editions))
    editions = "1 Edition" if len(missing) == 1 else f"{len(missing)} Editions"
    if missing:
        has = "has" if len(missing) == 1 else "have"
        print(
            f"evaluate: {editions} in the top {CROWDING_DEPTH} {has} no Work group: {', '.join(missing)}. Duplicates and"
            f" restatement count only the questions whose top {CROWDING_DEPTH} are all grouped; group them in {work_groups}"
            " (`--export-ungrouped` writes them with their titles)."
        )
    if export:
        write_export(export, missing, rows)
        print(f"evaluate: {editions} without a Work group exported to {export}")
    digest = hashlib.sha256(evaluation_set.read_bytes()).hexdigest()
    grouping = score_grouping(groups.editions, rows)
    write_eval_report(report, evaluation_set, digest, questions, corpus, runs, rule, groups, grouping, missing, comparison, rewriter)
    print(f"evaluate: {len(questions)} questions; report in {report}")
