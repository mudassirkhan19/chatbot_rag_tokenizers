"""A local page for checking the Work groups one Work at a time (ADR 0047): `uv run python hack/check_work_groups.py`.

It shows each Work with its Editions: title, authors, venue, identifiers with links, the abstract and Section
headings from the parse cache, the draft's note, and other Works that may be the same paper. Every save rewrites
those Editions' rows in data/eval/work-groups.csv and loads the file as `evaluate` does, so a Work with both Survey
and non-Survey Editions is refused before it is written. Needs the parse cache.
"""

import csv
import json
import os
import sys
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from chatbot_rag_tokenizers.collection.fulltext import read_manifest
from chatbot_rag_tokenizers.evaluation.work_groups import COLUMNS, WorkGroupsError, load_work_groups
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

WORK_GROUPS = Path("data/eval/work-groups.csv")
PAGE = Path(__file__).with_name("check_work_groups.html")
PORT = 8767
EDITABLE = ("work_id", "survey", "checked_by", "note")
IDENTIFIERS = ("edition_kind", "arxiv_id", "doi", "acl_id", "source_link", "pdf_link")


def read_rows() -> list[dict[str, str]]:
    with WORK_GROUPS.open(newline="", encoding="utf-8") as file:
        return [{column: row.get(column) or "" for column in COLUMNS} for row in csv.DictReader(file)]


def write_rows(rows: list[dict[str, str]]) -> None:
    """Writes the rows only if `evaluate` would load them; raises WorkGroupsError otherwise."""
    fd, tmp = tempfile.mkstemp(dir=WORK_GROUPS.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        try:
            load_work_groups(Path(tmp))
        except WorkGroupsError as error:
            raise WorkGroupsError(str(error).replace(tmp, str(WORK_GROUPS))) from None
        os.replace(tmp, WORK_GROUPS)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> None:
    print("check_work_groups: loading the corpus…", file=sys.stderr)
    corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"))
    manifest = {row["edition_id"]: row for row in read_manifest(Path("data/manifest.csv"))}
    grouped = {row["edition_id"] for row in read_rows()}
    abstracts: dict[str, list[str]] = {}
    first_chunk: dict[str, str] = {}  # in place of the abstract when GROBID found none
    sections: dict[str, list[str]] = {}
    for chunk in corpus.chunks:
        if chunk.edition_id not in grouped:
            continue
        first_chunk.setdefault(chunk.edition_id, chunk.text)
        section = chunk.section_path[0] if chunk.section_path else ""
        if section == "Abstract":
            abstracts.setdefault(chunk.edition_id, []).append(chunk.text)
        elif section and section not in (titles := sections.setdefault(chunk.edition_id, [])):
            titles.append(section)
    # What the page shows beside each row, which saving never changes.
    editions = {
        edition_id: {
            **{field: manifest.get(edition_id, {}).get(field, "") for field in IDENTIFIERS},
            "abstract": " ".join(" ".join(abstracts.get(edition_id) or [first_chunk.get(edition_id, "")]).split()),
            "sections": sections.get(edition_id, []),
        }
        for edition_id in grouped
    }
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if isinstance(body, bytes) else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/rows":
                self._send({"rows": read_rows(), "editions": editions})
            else:
                self._send(PAGE.read_bytes())

        def do_POST(self) -> None:
            """Body: a list of {edition_id, work_id, survey, checked_by, note}; only those fields of those rows change."""
            updates = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with lock:
                rows = read_rows()
                by_id = {row["edition_id"]: row for row in rows}
                if unknown := [update.get("edition_id") for update in updates if update.get("edition_id") not in by_id]:
                    self._send({"error": f"no row for {', '.join(map(str, unknown))}"}, HTTPStatus.BAD_REQUEST)
                    return
                for update in updates:
                    by_id[update["edition_id"]].update({field: str(update[field]).strip() for field in EDITABLE if field in update})
                try:
                    write_rows(rows)
                except WorkGroupsError as error:
                    self._send({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
            self._send({"rows": rows})

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"check_work_groups: checking {WORK_GROUPS} at http://localhost:{PORT} (Ctrl+C to stop)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
