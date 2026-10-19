"""A local page for checking the Evaluation set one question at a time (ADR 0046): `uv run python hack/check_evalset.py`.

It shows each question with its history and rewrite, each Passage's quote marked in the full text of its Section,
and for an unanswerable question the absence evidence from data/eval/absence-evidence.md, each Chunk in full.
Every save rewrites that question's line in data/eval/evaluation-set.jsonl and reruns eval-check on it against the
Chunks of the files it quotes, so a reworded quote that no longer matches shows up at once. Needs the parse cache.
"""

import json
import os
import re
import sys
import tempfile
import threading
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from chatbot_rag_tokenizers.collection.fulltext import read_manifest
from chatbot_rag_tokenizers.evaluation.check import check, describe
from chatbot_rag_tokenizers.evaluation.config import load_matching_rule
from chatbot_rag_tokenizers.evaluation.evalset import EvaluationSetError, _question
from chatbot_rag_tokenizers.evaluation.works import Works
from chatbot_rag_tokenizers.parsing.chunker import HEADER_SEPARATOR
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

EVALUATION_SET = Path("data/eval/evaluation-set.jsonl")
EVIDENCE = Path("data/eval/absence-evidence.md")
PAGE = Path(__file__).with_name("check_evalset.html")
PORT = 8766
UNCHECKED = "nobody has checked this question (checked_by is empty)"


def read_set() -> list[dict]:
    return [json.loads(line) for line in EVALUATION_SET.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_set(records: list[dict]) -> None:
    fd, tmp = tempfile.mkstemp(dir=EVALUATION_SET.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    os.replace(tmp, EVALUATION_SET)


def mark(text: str, quote: str) -> list[int] | None:
    """Where the quote is in the Section's text, allowing for line breaks, hyphens and citations between its words."""
    tokens = re.findall(r"[^\W_]+", quote)
    gap = r"(?:[\W_]|\[[^\]]{0,40}\]|\([^()]{0,80}\d{4}[a-z]?\))*?"
    found = re.search(gap.join(map(re.escape, tokens)), text, re.I) if tokens else None
    return [found.start(), found.end()] if found else None


def read_evidence(sections: dict[tuple[str, str], list[str]]) -> dict[str, dict]:
    """The absence evidence by question id: the drafter's reading and each search's rows, each with its Chunk's full text."""
    evidence: dict[str, dict] = {}
    current: dict = {}
    for line in EVIDENCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = evidence.setdefault(line[3:], {"reading": "", "searches": []})
        elif line.startswith("Drafter's reading: "):
            current["reading"] = line.removeprefix("Drafter's reading: ")
        elif line.startswith("### "):
            retriever, query = line[4:].split(": ", 1)
            current["searches"].append({"retriever": retriever, "query": query, "rows": []})
        elif line.startswith("| ") and line[2:3].isdigit():
            rank, score, pinned_id, section, snippet = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
            full = next((text for text in sections.get((pinned_id, section), []) if " ".join(text.split()).startswith(snippet)), snippet)
            current["searches"][-1]["rows"].append({"rank": rank, "score": score, "pinned_id": pinned_id, "section": section, "text": full})
    return evidence


def main() -> None:
    print("check_evalset: loading the corpus…", file=sys.stderr)
    corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"))
    rule = load_matching_rule()
    works = Works(read_manifest(Path("data/manifest.csv")))
    by_file: dict[str, list] = {}
    sections: dict[tuple[str, str], list[str]] = {}
    titles: dict[str, str] = {}
    for chunk in corpus.chunks:
        by_file.setdefault(chunk.pinned_id, []).append(chunk)
        path = HEADER_SEPARATOR.join(chunk.section_path)
        sections.setdefault((chunk.pinned_id, path), []).append(chunk.text)
        titles.setdefault(chunk.pinned_id, chunk.header.removesuffix(HEADER_SEPARATOR + path))
    evidence = read_evidence(sections)
    lock = threading.Lock()

    def checked(record: dict) -> dict:
        """eval-check on one question, against the Chunks of the files it quotes, with what a reviewer needs beside it."""
        try:
            question = _question(record, record.get("id", "?"))
        except EvaluationSetError as error:
            return {"problems": [str(error)], "lines": [], "passages": []}
        quoted = [chunk for p in question.passages for chunk in by_file.get(p.edition_id, [])]
        result = check([question], replace(corpus, chunks=tuple(dict.fromkeys(quoted))), rule, works)
        passages = []
        for p in question.passages:
            text = "\n\n".join(sections.get((p.edition_id, p.section), []))
            passages.append({"title": titles.get(p.edition_id, "(not in the corpus)"), "text": text, "mark": mark(text, p.quote)})
        problems = [problem.removeprefix(f"{question.id}: ") for problem in result.problems]
        return {
            "problems": [problem for problem in problems if problem != UNCHECKED],
            "lines": describe([question], result)[:-1],
            "passages": passages,
        }

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if isinstance(body, bytes) else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/questions":
                records = read_set()
                self._send([{"record": r, "check": checked(r), "evidence": evidence.get(r["id"])} for r in records])
            else:
                self._send(PAGE.read_bytes())

        def do_POST(self) -> None:
            record = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with lock:
                records = read_set()
                index = next((i for i, r in enumerate(records) if r["id"] == record.get("id")), None)
                if index is None:
                    self._send({"error": f"no question {record.get('id')!r}"}, HTTPStatus.BAD_REQUEST)
                    return
                records[index] = record
                write_set(records)
            self._send({"record": record, "check": checked(record)})

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"check_evalset: checking {EVALUATION_SET} at http://localhost:{PORT} (Ctrl+C to stop)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
