"""A Conversation: the Turns one page session has asked, and the chatbot that answers each (ADR 0053).

A Turn retrieves k Chunks for its question from the configured retriever, sends them to the answer model and
reads its reply. The answer model is loaded on first use and loaded again after it fails, so a page started
while Ollama was stopped answers once Ollama is started.
"""

import threading
import time
from dataclasses import dataclass, field

from ..parsing.chunker import Chunk
from ..retrieval.retriever import Retriever
from . import model as answer_model
from .answer import Answer, messages, read_answer
from .config import ChatConfig
from .model import AnswerModel, AnswerModelUnavailable


@dataclass(frozen=True)
class Turn:
    question: str
    retrieved: tuple[Chunk, ...]  # in rank order; Chunk n of the prompt is retrieved[n - 1]
    reply: str  # the model's raw output
    answer: Answer
    seconds: dict[str, float]  # retrieval and answering


@dataclass
class Chatbot:
    config: ChatConfig
    retriever: Retriever
    chunks: dict[str, Chunk]  # every Chunk of the corpus, by id
    turns: list[Turn] = field(default_factory=list)  # the Conversation so far
    _model: AnswerModel | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def model(self) -> AnswerModel:
        """The answer model, loaded and checked against its pin if it isn't yet. Raises AnswerModelUnavailable."""
        with self._lock:
            if self._model is None:
                self._model = answer_model.load_answer_model(self.config.model)
            return self._model

    def ask(self, question: str) -> Turn:
        model = self.model()
        started = time.perf_counter()
        retrieved = tuple(self.chunks[chunk_id] for chunk_id, _ in self.retriever.query(question, self.config.k))
        retrieval = time.perf_counter() - started
        try:
            reply = model.complete(messages(self.config.system_prompt, question, retrieved))
        except AnswerModelUnavailable:
            with self._lock:
                self._model = None  # checked against its pin again on the next Turn
            raise
        answering = time.perf_counter() - started - retrieval
        turn = Turn(question, retrieved, reply, read_answer(reply, len(retrieved), self.config.abstention), {"retrieval": retrieval, "answering": answering})
        self.turns.append(turn)
        return turn
