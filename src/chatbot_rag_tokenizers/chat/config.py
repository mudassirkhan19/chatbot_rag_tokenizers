"""The chatbot's config: the `[chat]` table of the retrieval config (ADR 0053).

It names the retriever the chatbot asks, out of the retrievers the same file configures, how many Chunks a Turn
retrieves, the pinned answer model and how it is run, the system prompt and the fixed Abstention sentence.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError, read_table
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.retriever import RetrieverConfig

DEFAULT_PATH = Path("config/retrieval.toml")
OLLAMA_PIN = re.compile(r"[0-9a-f]{64}@\d+\.\d+\.\d+")
_FIELDS = {
    "retriever": str,
    "k": int,
    "model": str,
    "revision": str,
    "think": bool,
    "temperature": float,
    "abstention": str,
    "system_prompt": str,
}


@dataclass(frozen=True)
class AnswerModelConfig:
    model: str  # the Ollama model name
    revision: str  # pinned as <digest>@<Ollama version>, as the judge is
    think: bool
    temperature: float


@dataclass(frozen=True)
class ChatConfig:
    retriever: RetrieverConfig
    k: int  # Chunks retrieved per Turn
    model: AnswerModelConfig
    abstention: str  # the fixed sentence the model writes when the Chunks don't answer the question
    system_prompt: str  # with the Abstention sentence filled in


def load_chat_config(path: Path = DEFAULT_PATH) -> ChatConfig:
    retrievers = load_retrieval_config(path).retrievers
    fields = read_table(tomllib.loads(path.read_text()), "chat", _FIELDS, path)
    if fields["retriever"] not in retrievers:
        raise ConfigError(f"[chat] retriever {fields['retriever']!r} is not a retriever {path} configures: {', '.join(retrievers)}")
    if fields["k"] < 1:
        raise ConfigError(f"[chat] k {fields['k']} must be at least 1")
    if not OLLAMA_PIN.fullmatch(fields["revision"]):
        raise ConfigError(f"[chat] revision {fields['revision']!r} is not pinned as <digest>@<Ollama version>")
    if "{abstention}" not in fields["system_prompt"]:
        raise ConfigError("[chat] system_prompt must name the Abstention sentence as {abstention}")
    model = AnswerModelConfig(fields["model"], fields["revision"], fields["think"], fields["temperature"])
    return ChatConfig(
        retriever=retrievers[fields["retriever"]],
        k=fields["k"],
        model=model,
        abstention=fields["abstention"],
        system_prompt=fields["system_prompt"].replace("{abstention}", fields["abstention"]),
    )
