"""The scope config file: scope topics, keyword queries tagged by topic, and the rule pre-filter."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

SOURCES = {"arxiv"}


@dataclass(frozen=True)
class KeywordQuery:
    id: str
    source: str
    topic: str
    query: str

    @property
    def discovery_channel(self) -> str:
        return f"{self.source}:{self.id}"


@dataclass(frozen=True)
class ExclusionPattern:
    name: str
    pattern: str


@dataclass(frozen=True)
class ScopeConfig:
    topics: dict[str, str]
    queries: list[KeywordQuery]
    required_terms: list[str]
    keep_if_title: list[str]
    exclusions: list[ExclusionPattern]
    arxiv_page_size: int


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> ScopeConfig:
    raw = tomllib.loads(path.read_text())
    topics = {topic["id"]: topic["description"] for topic in raw.get("topics", [])}
    queries = [KeywordQuery(**query) for query in raw.get("queries", [])]

    seen: set[str] = set()
    for query in queries:
        if query.id in seen:
            raise ConfigError(f"duplicate query id {query.id!r}")
        seen.add(query.id)
        if query.topic not in topics:
            raise ConfigError(f"query {query.id!r} is tagged with unknown topic {query.topic!r}")
        if query.source not in SOURCES:
            raise ConfigError(f"query {query.id!r} uses unsupported source {query.source!r}")

    rules = raw.get("rules", {})
    return ScopeConfig(
        topics=topics,
        queries=queries,
        required_terms=list(rules.get("required", [])),
        keep_if_title=list(rules.get("keep_if_title", [])),
        exclusions=[ExclusionPattern(**pattern) for pattern in rules.get("exclude", [])],
        arxiv_page_size=int(raw.get("sources", {}).get("arxiv", {}).get("page_size", 500)),
    )
