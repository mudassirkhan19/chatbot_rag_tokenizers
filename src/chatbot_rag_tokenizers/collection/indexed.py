"""The index record: which files the last `index` build covered, so the manifest can mark Editions indexed (ADR 0045).

`index` writes it to ``<snapshot>/index/files.jsonl`` and marks the manifest; `collect` and `fetch` read it as
they read the full-text record, so rebuilding the manifest from the Snapshot keeps the mark.
"""

import json
import sys
from pathlib import Path

from . import report
from .manifest import read_manifest, write_manifest

Row = dict[str, str]


class IndexRecord:
    """The record at ``<snapshot>/index/files.jsonl``: one JSON line per indexed file, sorted by pinned id.

    Two pinned ids can hold the same bytes, so a file is a (pinned id, sha256) pair.
    """

    def __init__(self, snapshot_root: Path) -> None:
        self.path = snapshot_root / "index" / "files.jsonl"
        lines = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        self.files = {(entry["pinned_id"], entry["sha256"]) for line in lines if line.strip() for entry in [json.loads(line)]}

    @property
    def hashes(self) -> set[str]:
        return {sha256 for _, sha256 in self.files}

    def save(self, files: set[tuple[str, str]]) -> None:
        """Replace the record with these files, as (pinned id, sha256) pairs."""
        self.files = set(files)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps({"pinned_id": pinned_id, "sha256": sha256}, sort_keys=True, separators=(",", ":")) for pinned_id, sha256 in sorted(files)]
        self.path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def apply_record(rows: list[Row], record: IndexRecord) -> None:
    """Mark each included row with full text "indexed" when every file it is pinned to is in the record.

    A row indexed before, whose files are no longer all in the record, goes back to "full text".
    """
    indexed = record.hashes
    for row in rows:
        if row["relevance_verdict"] != "included" or row["funnel_status"] not in {"full text", "indexed"}:
            continue
        hashes = [entry.split(" ")[1] for entry in row["pdf_files"].split("|") if entry]
        row["funnel_status"] = "indexed" if hashes and set(hashes) <= indexed else "full text"


def mark(snapshot_dir: Path, manifest_path: Path, report_path: Path, files: set[tuple[str, str]]) -> None:
    """Record the indexed files, as (pinned id, sha256) pairs, and mark the manifest and funnel report from them."""
    if not manifest_path.exists():
        print(f"index: there is no manifest at {manifest_path}, so no Edition is marked indexed", file=sys.stderr)
        return
    record = IndexRecord(snapshot_dir)
    record.save(files)
    rows = read_manifest(manifest_path)
    apply_record(rows, record)
    write_manifest(manifest_path, rows)
    report.write(report_path, rows)
    counts = report.funnel(rows)
    print(
        f"index: {counts.indexed} Editions indexed, {len(counts.not_indexed)} with full text not indexed;"
        f" wrote {manifest_path} and {report_path}",
        file=sys.stderr,
    )
