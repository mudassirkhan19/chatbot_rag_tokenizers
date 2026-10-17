"""The funnel and channel report: counts at each stage and per Discovery channel and source, built
from the manifest rows alone, so `collect` and `fetch` write the same report from the same manifest.

`summarise` prints it to stderr as plain lines and `write` writes it as Markdown for the write-up.
"""

import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .config import is_citation_channel, is_keyword_channel

Row = dict[str, str]


@dataclass
class Found:
    """What one Discovery channel or source found. The Editions no other one found are its added
    value, so their rule passes, inclusions and still-pending verdicts are counted too."""

    editions: int = 0
    included: int = 0
    alone: int = 0
    alone_passed: int = 0
    alone_included: int = 0
    alone_pending: int = 0


def _channels(row: Row) -> list[str]:
    return row["discovery_channels"].split("|")


def channel_of(channel: str) -> str:
    """Each Discovery channel on its own."""
    return channel


def source_of(channel: str) -> str:
    """The source a Discovery channel searched; a Seed and its citation hops count as "seeds"."""
    return channel.partition(":")[0] if is_keyword_channel(channel) else "seeds"


def found_by(rows: list[Row], group: Callable[[str], str]) -> dict[str, Found]:
    """``Found`` per group of Discovery channels, sorted by name."""
    found: dict[str, Found] = {}
    for row in rows:
        groups = {group(channel) for channel in _channels(row)}
        for name in groups:
            counts = found.setdefault(name, Found())
            counts.editions += 1
            counts.included += row["relevance_verdict"] == "included"
            if len(groups) == 1:
                counts.alone += 1
                counts.alone_passed += row["rule_outcome"] == "pass"
                counts.alone_included += row["relevance_verdict"] == "included"
                counts.alone_pending += row["relevance_verdict"] == "pending"
    return dict(sorted(found.items()))


@dataclass(frozen=True)
class Expansion:
    """What citation expansion adds beyond keyword search. A Seed's own record counts as neither:
    it was picked by hand, not found."""

    keyword: int
    keyword_included: int
    expanded: int
    expanded_included: int
    expansion_only: int
    expansion_only_included: int


def expansion(rows: list[Row]) -> Expansion:
    keyword, expanded, only = [], [], []
    for row in rows:
        by_keyword = any(is_keyword_channel(channel) for channel in _channels(row))
        if by_keyword:
            keyword.append(row)
        if any(is_citation_channel(channel) for channel in _channels(row)):
            expanded.append(row)
            if not by_keyword:
                only.append(row)

    def included(group: list[Row]) -> int:
        return sum(row["relevance_verdict"] == "included" for row in group)

    return Expansion(len(keyword), included(keyword), len(expanded), included(expanded), len(only), included(only))


@dataclass(frozen=True)
class Funnel:
    discovered: int
    rule_rejects: Counter[str]  # by the pattern that fired
    withdrawn: int
    judge_included: int
    judge_excluded: int
    pending: int
    fulltext: int
    no_fulltext: int
    to_fetch: int


def funnel(rows: list[Row]) -> Funnel:
    rejects = Counter(row["rule_pattern"] for row in rows if row["rule_outcome"] == "reject")
    stages = Counter(row["relevance_stage"] for row in rows)
    judged = Counter(row["relevance_verdict"] for row in rows if row["rule_outcome"] == "pass" and row["relevance_stage"] != "withdrawn")
    status = Counter(row["funnel_status"] for row in rows if row["relevance_verdict"] == "included")
    return Funnel(
        len(rows),
        Counter(dict(sorted(rejects.items()))),
        stages["withdrawn"],
        judged["included"],
        judged["excluded"],
        judged["pending"],
        status["full text"],
        status["no_fulltext"],
        status["relevant"],
    )


def _judge(rows: list[Row]) -> str:
    """The judge models and thresholds the rows were judged with, as the manifest names them."""
    judges = sorted({(row["judge_model"], row["judge_threshold"]) for row in rows if row["judge_model"]})
    return ", ".join(f"judge `{model}` at threshold {threshold}" for model, threshold in judges) or "no judge verdicts"


