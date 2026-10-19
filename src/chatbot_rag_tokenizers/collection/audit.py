"""The Audit set: a stratified, hand-labelled sample of Candidates used to measure the Relevance verdict.

`export` draws the sample from a collection run: an even share from each stratum (rule rejects,
judge rejects, judge accepts and, before the judge has run, rule passes still pending), capped
by the stratum's size. Each row records the size of the stratum it was drawn from, so the report
can weight it back to the whole population. Its draft label and reason are the pipeline's own
verdict, copied into `label` and `reason` as a starting point; the draft columns are kept so the
report can count the changes, and `labelled_by` records who set each label (ADR 0020).

`report` measures precision, recall and F1 on the labelled rows for the rule stage alone and
for rules plus each configured judge model, across thresholds. Each row is weighted by its
stratum's size over the labelled rows from that stratum, so the figures estimate the whole
population of Candidates rather than the sample's even shares. The rules are re-applied to each
row's title and abstract, so a rule change shows up without a new export. Judge verdicts for the
Audit set are kept apart from the collection's verdict cache, one per model, revision and prompt,
with the seconds each took to score.
"""

import csv
import json
import random
import sys
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from . import judge
from .config import AuditModel, JudgeConfig, ScopeConfig
from .editions import Edition
from ..ollama import split_pin
from .judge import question_hash
from .manifest import judge_includes
from .pipeline import SAVE_VERDICTS_EVERY, Assessed, assess
from .rules import RuleFilter

STRATA = ("rules-rejected", "judge-excluded", "judge-included", "pending")
COLUMNS = [
    "edition_id",
    "stratum",
    "stratum_size",
    "title",
    "abstract",
    "source_link",
    "draft_label",
    "draft_reason",
    "label",
    "reason",
    "labelled_by",  # who set the label: draft (the pipeline's verdict), agent or developer
    "review_note",  # why the row was flagged for the developer to check, if it was
]
DEFAULT_THRESHOLDS = [round(0.1 * step, 1) for step in range(1, 10)]


def _stratum(row: dict[str, str]) -> str:
    if row["relevance_stage"] == "rules":
        return "rules-rejected"
    if row["relevance_verdict"] == "pending":
        return "pending"
    return f"judge-{row['relevance_verdict']}"


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """Share ``total`` out one at a time across the strata, in order, skipping those already taken in full."""
    taken = dict.fromkeys(sizes, 0)
    while sum(taken.values()) < total:
        open_strata = [s for s in sizes if taken[s] < sizes[s]]
        if not open_strata:
            break
        for stratum in open_strata[: total - sum(taken.values())]:
            taken[stratum] += 1
    return taken


def sample(assessed: list[Assessed], threshold: float, size: int, seed: int) -> list[dict[str, str]]:
    by_stratum: dict[str, list[tuple[Assessed, dict[str, str]]]] = {stratum: [] for stratum in STRATA}
    for candidate in sorted(assessed, key=lambda c: c.edition.edition_id):
        row = candidate.manifest_row(threshold)
        by_stratum[_stratum(row)].append((candidate, row))
    sizes = {stratum: len(members) for stratum, members in by_stratum.items() if members}
    rng = random.Random(seed)
    rows = []
    for stratum, count in allocate(sizes, size).items():
        for candidate, row in rng.sample(by_stratum[stratum], count):
            label = {"included": "yes", "excluded": "no"}.get(row["relevance_verdict"], "")
            rows.append(
                {
                    "edition_id": candidate.edition.edition_id,
                    "stratum": stratum,
                    "stratum_size": str(sizes[stratum]),
                    "title": candidate.edition.title,
                    "abstract": candidate.edition.abstract,
                    "source_link": candidate.edition.source_link,
                    "draft_label": label,
                    "draft_reason": row["relevance_reason"],
                    "label": label,
                    "reason": row["relevance_reason"],
                    "labelled_by": "draft",
                    "review_note": "",
                }
            )
    return sorted(rows, key=lambda row: (STRATA.index(row["stratum"]), row["edition_id"]))


def export(config: ScopeConfig, snapshot_dir: Path, output: Path, size: int, seed: int, force: bool = False) -> None:
    """Write a stratified sample of Candidates to ``output`` for labelling. Never loads the judge model."""
    if output.exists() and not force:
        raise SystemExit(f"audit: {output} already exists and may hold corrected labels; pass --force to replace it")
    assessed = assess(config, snapshot_dir, run_judge=False)
    rows = sample(assessed, config.judge.threshold, size, seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"audit: wrote {len(rows)} Candidates to {output}", file=sys.stderr)
    counts = Counter(row["stratum"] for row in rows)
    sizes = {row["stratum"]: row["stratum_size"] for row in rows}
    for stratum in STRATA:
        if counts[stratum]:
            print(f"  {stratum}: {counts[stratum]} of {sizes[stratum]}", file=sys.stderr)


