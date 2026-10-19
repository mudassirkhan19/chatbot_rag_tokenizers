"""The funnel and channel report: counts at each stage and per Discovery channel and source, built
from the manifest rows alone, so `collect`, `fetch` and `index` write the same report from the same manifest.

`summarise` prints it to stderr as plain lines and `write` writes it as Markdown for the write-up.
"""

import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import works
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
    not_a_paper: int
    borrowed_file: int  # included by the judge, then excluded: the Edition's only file belongs to another one
    judge_included: int
    judge_excluded: int
    pending: int
    fulltext: int  # every pinned file fetched, indexed or not
    indexed: int
    not_indexed: list[str]  # the Editions with full text that aren't indexed, sorted
    no_fulltext: int
    to_fetch: int


def funnel(rows: list[Row]) -> Funnel:
    rejects = Counter(row["rule_pattern"] for row in rows if row["rule_outcome"] == "reject")
    stages = Counter(row["relevance_stage"] for row in rows)
    # Stages that exclude a rule pass apart from the judge: before it, or, for a borrowed file, after it.
    not_judged = {"withdrawn", "not a paper", "borrowed file"}
    judged = Counter(
        row["relevance_verdict"] for row in rows if row["rule_outcome"] == "pass" and row["relevance_stage"] not in not_judged
    )
    included = [row for row in rows if row["relevance_verdict"] == "included"]
    status = Counter(row["funnel_status"] for row in included)
    not_indexed = sorted(row["edition_id"] for row in included if row["funnel_status"] == "full text")
    return Funnel(
        len(rows),
        Counter(dict(sorted(rejects.items()))),
        stages["withdrawn"],
        stages["not a paper"],
        stages["borrowed file"],
        judged["included"],
        judged["excluded"],
        judged["pending"],
        status["full text"] + status["indexed"],
        status["indexed"],
        not_indexed,
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
        f"fulltext: {counts.fulltext} with full text ({counts.indexed} indexed), {counts.no_fulltext} with no open PDF,"
        f" {counts.to_fetch} still to fetch",
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
    print(f"not a paper: {counts.not_a_paper} excluded on their source metadata", file=sys.stderr)
    print(f"borrowed file: {counts.borrowed_file} excluded, its only file belongs to another Edition", file=sys.stderr)
    print(
        f"judge: {counts.judge_included} included, {counts.judge_excluded} excluded, {counts.pending} pending"
        f" (threshold {threshold:g})",
        file=sys.stderr,
    )
    summarise_fulltext(rows)
    grouping = works.group(rows)
    suspected = len(grouping.suspected)
    print(
        f"works: {len(grouping.works)} Works from {_included(rows)} included Editions, {_surveys(grouping)} Surveys,"
        f" {suspected} Suspected {'pair' if suspected == 1 else 'pairs'}",
        file=sys.stderr,
    )


def _included(rows: list[Row]) -> int:
    return sum(row["relevance_verdict"] == "included" for row in rows)


def _surveys(grouping: works.Grouping) -> int:
    return sum(work.survey for work in grouping.works)


def _cell(text: str) -> str:
    """Text for a Markdown table cell."""
    return text.replace("|", "\\|")


def _works(rows: list[Row]) -> list[str]:
    """The Works section: what Work grouping made of the included Editions, and the Suspected pairs it declined."""
    grouping = works.group(rows)
    joined = Counter(work.signal for work in grouping.works)
    canonical = Counter(work.canonical["edition_kind"] for work in grouping.works)
    lines = [
        "## Works",
        "",
        "Included Editions are one Work when they share an identifier (arXiv id, DOI, ACL ID), a file's bytes, or a"
        " title and first-author surname. A Work of several Editions is counted by the weakest signal it needed.",
        "",
        "| | Editions or Works |",
        "| --- | ---: |",
        f"| Included Editions | {_included(rows)} |",
        f"| Works | {len(grouping.works)} |",
        *(f"| Works of several Editions, joined by {signal} | {joined[signal]} |" for signal, _ in works.SIGNALS),
        f"| Canonical Edition is a venue Edition | {canonical['venue']} |",
        f"| Canonical Edition is a preprint | {canonical['arxiv-preprint']} |",
        f"| Surveys | {_surveys(grouping)} |",
        f"| Suspected pairs | {len(grouping.suspected)} |",
        "",
        "### Suspected pairs",
        "",
    ]
    if not grouping.suspected:
        return [*lines, "No two Works share a title.", ""]

    def side(editions: list[Row]) -> str:
        ids = ", ".join(f"`{row['edition_id']}`" for row in editions)
        return f"{ids} | {_cell(editions[0]['title'])} | {_cell(works.first_author(editions[0]))}"

    return [
        *lines,
        "Works with the same title but different first authors. They are never joined.",
        "",
        "| Editions | Title | First author | Editions | Title | First author |",
        "| --- | --- | --- | --- | --- | --- |",
        *(f"| {side(pair.first)} | {side(pair.second)} |" for pair in grouping.suspected),
        "",
    ]


def _found_table(heading: str, found: dict[str, Found]) -> list[str]:
    lines = [
        f"| {heading} | Editions | Included | Found by no other | of those: pass the rules | included | pending |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, counts in found.items():
        cells = [counts.editions, counts.included, counts.alone, counts.alone_passed, counts.alone_included, counts.alone_pending]
        lines.append(f"| {name} | {' | '.join(str(cell) for cell in cells)} |")
    return lines


def _not_indexed(editions: list[str]) -> list[str]:
    """The Editions with full text that aren't indexed: a file failed the parse quality gate (see the parse report),
    or `index` hasn't run since they were fetched."""
    if not editions:
        return []
    return [
        "## With full text, not indexed",
        "",
        "A file failed the parse quality gate (see the parse report), or `index` hasn't run since the Edition was fetched.",
        "",
        *(f"- `{edition}`" for edition in editions),
        "",
    ]


def render(rows: list[Row]) -> str:
    """The report as Markdown."""
    counts = funnel(rows)
    added = expansion(rows)
    lines = [
        "# Corpus funnel and channel report",
        "",
        f"Written by `collect`, `fetch` and `index` from the manifest: {_judge(rows)}. One row per Edition.",
        "",
        "## Funnel",
        "",
        "| Stage | Editions |",
        "| --- | ---: |",
        f"| Discovered | {counts.discovered} |",
        f"| Rejected by the rules | {counts.rule_rejects.total()} |",
        f"| Withdrawn from arXiv | {counts.withdrawn} |",
        f"| Not a paper | {counts.not_a_paper} |",
        f"| Rejected by the judge | {counts.judge_excluded} |",
        f"| File belongs to another Edition | {counts.borrowed_file} |",
        f"| Pending a judge verdict | {counts.pending} |",
        f"| Included | {counts.judge_included} |",
        f"| With full text | {counts.fulltext} |",
        f"| Indexed | {counts.indexed} |",
        f"| With full text, not indexed | {len(counts.not_indexed)} |",
        f"| No open PDF | {counts.no_fulltext} |",
        f"| Still to fetch | {counts.to_fetch} |",
        "",
        *_not_indexed(counts.not_indexed),
        *_works(rows),
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