def summarise_fulltext(rows: list[Row]) -> None:
    counts = funnel(rows)
    print(
        f"fulltext: {counts.fulltext} with full text, {counts.no_fulltext} with no open PDF, {counts.to_fetch} still to fetch",
        file=sys.stderr,
    )


def summarise(rows: list[Row], threshold: float) -> None:
    """Print the report to stderr."""

    def print_found(kind: str, found: dict[str, Found]) -> None:
        for name, counts in found.items():
            print(
                f"  {name}: {counts.editions} Editions, {counts.alone} found by no other {kind}"
                f" ({counts.alone_passed} pass the rules, {counts.alone_included} included, {counts.alone_pending} pending)",
                file=sys.stderr,
            )

    counts = funnel(rows)
    print(f"discover: {counts.discovered} Editions", file=sys.stderr)
    print_found("channel", found_by(rows, channel_of))
    print("discover: by source", file=sys.stderr)
    print_found("source", found_by(rows, source_of))
    added = expansion(rows)
    print(f"  keyword search: {added.keyword} Editions, {added.keyword_included} included", file=sys.stderr)
    print(
        f"  citation expansion: {added.expanded} Editions, {added.expansion_only} found by no keyword query,"
        f" {added.expansion_only_included} of those included",
        file=sys.stderr,
    )
    rejected = counts.rule_rejects.total()
    print(f"rules: {counts.discovered - rejected} passed, {rejected} rejected", file=sys.stderr)
    for pattern, count in counts.rule_rejects.items():
        print(f"  {pattern}: {count}", file=sys.stderr)
    print(f"withdrawn: {counts.withdrawn} excluded, the latest arXiv Version is a withdrawal", file=sys.stderr)
    print(
        f"judge: {counts.judge_included} included, {counts.judge_excluded} excluded, {counts.pending} pending"
        f" (threshold {threshold:g})",
        file=sys.stderr,
    )
    summarise_fulltext(rows)


def _found_table(heading: str, found: dict[str, Found]) -> list[str]:
    lines = [
        f"| {heading} | Editions | Included | Found by no other | of those: pass the rules | included | pending |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, counts in found.items():
        cells = [counts.editions, counts.included, counts.alone, counts.alone_passed, counts.alone_included, counts.alone_pending]
        lines.append(f"| {name} | {' | '.join(str(cell) for cell in cells)} |")
    return lines


def render(rows: list[Row]) -> str:
    """The report as Markdown."""
    counts = funnel(rows)
    added = expansion(rows)
    lines = [
        "# Corpus funnel and channel report",
        "",
        f"Written by `collect` and `fetch` from the manifest: {_judge(rows)}. One row per Edition.",
        "",
        "## Funnel",
        "",
        "| Stage | Editions |",
        "| --- | ---: |",
        f"| Discovered | {counts.discovered} |",
        f"| Rejected by the rules | {counts.rule_rejects.total()} |",
        f"| Withdrawn from arXiv | {counts.withdrawn} |",
        f"| Rejected by the judge | {counts.judge_excluded} |",
        f"| Pending a judge verdict | {counts.pending} |",
        f"| Included | {counts.judge_included} |",
        f"| With full text | {counts.fulltext} |",
        f"| No open PDF | {counts.no_fulltext} |",
        f"| Still to fetch | {counts.to_fetch} |",
        "",
        "## Rule rejections by pattern",
        "",
        "| Pattern | Editions |",
        "| --- | ---: |",
        *(f"| {pattern} | {count} |" for pattern, count in counts.rule_rejects.items()),
        "",
        "## By source",
        "",
        "A Seed and its citation hops count as the source `seeds`.",
        "",
        *_found_table("Source", found_by(rows, source_of)),
        "",
        "## By Discovery channel",
        "",
        *_found_table("Channel", found_by(rows, channel_of)),
        "",
        "## What citation expansion adds",
        "",
        "A Seed's own record counts as neither: it was picked by hand, not found.",
        "",
        "| Found by | Editions | Included | Found by no keyword query | of those: included |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Keyword search | {added.keyword} | {added.keyword_included} | | |",
        f"| Citation expansion | {added.expanded} | {added.expanded_included} | {added.expansion_only} | {added.expansion_only_included} |",
        "",
    ]
    return "\n".join(lines)


def write(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(rows), encoding="utf-8")