@dataclass(frozen=True)
class AuditVerdict:
    edition_id: str
    model: str
    revision: str
    prompt_hash: str
    p_yes: float
    seconds: float  # time to score this Candidate, not counting loading the model

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.edition_id, self.model, self.revision, self.prompt_hash)


class AuditVerdicts:
    """Judge verdicts for the Audit set: one JSON line per Edition, model, revision and prompt hash, sorted."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._verdicts: dict[tuple[str, str, str, str], AuditVerdict] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    verdict = AuditVerdict(**json.loads(line))
                    self._verdicts[verdict.key] = verdict

    def get(self, edition_id: str, judge_config: JudgeConfig) -> AuditVerdict | None:
        return self._verdicts.get((edition_id, judge_config.model, judge_config.revision, question_hash(judge_config)))

    def put(self, verdict: AuditVerdict) -> None:
        self._verdicts[verdict.key] = verdict

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(asdict(self._verdicts[key]), sort_keys=True, separators=(",", ":")) for key in sorted(self._verdicts)
        ]
        self.path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


@dataclass(frozen=True)
class Labelled:
    """One labelled row of the Audit set, with the number of Candidates it stands for."""

    edition: Edition
    stratum: str
    weight: float
    relevant: bool
    passes_rules: bool


def read_audit_set(path: Path, config: ScopeConfig) -> tuple[list[Labelled], list[dict[str, str]]]:
    """The labelled rows, weighted and re-checked against the current rules, and every row as read."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    labelled = [row for row in rows if row["label"] in ("yes", "no")]
    per_stratum = Counter(row["stratum"] for row in labelled)
    rules = RuleFilter(config)
    result = []
    for row in labelled:
        edition = Edition(row["edition_id"], "", row["title"], row["abstract"], [], "")
        weight = int(row["stratum_size"]) / per_stratum[row["stratum"]]
        result.append(Labelled(edition, row["stratum"], weight, row["label"] == "yes", rules.apply(edition).passed))
    return result, rows


def judge_config(config: ScopeConfig, model: AuditModel) -> JudgeConfig:
    """The [judge] settings, prompt and decision question with ``model`` in place of the judge's own."""
    return replace(config.judge, model=model.model, revision=model.revision, backend=model.backend)


def score_missing(config: ScopeConfig, model: AuditModel, editions: list[Edition], verdicts: AuditVerdicts) -> None:
    """Score the Editions that have no verdict from ``model``, timing each one."""
    model_config = judge_config(config, model)
    missing = [e for e in editions if verdicts.get(e.edition_id, model_config) is None]
    if not missing:
        return
    scorer = judge.load_judge(model_config)
    current_question = question_hash(model_config)
    for done, edition in enumerate(missing, 1):
        start = time.perf_counter()
        [p_yes] = scorer.score([edition])
        seconds = round(time.perf_counter() - start, 3)
        verdicts.put(AuditVerdict(edition.edition_id, model.model, model.revision, current_question, p_yes, seconds))
        if done % SAVE_VERDICTS_EVERY == 0 or done == len(missing):
            verdicts.save()
            print(f"  audit: {model.model} scored {done}/{len(missing)}", file=sys.stderr)


