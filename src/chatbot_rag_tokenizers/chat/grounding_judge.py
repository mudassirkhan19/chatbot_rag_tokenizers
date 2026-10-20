"""The decision model as a grounding judge (spec #63, ADR 0075): `chat-eval --judge` measured against the hand labels.

The pinned decision model of the scope judge, Tev1 4B, is asked the `[chat.judge]` question for each claim of a
sampled reply and each Chunk the claim cites: does this Chunk support this claim? A claim is a sentence that cites a
Chunk (`Answer.claims`), and a Chunk is its context header and text, as the answer model was shown it. Its P(yes)
for every claim and Chunk is averaged per Turn, and a Turn whose mean is at least the threshold is grounded by the
judge. A Turn with no cited claim has no score and is not grounded, as the automatic check does not ground an
uncited answer. The judge scores only the rows the developer labelled, so its agreement with them is reported
beside the automatic check's rather than trusted.

`load_grounding_judge` makes the real one on the local Ollama, checked against its pin; the tests put a scripted
fake in its place, as they do the answer model.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..ollama import OLLAMA_URL, Ollama, OllamaModelError, split_pin
from ..parsing.chunker import Chunk
from .config import GroundingJudgeConfig
from .grounding_check import Checked


class JudgeUnavailable(RuntimeError):
    """The decision model can't judge now: Ollama is stopped, runs another version or lacks the pinned model."""


class GroundingJudge(Protocol):
    def support(self, claim: str, chunk: Chunk) -> float:
        """P(yes) that the Chunk supports the claim."""
        ...


def pin(settings: GroundingJudgeConfig) -> str:
    """The pinned decision model as the report names it, from its revision, as the answer model is named."""
    digest, version = split_pin(settings.revision)
    return f"{settings.model}@{digest[:12]} on Ollama {version}"


def load_grounding_judge(settings: GroundingJudgeConfig) -> GroundingJudge:
    return OllamaGroundingJudge(settings)


class OllamaGroundingJudge:
    """The pinned decision model on the local Ollama, checked against its pin when made."""

    def __init__(self, settings: GroundingJudgeConfig, ollama: Ollama | None = None) -> None:
        self.settings = settings
        self.ollama = ollama or Ollama()
        with _named_failures():
            self.ollama.check_pin(settings.model, settings.revision)

    def support(self, claim: str, chunk: Chunk) -> float:
        settings = self.settings
        state = settings.state.format(claim=claim, chunk=f"{chunk.header}\n{chunk.text}")
        with _named_failures():
            return self.ollama.decide(settings.model, state, "supported", settings.instructions, settings.true, settings.false)


@dataclass(frozen=True)
class Judged:
    """A labelled row of the sample, scored by the judge."""

    row: Checked
    pairs: int  # the claims and Chunks judged: each claim once for each Chunk it cites
    score: float | None  # the mean P(yes) over them, or None with no cited claim
    verdict: str  # grounded or not grounded


def judge_sample(checked: Sequence[Checked], judge: GroundingJudge, threshold: float) -> list[Judged]:
    """Each row's claims judged against the Chunks they cite. Raises JudgeUnavailable."""
    judged = []
    for row in checked:
        scores = [judge.support(claim, row.retrieved[number - 1]) for claim, numbers in row.answer.claims for number in numbers]
        score = sum(scores) / len(scores) if scores else None
        judged.append(Judged(row, len(scores), score, "grounded" if score is not None and score >= threshold else "not grounded"))
    return judged


@contextmanager
def _named_failures() -> Iterator[None]:
    """Turns Ollama's failures into JudgeUnavailable, saying what to do."""
    try:
        yield
    except httpx.TransportError as error:
        raise JudgeUnavailable(f"Ollama is not answering at {OLLAMA_URL}. Start the Ollama app or run `ollama serve`, then judge again.") from error
    except OllamaModelError as error:
        raise JudgeUnavailable(f"the grounding judge is not ready: {error}. `just init` checks and pulls the pinned judge.") from error
    except httpx.HTTPStatusError as error:
        raise JudgeUnavailable(f"Ollama refused the request: {error.response.status_code} {error.response.text}") from error
