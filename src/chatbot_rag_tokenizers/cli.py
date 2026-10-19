"""Command-line entry point."""

import argparse
import sys
from pathlib import Path

from .chat import page
from .chat.answers import AnswersMismatch
from .chat.chat_eval import chat_eval, rescore_answers
from .chat.config import ChatConfig, load_chat_config
from .chat.conversation import Chatbot
from .chat.model import AnswerModelUnavailable
from .collection import audit, audit_label, fulltext, indexed
from .config import ConfigError
from .collection.config import load_config
from .collection.manifest import read_manifest
from .collection.pipeline import collect
from .evaluation import pipeline as evaluation
from .evaluation.check import check, describe
from .evaluation.comparison import BaselineMissing
from .evaluation.config import load_matching_rule
from .evaluation.evalset import EvaluationSetError, load_evaluation_set
from .evaluation.matching import MatchingRule
from .evaluation.work_groups import WorkGroupsError
from .evaluation.works import Works
from .parsing import inputs
from .parsing import pipeline as parsing
from .parsing.config import load_parse_config
from .parsing.grobid import GrobidUnreachable
from .retrieval import index
from .retrieval.config import load_retrieval_config
from .retrieval.corpus import Corpus, CorpusError, load_corpus
from .retrieval.retriever import RetrieverConfig


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
    collect_cmd.add_argument("--report", type=Path, default=Path("data/report.md"), help="the funnel and channel report")
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
    fetch_cmd.add_argument("--report", type=Path, default=Path("data/report.md"), help="the funnel and channel report")
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
        "--manifest",
        type=Path,
        default=Path("data/manifest.csv"),
        help="only the files of its included Editions are parsed (default data/manifest.csv)",
    )
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

    index_cmd = commands.add_parser(
        "index",
        help="build the retrievers over the Chunks of every file the parse report lists",
        description=(
            "Reads the Chunks of each file the parse report lists as parsed from the parse cache, and builds each"
            " retriever over their context headers and text into the index cache. An index already built over the"
            " same files, chunking config and retriever settings is kept."
        ),
    )
    _add_corpus_arguments(index_cmd)
    index_cmd.add_argument("--snapshot", type=Path, default=Path("data/snapshot"), help="where the index record of indexed files goes")
    index_cmd.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"), help="its Editions whose files are all indexed are marked indexed")
    index_cmd.add_argument("--funnel-report", type=Path, default=Path("data/report.md"), help="the funnel and channel report, rewritten with the indexed count")

    evaluate_cmd = commands.add_parser(
        "evaluate",
        help="score the retrievers on the Evaluation set and write the eval report",
        description=(
            "Runs every question of the Evaluation set through each retriever `index` built, scores the raw rankings"
            " and their Collapsed rankings (`<retriever>+collapsed`, copies from a Work's other files merged)"
            " against the questions' Passages (Recall@5, MRR@10, Hit@5), measures what crowds the top 5 (duplicates"
            " of one Work and Survey restatement, against the Work groups, and mostly-numeric Chunks) and writes the"
            " committed eval report."
        ),
    )
    _add_corpus_arguments(evaluate_cmd)
    _add_evaluation_set_arguments(evaluate_cmd)
    evaluate_cmd.add_argument("--report", type=Path, default=Path("data/eval/eval-report.md"), help="the eval report (committed)")
    evaluate_cmd.add_argument(
        "--work-groups",
        type=Path,
        default=Path("data/eval/work-groups.csv"),
        help="the hand-assigned Work and Survey flag of each Edition, for the duplicate rate (committed)",
    )
    evaluate_cmd.add_argument(
        "--export-ungrouped",
        type=Path,
        metavar="CSV",
        help="also write every Edition in a top 5 with no Work group, with its title, authors, year and venue, for grouping",
    )

    chat_cmd = commands.add_parser(
        "chat",
        help="serve the chat page on localhost: questions answered from retrieved Chunks, with Citations",
        description=(
            "Retrieves the top k Chunks for each question from the retriever the [chat] table of the retrieval config"
            " names, and has the pinned answer model on Ollama answer from them with numbered Citations, or say the"
            " corpus doesn't answer it. Needs that retriever's index (`just index`) and Ollama with the pinned model"
            " (`just init`)."
        ),
    )
    chat_cmd.add_argument("--config", type=Path, default=Path("config/retrieval.toml"), help="the [chat] table and the retrievers")
    _add_chunk_arguments(chat_cmd)
    chat_cmd.add_argument("--index-cache", type=Path, default=Path("data/index-cache"), help="the index cache (default data/index-cache)")
    chat_cmd.add_argument("--port", type=int, default=8766, help="port on localhost (default 8766)")

    chat_eval_cmd = commands.add_parser(
        "chat-eval",
        help="ask the chatbot every question of the Evaluation set and write the chat report and the answers",
        description=(
            "Asks each question as a Conversation of its own through the chatbot of the [chat] table, a follow-up after"
            " its stored history, and writes the committed chat report (grounded, abstention and false-abstention rates,"
            " Recall@k of the retrieved Chunks, a line per question and the latency per Turn) and every Turn's answer as"
            " JSON Lines. Refuses a set that fails `eval-check`. Needs the retriever's index (`just index`) and Ollama with"
            " the pinned model (`just init`), except with --from-answers, which asks nothing."
        ),
    )
    chat_eval_cmd.add_argument("--config", type=Path, default=Path("config/retrieval.toml"), help="the [chat] table and the retrievers")
    _add_chunk_arguments(chat_eval_cmd)
    chat_eval_cmd.add_argument("--index-cache", type=Path, default=Path("data/index-cache"), help="the index cache (default data/index-cache)")
    _add_evaluation_set_arguments(chat_eval_cmd)
    chat_eval_cmd.add_argument("--report", type=Path, default=Path("data/eval/chat-report.md"), help="the chat report (committed)")
    chat_eval_cmd.add_argument(
        "--answers", type=Path, default=Path("data/eval/chat-answers.jsonl"), help="every Turn's answer, one per line (committed)"
    )
    chat_eval_cmd.add_argument(
        "--from-answers",
        action="store_true",
        help="ask nothing: score the --answers file (and its runs file) again with the current code, and rewrite it and the report",
    )
    chat_eval_cmd.add_argument(
        "--baseline",
        type=Path,
        help="an answers file to compare with question by question; read before anything is written, so it may be --answers",
    )
    chat_eval_cmd.add_argument(
        "--runs", type=_at_least_one, default=1, help="ask the whole set this many times and report the variation (default 1)"
    )

    eval_check_cmd = commands.add_parser(
        "eval-check",
        help="check every question and Passage of the Evaluation set against the parsed text",
        description=(
            "Fails a Passage whose quote isn't in its named Edition and Section, or is over 300 characters, and a"
            " question of the wrong shape. Reports, for every Passage, the Chunks that hold it and their Editions,"
            " and each question's lexical overlap with its Passages. Exits non-zero on any failure."
        ),
    )
    _add_chunk_arguments(eval_check_cmd)
    _add_evaluation_set_arguments(eval_check_cmd)

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
        collect(
            load_config(args.config), args.snapshot, args.manifest, args.report, refresh=args.refresh, run_judge=not args.no_judge
        )
    elif args.command == "fetch":
        try:
            fulltext.fetch(args.snapshot, args.manifest, args.report, args.pdfs, args.limit)
        except fulltext.FetchErrors as errors:
            sys.exit(f"fetch: {errors}")
    elif args.command == "parse":
        try:
            files, problems = (inputs.from_paths(args.files), []) if args.files else inputs.from_record(args.snapshot, args.pdfs, args.manifest)
        except inputs.NotFiles as error:
            sys.exit(f"parse: {error}")
        # A smoke run must not quietly replace the committed report of the full run (ADR 0029).
        report = args.report or (None if args.limit is not None else Path("data/parse-report.md"))
        messages = []
        try:
            parsing.parse(load_parse_config(args.config), files, args.cache, report, not args.files, args.limit, args.retry_failed)
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
    elif args.command == "index":
        corpus, retrievers = _corpus_and_retrievers(args)
        index.build(args.index_cache, corpus, retrievers)
        if corpus.from_record:
            indexed.mark(args.snapshot, args.manifest, args.funnel_report, set(corpus.parsed))
        else:
            # A Seeds-only corpus isn't the manifest's: marking from it would unmark the full corpus (ADR 0045).
            print("index: the parse report comes from a `--files` run, so no Edition is marked indexed", file=sys.stderr)
    elif args.command == "evaluate":
        corpus, retrievers = _corpus_and_retrievers(args)
        retrieval = load_retrieval_config(args.config)
        rule = _matching_rule(args)
        try:
            evaluation.evaluate(
                corpus,
                retrievers,
                args.index_cache,
                args.evaluation_set,
                args.report,
                rule,
                read_manifest(args.manifest),
                args.work_groups,
                retrieval.collapse_pool,
                retrieval.comparison,
                args.export_ungrouped,
            )
        except (EvaluationSetError, WorkGroupsError, index.IndexMissing, BaselineMissing) as error:
            sys.exit(f"evaluate: {error}")
    elif args.command == "chat":
        _chat(args)
    elif args.command == "chat-eval":
        if args.from_answers and args.runs != 1:
            sys.exit("chat-eval: --from-answers asks nothing, so it takes the runs the answers file holds, not --runs")
        try:
            if args.from_answers:
                config, corpus = _chat_config(args), _load_corpus(args)
                rescore_answers(config, corpus, args.evaluation_set, args.report, args.answers, _matching_rule(args), _works(args), args.baseline)
            else:
                chatbot, corpus = _chatbot(args)
                chat_eval(chatbot, corpus, args.evaluation_set, args.report, args.answers, _matching_rule(args), _works(args), args.runs, args.baseline)
        except (EvaluationSetError, AnswerModelUnavailable, AnswersMismatch) as error:
            sys.exit(f"chat-eval: {error}")
    elif args.command == "eval-check":
        rule = _matching_rule(args)
        try:
            questions = load_evaluation_set(args.evaluation_set)
        except EvaluationSetError as error:
            sys.exit(f"eval-check: {error}")
        result = check(questions, _load_corpus(args), rule, _works(args))
        print("\n".join(describe(questions, result)))
        if result.problems:
            sys.exit(f"eval-check: {result.failure(args.evaluation_set)}")
    elif args.command == "audit" and args.audit_command == "export":
        audit.export(load_config(args.config), args.snapshot, args.output, args.size, args.seed, force=args.force)
    elif args.command == "audit" and args.audit_command == "report":
        audit.report(
            load_config(args.config), args.audit_set, args.verdicts, args.output, args.thresholds, run_judge=not args.no_judge
        )
    elif args.command == "audit" and args.audit_command == "label":
        audit_label.serve(load_config(args.config), args.audit_set, args.port)


