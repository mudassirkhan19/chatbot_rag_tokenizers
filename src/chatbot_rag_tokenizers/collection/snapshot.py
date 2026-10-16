"""Snapshot store: compressed raw source responses, keyed by a credential-free request description.

A request description is a JSON-serialisable dict such as
``{"source": "arxiv", "url": ..., "params": {...}}``. It must never contain credentials:
clients send keys as headers that are not part of the description, so a key can't end up
in the key of a stored response or in the stored record.
"""

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


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
