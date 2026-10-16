"""Stage 1 of the Relevance verdict: a deterministic rule pre-filter.

A Candidate passes when its title matches no exclusion pattern and its title or abstract
matches at least one required term. Exclusions are checked first, so an off-topic paper is
named by the specific pattern that fired rather than by the generic missing-term reason.
Exclusions look at the title only: an off-topic sense of "token" (token merging, KV-cache
eviction, crypto tokens) shows up there, while an on-topic abstract may mention those senses
in passing. They never fire on a title that matches a ``keep_if_title`` term, so a byte-level
paper about token merging stays in. Anything uncertain is left to the LLM judge.
"""

import re
from dataclasses import dataclass

from .config import ScopeConfig
from .editions import Edition

MISSING_REQUIRED_TERM = "missing-required-term"


@dataclass(frozen=True)
class RuleOutcome:
    passed: bool
    pattern: str = ""  # the pattern that fired, when rejected
    reason: str = ""


class RuleFilter:
    def __init__(self, config: ScopeConfig) -> None:
        self._required = [re.compile(term, re.IGNORECASE) for term in config.required_terms]
        self._keep = [re.compile(term, re.IGNORECASE) for term in config.keep_if_title]
        self._exclusions = [(p.name, re.compile(p.pattern, re.IGNORECASE)) for p in config.exclusions]

    def apply(self, edition: Edition) -> RuleOutcome:
        if not any(term.search(edition.title) for term in self._keep):
            for name, pattern in self._exclusions:
                match = pattern.search(edition.title)
                if match:
                    return RuleOutcome(False, name, f"{name}: title matches {match.group(0)!r}")
        text = f"{edition.title}\n{edition.abstract}"
        if not any(term.search(text) for term in self._required):
            return RuleOutcome(False, MISSING_REQUIRED_TERM, f"{MISSING_REQUIRED_TERM}: no tokenization term in title or abstract")
        return RuleOutcome(True)
