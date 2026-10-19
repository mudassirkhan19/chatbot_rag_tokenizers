"""`chat-eval` (spec #63, ADRs 0059 and 0062): the whole Evaluation set asked of the chatbot, through the same
Conversation code as the chat page, scored and written as the chat report and the answers.

Each question is a Conversation of its own. A single-paper, multi-paper or unanswerable question is one Turn. A
follow-up first asks its stored history as real Turns, the bot answering each, then the follow-up, so the
rewriter works from the bot's own answers as it would on the page. Only the question's own Turn is scored; the
history's Turns are in the answers file and the latency.

`--runs N` asks the whole set N times: the first run is the one reported, and the others measure how much the
answer model varies. `--from-answers` asks nothing: it scores the answers file's Turns again with the current code
and rewrites the file, so a change to the scoring is measured with no model noise.
"""

from collections.abc import Sequence
from pathlib import Path

from ..evaluation.evalset import Question
from ..evaluation.matching import MatchingRule
from ..evaluation.pipeline import checked_questions
from ..evaluation.works import Works
from ..retrieval.corpus import Corpus
from .answers import Asked, Baseline, Run, read_baseline, rescore, runs_path, score, write_answers
from .chat_report import write_chat_report
from .config import ChatConfig
from .conversation import Chatbot


def chat_eval(
    chatbot: Chatbot,
    corpus: Corpus,
    evaluation_set: Path,
    report: Path,
    answers: Path,
    rule: MatchingRule,
    works: Works,
    runs: int = 1,
    baseline: Path | None = None,
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check`, AnswerModelUnavailable when the answer model
    can't answer, and AnswersMismatch for a baseline that isn't an answers file, before any question is asked."""
    questions = checked_questions(evaluation_set, corpus, rule, works)
    compared = None if baseline is None else read_baseline(baseline)
    chatbot.model()  # checked against its pin before anything is asked
    asked = [ask_all(questions, chatbot, rule) for _ in range(runs)]
    _write(chatbot.config, corpus, evaluation_set, questions, report, answers, asked, compared, rescored=False)


def rescore_answers(
    config: ChatConfig, corpus: Corpus, evaluation_set: Path, report: Path, answers: Path, rule: MatchingRule, works: Works, baseline: Path | None = None
) -> None:
    """Raises EvaluationSetError for a set that fails `eval-check`, and AnswersMismatch for an answers file asked
    over other Chunks, another chatbot or another set."""
    questions = checked_questions(evaluation_set, corpus, rule, works)
    compared = None if baseline is None else read_baseline(baseline)
    runs = rescore(answers, questions, corpus, config, rule)
    _write(config, corpus, evaluation_set, questions, report, answers, runs, compared, rescored=True)


def _write(
    config: ChatConfig,
    corpus: Corpus,
    evaluation_set: Path,
    questions: Sequence[Question],
    report: Path,
    answers: Path,
    runs: Sequence[Run],
    baseline: Baseline | None,
    rescored: bool,
) -> None:
    write_answers(answers, corpus, config, runs)
    write_chat_report(report, evaluation_set, questions, corpus, config, runs, baseline, answers if rescored else None)
    turns = sum(1 for item in runs[0] if not item.scored)
    stored = f"answers in {answers}" + (f" and runs 2..{len(runs)} in {runs_path(answers)}" if len(runs) > 1 else "")
    print(
        f"chat-eval: {len(questions)} questions, {len(runs[0])} Turns ({turns} of them follow-ups' history)"
        f"{f', {len(runs)} runs' if len(runs) > 1 else ''}{', re-scored' if rescored else ''}; report in {report}, {stored}"
    )


def ask_all(questions: Sequence[Question], chatbot: Chatbot, rule: MatchingRule) -> list[Asked]:
    """Every question as its own Conversation, each Turn of each in the order asked. Raises AnswerModelUnavailable."""
    asked = []
    for question in questions:
        chatbot.reset()
        for number, text in enumerate([*question.history, question.question], start=1):
            asked.append(score(question, number, chatbot.ask(text), rule))
    return asked