def _chat_config(args: argparse.Namespace) -> ChatConfig:
    try:
        return load_chat_config(args.config)
    except ConfigError as error:
        sys.exit(f"{args.command}: {error}")


def _at_least_one(text: str) -> int:
    if int(text) < 1:
        raise argparse.ArgumentTypeError(f"{text} is not at least 1")
    return int(text)


def _chatbot(args: argparse.Namespace) -> tuple[Chatbot, Corpus]:
    """The chatbot the [chat] table configures, over the corpus's index, and the corpus."""
    config = _chat_config(args)
    corpus = _load_corpus(args)
    try:
        built = index.load(args.index_cache, corpus, config.retriever)
    except index.IndexMissing as error:
        sys.exit(f"{args.command}: {error}")
    return Chatbot(config, built.retriever, {chunk.chunk_id: chunk for chunk in corpus.chunks}), corpus


def _chat(args: argparse.Namespace) -> None:
    chatbot, _ = _chatbot(args)
    try:
        server = page.make_server(chatbot, args.port)
    except OSError as error:
        sys.exit(f"chat: can't serve on port {args.port} ({error}); pass another with --port")
    page.serve(chatbot, server)


def _add_corpus_arguments(command: argparse.ArgumentParser) -> None:
    """The arguments `index` and `evaluate` share: where the Chunks are, and which retrievers."""
    command.add_argument("--config", type=Path, default=Path("config/retrieval.toml"), help="the retrievers' settings")
    _add_chunk_arguments(command)
    command.add_argument("--index-cache", type=Path, default=Path("data/index-cache"), help="the index cache (default data/index-cache, gitignored)")
    command.add_argument("--retriever", action="append", help="a retriever in the config, e.g. bm25; repeat for several (default all)")


