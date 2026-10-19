"""The chat page (#64), served by `chat` over the fixture corpus with the scripted fake answer model.

The last test asks the real pinned model on the local Ollama instead. It is skipped unless RUN_OLLAMA_TESTS=1, and needs
`just init` to have pulled the model:

    RUN_OLLAMA_TESTS=1 just test tests/test_chat_page.py -k real -s

The corpus is the retrieval tests' (WECHSEL v2 and a trimmed BPE paper, parsed through the fake GROBID service
and indexed with the fake embedder). Each test posts a question to the served page and reads the Turn it returns.
"""

import json
import os
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from chatbot_rag_tokenizers.chat import model as answer_model
from chatbot_rag_tokenizers.chat import page
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.cli import main
from parse_support import WECHSEL_TITLE, FakeGrobid, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"
REAL_LOAD = answer_model.load_answer_model  # taken before the conftest puts the fake in its place
# The sockets as they are before the offline parse blocks them, so the test can reach the page on localhost.
REAL_TRANSPORT = httpx.HTTPTransport.handle_request  # taken before the fake GROBID service replaces it
SOCKETS = [(socket.socket, "connect", socket.socket.connect), (socket, "create_connection", socket.create_connection), (socket, "getaddrinfo", socket.getaddrinfo)]
FREEZING = "Does WECHSEL need to freeze the non-embedding parameters at the start of training?"
ABSTENTION = load_chat_config(RETRIEVAL_CONFIG).abstention
TITLES = {WECHSEL_TITLE, "Neural Machine Translation of Rare Words with Subword Units"}


@pytest.fixture
def indexed(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path and indexed with the chatbot's retriever."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    main(["index", *corpus_arguments(tmp_path), "--retriever", "dense.bge-small",
          "--snapshot", str(tmp_path / "snapshot"), "--manifest", str(tmp_path / "manifest.csv"),
          "--funnel-report", str(tmp_path / "report.md")])  # fmt: skip
    return tmp_path


def corpus_arguments(tmp_path: Path) -> list[str]:
    return [
        "--config", str(RETRIEVAL_CONFIG),
        "--cache", str(tmp_path / "cache"),
        "--parse-report", str(tmp_path / "parse-report.md"),
        "--index-cache", str(tmp_path / "index-cache"),
    ]  # fmt: skip


@dataclass
class Chat:
    url: str
    server: ThreadingHTTPServer


@pytest.fixture
def start_chat(indexed: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], Chat]]:
    """Starts `chat` in a thread on a free port, as `just chat` runs it, and stops it after the test."""
    for owner, name, real in SOCKETS:
        monkeypatch.setattr(owner, name, real)
    servers: list[ThreadingHTTPServer] = []
    threads: list[threading.Thread] = []
    make_server = page.make_server

    def recorded(*args, **kwargs) -> ThreadingHTTPServer:
        servers.append(make_server(*args, **kwargs))
        return servers[-1]

    def start() -> Chat:
        monkeypatch.setattr(page, "make_server", recorded)
        thread = threading.Thread(target=main, args=(["chat", *corpus_arguments(indexed), "--port", "0"],), daemon=True)
        threads.append(thread)
        thread.start()
        while not servers:
            assert thread.is_alive(), "chat stopped before serving"
            thread.join(0.01)
        return Chat(f"http://127.0.0.1:{servers[0].server_address[1]}", servers[0])

    yield start
    for server in servers:
        server.shutdown()
    for thread in threads:
        thread.join(5)


@pytest.fixture
def chat(start_chat: Callable[[], Chat]) -> Chat:
    return start_chat()


