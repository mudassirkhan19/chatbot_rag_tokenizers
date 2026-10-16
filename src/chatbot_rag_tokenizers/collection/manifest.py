"""The manifest CSV: one row per Edition, with its Relevance verdict and funnel status."""

import csv
from pathlib import Path

from .editions import Edition
from .rules import RuleOutcome

COLUMNS = [
    "edition_id",
    "edition_kind",
    "title",
    "authors",
    "year",
    "venue",
    "arxiv_comments",
    "journal_ref",
    "source_link",
    "arxiv_id",
    "doi",
    "discovery_channels",
    "rule_outcome",
    "rule_pattern",
    "relevance_verdict",
    "relevance_stage",
    "relevance_reason",
    "licence",
    "funnel_status",
    "work_id",
]


def manifest_row(edition: Edition, outcome: RuleOutcome) -> dict[str, str]:
    return {
        "edition_id": edition.edition_id,
        "edition_kind": edition.edition_kind,
        "title": edition.title,
        "authors": "; ".join(edition.authors),
        "year": edition.year,
        "venue": edition.venue,
        "arxiv_comments": edition.arxiv_comments,
        "journal_ref": edition.journal_ref,
        "source_link": edition.source_link,
        "arxiv_id": edition.arxiv_id,
        "doi": edition.doi,
        "discovery_channels": "|".join(sorted(edition.discovery_channels)),
        "rule_outcome": "pass" if outcome.passed else "reject",
        "rule_pattern": outcome.pattern,
        # Rule passes await the LLM judge, which is a later stage.
        "relevance_verdict": "pending" if outcome.passed else "excluded",
        "relevance_stage": "" if outcome.passed else "rules",
        "relevance_reason": outcome.reason,
        "licence": edition.licence,
        # The furthest funnel stage reached: discovered → relevant → full text → indexed.
        "funnel_status": "discovered",
        "work_id": "",  # filled in by the dedup stage
    }


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["edition_id"]))
