"""The `collect` run: keyword queries → Snapshot → Editions → rule pre-filter → manifest."""

import sys
from collections import Counter
from pathlib import Path

from .arxiv import ArxivSource
from .config import ScopeConfig
from .editions import Edition
from .manifest import manifest_row, write_manifest
from .rules import RuleFilter
from .snapshot import SnapshotStore


def _version(edition: Edition) -> int:
    return int(edition.edition_id.rsplit("v", 1)[1])


def discover(config: ScopeConfig, snapshot: SnapshotStore) -> list[Edition]:
    """Run every keyword query and merge repeats of the same Edition, keeping all their channels.

    A preprint revised between two page fetches shows up under two Versions; it is still one
    Edition, pinned to the newest Version seen.
    """
    arxiv = ArxivSource(snapshot, page_size=config.arxiv_page_size)
    editions: dict[str, Edition] = {}
    for query in config.queries:
        found = arxiv.search(query.query)
        for edition in found:
            kept = editions.get(edition.arxiv_id)
            if kept is None or _version(edition) > _version(kept):
                if kept is not None:
                    edition.discovery_channels |= kept.discovery_channels
                editions[edition.arxiv_id] = kept = edition
            kept.discovery_channels.add(query.discovery_channel)
        print(f"discover: {query.discovery_channel} found {len(found)} Candidates", file=sys.stderr)
    return list(editions.values())


def collect(config: ScopeConfig, snapshot_dir: Path, manifest_path: Path) -> None:
    editions = discover(config, SnapshotStore(snapshot_dir))
    rules = RuleFilter(config)
    rows = [manifest_row(edition, rules.apply(edition)) for edition in editions]
    write_manifest(manifest_path, rows)

    rejected = Counter(row["rule_pattern"] for row in rows if row["rule_outcome"] == "reject")
    print(f"discover: {len(rows)} Editions", file=sys.stderr)
    print(f"rules: {len(rows) - rejected.total()} passed, {rejected.total()} rejected", file=sys.stderr)
    for pattern, count in sorted(rejected.items()):
        print(f"  {pattern}: {count}", file=sys.stderr)
    print(f"manifest: wrote {manifest_path}", file=sys.stderr)