def _add_chunk_arguments(command: argparse.ArgumentParser) -> None:
    """Where the corpus's Chunks are: the parse config, cache and report."""
    command.add_argument("--parse-config", type=Path, default=Path("config/parse.toml"), help="the chunking config the Chunks were cut with")
    command.add_argument("--cache", type=Path, default=Path("data/parse-cache"), help="the parse cache (default data/parse-cache)")
    command.add_argument(
        "--parse-report", type=Path, default=Path("data/parse-report.md"), help="its parsed files make up the corpus (default data/parse-report.md)"
    )


def _add_evaluation_set_arguments(command: argparse.ArgumentParser) -> None:
    """The arguments `evaluate`, `chat-eval` and `eval-check` share: the Evaluation set and the Passage matching rule."""
    command.add_argument("--evaluation-set", type=Path, default=Path("data/eval/evaluation-set.jsonl"))
    command.add_argument("--eval-config", type=Path, default=Path("config/evaluation.toml"), help="the Passage matching rule")
    command.add_argument(
        "--manifest", type=Path, default=Path("data/manifest.csv"), help="links the Editions of a Work, for the multi-paper check"
    )


def _matching_rule(args: argparse.Namespace) -> MatchingRule:
    try:
        return load_matching_rule(args.eval_config)
    except ConfigError as error:
        sys.exit(f"{args.command}: {error}")


def _works(args: argparse.Namespace) -> Works:
    return Works(read_manifest(args.manifest))


def _load_corpus(args: argparse.Namespace) -> Corpus:
    try:
        return load_corpus(load_parse_config(args.parse_config), args.cache, args.parse_report)
    except CorpusError as error:
        sys.exit(f"{args.command}: {error}")


def _corpus_and_retrievers(args: argparse.Namespace) -> tuple[Corpus, list[RetrieverConfig]]:
    try:
        configured = load_retrieval_config(args.config).retrievers
    except ConfigError as error:
        sys.exit(f"{args.command}: {error}")
    names = args.retriever or list(configured)
    if unknown := [name for name in names if name not in configured]:
        sys.exit(f"{args.command}: unknown retriever {', '.join(unknown)}; {args.config} configures {', '.join(configured)}")
    return _load_corpus(args), [configured[name] for name in names]
