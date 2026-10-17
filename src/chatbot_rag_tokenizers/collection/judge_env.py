"""Print the judge's Ollama pin from config/scope.toml as shell assignments, for `just init` to eval (ADR 0022).

All four are empty when the judge does not run on Ollama, so init skips the Ollama checks.

Usage: python -m chatbot_rag_tokenizers.collection.judge_env [path/to/scope.toml]
"""

import shlex
import sys
from pathlib import Path

from chatbot_rag_tokenizers.collection.config import load_config
from chatbot_rag_tokenizers.collection.judge import OLLAMA_URL, split_pin

DEFAULT_PATH = Path("config/scope.toml")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    judge = load_config(Path(args[0]) if args else DEFAULT_PATH).judge
    on_ollama = judge.backend in ("ollama", "ollama-decision")
    digest, version = split_pin(judge.revision) if on_ollama else ("", "")
    settings = {
        "OLLAMA_MODEL": judge.model if on_ollama else "",
        "OLLAMA_DIGEST": digest,
        "OLLAMA_VERSION": version,
        "OLLAMA_URL": OLLAMA_URL if on_ollama else "",
    }
    for name, value in settings.items():
        print(f"{name}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
