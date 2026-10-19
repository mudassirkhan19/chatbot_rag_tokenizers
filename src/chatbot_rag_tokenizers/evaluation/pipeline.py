"""`evaluate` (ADR 0039): score each retriever's index on the Evaluation set and write the eval report, with what
crowds the top 5 measured against the Work groups (ADR 0044). Every retriever is scored twice: raw, and as its
Collapsed ranking over the same index (ADR 0052)."""

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ..retrieval import index
from ..retrieval.collapse import Collapsed
from ..retrieval.corpus import Corpus
from ..retrieval.retriever import RetrieverConfig
from .check import check
from .crowding import ungrouped
from .evalset import EvaluationSetError, load_evaluation_set
from .harness import CROWDING_DEPTH, all_answerable, metrics, score
from .matching import MatchingRule
from .report import RetrieverRun, write_eval_report
from .work_groups import load_work_groups, write_export
from .works import Works


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
    export: Path | None = None,
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check` (ADR 0041), WorkGroupsError for a malformed Work
    groups file and index.IndexMissing when a retriever isn't built. `pool` is the raw Chunks each Collapsed ranking
    picks one per Work from. With `export`, also writes there every Edition in a top 5 that has no Work group."""
    rows = {row["edition_id"]: row for row in manifest}
    works = Works(rows.values())
    groups = load_work_groups(work_groups)
    questions = load_evaluation_set(evaluation_set)
    if not questions:
        raise EvaluationSetError(f"{evaluation_set} holds no questions")
    checked = check(questions, corpus, rule, works)
    if checked.problems:
        raise EvaluationSetError(f"{checked.failure(evaluation_set)}\nFix the set; `just eval-check` gives every Passage's matches too.")
    indexes = [(config, index.load(index_root, corpus, config)) for config in configs]
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    runs = []
    for config, built in indexes:
        collapsed = Collapsed(built.retriever, chunks, rows.values(), pool)
        for run in (
            RetrieverRun(config, built, score(questions, built.retriever, chunks, rule)),
            RetrieverRun(config, built, score(questions, collapsed, chunks, rule), pool),
        ):
            runs.append(run)
            if overall := metrics(all_answerable(run.scored)):
                print(f"evaluate: {run.name}: Recall@5 {overall.recall:.2f}, MRR@10 {overall.mrr:.3f}, Hit@5 {overall.hit:.2f}")
    missing = sorted(ungrouped((s for run in runs for s in run.scored if s.question.answerable), groups.editions))
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
    write_eval_report(report, evaluation_set, digest, questions, corpus, runs, rule, groups, missing)
    print(f"evaluate: {len(questions)} questions; report in {report}")
