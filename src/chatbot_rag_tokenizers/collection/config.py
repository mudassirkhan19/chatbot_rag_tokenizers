"""The scope config file: scope topics, keyword queries and Seeds tagged by topic, the rule pre-filter and the judge."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError

SOURCES = {"arxiv", "semantic-scholar", "openalex"}


@dataclass(frozen=True)
class KeywordQuery:
    id: str
    source: str
    topic: str
    query: str

    @property
    def discovery_channel(self) -> str:
        return f"{self.source}:{self.id}"


# Discovery channel prefixes for a Seed's own record, its references and its citations.
SEED_PREFIX, REFERENCES_PREFIX, CITATIONS_PREFIX = "seed:", "seed-references:", "seed-citations:"


def is_keyword_channel(channel: str) -> bool:
    return not channel.startswith((SEED_PREFIX, REFERENCES_PREFIX, CITATIONS_PREFIX))


def is_citation_channel(channel: str) -> bool:
    """A citation hop from a Seed; the Seed's own record is not one."""
    return channel.startswith((REFERENCES_PREFIX, CITATIONS_PREFIX))


@dataclass(frozen=True)
class Seed:
    id: str
    paper: str  # a Semantic Scholar paper id, e.g. "ARXIV:1508.07909" or "DOI:10.1109/..."
    topic: str
    reason: str  # one line on why this Work is a starting point

    @property
    def discovery_channel(self) -> str:
        return f"{SEED_PREFIX}{self.id}"

    @property
    def references_channel(self) -> str:
        return f"{REFERENCES_PREFIX}{self.id}"

    @property
    def citations_channel(self) -> str:
        return f"{CITATIONS_PREFIX}{self.id}"


@dataclass(frozen=True)
class ExclusionPattern:
    name: str
    pattern: str


@dataclass(frozen=True)
class JudgeConfig:
    model: str  # Hugging Face model id
    revision: str  # pinned commit of the model repository
    threshold: float  # P("Yes") at or above this includes a Candidate
    prompt: str  # with {title} and {abstract} placeholders


@dataclass(frozen=True)
class AuditModel:
    model: str  # Hugging Face model id
    revision: str  # pinned commit of the model repository


@dataclass(frozen=True)
class ScopeConfig:
    topics: dict[str, str]
    queries: list[KeywordQuery]
    seeds: list[Seed]
    required_terms: list[str]
    keep_if_title: list[str]
    exclusions: list[ExclusionPattern]
    arxiv_page_size: int
    s2_fields_of_study: str  # comma-separated; empty means no filter
    disabled_sources: set[str]  # sources whose queries are skipped (`enabled = false`)
    judge: JudgeConfig
    audit_models: list[AuditModel]  # judge models compared on the Audit set, with the [judge] prompt

    def enabled_queries(self) -> list[KeywordQuery]:
        return [query for query in self.queries if query.source not in self.disabled_sources]


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

    seeds = [Seed(**seed) for seed in raw.get("seeds", [])]
    seen.clear()
    for seed in seeds:
        if seed.id in seen:
            raise ConfigError(f"duplicate seed id {seed.id!r}")
        seen.add(seed.id)
        if seed.topic not in topics:
            raise ConfigError(f"seed {seed.id!r} is tagged with unknown topic {seed.topic!r}")
        if not seed.reason.strip():
            raise ConfigError(f"seed {seed.id!r} has no reason")

    if "judge" not in raw:
        raise ConfigError("missing [judge] section")
    judge = JudgeConfig(**raw["judge"])
    if not 0.0 <= judge.threshold <= 1.0:
        raise ConfigError(f"judge threshold {judge.threshold} is not between 0 and 1")
    for placeholder in ("{title}", "{abstract}"):
        if placeholder not in judge.prompt:
            raise ConfigError(f"judge prompt has no {placeholder} placeholder")

    # Without [[audit.models]], the Audit set measures the configured judge alone.
    audit_models = [AuditModel(**model) for model in raw.get("audit", {}).get("models", [])]
    if not audit_models:
        audit_models = [AuditModel(judge.model, judge.revision)]

    rules = raw.get("rules", {})
    sources = raw.get("sources", {})
    for name in sources:
        if name not in SOURCES:
            raise ConfigError(f"settings for unknown source {name!r} under [sources]")
    return ScopeConfig(
        topics=topics,
        queries=queries,
        seeds=seeds,
        required_terms=list(rules.get("required", [])),
        keep_if_title=list(rules.get("keep_if_title", [])),
        exclusions=[ExclusionPattern(**pattern) for pattern in rules.get("exclude", [])],
        arxiv_page_size=int(sources.get("arxiv", {}).get("page_size", 500)),
        s2_fields_of_study=str(sources.get("semantic-scholar", {}).get("fields_of_study", "")),
        disabled_sources={name for name, settings in sources.items() if not settings.get("enabled", True)},
        judge=judge,
        audit_models=audit_models,
    )
