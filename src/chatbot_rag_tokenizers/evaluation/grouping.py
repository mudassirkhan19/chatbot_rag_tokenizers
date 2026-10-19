"""The grouping rule scored against the Work groups (ADR 0060): does the manifest's work_id, which `collect`'s Work
grouping fills (ADR 0051), join the Editions the hand check joins, and does its Survey flag match the check's?

Over the Editions in the Work groups, a pair is two Editions one Work holds. The rule's pairs are those with the
same work_id; an Edition with none, or with no manifest row, is its own Work. Each Work of the Work groups is
compared with the rule's survey column on its Editions.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from itertools import combinations

from .work_groups import WorkGroup


@dataclass(frozen=True)
class SurveyDisagreement:
    work_id: str  # the Work groups' Work
    checked: bool  # the Work groups' Survey flag
    flagged: tuple[str, ...]  # the rule's survey column over its Editions, each value once, in order
    editions: tuple[str, ...]


@dataclass(frozen=True)
class GroupingScore:
    editions: int  # in the Work groups
    titles: dict[str, str]  # each of those Editions' title in the manifest, "" with no manifest row
    work_ids: dict[str, str]  # and its work_id there, "" when it has none
    without_work_id: tuple[str, ...]  # the Editions the manifest gives no work_id
    rule: frozenset[tuple[str, str]]  # each pair as its two Edition ids in order
    checked: frozenset[tuple[str, str]]
    works: int  # in the Work groups
    surveys: int  # of those Works, the Surveys
    flagged: int  # of those Works, the ones the rule flags on every Edition
    survey_disagreements: tuple[SurveyDisagreement, ...]  # by work_id

    @property
    def joined_apart(self) -> list[tuple[str, str]]:
        """Pairs the rule joins and the Work groups keep apart."""
        return sorted(self.rule - self.checked)

    @property
    def missed(self) -> list[tuple[str, str]]:
        """Pairs the Work groups join and the rule misses."""
        return sorted(self.checked - self.rule)


def score_grouping(groups: Mapping[str, WorkGroup], manifest: Mapping[str, Mapping[str, str]]) -> GroupingScore | None:
    """None when no manifest row has a work_id: there is no grouping to score."""
    if not any(row.get("work_id") for row in manifest.values()):
        return None
    editions = sorted(groups)

    def work_id(edition_id: str) -> str:
        return manifest.get(edition_id, {}).get("work_id", "")

    def pairs(same: Callable[[str, str], bool]) -> frozenset[tuple[str, str]]:
        return frozenset((first, second) for first, second in combinations(editions, 2) if same(first, second))

    works: dict[str, list[str]] = {}
    for edition_id in editions:
        works.setdefault(groups[edition_id].work_id, []).append(edition_id)
    disagreements = []
    surveys = flagged = 0
    for name, members in sorted(works.items()):
        checked = groups[members[0]].survey
        values = tuple(sorted({manifest.get(edition_id, {}).get("survey", "") or "no" for edition_id in members}))
        surveys += checked
        flagged += values == ("yes",)
        if values != ("yes" if checked else "no",):
            disagreements.append(SurveyDisagreement(name, checked, values, tuple(members)))
    return GroupingScore(
        editions=len(editions),
        titles={edition_id: manifest.get(edition_id, {}).get("title", "") for edition_id in editions},
        work_ids={edition_id: work_id(edition_id) for edition_id in editions},
        without_work_id=tuple(edition_id for edition_id in editions if not work_id(edition_id)),
        rule=pairs(lambda first, second: bool(work_id(first)) and work_id(first) == work_id(second)),
        checked=pairs(lambda first, second: groups[first].work_id == groups[second].work_id),
        works=len(works),
        surveys=surveys,
        flagged=flagged,
        survey_disagreements=tuple(disagreements),
    )
