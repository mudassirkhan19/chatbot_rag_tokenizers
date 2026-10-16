"""The common Edition record that every source's results are normalised into."""

from dataclasses import dataclass, field


@dataclass
class Edition:
    edition_id: str  # pinned, e.g. "2106.12345v3"
    edition_kind: str  # "arxiv-preprint" or "venue"
    title: str
    abstract: str
    authors: list[str]
    year: str
    venue: str = ""
    arxiv_comments: str = ""
    journal_ref: str = ""
    source_link: str = ""
    arxiv_id: str = ""
    doi: str = ""
    licence: str = "unknown"
    discovery_channels: set[str] = field(default_factory=set)
