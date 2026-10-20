"""The developer's check of the grounding verdict (spec #63, ADR 0071): a seeded sample of answered Turns, labelled
by hand, and the automatic check's agreement with it.

`chat-eval --export-check` draws the sample from the answers file, scored again with the current code, as
`--from-answers` scores it: the scored Turns that are not Abstentions, in the Evaluation set's order. Each row holds
the Turn's question, Rewrite, reply, retrieved Chunk ids and the text of each cited Chunk, so the file reads on its
own, and the automatic verdict copied into `label` as the draft, as `audit export` drafts the Audit set. `checked_by`
records who set the label: `draft`, `agent` or `developer` (ADR 0020).

`chat-label` serves a page, in the audit label page's shape, that shows one row at a time and saves `label`,
`checked_by=developer` and a note straight to the file. The chat report compares the hand labels with the automatic
check scored on each labelled row's reply over its Chunks, as stored in the sample, whatever a later run has answered
(ADR 0072). Only a row whose Chunks the corpus no longer has is left out.
"""

import csv
import json
import os
import random
import sys
import tempfile
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path

from ..parsing.chunker import Chunk
from .answer import read_answer
from .answers import Asked, verdict
from .grounding import Grounding, ground

COLUMNS = [
    "question_id",
    "type",
    "question",
    "rewrite",
    "reply",
    "retrieved",  # the Turn's retrieved Chunk ids, in rank order, space-separated
    "cited_chunks",  # JSON: each cited Chunk's number in the Turn, id, context header and text, in the order first cited
    "draft_label",
    "draft_reason",
    "label",  # grounded, not grounded, or empty when unsure
    "checked_by",  # who set the label: draft (the automatic verdict), agent or developer
    "note",
]
LABELS = ("grounded", "not grounded", "")


class CheckExists(FileExistsError):
    """The sample file exists and may hold labels; `--force` replaces it."""


def export(answered: Sequence[Asked], check: Path, size: int, seed: int, force: bool = False) -> int:
    """Write a sample of ``size`` of the scored Turns that are not Abstentions, drawn with ``seed``, and return how
    many were written. Raises CheckExists unless ``force``."""
    if check.exists() and not force:
        raise CheckExists(f"{check} already exists and may hold labels; pass --force to replace it")
    candidates = [item for item in answered if item.scored and item.grounding is not None]
    chosen = sorted(random.Random(seed).sample(range(len(candidates)), min(size, len(candidates))))
    _write(check, [_row(candidates[place]) for place in chosen])
    return len(chosen)


def _row(item: Asked) -> dict[str, str]:
    """A sampled Turn, which is not an Abstention."""
    turn = item.turn
    assert item.grounding is not None
    cited = [
        {"number": number, "chunk_id": turn.retrieved[number - 1].chunk_id, "header": turn.retrieved[number - 1].header, "text": turn.retrieved[number - 1].text}
        for number in turn.answer.cited
    ]
    return {
        "question_id": item.question.id,
        "type": item.question.type,
        "question": turn.question,
        "rewrite": turn.rewrite or "",
        "reply": turn.reply,
        "retrieved": " ".join(chunk.chunk_id for chunk in turn.retrieved),
        "cited_chunks": json.dumps(cited, ensure_ascii=False),
        "draft_label": item.verdict,
        "draft_reason": _reason(item.grounding),
        "label": item.verdict,
        "checked_by": "draft",
        "note": "",
    }


@dataclass(frozen=True)
class Disagreement:
    question_id: str
    type: str
    automatic: str  # the automatic verdict on the sampled reply
    label: str  # the developer's
    note: str


@dataclass(frozen=True)
class Comparison:
    """The sample's hand labels against the automatic verdict on each sampled reply."""

    rows: int
    labelled: int  # rows the developer gave a label
    unsure: int  # rows the developer checked and left without one
    compared: int  # the labelled rows scored
    disagreements: tuple[Disagreement, ...]
    dropped: tuple[str, ...]  # question ids of the labelled rows whose Chunks the corpus no longer has

    @property
    def agreed(self) -> int:
        return self.compared - len(self.disagreements)


