"""Command-line entry point."""

import argparse
from pathlib import Path

from .collection import audit
from .collection.config import load_config
from .collection.pipeline import collect


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="chatbot-rag-tokenizers")
    commands = parser.add_subparsers(dest="command", required=True)

    collect_cmd = commands.add_parser(
        "collect",
        help="run the keyword queries, apply the rule pre-filter and the LLM judge, and write the manifest",
        description=(
            "Reads source responses and judge verdicts from the Snapshot; fetches and scores only what is missing."
        ),
    )
    collect_cmd.add_argument("--config", type=Path, default=Path("config/scope.toml"))
    collect_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"))
    collect_cmd.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    judging = collect_cmd.add_mutually_exclusive_group()
    judging.add_argument("--refresh", action="store_true", help="re-score every Candidate that passes the rules, ignoring cached verdicts")
    judging.add_argument(
        "--no-judge",
        action="store_true",
        help="never load the judge model; Candidates without a cached verdict stay pending",
    )

    audit_cmd = commands.add_parser("audit", help="build the Audit set and measure the Relevance verdict on it")
    audit_commands = audit_cmd.add_subparsers(dest="audit_command", required=True)
    export_cmd = audit_commands.add_parser(
        "export",
        help="write a stratified sample of Candidates, with draft labels, for labelling",
        description=(
            "Draws an even share from each stratum (rule rejects, judge rejects, judge accepts, and rule passes"
            " still pending a verdict). Never loads the judge model."
        ),
    )
    export_cmd.add_argument("--config", type=Path, default=Path("config/scope.toml"))
    export_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"))
    export_cmd.add_argument("--output", type=Path, default=Path("data/audit/audit-set.csv"))
    export_cmd.add_argument("--size", type=int, default=180, help="number of Candidates to sample (default 180)")
    export_cmd.add_argument("--seed", type=int, default=0, help="random seed for the sample (default 0)")
    export_cmd.add_argument("--force", action="store_true", help="replace an existing Audit set file and its labels")

    report_cmd = audit_commands.add_parser(
        "report",
        help="report precision, recall and F1 on the Audit set for the rules and each judge model",
        description=(
            "Scores the Audit set's rule passes with each model in [[audit.models]] that has no verdict yet,"
            " then writes the report."
        ),
    )
    report_cmd.add_argument("--config", type=Path, default=Path("config/scope.toml"))
    report_cmd.add_argument("--audit-set", type=Path, default=Path("data/audit/audit-set.csv"))
    report_cmd.add_argument("--verdicts", type=Path, default=Path("data/audit/verdicts.jsonl"))
    report_cmd.add_argument("--output", type=Path, default=Path("data/audit/report.md"))
    report_cmd.add_argument(
        "--thresholds",
        type=lambda text: [float(value) for value in text.split(",")],
        help="comma-separated thresholds (default 0.1 to 0.9 in steps of 0.1, plus the configured one)",
    )
    report_cmd.add_argument("--no-judge", action="store_true", help="never load a model; report only cached verdicts")

    args = parser.parse_args(argv)
    if args.command == "collect":
        collect(load_config(args.config), args.snapshot, args.manifest, refresh=args.refresh, run_judge=not args.no_judge)
    elif args.command == "audit" and args.audit_command == "export":
        audit.export(load_config(args.config), args.snapshot, args.output, args.size, args.seed, force=args.force)
    elif args.command == "audit" and args.audit_command == "report":
        audit.report(
            load_config(args.config), args.audit_set, args.verdicts, args.output, args.thresholds, run_judge=not args.no_judge
        )
