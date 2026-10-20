"""The one way any model here is reached on Ollama (ADRs 0021 and 0054): a client for the local server, the pin
parser and the check that the server runs the pinned weights on the pinned runtime. A chat model completes a chat;
a decision model such as Tev1 answers one true/false question about a text.

An Ollama model is pinned as ``<digest>@<Ollama version>``. The digest pins the weights and the version pins
the runtime that runs them: upgrading Ollama moved some of the judge's P("Yes") scores by 0.16 (ADR 0021).
The judge refuses to start, and the chatbot's answer model to answer, unless both match.
"""

import re
from collections.abc import Sequence
from typing import Any

import httpx

OLLAMA_URL = "http://localhost:11434"
PIN = re.compile(r"[0-9a-f]{64}@\d+\.\d+\.\d+")  # <digest>@<Ollama version>
# Ollama's answer when a decision model's input is longer than its context, which it never truncates.
_TOO_LONG = re.compile(r"has (?P<tokens>\d+) tokens; expected 1\u2013(?P<limit>\d+)")
_TIMEOUT = 120.0  # seconds; an answer from a few-billion-parameter model on a laptop takes a few


class OllamaModelError(ValueError):
    pass


class InputTooLong(OllamaModelError):
    """A decision model's input is longer than its context: ``tokens`` of at most ``limit``."""

    def __init__(self, tokens: int, limit: int) -> None:
        super().__init__(f"the input has {tokens} tokens, more than the model's {limit}-token context")
        self.tokens, self.limit = tokens, limit


def split_pin(revision: str) -> tuple[str, str]:
    """An Ollama pin ``<digest>@<Ollama version>`` as (digest, version); version is "" for any other revision."""
    digest, _, version = revision.partition("@")
    return digest, version


class Ollama:
    """The local Ollama server, over its HTTP API."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(base_url=OLLAMA_URL, timeout=_TIMEOUT)

    def get(self, path: str) -> dict[str, Any]:
        return response_json(self.client.get(path))

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return response_json(self.client.post(path, json=body))

    def check_pin(self, model: str, revision: str) -> tuple[str, str]:
        """Raise OllamaModelError unless the server runs ``model`` at the digest and Ollama version ``revision`` pins;
        return the two."""
        digest, version = split_pin(revision)
        if not version:
            raise OllamaModelError(f"pin {model} as <digest>@<Ollama version>, not {revision!r}")
        running = self.get("/api/version")["version"]
        if running != version:
            raise OllamaModelError(f"Ollama {running} is running, not the pinned {version}")
        installed = {entry["name"]: entry["digest"] for entry in self.get("/api/tags")["models"]}
        if model not in installed:
            raise OllamaModelError(f"{model} is not installed in Ollama; run `ollama pull {model}`")
        if installed[model] != digest:
            raise OllamaModelError(f"{model} in Ollama has digest {installed[model]}, not the pinned {digest}")
        return digest, version

    def chat(self, model: str, messages: Sequence[dict[str, str]], *, think: bool, options: dict[str, Any], **fields: Any) -> dict[str, Any]:
        """One whole chat completion from `/api/chat`, not streamed. ``fields`` are further request fields, such as
        the judge's logprobs."""
        body = {"model": model, "messages": list(messages), "think": think, "stream": False, **fields, "options": options}
        return self.post("/api/chat", body)

    def decide(self, model: str, state: str, name: str, instructions: str, true: str, false: str) -> float:
        """The probability a decision model gives that the true/false question ``name`` is true of ``state``, from
        `/v1/systemone`. Raises InputTooLong when the input is longer than the model's context."""
        question = {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}
        response = self.client.post("/v1/systemone", json={"model": model, "state": state, "questions": {name: question}})
        too_long = _TOO_LONG.search(response.text) if response.status_code == 400 else None
        if too_long is not None:
            raise InputTooLong(int(too_long["tokens"]), int(too_long["limit"]))
        return float(response_json(response)["answers"][name]["noul"])


def response_json(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    return response.json()