def compare(rows: Sequence[dict[str, str]], chunks: Mapping[str, Chunk], abstention: str) -> Comparison:
    """The developer's labelled rows against the automatic check scored on each row's reply over its Chunks, as
    stored in the sample, whatever a later run has answered: a label and the check both judge that one reply."""
    labelled = [row for row in rows if row["checked_by"] == "developer" and row["label"]]
    scored: list[tuple[dict[str, str], str]] = []
    dropped = []
    for row in labelled:
        ids = row["retrieved"].split()
        if all(chunk_id in chunks for chunk_id in ids):
            retrieved = [chunks[chunk_id] for chunk_id in ids]
            answer = read_answer(row["reply"], len(retrieved), abstention)
            grounding = ground(answer, retrieved)
            scored.append((row, verdict(answer.abstention, None if grounding is None else grounding.grounded)))
        else:
            dropped.append(row["question_id"])
    return Comparison(
        rows=len(rows),
        labelled=len(labelled),
        unsure=sum(1 for row in rows if row["checked_by"] == "developer" and not row["label"]),
        compared=len(scored),
        disagreements=tuple(
            Disagreement(row["question_id"], row["type"], automatic, row["label"], row["note"]) for row, automatic in scored if row["label"] != automatic
        ),
        dropped=tuple(dropped),
    )


def _reason(grounding: Grounding) -> str:
    """Why the automatic check gave an answer its verdict, in words."""
    if grounding.grounded:
        return "cites a retrieved Chunk, and every number is in a cited Chunk"
    reasons = []
    if not grounding.cited:
        reasons.append("cites no retrieved Chunk")
    if grounding.invalid:
        reasons.append(f"markers naming no retrieved Chunk: {', '.join(f'[{number}]' for number in grounding.invalid)}")
    if grounding.missing:
        reasons.append(f"numbers in no cited Chunk: {', '.join(grounding.missing)}")
    return "; ".join(reasons)


def read_check(check: Path) -> list[dict[str, str]]:
    with check.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class CheckFile:
    """The sample file, read and rewritten whole on every save."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def read(self) -> list[dict[str, str]]:
        return read_check(self.path)

    def save_label(self, index: int, label: str, note: str) -> None:
        with self._lock:
            rows = self.read()
            rows[index].update(label=label, checked_by="developer", note=note)
            _write(self.path, rows)


def make_server(check: Path, port: int = 8767) -> ThreadingHTTPServer:
    """A server for the label page on localhost; ``port=0`` picks a free one."""
    check_file = CheckFile(check)
    page = resources.files(__package__).joinpath("grounding_check.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/rows":
                rows = [{**row, "cited_chunks": json.loads(row["cited_chunks"]), "index": i} for i, row in enumerate(check_file.read())]
                self._send(json.dumps({"file": str(check), "rows": rows}).encode(), "application/json")
            else:
                self._send(page, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path != "/save":
                self._send(b'{"ok":false}', "application/json", HTTPStatus.NOT_FOUND)
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if not isinstance(payload, dict):
                payload = {}
            index, label, note = payload.get("index"), payload.get("label"), payload.get("note", "")
            rows = check_file.read()
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(rows) or label not in LABELS or not isinstance(note, str):
                self._send(b'{"ok":false}', "application/json", HTTPStatus.BAD_REQUEST)
                return
            check_file.save_label(index, label, note.strip())
            self._send(b'{"ok":true}', "application/json")

        def log_message(self, format: str, *args: object) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(server: ThreadingHTTPServer, check: Path) -> None:
    print(f"chat-label: checking {check} at http://localhost:{server.server_address[1]} (Ctrl+C to stop)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _write(check: Path, rows: Sequence[dict[str, str]]) -> None:
    """The whole file, written to a temporary file beside it and moved into place."""
    check.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=check.parent, suffix=".tmp")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, check)