def ask(chat: Chat, question: str) -> dict:
    request = urllib.request.Request(f"{chat.url}/turn", json.dumps({"question": question}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def markers(turn: dict) -> list[tuple[int, bool]]:
    return [(part["marker"], part["valid"]) for part in turn["answer"] if "marker" in part]


def test_an_answer_cites_the_chunks_the_model_saw_under_those_numbers(chat, fake_answer_model):
    fake_answer_model.script[FREEZING] = "WECHSEL does not need freezing [1]. Freezing helped TransInner [3][1]."

    turn = ask(chat, FREEZING)

    assert "".join(part.get("text", "") for part in turn["answer"]) == "WECHSEL does not need freezing . Freezing helped TransInner ."
    assert markers(turn) == [(1, True), (3, True), (1, True)]
    assert turn["abstention"] is False
    # The model was given the question and five Chunks, numbered from 1, each under its context header.
    [[system, user]] = fake_answer_model.chats
    assert system["role"] == "system" and ABSTENTION in system["content"]
    assert FREEZING in user["content"]
    chunks = turn["chunks"]
    assert [chunk["number"] for chunk in chunks] == [1, 2, 3, 4, 5]
    for chunk in chunks:
        assert f"[{chunk['number']}] {chunk['header']}\n{chunk['text']}" in user["content"]
    # A reference per cited Chunk, in the order first cited, from its Citation anchor.
    references = turn["references"]
    assert [reference["number"] for reference in references] == [1, 3]
    for reference in references:
        chunk = chunks[reference["number"] - 1]
        assert reference["title"] in TITLES and chunk["header"].startswith(reference["title"])
        assert reference["edition"] in ("2112.06598v2", "1508.07909v5")
        assert chunk["header"].endswith(reference["section_title"])
        assert reference["pages"]
    assert [chunk["cited"] for chunk in chunks] == [True, False, True, False, False]


def test_chat_prints_where_the_page_is_and_serves_it(start_chat, capsys):
    chat = start_chat()
    with urllib.request.urlopen(chat.url) as response:
        assert b"<title>Tokenization Chat</title>" in response.read()

    # Printed before serving began, so by now.
    assert f"chat: the page is at http://localhost:{chat.server.server_address[1]}" in capsys.readouterr().out


def test_a_marker_naming_no_retrieved_chunk_is_shown_invalid_not_dropped(chat, fake_answer_model):
    fake_answer_model.script[FREEZING] = "Freezing is not needed [2]. It doubles the score [7][2, 0]."

    turn = ask(chat, FREEZING)

    assert markers(turn) == [(2, True), (7, False), (2, True), (0, False)]
    assert turn["invalid"] == [7, 0]
    assert [reference["number"] for reference in turn["references"]] == [2]
    assert [chunk["number"] for chunk in turn["chunks"] if chunk["cited"]] == [2]


def test_the_abstention_sentence_is_recognised_and_the_retrieved_chunks_still_shown(chat, fake_answer_model):
    # Matched after normalisation, so the model's case and punctuation don't matter.
    fake_answer_model.script["capital of France"] = ABSTENTION.upper().rstrip(".") + "!"

    turn = ask(chat, "What is the capital of France?")

    assert turn["abstention"] is True
    assert turn["references"] == [] and turn["invalid"] == []
    assert len(turn["chunks"]) == 5 and not any(chunk["cited"] for chunk in turn["chunks"])


def test_a_decline_in_the_models_own_words_is_an_abstention(chat, fake_answer_model):
    # As the pinned model declines a near miss, instead of writing the fixed sentence (#73).
    fake_answer_model.script[FREEZING] = "The provided chunks do not explicitly state whether WECHSEL freezes its non-embedding weights."

    turn = ask(chat, FREEZING)

    assert turn["abstention"] is True
    assert turn["references"] == [] and len(turn["chunks"]) == 5


def test_an_answer_that_only_mentions_abstaining_is_not_an_abstention(chat, fake_answer_model):
    fake_answer_model.script[FREEZING] = "WECHSEL does not need freezing [1]. The papers in this corpus do not answer whether it helps."

    assert ask(chat, FREEZING)["abstention"] is False


def test_a_decline_followed_by_an_answer_is_an_answer(chat, fake_answer_model):
    fake_answer_model.script[FREEZING] = "The provided chunks do not contain TransInner's results. WECHSEL does not need freezing [1]."

    turn = ask(chat, FREEZING)

    assert turn["abstention"] is False
    assert [reference["number"] for reference in turn["references"]] == [1]


def test_a_decline_carrying_stray_markers_is_an_abstention_and_its_markers_are_kept(chat, fake_answer_model):
    # The markers stand before the decline and cite no sentence of it, as in the pinned model's byt5 reply.
    fake_answer_model.script[FREEZING] = "[3][7]\n\nThe provided chunks don't say whether WECHSEL freezes them."

    turn = ask(chat, FREEZING)

    assert turn["abstention"] is True
    assert markers(turn) == [(3, True), (7, False)]
    assert turn["invalid"] == [7]


@pytest.mark.parametrize("body", [b"not json", b'["a list"]', b'{"question": "  "}'], ids=["not-json", "not-an-object", "blank"])
def test_a_turn_without_a_question_is_refused_and_asks_nothing(chat, fake_answer_model, body):
    request = urllib.request.Request(f"{chat.url}/turn", body, {"Content-Type": "application/json"})

    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(request)

    assert raised.value.code == 400
    assert fake_answer_model.chats == []


def ollama_answering(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    """The real answer model, with every request to Ollama answered by ``handler``."""
    monkeypatch.setattr(answer_model, "load_answer_model", REAL_LOAD)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: handler(request))


def refused(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 61] Connection refused")


def other_version(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/version"
    return httpx.Response(200, json={"version": "0.41.0"})


def post_error(chat: Chat, question: str) -> tuple[int, str]:
    with pytest.raises(urllib.error.HTTPError) as raised:
        ask(chat, question)
    return raised.value.code, json.loads(raised.value.read())["error"]


@pytest.mark.parametrize(
    "handler, message",
    [
        (refused, "Ollama is not answering at http://localhost:11434. Start the Ollama app or run `ollama serve`"),
        (other_version, "Ollama 0.41.0 is running, not the pinned 0.40.5. `just init` checks and pulls the pinned model."),
    ],
    ids=["stopped", "other-version"],
)
def test_an_ollama_that_cant_serve_the_pinned_model_is_named_on_the_page_and_in_the_terminal(start_chat, monkeypatch, capsys, handler, message):
    ollama_answering(monkeypatch, handler)
    chat = start_chat()

    status, error = post_error(chat, FREEZING)

    assert status == 503 and message in error
    assert message in capsys.readouterr().err
    with urllib.request.urlopen(f"{chat.url}/status") as response:
        assert message in json.loads(response.read())["error"]


class PinnedOllama:
    """Ollama 0.40.5 with the pinned gemma4:e2b-mlx, answering every chat with ``reply``."""

    def __init__(self, reply: str) -> None:
        self.reply = reply

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.5"})
        if request.url.path == "/api/tags":
            digest, _ = load_chat_config(RETRIEVAL_CONFIG).model.revision.split("@")
            return httpx.Response(200, json={"models": [{"name": "gemma4:e2b-mlx", "digest": digest}]})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": self.reply}})


def test_the_page_answers_once_ollama_is_started_without_restarting_chat(start_chat, monkeypatch):
    ollama_answering(monkeypatch, refused)
    chat = start_chat()
    assert post_error(chat, FREEZING)[0] == 503

    ollama_answering(monkeypatch, PinnedOllama("WECHSEL does not need freezing [1]."))

    assert markers(ask(chat, FREEZING)) == [(1, True)]


def test_chat_started_while_ollama_is_stopped_says_so_and_still_serves_the_page(indexed, monkeypatch, capsys):
    ollama_answering(monkeypatch, refused)
    monkeypatch.setattr(ThreadingHTTPServer, "serve_forever", lambda self: None)

    main(["chat", *corpus_arguments(indexed), "--port", "0"])

    captured = capsys.readouterr()
    assert "chat: Ollama is not answering at http://localhost:11434" in captured.err
    assert "chat: the page is at http://localhost:" in captured.out


# Follow-ups (#65): a Turn after the first is retrieved with the Rewrite the answer model writes from the Conversation.
MMLU = "How much did that help on MMLU?"
REWRITTEN = "How much did freezing the non-embedding parameters help WECHSEL on MMLU?"


def post(chat: Chat, action: str) -> dict:
    request = urllib.request.Request(f"{chat.url}/{action}", b"{}", {"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def test_the_first_turn_has_no_rewrite_costs_one_model_call_and_carries_its_timings_and_retrieved_ids(chat, fake_answer_model):
    fake_answer_model.script[FREEZING] = "WECHSEL does not need freezing [1]."

    turn = ask(chat, FREEZING)

    assert turn["rewrite"] is None
    assert len(fake_answer_model.chats) == 1
    assert set(turn["seconds"]) == {"retrieval", "rewriting", "answering"} and turn["seconds"]["rewriting"] == 0
    assert turn["retrieved"] == [chunk["chunk_id"] for chunk in turn["chunks"]] and len(turn["retrieved"]) == 5
    assert turn["reply"] == "WECHSEL does not need freezing [1]."


def script_follow_up(fake_answer_model) -> None:
    # The fake answers the first key found in the last message, and the rewriter's holds the earlier questions
    # too, so the follow-up's key goes first.
    fake_answer_model.script[MMLU] = REWRITTEN
    fake_answer_model.script[REWRITTEN] = "Freezing gave no gain on MMLU [2]."
    fake_answer_model.script[FREEZING] = "WECHSEL does not need freezing [1]."


def test_a_follow_up_is_retrieved_with_the_rewrite_and_shows_it(chat, fake_answer_model):
    script_follow_up(fake_answer_model)
    ask(chat, FREEZING)

    follow_up = ask(chat, MMLU)

    assert follow_up["question"] == MMLU and follow_up["rewrite"] == REWRITTEN
    assert len(fake_answer_model.chats) == 3  # the first answer, then the Rewrite and the follow-up's answer
    assert set(follow_up["seconds"]) == {"retrieval", "rewriting", "answering"}
    *_, answering = fake_answer_model.chats
    assert f"Question: {REWRITTEN}" in answering[-1]["content"] and MMLU not in answering[-1]["content"]
    # Retrieval saw the Rewrite: the follow-up has the Chunks the Rewrite gets when asked as a first question,
    # not those of the follow-up asked alone.
    post(chat, "reset")
    assert ask(chat, REWRITTEN)["retrieved"] == follow_up["retrieved"]
    post(chat, "reset")
    fake_answer_model.script[MMLU] = "Freezing gave no gain on MMLU [2]."
    assert ask(chat, MMLU)["retrieved"] != follow_up["retrieved"]


def test_the_rewriter_sees_the_earlier_questions_and_answer_texts_and_no_chunk_text(chat, fake_answer_model):
    script_follow_up(fake_answer_model)
    first = ask(chat, FREEZING)

    ask(chat, MMLU)

    rewriting = "\n".join(message["content"] for message in fake_answer_model.chats[1])
    assert FREEZING in rewriting and MMLU in rewriting
    assert "WECHSEL does not need freezing." in rewriting  # the answer's text, its markers taken out
    assert "[1]" not in rewriting
    for chunk in first["chunks"]:
        assert chunk["text"] not in rewriting


def test_the_answer_model_sees_the_earlier_turns_before_the_rewrite_and_this_turns_chunks(chat, fake_answer_model):
    script_follow_up(fake_answer_model)
    ask(chat, FREEZING)

    follow_up = ask(chat, MMLU)

    system, earlier_question, earlier_answer, this_turn = fake_answer_model.chats[2]
    assert system["role"] == "system"
    assert earlier_question == {"role": "user", "content": f"Question: {FREEZING}"}
    assert earlier_answer == {"role": "assistant", "content": "WECHSEL does not need freezing."}
    assert this_turn["role"] == "user"
    for chunk in follow_up["chunks"]:
        assert f"[{chunk['number']}] {chunk['header']}\n{chunk['text']}" in this_turn["content"]


def test_reset_empties_the_conversation_so_the_next_question_is_a_first_turn(chat, fake_answer_model):
    script_follow_up(fake_answer_model)
    ask(chat, FREEZING)
    ask(chat, MMLU)

    assert post(chat, "reset") == {"turns": 0}
    fake_answer_model.chats.clear()
    again = ask(chat, FREEZING)

    assert again["rewrite"] is None
    assert len(fake_answer_model.chats) == 1 and len(fake_answer_model.chats[0]) == 2


@pytest.mark.skipif(os.environ.get("RUN_OLLAMA_TESTS") != "1", reason="asks the pinned model on Ollama; set RUN_OLLAMA_TESTS=1")
def test_the_real_pinned_model_cites_a_retrieved_chunk_and_abstains_off_topic(start_chat, monkeypatch):
    monkeypatch.setattr(answer_model, "load_answer_model", REAL_LOAD)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", REAL_TRANSPORT)
    chat = start_chat()

    # Each a first Turn, so none is rewritten.
    answered = ask(chat, FREEZING)
    post(chat, "reset")
    again = ask(chat, FREEZING)
    post(chat, "reset")
    off_topic = ask(chat, "What is the capital of France?")

    print("answer:", "".join(part.get("text", f"[{part.get('marker')}]") for part in answered["answer"]))
    print("off topic:", "".join(part.get("text", f"[{part.get('marker')}]") for part in off_topic["answer"]))
    assert answered["abstention"] is False
    assert answered["references"] and answered["invalid"] == []
    # Thinking off, temperature 0 and a fixed seed: the same question gets the same answer.
    assert again["answer"] == answered["answer"]
    assert off_topic["abstention"] is True


@pytest.mark.skipif(os.environ.get("RUN_OLLAMA_TESTS") != "1", reason="asks the pinned model on Ollama; set RUN_OLLAMA_TESTS=1")
def test_the_real_pinned_model_abstains_on_a_near_miss_in_whatever_words(start_chat, monkeypatch):
    # The BPE paper reports English→German and English→Russian, not English→French (#73).
    monkeypatch.setattr(answer_model, "load_answer_model", REAL_LOAD)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", REAL_TRANSPORT)
    chat = start_chat()

    near_miss = ask(chat, "What BLEU score did Sennrich et al.'s subword NMT paper report for English to French translation?")

    print("near miss:", "".join(part.get("text", f"[{part.get('marker')}]") for part in near_miss["answer"]))
    assert near_miss["abstention"] is True
