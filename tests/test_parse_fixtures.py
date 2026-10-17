"""The committed TEI fixtures carry paper text, so each must come from a paper whose licence lets us share it
(ADR 0031): each is attributed in fixtures/tei/README.md, under a CC BY licence the manifest records."""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEI = Path(__file__).parent / "fixtures" / "tei"
# CC BY 4.0, as arXiv and the ACL Anthology spell it
SHAREABLE = {"http://creativecommons.org/licenses/by/4.0/", "https://creativecommons.org/licenses/by/4.0/"}


def attributions() -> dict[str, tuple[str, str]]:
    """Fixture file name → (arXiv pinned id, licence URL), from the README's table."""
    rows = {}
    for line in (TEI / "README.md").read_text().splitlines():
        if match := re.fullmatch(r"\| `(?P<file>[^`]+)` \|.*\| (?P<arxiv>\S+) \| \[[^]]+\]\((?P<licence>[^)]+)\) \|.*", line):
            rows[match["file"]] = (match["arxiv"], match["licence"])
    return rows


def test_every_tei_fixture_is_attributed_to_a_paper_the_manifest_records_as_cc_by():
    attributed = attributions()
    assert set(attributed) == {path.name for path in TEI.glob("*.tei.xml")}
    with (ROOT / "data" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        licences = {row["edition_id"]: row["licence"] for row in csv.DictReader(f)}
    for name, (arxiv_id, licence) in attributed.items():
        assert licence in SHAREABLE, name
        assert licences[arxiv_id] == licence, name
