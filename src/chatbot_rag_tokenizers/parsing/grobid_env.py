"""Print the GROBID settings from config/parse.toml as shell assignments, for the justfile to eval (ADR 0023).

Usage: python -m chatbot_rag_tokenizers.parsing.grobid_env [path/to/parse.toml]
"""

import shlex
import sys
from pathlib import Path

from chatbot_rag_tokenizers.parsing.config import DEFAULT_PATH, load_grobid_config


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    grobid = load_grobid_config(Path(args[0]) if args else DEFAULT_PATH)
    settings = {
        "GROBID_REFERENCE": grobid.reference,
        "GROBID_TAG": grobid.tag,
        "GROBID_PORT": grobid.port,
        "GROBID_URL": grobid.url,
    }
    for name, value in settings.items():
        print(f"{name}={shlex.quote(str(value))}")


if __name__ == "__main__":
    main()
