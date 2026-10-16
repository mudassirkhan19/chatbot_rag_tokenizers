"""Stage 1 of the Relevance verdict: a deterministic rule pre-filter.

A Candidate passes when its title or abstract matches at least one required term and its
title matches no exclusion pattern. Exclusions look at the title only: an off-topic sense of
"token" (token merging, KV-cache eviction, crypto tokens) shows up there, while an on-topic
abstract may mention those senses in passing. Exclusions also never fire on a title that
matches a ``keep_if_title`` term, so a byte-level paper about token merging stays in.
Anything uncertain is left to the LLM judge.
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

    def judge(self, edition: Edition) -> RuleOutcome:
        text = f"{edition.title}\n{edition.abstract}"
        if not any(term.search(text) for term in self._required):
            return RuleOutcome(False, MISSING_REQUIRED_TERM, f"{MISSING_REQUIRED_TERM}: no tokenization term in title or abstract")
        if any(term.search(edition.title) for term in self._keep):
            return RuleOutcome(True)
        for name, pattern in self._exclusions:
            match = pattern.search(edition.title)
            if match:
                return RuleOutcome(False, name, f"{name}: title matches {match.group(0)!r}")
        return RuleOutcome(True)
