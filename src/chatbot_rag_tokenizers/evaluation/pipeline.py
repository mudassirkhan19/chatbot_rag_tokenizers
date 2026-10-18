"""`evaluate`: score each retriever's index on the Evaluation set and write the eval report."""

import hashlib
from collections.abc import Sequence
from pathlib import Path

from ..parsing.config import ChunkingConfig
from ..retrieval import index
from ..retrieval.corpus import Corpus
from ..retrieval.retriever import RetrieverConfig
from .evalset import EvaluationSetError, load_evaluation_set
from .harness import metrics, score
from .report import RetrieverRun, write_eval_report


def evaluate(
    chunking: ChunkingConfig, corpus: Corpus, configs: Sequence[RetrieverConfig], index_root: Path, evaluation_set: Path, report: Path
) -> None:
    """Raises EvaluationSetError for a malformed set and index.IndexMissing when a retriever isn't built."""
    questions = load_evaluation_set(evaluation_set)
    if not questions:
        raise EvaluationSetError(f"{evaluation_set} holds no questions")
    indexes = [(config, index.load(index_root, corpus, config)) for config in configs]
    chunk_texts = {chunk.chunk_id: chunk.text for chunk in corpus.chunks}
    runs = []
    for config, built in indexes:
        scored = score(questions, built.retriever, chunk_texts)
        runs.append(RetrieverRun(config, built.build_seconds, scored))
        overall = metrics([s for s in scored if s.question.answerable and s.query in ("as asked", "follow-up alone")])
        if overall:
            print(f"evaluate: {config.name}: Recall@5 {overall.recall:.2f}, MRR@10 {overall.mrr:.3f}, Hit@5 {overall.hit:.2f}")
    digest = hashlib.sha256(evaluation_set.read_bytes()).hexdigest()
    write_eval_report(report, evaluation_set, digest, questions, chunking, corpus, runs)
    print(f"evaluate: {len(questions)} questions; report in {report}")
