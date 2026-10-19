"""The grounding check (spec #63, ADR 0059): whether an answer is Grounded, decided from the Turn alone.

An answer is Grounded when it cites at least one retrieved Chunk, every marker in it names a Chunk retrieved for
its Turn, and every number in it appears in a cited Chunk. Numbers are compared as the Passage matcher cuts
words (ADR 0041): after unicode, case and hyphenation are normalised and citations dropped, a word that starts
with a digit is a number ("50k", "0.1", "32,000", kept whole). A name holding a digit, such as "ByT5" or "F1", is
not: it is a name, and the matcher's rule, any digit, would fail an answer for naming a model its Chunk spells
"F 1". A cited Chunk is its context header
and its text, as the answer model was shown it. An uncited answer is not Grounded, however few numbers it has.
An Abstention is neither Grounded nor not: it is counted in the abstention rates instead.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from ..evaluation.matching import words
from ..parsing.chunker import Chunk
from .answer import Answer


@dataclass(frozen=True)
class Grounding:
    cited: bool  # the answer cites at least one retrieved Chunk
    invalid: tuple[int, ...]  # markers naming no retrieved Chunk
    missing: tuple[str, ...]  # the answer's numbers in no cited Chunk, each once, in the order written

    @property
    def grounded(self) -> bool:
        return self.cited and not self.invalid and not self.missing


def ground(answer: Answer, retrieved: Sequence[Chunk]) -> Grounding | None:
    """The answer's Grounding, or None for an Abstention."""
    if answer.abstention:
        return None
    cited = {word for number in answer.cited for word in words(f"{retrieved[number - 1].header}\n{retrieved[number - 1].text}")}
    numbers = dict.fromkeys(word for word in words(answer.text) if word[0].isdigit())
    return Grounding(bool(answer.cited), tuple(answer.invalid), tuple(number for number in numbers if number not in cited))
