"""`evaluate` (ADR 0039): score each retriever's index on the Evaluation set and write the eval report."""

import hashlib
from collections.abc import Sequence
from pathlib import Path

from ..retrieval import index
from ..retrieval.corpus import Corpus
from ..retrieval.retriever import RetrieverConfig
from .check import check
from .evalset import EvaluationSetError, load_evaluation_set
from .harness import all_answerable, metrics, score
from .matching import MatchingRule
from .report import RetrieverRun, write_eval_report
from .works import Works


def evaluate(
    corpus: Corpus,
    configs: Sequence[RetrieverConfig],
    index_root: Path,
    evaluation_set: Path,
    report: Path,
    rule: MatchingRule,
    works: Works,
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check` (ADR 0041) and index.IndexMissing when a
    retriever isn't built."""
    questions = load_evaluation_set(evaluation_set)
    if not questions:
        raise EvaluationSetError(f"{evaluation_set} holds no questions")
    checked = check(questions, corpus, rule, works)
    if checked.problems:
        raise EvaluationSetError(f"{checked.failure(evaluation_set)}\nFix the set; `just eval-check` gives every Passage's matches too.")
    indexes = [(config, index.load(index_root, corpus, config)) for config in configs]
    chunk_texts = {chunk.chunk_id: chunk.text for chunk in corpus.chunks}
    runs = []
    for config, built in indexes:
        scored = score(questions, built.retriever, chunk_texts, rule)
        runs.append(RetrieverRun(config, built.build_seconds, scored))
        overall = metrics(all_answerable(scored))
        if overall:
            print(f"evaluate: {config.name}: Recall@5 {overall.recall:.2f}, MRR@10 {overall.mrr:.3f}, Hit@5 {overall.hit:.2f}")
    digest = hashlib.sha256(evaluation_set.read_bytes()).hexdigest()
    write_eval_report(report, evaluation_set, digest, questions, corpus, runs, rule)
    print(f"evaluate: {len(questions)} questions; report in {report}")
