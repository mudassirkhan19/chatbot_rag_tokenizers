"""The one way any model here is reached on Ollama (ADRs 0021 and 0053): a client for the local server, the pin
parser and the check that the server runs the pinned weights on the pinned runtime.

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
_TIMEOUT = 120.0  # seconds; an answer from a few-billion-parameter model on a laptop takes a few


class OllamaModelError(ValueError):
    pass


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


def response_json(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    return response.json()