def metrics(rows: Iterable[tuple[Labelled, bool]]) -> tuple[float | None, float | None, float | None]:
    """Weighted precision, recall and F1 over (row, predicted relevant) pairs; None where undefined."""
    true_positive = predicted = relevant = 0.0
    for row, prediction in rows:
        predicted += row.weight * prediction
        relevant += row.weight * row.relevant
        true_positive += row.weight * (prediction and row.relevant)
    precision = true_positive / predicted if predicted else None
    recall = true_positive / relevant if relevant else None
    f1 = None
    if precision is not None and recall is not None and precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _cell(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _model_section(
    config: ScopeConfig,
    model: AuditModel,
    rows: list[Labelled],
    verdicts: AuditVerdicts,
    thresholds: list[float],
    rule_pass_population: int,
) -> tuple[list[str], str]:
    """The model's section of the report, and its row in the comparison: its best threshold and run time."""
    lines = [f"## Rules and judge: {model.model}@{model.revision}", ""]
    digest, runtime = split_pin(model.revision)
    name = f"{model.model}@{digest[:8]}" + (f"@{runtime}" if runtime else "")
    passes = [row for row in rows if row.passes_rules]
    model_config = judge_config(config, model)
    found = {row.edition.edition_id: verdicts.get(row.edition.edition_id, model_config) for row in passes}
    missing = sum(verdict is None for verdict in found.values())
    if missing:
        return lines + [
            f"No verdicts for {missing} of the {len(passes)} rule passes. Run `audit report` without --no-judge to score them.",
            "",
        ], f"| {name} | no verdicts | | | | | |"
    scored = [verdict for verdict in found.values() if verdict is not None]
    per_candidate = sum(verdict.seconds for verdict in scored) / len(scored) if scored else 0.0
    minutes = per_candidate * rule_pass_population / 60
    lines += [
        f"Scoring took {per_candidate:.2f} s per Candidate over {len(scored)} rule passes:"
        f" about {minutes:.1f} min for the {rule_pass_population} rule passes"
        " in the population, plus loading the model.",
        "",
        "| threshold | precision | recall | F1 |",
        "|---|---|---|---|",
    ]
    best: tuple[float, float, float | None, float | None] | None = None
    for threshold in thresholds:

        def included(row: Labelled) -> bool:
            verdict = found.get(row.edition.edition_id)
            return verdict is not None and judge_includes(verdict.p_yes, threshold)

        precision, recall, f1 = metrics((row, included(row)) for row in rows)
        lines.append(f"| {threshold:g} | {_cell(precision)} | {_cell(recall)} | {_cell(f1)} |")
        if f1 is not None and (best is None or f1 > best[0]):
            best = (f1, threshold, precision, recall)
    lines.append("")
    if best is None:
        return lines, f"| {name} | n/a | | | | {per_candidate:.2f} | {minutes:.1f} |"
    f1, threshold, precision, recall = best
    lines += [f"Best F1 {f1:.3f} at threshold {threshold:g}.", ""]
    row = f"| {name} | {threshold:g} | {_cell(precision)} | {_cell(recall)} | {f1:.3f} | {per_candidate:.2f} | {minutes:.1f} |"
    return lines, row


def report(
    config: ScopeConfig,
    audit_set: Path,
    verdicts_path: Path,
    output: Path,
    thresholds: list[float] | None = None,
    run_judge: bool = True,
) -> None:
    """Write the Audit report to ``output``, first scoring any missing verdicts unless ``run_judge`` is off."""
    rows, all_rows = read_audit_set(audit_set, config)
    if thresholds is None:
        thresholds = sorted({*DEFAULT_THRESHOLDS, config.judge.threshold})
    verdicts = AuditVerdicts(verdicts_path)
    if run_judge:
        passes = [row.edition for row in rows if row.passes_rules]
        for model in config.audit_models:
            score_missing(config, model, passes, verdicts)

    sizes = {row["stratum"]: int(row["stratum_size"]) for row in all_rows}
    rule_pass_population = sum(size for stratum, size in sizes.items() if stratum != "rules-rejected")
    changed = sum(row["label"] != row["draft_label"] for row in all_rows)
    covered = {row.stratum for row in rows}
    lines = [
        "# Audit report",
        "",
        f"{len(rows)} labelled Candidates ({changed} labels changed from the draft, {len(all_rows) - len(rows)} unlabelled)"
        f" from `{audit_set}`. Each is weighted by its stratum's size over the labelled rows from it, so"
        f" the figures estimate precision and recall over the {sum(sizes[s] for s in covered)} Candidates"
        " in the strata with labels.",
        "",
    ]
    if uncovered := [s for s in STRATA if s in sizes and s not in covered]:
        lines += [f"No labels yet in {', '.join(uncovered)}: those Candidates are left out of every figure.", ""]
    lines += [
        "| stratum | Candidates | labelled | labelled yes |",
        "|---|---|---|---|",
    ]
    for stratum in STRATA:
        if stratum in sizes:
            members = [row for row in rows if row.stratum == stratum]
            lines.append(f"| {stratum} | {sizes[stratum]} | {len(members)} | {sum(row.relevant for row in members)} |")
    precision, recall, f1 = metrics((row, row.passes_rules) for row in rows)
    lines += [
        "",
        "## Rule stage alone",
        "",
        "A Candidate counts as relevant when it passes the rules in the current config."
        " Its recall is the most the judge can reach.",
        "",
        "| precision | recall | F1 |",
        "|---|---|---|",
        f"| {_cell(precision)} | {_cell(recall)} | {_cell(f1)} |",
        "",
    ]
    sections = [_model_section(config, model, rows, verdicts, thresholds, rule_pass_population) for model in config.audit_models]
    if sections:
        lines += [
            "## Model comparison",
            "",
            "Each model at the threshold with its best F1, and its run time over every rule pass in the population.",
            "",
            "| model | threshold | precision | recall | F1 | s per Candidate | full run (min) |",
            "|---|---|---|---|---|---|---|",
            *(row for _, row in sections),
            "",
        ]
    for section, _ in sections:
        lines += section
    lines.append("The best threshold is chosen on this same Audit set, so its F1 is an optimistic estimate.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"audit: wrote {output}", file=sys.stderr)
