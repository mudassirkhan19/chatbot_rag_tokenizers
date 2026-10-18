"""The evaluation config file: the Passage matching rule that `eval-check` and `evaluate` share (ADR 0041)."""

import tomllib
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table

from .matching import MatchingRule

DEFAULT_PATH = Path("config/evaluation.toml")


def load_matching_rule(path: Path = DEFAULT_PATH) -> MatchingRule:
    raw = tomllib.loads(path.read_text())
    rule = MatchingRule(**read_table(raw, "matching", {"threshold": float, "edge_min_words": int}, path))
    if not 0 < rule.threshold <= 1:
        raise ConfigError(f"[matching] threshold {rule.threshold} is not above 0 and at most 1")
    if rule.edge_min_words < 2:
        raise ConfigError(f"[matching] edge_min_words {rule.edge_min_words} is less than 2")
    return rule
