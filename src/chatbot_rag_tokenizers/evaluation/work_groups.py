"""The Work groups: the hand-assigned Work of each Edition the duplicate rate is measured against (ADR 0044).

A committed CSV, one Edition per row, with the columns of the export `evaluate --export-ungrouped` writes:

    edition_id,work_id,survey,title,authors,year,venue,checked_by,note
    2112.06598v2,minixhofer-2022-wechsel,no,WECHSEL: …,Benjamin Minixhofer; …,2021,,mudassir,

Editions with the same work_id are one Work. survey is "yes" for a Survey's Editions and "no" otherwise; a
Survey is always its own Work, so a Work's Editions are all Surveys or none is. A row whose work_id is blank,
as the export writes it, is an Edition with no Work group yet. Title, authors, year and venue are only there
for the person grouping and are not read. checked_by says who checked the row: a person's name, or a draft
the person approved without reading each row ("draft, approved by …"). Blank, or no such column, means nobody has, and the eval report counts the rows that were (ADR 0047). note says why a drafted row
needs a closer look, for the person checking it, and is not read.

The grouping is given, never computed, so the duplicate stage is never scored by its own grouping.
"""

import csv
import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("edition_id", "work_id", "survey", "title", "authors", "year", "venue", "checked_by", "note")
_REQUIRED = COLUMNS[:3]
_SURVEY = {"yes": True, "no": False}


class WorkGroupsError(ValueError):
    """The Work groups file is malformed, worded for the person editing it."""


@dataclass(frozen=True)
class WorkGroup:
    work_id: str
    survey: bool


@dataclass(frozen=True)
class WorkGroups:
    path: Path
    sha256: str  # of the file, so the eval report names exactly the grouping it was measured against
    editions: dict[str, WorkGroup]  # each grouped Edition's Work, by Edition id
    checked: int  # the grouped Editions whose row names who checked it


def load_work_groups(path: Path) -> WorkGroups:
    if not path.exists():
        raise WorkGroupsError(f"there is no Work groups file at {path}; `evaluate --export-ungrouped` writes one to start from")
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if missing := [column for column in _REQUIRED if column not in (reader.fieldnames or ())]:
            raise WorkGroupsError(f"{path}: missing columns {', '.join(missing)}")
        groups: dict[str, WorkGroup] = {}
        checked = 0
        for number, row in enumerate(reader, start=2):
            edition_id, work_id, survey = (row[column].strip() for column in _REQUIRED)
            if not edition_id:
                raise WorkGroupsError(f"{path}:{number}: no edition_id")
            if edition_id in groups:
                raise WorkGroupsError(f"{path}:{number}: Edition {edition_id} is listed twice")
            if not work_id:
                continue
            if survey not in _SURVEY:
                raise WorkGroupsError(f"{path}:{number}: survey {survey!r} is not yes or no")
            groups[edition_id] = WorkGroup(work_id, _SURVEY[survey])
            checked += bool((row.get("checked_by") or "").strip())
    surveys: dict[str, set[bool]] = {}
    for group in groups.values():
        surveys.setdefault(group.work_id, set()).add(group.survey)
    if mixed := sorted(work_id for work_id, flags in surveys.items() if len(flags) > 1):
        raise WorkGroupsError(f"{path}: Works with both Survey and non-Survey Editions (a Survey is its own Work): {', '.join(mixed)}")
    return WorkGroups(path, hashlib.sha256(path.read_bytes()).hexdigest(), groups, checked)


def write_export(path: Path, edition_ids: Iterable[str], manifest: Mapping[str, Mapping[str, str]]) -> None:
    """The Editions to group, in id order, with their title, authors, year and venue from the manifest and the
    work_id, survey, checked_by and note left blank."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, COLUMNS, lineterminator="\n")
        writer.writeheader()
        for edition_id in sorted(edition_ids):
            row = manifest.get(edition_id, {})
            writer.writerow({"edition_id": edition_id, "work_id": "", "survey": ""} | {column: row.get(column, "") for column in COLUMNS[3:]})
