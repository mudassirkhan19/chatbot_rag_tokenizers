"""Print the answer model's Ollama pin from the [chat] table of config/retrieval.toml as shell assignments, for
`just init` to eval, as judge_env does for the judge (ADRs 0022 and 0054).

Usage: python -m chatbot_rag_tokenizers.chat.chat_env [path/to/retrieval.toml]
"""

import shlex
import sys
from pathlib import Path

from chatbot_rag_tokenizers.chat.config import DEFAULT_PATH, load_chat_config
from chatbot_rag_tokenizers.ollama import OLLAMA_URL, split_pin


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    model = load_chat_config(Path(args[0]) if args else DEFAULT_PATH).model
    digest, version = split_pin(model.revision)
    settings = {"CHAT_MODEL": model.model, "CHAT_DIGEST": digest, "CHAT_VERSION": version, "OLLAMA_URL": OLLAMA_URL}
    for name, value in settings.items():
        print(f"{name}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
