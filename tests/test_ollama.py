"""The shared Ollama module (ADR 0053) against a stand-in Ollama server: the answer model's pin check
and its chat completion. The judge's own requests are in test_ollama_judge.py."""

import json

import httpx
import pytest

from chatbot_rag_tokenizers.chat.config import AnswerModelConfig
from chatbot_rag_tokenizers.chat.model import AnswerModelUnavailable, OllamaAnswerModel
from chatbot_rag_tokenizers.ollama import Ollama

DIGEST = "e98b54fe1913178321e1d9cd007d12a465de77a8f8eae37af69d2501ca03c6b5"


def settings(revision: str = f"{DIGEST}@0.40.5", model: str = "gemma4:e2b-mlx") -> AnswerModelConfig:
    return AnswerModelConfig(model=model, revision=revision, think=False, temperature=0.0)


class StubOllama:
    """Ollama 0.40.5 with gemma4:e2b-mlx installed, answering every chat with the same text."""

    def __init__(self, answer: str = "WECHSEL needs no freezing [1].") -> None:
        self.answer = answer
        self.chats: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.5"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e2b-mlx", "digest": DIGEST}]})
        assert request.url.path == "/api/chat"
        self.chats.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"role": "assistant", "content": self.answer}, "done": True})


def ollama(server) -> Ollama:
    return Ollama(httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(server)))


def test_the_answer_model_completes_a_chat_with_thinking_off_at_temperature_0():
    server = StubOllama()
    model = OllamaAnswerModel(settings(), ollama(server))
    messages = [{"role": "system", "content": "Answer from the Chunks."}, {"role": "user", "content": "Is freezing needed?"}]

    assert model.complete(messages) == "WECHSEL needs no freezing [1]."

    [chat] = server.chats
    assert chat["model"] == "gemma4:e2b-mlx"
    assert chat["messages"] == messages
    assert chat["think"] is False
    assert chat["stream"] is False
    assert chat["options"]["temperature"] == 0
    assert model.pin == f"gemma4:e2b-mlx@{DIGEST[:12]} on Ollama 0.40.5"


@pytest.mark.parametrize(
    "revision, model, message",
    [
        ("0" * 64 + "@0.40.5", "gemma4:e2b-mlx", "gemma4:e2b-mlx in Ollama has digest e98b54fe.*not the pinned 00000000"),
        (f"{DIGEST}@0.34.2", "gemma4:e2b-mlx", "Ollama 0.40.5 is running, not the pinned 0.34.2"),
        (DIGEST, "gemma4:e2b-mlx", "<digest>@<Ollama version>"),
        (f"{DIGEST}@0.40.5", "gemma4:e4b", "gemma4:e4b is not installed in Ollama"),
    ],
    ids=["digest", "version", "no-version", "not-installed"],
)
def test_the_answer_model_is_refused_unless_ollama_serves_its_pin(revision, model, message):
    with pytest.raises(AnswerModelUnavailable, match=message):
        OllamaAnswerModel(settings(revision, model), ollama(StubOllama()))


def refused(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 61] Connection refused")


def test_a_stopped_ollama_is_named_with_how_to_start_it():
    with pytest.raises(AnswerModelUnavailable, match="Ollama is not answering at .*ollama serve"):
        OllamaAnswerModel(settings(), ollama(refused))


def test_ollama_stopping_after_the_pin_check_is_named_too():
    server = StubOllama()
    model = OllamaAnswerModel(settings(), ollama(server))
    model.ollama.client = httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(refused))

    with pytest.raises(AnswerModelUnavailable, match="Ollama is not answering"):
        model.complete([{"role": "user", "content": "Is freezing needed?"}])
