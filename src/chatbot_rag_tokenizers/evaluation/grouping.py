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

Pair = tuple[str, str]  # two Edition ids, in order


@dataclass(frozen=True)
class SurveyDisagreement:
    """A Work of the Work groups whose Survey flag the rule does not give every one of its Editions."""

    work_id: str  # the Work groups' Work
    survey: bool  # the Work groups' Survey flag
    rule_flags: tuple[str, ...]  # the rule's survey column over its Editions, each value once, in order
    editions: tuple[str, ...]


@dataclass(frozen=True)
class GroupingScore:
    """The rule's pairs and Survey flags against the Work groups'."""

    titles: dict[str, str]  # each Edition in the Work groups, by id, with its title in the manifest ("" with no row)
    work_ids: dict[str, str]  # and its work_id there, "" when it has none
    rule_pairs: frozenset[Pair]
    checked_pairs: frozenset[Pair]
    works: int  # in the Work groups
    surveys: int  # of those Works, the Surveys
    rule_surveys: int  # of those Works, the ones the rule flags on every Edition
    survey_disagreements: tuple[SurveyDisagreement, ...]  # by work_id

    @property
    def without_work_id(self) -> list[str]:
        return [edition_id for edition_id, work_id in self.work_ids.items() if not work_id]

    @property
    def joined_apart(self) -> list[Pair]:
        """Pairs the rule joins and the Work groups keep apart."""
        return sorted(self.rule_pairs - self.checked_pairs)

    @property
    def missed(self) -> list[Pair]:
        """Pairs the Work groups join and the rule misses."""
        return sorted(self.checked_pairs - self.rule_pairs)


def score_grouping(groups: Mapping[str, WorkGroup], manifest: Mapping[str, Mapping[str, str]]) -> GroupingScore | None:
    """None when no manifest row has a work_id: there is no grouping to score."""
    if not any(row.get("work_id") for row in manifest.values()):
        return None
    editions = sorted(groups)

    def column(edition_id: str, name: str) -> str:
        return manifest.get(edition_id, {}).get(name, "")

    def pairs(same: Callable[[str, str], bool]) -> frozenset[Pair]:
        return frozenset((first, second) for first, second in combinations(editions, 2) if same(first, second))

    works: dict[str, list[str]] = {}
    for edition_id in editions:
        works.setdefault(groups[edition_id].work_id, []).append(edition_id)
    disagreements = []
    for work_id, members in sorted(works.items()):
        survey = groups[members[0]].survey
        flags = tuple(sorted({column(edition_id, "survey") or "no" for edition_id in members}))
        if flags != ("yes" if survey else "no",):
            disagreements.append(SurveyDisagreement(work_id, survey, flags, tuple(members)))
    work_ids = {edition_id: column(edition_id, "work_id") for edition_id in editions}
    return GroupingScore(
        titles={edition_id: column(edition_id, "title") for edition_id in editions},
        work_ids=work_ids,
        rule_pairs=pairs(lambda first, second: bool(work_ids[first]) and work_ids[first] == work_ids[second]),
        checked_pairs=pairs(lambda first, second: groups[first].work_id == groups[second].work_id),
        works=len(works),
        surveys=sum(1 for members in works.values() if groups[members[0]].survey),
        rule_surveys=sum(1 for members in works.values() if all(column(edition_id, "survey") == "yes" for edition_id in members)),
        survey_disagreements=tuple(disagreements),
    )
