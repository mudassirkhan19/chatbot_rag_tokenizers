"""What crowds the top 5 (ADR 0044): duplicates, Survey restatement and mostly-numeric Chunks, on the raw ranking.

- A duplicate slot holds a Chunk from a Work already ranked higher: another Edition or Version of it, or
  another Chunk of the same file. A Survey's Chunk is never a duplicate.
- A restatement slot holds a Chunk from a Survey, which restates other Works' findings.
- A mostly-numeric slot holds a text Chunk that is mostly numbers (ADR 0035), most often a missed table's cells.

Works come from the Work groups, never from the system being measured. Duplicates and restatement are only
counted for a query whose top 5 are all grouped; any other is left out of their totals, so a missing group
never reads as "no duplicate". The numeric share needs no grouping and counts every query.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .harness import Scored
from .work_groups import WorkGroup


@dataclass(frozen=True)
class Crowding:
    """What crowds one query's top 5."""

    duplicates: int | None  # None when an Edition in the top 5 has no Work group
    restatements: int | None
    numeric: int
    numeric_holding: int  # mostly-numeric slots whose Chunk holds a Passage


def crowding(scored: Scored, groups: Mapping[str, WorkGroup]) -> Crowding:
    numeric = [slot for slot in scored.top if slot.mostly_numeric]
    holding = sum(1 for slot in numeric if slot.holds_passage)
    if any(slot.edition_id not in groups for slot in scored.top):
        return Crowding(None, None, len(numeric), holding)
    works: set[str] = set()
    duplicates = restatements = 0
    for slot in scored.top:
        group = groups[slot.edition_id]
        if group.survey:
            restatements += 1
        elif group.work_id in works:
            duplicates += 1
        else:
            works.add(group.work_id)
    return Crowding(duplicates, restatements, len(numeric), holding)


def ungrouped(scored: Iterable[Scored], groups: Mapping[str, WorkGroup]) -> set[str]:
    """The Editions in these queries' top 5 that have no Work group."""
    return {slot.edition_id for s in scored for slot in s.top if slot.edition_id not in groups}


@dataclass(frozen=True)
class Share:
    slots: int
    of_slots: int
    questions: int  # those with at least one such slot
    of_questions: int


@dataclass(frozen=True)
class Totals:
    duplicate: Share
    restatement: Share
    numeric: Share
    numeric_holding: int
    grouped: int  # the queries whose top 5 are all grouped
    queries: int


def totals(scored: Iterable[Scored], groups: Mapping[str, WorkGroup]) -> Totals:
    measured = [(s, crowding(s, groups)) for s in scored]
    grouped = [(s, c) for s, c in measured if c.duplicates is not None]

    def share(pairs: list[tuple[Scored, Crowding]], counts: list[int]) -> Share:
        return Share(sum(counts), sum(len(s.top) for s, _ in pairs), sum(1 for count in counts if count), len(pairs))

    return Totals(
        duplicate=share(grouped, [c.duplicates or 0 for _, c in grouped]),
        restatement=share(grouped, [c.restatements or 0 for _, c in grouped]),
        numeric=share(measured, [c.numeric for _, c in measured]),
        numeric_holding=sum(c.numeric_holding for _, c in measured),
        grouped=len(grouped),
        queries=len(measured),
    )
