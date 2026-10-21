"""`evaluate` (ADR 0039): score each retriever's index on the Evaluation set and write the eval report, with what
crowds the top 5 measured against the Work groups (ADR 0044). Every retriever is scored twice: raw, and as its
Collapsed ranking over the same index (ADR 0053). A follow-up is scored a fourth way, as the chatbot's Rewrite of its
stored history and itself, when the [chat] answer model answers at its pin; otherwise that row is skipped (ADR 0067).
With the same model, every retriever is scored a third time, per paper and collapsed: the papers each query names,
listed once per query, fill the slots in rotation (ADR 0076). Each retriever [rerank] names is scored three times more,
reranked: its top `pool` Chunks reordered by the cross-encoder, then collapsed, and per paper and collapsed (#62)."""

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ..chat import model as answer_model
from ..chat.config import load_chat_config
from ..config import ConfigError
from ..chat.model import AnswerModelUnavailable
from ..chat.names import name_papers
from ..chat.rewrite import rewrite
from ..retrieval import index, rerank as reranking
from ..retrieval.collapse import Collapsed
from ..retrieval.config import ComparisonConfig
from ..retrieval.corpus import Corpus
from ..retrieval.per_paper import NamedWorks, PerPaper
from ..retrieval.rerank import RerankConfig, Reranked
from ..retrieval.retriever import Retriever, RetrieverConfig
from .check import check
from .comparison import check_baseline
from .crowding import ungrouped
from .evalset import EvaluationSetError, Question, load_evaluation_set
from .grouping import score_grouping
from .harness import CROWDING_DEPTH, REWRITER, all_answerable, metrics, queries, score
from .matching import MatchingRule
from .report import PaperNames, Rewriter, RetrieverRun, write_eval_report
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
        return Rewriter(f"{answer_model.pin(chat.model)}, {settings}", chat.rewrite_prompt, skipped=str(error), chat_retriever=chat.retriever_name, chat_k=chat.k)
    return Rewriter(f"{model.pin}, {settings}", chat.rewrite_prompt, written, chat_retriever=chat.retriever_name, chat_k=chat.k)


def name_queries(questions: Sequence[Question], rewrites: Mapping[str, str], chat_config: Path, works: NamedWorks) -> PaperNames:
    """The papers every query of every question names, each query text asked once, by the answer model of the [chat]
    table in ``chat_config`` with its names prompt. Skipped, with the reason, when that table can't be read or the
    answer model can't answer, so the per-paper twins are left out and the rest is scored without them. ``works``
    finds the Works each name could be, for the report."""
    try:
        chat = load_chat_config(chat_config)
    except ConfigError as error:
        return PaperNames("", "", skipped=str(error))
    settings = f"thinking {'on' if chat.model.think else 'off'}, temperature {chat.model.temperature}"
    texts = dict.fromkeys(text for question in questions for _, text in queries(question, rewrites))
    try:
        model = answer_model.load_answer_model(chat.model)
        named = {text: name_papers(model, chat.names_prompt, text) for text in texts}
    except AnswerModelUnavailable as error:
        return PaperNames(f"{answer_model.pin(chat.model)}, {settings}", chat.names_prompt, skipped=str(error))
    found = {name: works(name) for listed in named.values() for name in listed}
    return PaperNames(f"{model.pin}, {settings}", chat.names_prompt, named, found)


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
    overlap: float,
    comparison: ComparisonConfig,
    rerank: RerankConfig,
    chat_config: Path,
    export: Path | None = None,
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check` (ADR 0041), WorkGroupsError for a malformed Work
    groups file, BaselineMissing when the Comparison's baseline isn't one of `configs` and index.IndexMissing when a
    retriever isn't built. `pool` is the raw Chunks each Collapsed ranking
    merges copies in, `overlap` the share of word 5-grams that makes two Chunks copies, `rerank` the cross-encoder and the
    retrievers it reranks, and `chat_config` holds the [chat] table of the rewriter's model and prompt. With `export`, also writes there every Edition in a top 5 that has no Work group."""
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
    named_works = NamedWorks(chunks, rows.values())
    names = name_queries(questions, rewriter.rewrites, chat_config, named_works)
    if not names.ran:
        print(f"evaluate: the per-paper twins are skipped: {names.skipped}")
    # One cross-encoder for every reranked twin, loaded only when a retriever it reranks is scored.
    reranked = [config.name for config, _ in indexes if config.name in rerank.retrievers]
    scorer = reranking.load_scorer(rerank) if reranked else None
    runs = []
    for config, built in indexes:
        rankings: list[tuple[Retriever, RerankConfig | None]] = [(built.retriever, None)]
        if scorer and config.name in reranked:
            rankings.append((Reranked(built.retriever, chunks, scorer, rerank.pool), rerank))
        for retriever, reranked_by in rankings:
            collapsed = Collapsed(retriever, chunks, rows.values(), pool, overlap)
            twins = [
                RetrieverRun(config, built, retriever, score(questions, retriever, chunks, rule, rewriter.rewrites), rerank=reranked_by),
                RetrieverRun(config, built, collapsed, score(questions, collapsed, chunks, rule, rewriter.rewrites), pool, overlap, rerank=reranked_by),
            ]
            if names.ran:
                split = PerPaper(retriever, chunks, named_works, lambda text: names.names[text])
                per_paper = Collapsed(split, chunks, rows.values(), pool, overlap)
                scored = score(questions, per_paper, chunks, rule, rewriter.rewrites)
                twins.append(RetrieverRun(config, built, per_paper, scored, pool, overlap, per_paper=True, rerank=reranked_by))
            for run in twins:
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
    write_eval_report(report, evaluation_set, digest, questions, corpus, runs, rule, groups, grouping, missing, comparison, rewriter, names)
    print(f"evaluate: {len(questions)} questions; report in {report}")
