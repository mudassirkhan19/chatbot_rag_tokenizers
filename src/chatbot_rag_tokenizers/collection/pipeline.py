"""The `collect` run: keyword queries → Snapshot → Editions → arXiv records → rule pre-filter → manifest."""

import sys
from collections import Counter
from pathlib import Path

from .arxiv import ArxivSource
from .config import ScopeConfig
from .editions import Edition
from .manifest import manifest_row, write_manifest
from .rules import RuleFilter
from .snapshot import SnapshotStore


def discover(config: ScopeConfig, arxiv: ArxivSource) -> list[Edition]:
    """Run every keyword query and merge repeats of the same Edition, keeping all their channels.

    A preprint revised between two page fetches shows up under two Versions; it is still one
    Edition. Its pin comes later, from the full arXiv record.
    """
    editions: dict[str, Edition] = {}
    for query in config.queries:
        found = arxiv.search(query.query)
        for edition in found:
            editions.setdefault(edition.arxiv_id, edition).discovery_channels.add(query.discovery_channel)
        print(f"discover: {query.discovery_channel} found {len(found)} Candidates", file=sys.stderr)
    return list(editions.values())


def add_arxiv_records(editions: list[Edition], arxiv: ArxivSource) -> None:
    """Give every arXiv Edition, whichever channel found it, its full record from arXiv.

    The record is the authority: the Edition is re-pinned to the latest Version it lists, and
    its comments and licence replace whatever the finding source reported.
    """
    preprints = [edition for edition in editions if edition.edition_kind == "arxiv-preprint"]
    for done, edition in enumerate(preprints, 1):
        record = arxiv.record(edition.arxiv_id)
        edition.edition_id = f"{edition.arxiv_id}{record.latest_version}"
        edition.source_link = f"https://arxiv.org/abs/{edition.edition_id}"
        edition.versions = record.versions
        edition.arxiv_comments = record.comments
        edition.licence = record.licence
        if done % 100 == 0:
            print(f"  arxiv: {done}/{len(preprints)} records", file=sys.stderr)
    print(f"arxiv: {len(preprints)} records", file=sys.stderr)


def collect(config: ScopeConfig, snapshot_dir: Path, manifest_path: Path) -> None:
    arxiv = ArxivSource(SnapshotStore(snapshot_dir), page_size=config.arxiv_page_size)
    editions = discover(config, arxiv)
    add_arxiv_records(editions, arxiv)
    rules = RuleFilter(config)
    rows = [manifest_row(edition, rules.apply(edition)) for edition in editions]
    write_manifest(manifest_path, rows)

    rejected = Counter(row["rule_pattern"] for row in rows if row["rule_outcome"] == "reject")
    print(f"discover: {len(rows)} Editions", file=sys.stderr)
    print(f"rules: {len(rows) - rejected.total()} passed, {rejected.total()} rejected", file=sys.stderr)
    for pattern, count in sorted(rejected.items()):
        print(f"  {pattern}: {count}", file=sys.stderr)
    print(f"manifest: wrote {manifest_path}", file=sys.stderr)
