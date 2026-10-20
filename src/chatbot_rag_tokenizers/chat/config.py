"""The chatbot's config: the `[chat]` table of the retrieval config (ADRs 0054, 0056 and 0069).

It names the retriever the chatbot asks, out of the retrievers the same file configures or their `+collapsed`
twins (ADR 0053), which retrieve over their retriever's index with the `[collapse]` pool, how many Chunks a Turn
retrieves, the pinned answer model and how it is run, the system prompt and the fixed Abstention sentence, how
many earlier Turns a follow-up is shown, and the rewriter's prompt.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table
from chatbot_rag_tokenizers.ollama import PIN
from chatbot_rag_tokenizers.retrieval.collapse import SUFFIX
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")
_FIELDS = {
    "retriever": str,
    "k": int,
    "model": str,
    "revision": str,
    "think": bool,
    "temperature": float,
    "abstention": str,
    "history": int,
    "system_prompt": str,
    "rewrite_prompt": str,
}


@dataclass(frozen=True)
class AnswerModelConfig:
    model: str  # the Ollama model name
    revision: str  # pinned as <digest>@<Ollama version>, as the judge is
    think: bool
    temperature: float


@dataclass(frozen=True)
class ChatConfig:
    retriever: RetrieverConfig  # whose index the chatbot retrieves over
    k: int  # Chunks retrieved per Turn
    model: AnswerModelConfig
    abstention: str  # the fixed sentence the model writes when the Chunks don't answer the question
    system_prompt: str  # with the Abstention sentence filled in
    history: int  # the earlier Turns the answer model and the rewriter are shown on a follow-up
    rewrite_prompt: str
    collapse_pool: int | None = None  # the raw Chunks the Collapsed ranking merges copies in; None for the raw ranking
    collapse_overlap: float | None = None  # the share of word 5-grams that makes two Chunks copies (ADR 0074); None for the raw ranking

    @property
    def retriever_name(self) -> str:
        """The name `[chat]` gives the retriever: a `+collapsed` twin's when the ranking is collapsed."""
        return self.retriever.name + (SUFFIX if self.collapse_pool else "")


def load_chat_config(path: Path = DEFAULT_PATH) -> ChatConfig:
    retrieval = load_retrieval_config(path)
    retrievers = retrieval.retrievers
    fields = read_table(tomllib.loads(path.read_text()), "chat", _FIELDS, path)
    name = fields["retriever"].removesuffix(SUFFIX)
    if name not in retrievers:
        raise ConfigError(
            f"[chat] retriever {fields['retriever']!r} is not a retriever {path} configures: {', '.join(retrievers)}, or one of them {SUFFIX}"
        )
    if fields["k"] < 1:
        raise ConfigError(f"[chat] k {fields['k']} must be at least 1")
    if fields["history"] < 1:
        raise ConfigError(f"[chat] history {fields['history']} must be at least 1, or a follow-up has nothing to resolve against")
    if not PIN.fullmatch(fields["revision"]):
        raise ConfigError(f"[chat] revision {fields['revision']!r} is not pinned as <digest>@<Ollama version>")
    if "{abstention}" not in fields["system_prompt"]:
        raise ConfigError("[chat] system_prompt must name the Abstention sentence as {abstention}")
    model = AnswerModelConfig(fields["model"], fields["revision"], fields["think"], fields["temperature"])
    return ChatConfig(
        retriever=retrievers[name],
        k=fields["k"],
        model=model,
        abstention=fields["abstention"],
        system_prompt=fields["system_prompt"].replace("{abstention}", fields["abstention"]),
        history=fields["history"],
        rewrite_prompt=fields["rewrite_prompt"],
        collapse_pool=retrieval.collapse_pool if fields["retriever"].endswith(SUFFIX) else None,
        collapse_overlap=retrieval.collapse_overlap if fields["retriever"].endswith(SUFFIX) else None,
    )
