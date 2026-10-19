"""The Comparison (spec #55, ADR 0061): each retriever against a baseline, question by question, on the answerable
questions as a user asks them (harness.all_answerable).

- A win is a question where the retriever's Recall@5 (or reciprocal rank) is higher than the baseline's, a loss
  one where it is lower, a tie one where the two are equal.
- The intervals are 95% percentile bootstrap intervals: the questions are drawn with replacement, as many as there
  are, `resamples` times, and each draw's mean is taken; the interval runs from the 2.5th to the 97.5th
  percentile of those means. Every retriever is scored on the same draws, so the difference from the baseline is
  paired: each draw's mean of the per-question differences. The baseline against itself differs by exactly 0 in
  every draw.
- A difference whose interval holds 0 is within noise.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from .harness import Scored, all_answerable

CONFIDENCE = 0.95


class BaselineMissing(ValueError):
    """The Comparison's baseline isn't among the retrievers `evaluate` scores, worded for the person running it."""


def check_baseline(baseline: str, scored: Sequence[str]) -> None:
    """Raises BaselineMissing unless the baseline is one of the retrievers to be scored, named as `--retriever` takes them."""
    if baseline not in scored:
        raise BaselineMissing(
            f"the Comparison's baseline, {baseline}, is not among the retrievers scored ({', '.join(scored)}); add"
            f" `--retriever {baseline}`, or name another baseline in [comparison] of the retrieval config"
        )


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    @property
    def holds_zero(self) -> bool:
        return self.low <= 0 <= self.high


@dataclass(frozen=True)
class Compared:
    """One metric of one retriever against its baseline, over the same questions and draws."""

    mean: float
    interval: Interval
    difference: float  # the retriever's mean less the baseline's
    difference_interval: Interval
    wins: int
    ties: int
    losses: int

    @property
    def within_noise(self) -> bool:
        return self.difference_interval.holds_zero


def draws(questions: int, resamples: int, seed: int) -> np.ndarray:
    """`resamples` rows of `questions` question positions, drawn with replacement: the draws every retriever shares."""
    return np.random.default_rng(seed).integers(0, questions, size=(resamples, questions))


def compare(scored: Sequence[Scored], baseline: Sequence[Scored], measure: Callable[[Scored], float], drawn: np.ndarray) -> Compared:
    """The retriever's queries against the baseline's, on one per-question measure (harness.recall, say)."""
    ours, theirs = all_answerable(scored), all_answerable(baseline)
    if [s.question.id for s in ours] != [s.question.id for s in theirs]:
        raise ValueError("a retriever and its baseline were scored on different questions")
    values = np.array([measure(s) for s in ours])
    differences = values - np.array([measure(s) for s in theirs])
    return Compared(
        mean=float(values.mean()),
        interval=_interval(values, drawn),
        difference=float(differences.mean()),
        difference_interval=_interval(differences, drawn),
        wins=int((differences > 0).sum()),
        ties=int((differences == 0).sum()),
        losses=int((differences < 0).sum()),
    )


def _interval(values: np.ndarray, drawn: np.ndarray) -> Interval:
    tail = (1 - CONFIDENCE) / 2 * 100
    low, high = np.percentile(values[drawn].mean(axis=1), [tail, 100 - tail])
    return Interval(float(low), float(high))
