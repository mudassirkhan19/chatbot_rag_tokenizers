"""A local page for labelling the Audit set one Candidate at a time.

`audit label` serves the page on localhost. It shows each row's title, abstract and link, the
pipeline's draft verdict explained in words, any review note, and the current label and reason.
Every save rewrites that row in the Audit set file and sets `labelled_by` to `developer`, so the
committed file records which labels the developer checked. A file exported before the
provenance columns existed reads as unreviewed pipeline drafts.
"""

import csv
import json
import os
import sys
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path

from .audit import COLUMNS
from .config import ScopeConfig

PROVENANCE_DEFAULTS = {"labelled_by": "draft", "review_note": ""}


class AuditSetFile:
    """The Audit set CSV, read and rewritten whole on every save, in the same format as `audit export`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def read(self) -> tuple[list[str], list[dict[str, str]]]:
        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fields = list(reader.fieldnames or COLUMNS)
        fields += [column for column in PROVENANCE_DEFAULTS if column not in fields]
        return fields, [{**PROVENANCE_DEFAULTS, **row} for row in rows]

    def save_label(self, index: int, label: str, reason: str) -> None:
        with self._lock:
            fields, rows = self.read()
            rows[index].update(label=label, reason=reason, labelled_by="developer")
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            os.replace(tmp, self.path)


def make_server(config: ScopeConfig, audit_set: Path, port: int = 8765) -> ThreadingHTTPServer:
    """A server for the labelling page on localhost; ``port=0`` picks a free one."""
    audit_file = AuditSetFile(audit_set)
    judge = {"model": config.judge.model, "threshold": config.judge.threshold}
    page = resources.files(__package__).joinpath("audit_label.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/rows":
                _, rows = audit_file.read()
                listing = {"judge": judge, "rows": [{**row, "index": i} for i, row in enumerate(rows)]}
                self._send(json.dumps(listing).encode(), "application/json")
            else:
                self._send(page, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path != "/save":
                self._send(b'{"ok":false}', "application/json", HTTPStatus.NOT_FOUND)
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            index, label, reason = payload.get("index"), payload.get("label"), payload.get("reason", "")
            _, rows = audit_file.read()
            if label not in ("yes", "no", "") or not isinstance(index, int) or not 0 <= index < len(rows):
                self._send(b'{"ok":false}', "application/json", HTTPStatus.BAD_REQUEST)
                return
            audit_file.save_label(index, label, str(reason).strip())
            self._send(b'{"ok":true}', "application/json")

        def log_message(self, format: str, *args: object) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(config: ScopeConfig, audit_set: Path, port: int) -> None:
    server = make_server(config, audit_set, port)
    print(f"audit: labelling {audit_set} at http://localhost:{server.server_address[1]} (Ctrl+C to stop)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
