"""A Conversation: the Turns asked on the chat page since `chat` started or the page was reset, and the chatbot
that answers each (ADRs 0054 and 0055).

A Turn retrieves k Chunks from the configured retriever, sends them to the answer model and reads its reply. The
first Turn of a Conversation retrieves its question as asked. A later Turn is a follow-up: the answer model first
writes a Rewrite from the last `history` Turns' questions and answer texts and the new question, retrieval sees
the Rewrite, and the answer model is shown those Turns before the Rewrite and its Chunks. The answer model is
loaded on first use and loaded again after it fails, so a page started while Ollama was stopped answers once
Ollama is started.
"""

import threading
import time
from dataclasses import dataclass, field

from ..parsing.chunker import Chunk
from ..retrieval.retriever import Retriever
from . import model as answer_model
from .answer import Answer, messages, read_answer
from .config import ChatConfig
from .model import AnswerModel, AnswerModelUnavailable, Message
from .rewrite import read_rewrite, rewrite_messages


@dataclass(frozen=True)
class Turn:
    question: str
    rewrite: str | None  # what retrieval saw on a follow-up Turn; None on the first Turn, which retrieves the question
    retrieved: tuple[Chunk, ...]  # in rank order; Chunk n of the prompt is retrieved[n - 1]
    reply: str  # the model's raw output
    answer: Answer
    seconds: dict[str, float]  # retrieval, rewriting and answering


@dataclass
class Chatbot:
    config: ChatConfig
    retriever: Retriever
    chunks: dict[str, Chunk]  # every Chunk of the corpus, by id
    turns: list[Turn] = field(default_factory=list)  # the Conversation so far
    _model: AnswerModel | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _asking: threading.Lock = field(default_factory=threading.Lock)  # one Turn at a time, so each sees the last

    def model(self) -> AnswerModel:
        """The answer model, loaded and checked against its pin if it isn't yet. Raises AnswerModelUnavailable."""
        with self._lock:
            if self._model is None:
                self._model = answer_model.load_answer_model(self.config.model)
            return self._model

    def ask(self, question: str) -> Turn:
        with self._asking:
            model = self.model()
            shown = self.turns[-self.config.history :]
            rewrite, rewriting = None, 0.0
            if shown:
                started = time.perf_counter()
                # The rewriter reads the questions as the user asked them, as a reader of the transcript would.
                asked = [(turn.question, turn.answer.text) for turn in shown]
                rewrite = read_rewrite(self._complete(model, rewrite_messages(self.config.rewrite_prompt, asked, question)), question)
                rewriting = time.perf_counter() - started
            query = rewrite or question
            started = time.perf_counter()
            retrieved = tuple(self.chunks[chunk_id] for chunk_id, _ in self.retriever.query(query, self.config.k))
            retrieval = time.perf_counter() - started
            # The answer model is shown each earlier Turn as it was answered: its Rewrite, or its question on a first Turn.
            earlier = [(turn.rewrite or turn.question, turn.answer.text) for turn in shown]
            started = time.perf_counter()
            reply = self._complete(model, messages(self.config.system_prompt, query, retrieved, earlier))
            answering = time.perf_counter() - started
            seconds = {"retrieval": retrieval, "rewriting": rewriting, "answering": answering}
            turn = Turn(question, rewrite, retrieved, reply, read_answer(reply, len(retrieved), self.config.abstention), seconds)
            self.turns.append(turn)
            return turn

    def reset(self) -> None:
        """Starts a new Conversation: the next question is a first Turn again."""
        with self._asking:
            self.turns.clear()

    def _complete(self, model: AnswerModel, chat: list[Message]) -> str:
        try:
            return model.complete(chat)
        except AnswerModelUnavailable:
            with self._lock:
                self._model = None  # checked against its pin again on the next Turn
            raise
