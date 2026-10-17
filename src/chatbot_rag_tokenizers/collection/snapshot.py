"""Snapshot store: compressed raw source responses, keyed by a credential-free request description.

A request description is a JSON-serialisable dict such as
``{"source": "arxiv", "url": ..., "params": {...}}``. It must never contain credentials:
clients send keys as headers that are not part of the description, so a key can't end up
in the key of a stored response or in the stored record.
"""

import gzip
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

MB = 1000**2
SIZE_WARNING_BYTES = 50 * MB  # the spec's warning size for the committed Snapshot (ADR 0026)


@dataclass(frozen=True)
class StoredResponse:
    request: dict
    collected_at: str
    body: str


def request_key(request: dict) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class SnapshotStore:
    """Content-addressed storage under ``<root>/responses/<source>/<key>.json.gz``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, request: dict) -> Path:
        return self.root / "responses" / request["source"] / f"{request_key(request)}.json.gz"

    def load(self, request: dict) -> StoredResponse | None:
        path = self._path(request)
        if not path.exists():
            return None
        record = json.loads(gzip.decompress(path.read_bytes()))
        return StoredResponse(record["request"], record["collected_at"], record["body"])

    def save(self, request: dict, body: str, collected_at: str) -> StoredResponse:
        record = {"request": request, "collected_at": collected_at, "body": body}
        data = json.dumps(record, sort_keys=True, indent=1, ensure_ascii=False).encode()
        path = self._path(request)
        path.parent.mkdir(parents=True, exist_ok=True)
        # mtime=0 keeps the compressed bytes stable, so re-saving the same response is a no-op in git.
        path.write_bytes(gzip.compress(data, mtime=0))
        return StoredResponse(request, collected_at, body)


def size(root: Path) -> int:
    """The size in bytes of every file under the Snapshot directory, as stored on disk."""
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def check_size(root: Path) -> None:
    """Print the Snapshot's size, with a warning when it is over ``SIZE_WARNING_BYTES``."""
    total = size(root)
    print(f"snapshot: {total / MB:.1f} MB", file=sys.stderr)
    if total > SIZE_WARNING_BYTES:
        print(
            f"snapshot: warning: the Snapshot is {total / MB:.1f} MB, more than about {SIZE_WARNING_BYTES / MB:g} MB."
            " Check what grew before committing it (ADR 0026).",
            file=sys.stderr,
        )


def files_containing(root: Path, secrets: Mapping[str, str]) -> dict[str, list[Path]]:
    """For each named secret, the Snapshot files whose content (decompressed) contains its value."""
    found: dict[str, list[Path]] = {}
    if not secrets:
        return found
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if path.suffix == ".gz":
            data = gzip.decompress(data)
        for name, value in secrets.items():
            if value.encode() in data:
                found.setdefault(name, []).append(path)
    return found


def check_credentials(root: Path, key_envs: Sequence[str]) -> None:
    """Stop if the value of any API key named in ``key_envs`` and set in the environment is anywhere
    in the Snapshot.

    Keys are sent as headers and never stored (ADR 0003), so this is a last check before the
    Snapshot is committed. Without a key in the environment there is nothing to look for.
    """
    secrets = {name: value for name in key_envs if (value := os.environ.get(name))}
    leaks = files_containing(root, secrets)
    if leaks:
        found = "; ".join(f"{name} in {', '.join(str(path) for path in paths)}" for name, paths in leaks.items())
        raise SystemExit(f"snapshot: an API key is stored in the Snapshot, so it must not be committed: {found}")
