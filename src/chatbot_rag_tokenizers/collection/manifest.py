"""The manifest CSV: one row per Edition, with its Relevance verdict and funnel status."""

import csv
from pathlib import Path

from .editions import Edition
from .judge import JudgeVerdict
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
    "judge_probability",
    "judge_threshold",
    "judge_model",
    "relevance_verdict",
    "relevance_stage",
    "relevance_reason",
    "licence",
    "versions",
    "funnel_status",
    "work_id",
]


def _relevance(outcome: RuleOutcome, verdict: JudgeVerdict | None, threshold: float) -> dict[str, str]:
    """The Relevance verdict columns. The threshold is applied here, so changing it never re-scores."""
    if not outcome.passed:
        return {"relevance_verdict": "excluded", "relevance_stage": "rules", "relevance_reason": outcome.reason}
    if verdict is None:
        return {
            "relevance_verdict": "pending",
            "relevance_stage": "",
            "relevance_reason": "no judge verdict for the configured model, revision and prompt",
        }
    # Compare the probability as the manifest shows it, so the reason never contradicts itself.
    probability = f"{verdict.p_yes:.4f}"
    included = float(probability) >= threshold
    comparison = ">=" if included else "<"
    return {
        "relevance_verdict": "included" if included else "excluded",
        "relevance_stage": "judge",
        "relevance_reason": f"judge: P(Yes) {probability} {comparison} threshold {threshold:g}",
        "judge_probability": probability,
        "judge_threshold": f"{threshold:g}",
        "judge_model": f"{verdict.model}@{verdict.revision}",
    }


def manifest_row(
    edition: Edition, outcome: RuleOutcome, verdict: JudgeVerdict | None, threshold: float
) -> dict[str, str]:
    relevance = _relevance(outcome, verdict, threshold)
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
        "judge_probability": relevance.get("judge_probability", ""),
        "judge_threshold": relevance.get("judge_threshold", ""),
        "judge_model": relevance.get("judge_model", ""),
        "relevance_verdict": relevance["relevance_verdict"],
        "relevance_stage": relevance["relevance_stage"],
        "relevance_reason": relevance["relevance_reason"],
        "licence": edition.licence,
        "versions": "|".join(f"{label} {submitted}" for label, submitted in edition.versions),
        # The furthest funnel stage reached: discovered → relevant → full text → indexed.
        "funnel_status": "relevant" if relevance["relevance_verdict"] == "included" else "discovered",
        "work_id": "",  # filled in by the dedup stage
    }


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["edition_id"]))
