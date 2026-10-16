"""Command-line entry point."""

import argparse
from pathlib import Path

from .collection.config import load_config
from .collection.pipeline import collect


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="chatbot-rag-tokenizers")
    commands = parser.add_subparsers(dest="command", required=True)

    collect_cmd = commands.add_parser(
        "collect",
        help="run the keyword queries, apply the rule pre-filter and write the manifest",
        description="Reads source responses from the Snapshot and fetches only what is missing.",
    )
    collect_cmd.add_argument("--config", type=Path, default=Path("config/scope.toml"))
    collect_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"))
    collect_cmd.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))

    args = parser.parse_args(argv)
    if args.command == "collect":
        collect(load_config(args.config), args.snapshot, args.manifest)
