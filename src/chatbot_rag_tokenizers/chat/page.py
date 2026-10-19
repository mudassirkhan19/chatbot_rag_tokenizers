"""The chat page (ADR 0053): `chat` serves it on localhost with the standard library's threading HTTP server, as
`audit label` serves its page.

    GET  /        the page
    GET  /status  the retriever and the answer model, or why the model can't answer
    POST /turn    {"question": ...}: the Turn, or a 503 saying why the model can't answer

A Turn comes back as its answer, cut into text and markers (each marker valid or not), a reference per cited
Chunk from its Citation anchor, and every retrieved Chunk in rank order, numbered as the model saw it and marked
cited or not. The page folds the uncited ones away.
"""

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any

from ..parsing.chunker import HEADER_SEPARATOR, Chunk
from .answer import Marker
from .conversation import Chatbot, Turn
from .model import AnswerModelUnavailable


def make_server(chatbot: Chatbot, port: int = 8766) -> ThreadingHTTPServer:
    """A server for the chat page on localhost; ``port=0`` picks a free one."""
    page = resources.files(__package__).joinpath("page.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def do_GET(self) -> None:
            if self.path == "/status":
                self._json(status(chatbot))
            else:
                self._send(page, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path != "/turn":
                self._json({"error": f"no such action: {self.path}"}, HTTPStatus.NOT_FOUND)
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            question = str(payload.get("question", "")).strip()
            if not question:
                self._json({"error": "ask a question"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                turn = chatbot.ask(question)
            except AnswerModelUnavailable as error:
                print(f"chat: {error}", file=sys.stderr)
                self._json({"error": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._json(turn_json(turn))

        def log_message(self, format: str, *args: object) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(chatbot: Chatbot, server: ThreadingHTTPServer) -> None:
    """Check the answer model, say where the page is and serve it until Ctrl+C. A model that can't answer is
    reported here and on the page, which still opens, so Ollama can be started without restarting `chat`."""
    model = status(chatbot)
    if model["error"]:
        print(f"chat: {model['error']}", file=sys.stderr)
    else:
        print(f"chat: answering with {model['model']} from Chunks retrieved by {model['retriever']}", file=sys.stderr)
    print(f"chat: the page is at http://localhost:{server.server_address[1]} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def status(chatbot: Chatbot) -> dict[str, Any]:
    try:
        model, error = chatbot.model().pin, None
    except AnswerModelUnavailable as unavailable:
        model, error = chatbot.config.model.model, str(unavailable)
    return {"retriever": chatbot.config.retriever.name, "k": chatbot.config.k, "model": model, "error": error}


def turn_json(turn: Turn) -> dict[str, Any]:
    cited = turn.answer.cited
    return {
        "question": turn.question,
        "answer": [{"marker": part.number, "valid": part.valid} if isinstance(part, Marker) else {"text": part} for part in turn.answer.parts],
        "abstention": turn.answer.abstention,
        "invalid": turn.answer.invalid,
        "references": [{"number": number, **anchor(turn.retrieved[number - 1])} for number in cited],
        "chunks": [
            {"number": number, "chunk_id": chunk.chunk_id, "cited": number in cited, "header": chunk.header, "text": chunk.text, **anchor(chunk)}
            for number, chunk in enumerate(turn.retrieved, start=1)
        ],
        "seconds": {name: round(seconds, 3) for name, seconds in turn.seconds.items()},
    }


def anchor(chunk: Chunk) -> dict[str, str]:
    """The Chunk's Citation anchor, and the title of its paper."""
    if chunk.page_start is None or chunk.page_end is None:
        pages = ""
    elif chunk.page_start == chunk.page_end:
        pages = f"p. {chunk.page_start}"
    else:
        pages = f"pp. {chunk.page_start}–{chunk.page_end}"
    section = " ".join(part for part in (chunk.section_number, chunk.section_title) if part)
    return {
        "title": title(chunk),
        "edition": chunk.pinned_id,
        "section_number": chunk.section_number,
        "section_title": chunk.section_title,
        "pages": pages,
        "anchor": " · ".join(part for part in (chunk.pinned_id, section, pages) if part),
    }


def title(chunk: Chunk) -> str:
    """The paper's title: the context header without its Section path."""
    path = HEADER_SEPARATOR.join(chunk.section_path)
    return chunk.header.removesuffix(HEADER_SEPARATOR + path) if path else chunk.header
