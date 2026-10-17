"""Command-line entry point."""

import argparse
import sys
from pathlib import Path

from .collection import audit, audit_label, fulltext
from .collection.config import load_config
from .collection.pipeline import collect
from .parsing import inputs
from .parsing import pipeline as parsing
from .parsing.config import load_parse_config
from .parsing.grobid import GrobidUnreachable


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

    fetch_cmd = commands.add_parser(
        "fetch",
        help="download the pinned PDFs of every included Edition and record their hashes",
        description=(
            "Reads the manifest written by `collect`. Fetches v1 and the latest Version of each included arXiv"
            " preprint and the ACL Anthology or open-access PDF of each included venue Edition, checks re-downloads"
            " against the hashes recorded in the Snapshot, and updates the manifest."
        ),
    )
    fetch_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"))
    fetch_cmd.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    fetch_cmd.add_argument("--pdfs", type=Path, default=Path("data/pdfs"), help="where PDFs go (default data/pdfs, gitignored)")
    fetch_cmd.add_argument("--limit", type=int, help="download at most this many files, e.g. for a smoke test")

    parse_cmd = commands.add_parser(
        "parse",
        help="parse PDFs with the pinned GROBID service into Section-aware Chunks and write the parse report",
        description=(
            "Sends each PDF to GROBID unless its TEI is already in the parse cache, cuts the text into Chunks"
            " that never cross a Section, stores them in the cache and writes the committed parse report."
        ),
    )
    parse_cmd.add_argument("--config", type=Path, default=Path("config/parse.toml"))
    parse_cmd.add_argument("--cache", type=Path, default=Path("data/parse-cache"), help="the parse cache (default data/parse-cache, gitignored)")
    parse_cmd.add_argument(
        "--report",
        type=Path,
        help="where the parse report goes (default data/parse-report.md; with --limit, none is written unless this is given)",
    )
    parse_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"))
    parse_cmd.add_argument("--pdfs", type=Path, default=Path("data/pdfs"), help="where `fetch` put the PDFs (default data/pdfs)")
    parse_cmd.add_argument(
        "--limit",
        type=int,
        help="parse at most this many files, the first in pinned-id order, e.g. for a smoke test; writes no report unless --report is given",
    )
    parse_cmd.add_argument(
        "--retry-failed",
        action="store_true",
        help="try again the files whose failure an earlier run recorded, instead of reporting the recorded failure",
    )
    parse_cmd.add_argument(
        "--files",
        type=Path,
        nargs="+",
        help=(
            "parse these PDFs instead of the files in the full-text record, each named by its pinned id,"
            " or as a Seed PDF (<seed>_<pinned id>.pdf)"
        ),
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

    label_cmd = audit_commands.add_parser(
        "label",
        help="serve a local page for checking and correcting the Audit set's labels one Candidate at a time",
        description="Each save rewrites that row of the Audit set file and marks it labelled_by=developer.",
    )
    label_cmd.add_argument("--config", type=Path, default=Path("config/scope.toml"))
    label_cmd.add_argument("--audit-set", type=Path, default=Path("data/audit/audit-set.csv"))
    label_cmd.add_argument("--port", type=int, default=8765, help="port on localhost (default 8765)")

    args = parser.parse_args(argv)
    if args.command == "collect":
        collect(load_config(args.config), args.snapshot, args.manifest, refresh=args.refresh, run_judge=not args.no_judge)
    elif args.command == "fetch":
        try:
            fulltext.fetch(args.snapshot, args.manifest, args.pdfs, args.limit)
        except fulltext.FetchErrors as errors:
            sys.exit(f"fetch: {errors}")
    elif args.command == "parse":
        try:
            files, problems = (inputs.from_paths(args.files), []) if args.files else inputs.from_record(args.snapshot, args.pdfs)
        except inputs.NotFiles as error:
            sys.exit(f"parse: {error}")
        # A smoke run must not quietly replace the committed report of the full run (ADR 0029).
        report = args.report or (None if args.limit is not None else Path("data/parse-report.md"))
        messages = []
        try:
            parsing.parse(load_parse_config(args.config), files, args.cache, report, args.limit, args.retry_failed)
        except parsing.ParseErrors as errors:
            messages.append(f"parse: {errors}")
        except GrobidUnreachable as error:
            sys.exit(f"parse: {error}")
        if problems:
            messages.append(
                f"parse: {len(problems)} recorded file(s) weren't parsed. Run `just fetch` to download them again:\n"
                + "\n".join(f"  {problem}" for problem in problems)
            )
        if messages:
            sys.exit("\n".join(messages))
    elif args.command == "audit" and args.audit_command == "export":
        audit.export(load_config(args.config), args.snapshot, args.output, args.size, args.seed, force=args.force)
    elif args.command == "audit" and args.audit_command == "report":
        audit.report(
            load_config(args.config), args.audit_set, args.verdicts, args.output, args.thresholds, run_judge=not args.no_judge
        )
    elif args.command == "audit" and args.audit_command == "label":
        audit_label.serve(load_config(args.config), args.audit_set, args.port)
