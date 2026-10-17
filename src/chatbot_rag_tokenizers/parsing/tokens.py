"""Token counts from the one pinned tokenizer named in the chunking config (ADR 0025)."""

import hashlib

from tokenizers import Tokenizer

from chatbot_rag_tokenizers.config import ConfigError

from .config import ChunkingConfig


class TokenCounter:
    def __init__(self, config: ChunkingConfig) -> None:
        data = config.tokenizer_file.read_bytes()
        if (found := hashlib.sha256(data).hexdigest()) != config.tokenizer_sha256:
            raise ConfigError(
                f"the tokenizer file {config.tokenizer_file} has sha256 {found[:12]}, not the pinned"
                f" {config.tokenizer_sha256[:12]}"
            )
        self._tokenizer = Tokenizer.from_str(data.decode())
        # A tokenizer file may set truncation (to the model's 512) or padding; a count must see every token.
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()

    def count(self, text: str) -> int:
        """Tokens in the text alone, without the special tokens an embedder adds around it."""
        return len(self._tokenizer.encode(text, add_special_tokens=False).ids)
