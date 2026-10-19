"""The answer-model boundary (ADR 0053), shaped like the embedder's: the one way the chatbot gets text from a model.

An answer model completes a chat, a list of messages, with one text, and describes its pin. `load_answer_model`
makes the real one, the pinned model on the local Ollama; the tests put a scripted fake in its place, so no test
needs Ollama. A model that can't be reached or isn't the pinned one raises AnswerModelUnavailable, worded for the
person at the page.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Protocol

import httpx

from ..ollama import OLLAMA_URL, Ollama, OllamaModelError
from .config import AnswerModelConfig

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": ...}


class AnswerModelUnavailable(RuntimeError):
    """The answer model can't answer now: Ollama is stopped, runs another version or lacks the pinned model."""


class AnswerModel(Protocol):
    @property
    def pin(self) -> str:
        """The model and its pin, as the page and the reports name it."""
        ...

    def complete(self, messages: Sequence[Message]) -> str:
        """The model's reply to the chat."""
        ...


def load_answer_model(settings: AnswerModelConfig) -> AnswerModel:
    return OllamaAnswerModel(settings)


class OllamaAnswerModel:
    """The pinned model on the local Ollama, checked against its pin when made."""

    def __init__(self, settings: AnswerModelConfig, ollama: Ollama | None = None) -> None:
        self.settings = settings
        self.ollama = ollama or Ollama()
        with _named_failures():
            digest, version = self.ollama.check_pin(settings.model, settings.revision)
        self.pin = f"{settings.model}@{digest[:12]} on Ollama {version}"

    def complete(self, messages: Sequence[Message]) -> str:
        # A fixed seed as well as temperature 0, as the judge sends, so a rerun gives the same text.
        options = {"temperature": self.settings.temperature, "seed": 0}
        with _named_failures():
            response = self.ollama.chat(self.settings.model, messages, think=self.settings.think, options=options)
        return response["message"]["content"]


@contextmanager
def _named_failures() -> Iterator[None]:
    """Turns Ollama's failures into AnswerModelUnavailable, saying what to do."""
    try:
        yield
    except httpx.TransportError as error:
        raise AnswerModelUnavailable(
            f"Ollama is not answering at {OLLAMA_URL}. Start the Ollama app or run `ollama serve`, then ask again."
        ) from error
    except OllamaModelError as error:
        raise AnswerModelUnavailable(f"the answer model is not ready: {error}. `just init` checks and pulls the pinned model.") from error
    except httpx.HTTPStatusError as error:
        raise AnswerModelUnavailable(f"Ollama refused the request: {error.response.status_code} {error.response.text}") from error
