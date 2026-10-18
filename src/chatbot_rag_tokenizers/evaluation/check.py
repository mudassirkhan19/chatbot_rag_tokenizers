"""`eval-check` (ADR 0041): checks the Evaluation set against the parsed text before anything is scored on it.

For every Passage it reports how many Chunks hold it and in which Editions, so a matching rule that is too
loose shows up as one Passage held by dozens of Chunks.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..parsing.chunker import HEADER_SEPARATOR
from ..retrieval.corpus import Corpus
from .evalset import Passage, Question
from .matching import MatchingRule, Words, holds_words, words
from .works import Works

MAX_QUOTE_CHARACTERS = 300  # the repo quotes papers only briefly (spec #31)


@dataclass(frozen=True)
class PassageCheck:
    question: Question
    number: int  # the Passage's place in its question, from 1
    passage: Passage
    holders: Counter[str]  # the Chunks holding it, counted by pinned id


@dataclass(frozen=True)
class CheckResult:
    passages: list[PassageCheck]
    problems: list[str]  # each failure, worded for the person editing the set

    def failure(self, evaluation_set: Path) -> str:
        count = f"{len(self.problems)} check{'' if len(self.problems) == 1 else 's'}"
        return "\n".join([f"{evaluation_set} fails eval-check on {count}:", *(f"  {problem}" for problem in self.problems)])


def check(questions: Sequence[Question], corpus: Corpus, rule: MatchingRule, works: Works) -> CheckResult:
    listed = [(question, number, passage) for question in questions for number, passage in enumerate(question.passages, start=1)]
    problems = [f"{question.id}: {problem}" for question in questions for problem in _shape(question)]
    # A Passage names the pinned id of the file it quotes; its Chunks name that file's Edition.
    editions = {chunk.pinned_id: chunk.edition_id for chunk in corpus.chunks}
    for question in questions:
        quoted = {works.of(editions.get(passage.edition_id, passage.edition_id)) for passage in question.passages}
        if question.type == "multi-paper" and len(quoted) < 2:
            problems.append(f"{question.id}: a multi-paper question needs Passages from at least two Works")
    quotes = [Words.of(passage.quote) for _, _, passage in listed]
    holders: list[Counter[str]] = [Counter() for _ in listed]
    # Each Section's words, by the pinned id of its file and its path as a Passage names it.
    sections: dict[tuple[str, str], list[str]] = {}
    # Each Chunk is cut into words once and tried against every quote.
    for chunk in corpus.chunks:
        text = Words.of(chunk.text)
        sections.setdefault((chunk.pinned_id, HEADER_SEPARATOR.join(chunk.section_path)), []).extend(text.words)
        for counts, quote in zip(holders, quotes):
            if holds_words(text, quote, rule):
                counts[chunk.pinned_id] += 1
    for (question, number, passage), quote in zip(listed, quotes):
        if len(passage.quote) > MAX_QUOTE_CHARACTERS:
            problems.append(
                f"{question.id} Passage {number}: the quote is {len(passage.quote)} characters long; the limit is {MAX_QUOTE_CHARACTERS}"
            )
        # Found means verbatim after normalising: the quote's words in a row in the named Section.
        if not _contains(sections.get((passage.edition_id, passage.section), []), quote.words):
            problems.append(f"{question.id} Passage {number}: the quote isn't in {passage.edition_id} › {passage.section}")
    checked = [PassageCheck(question, number, passage, counts) for (question, number, passage), counts in zip(listed, holders)]
    return CheckResult(checked, problems)


def _contains(section: list[str], quote: tuple[str, ...]) -> bool:
    # Words hold no spaces, so joining both with spaces keeps word boundaries.
    return bool(quote) and f" {' '.join(quote)} " in f" {' '.join(section)} "


def _overlap_line(question: Question) -> str:
    """The share of the question's distinct words that are in its Passages' quotes: how much a keyword search is
    handed by the wording. A follow-up's rewrite gets its own share."""
    quoted = {word for passage in question.passages for word in words(passage.quote)}

    def overlap(text: str) -> tuple[float, int, int]:
        asked = set(words(text))
        shared = len(asked & quoted)
        return (shared / len(asked) if asked else 0.0), shared, len(asked)

    share, shared, total = overlap(question.question)
    line = f"{question.id}: lexical overlap {share:.2f} ({shared} of {total} question words are in its Passages)"
    if question.rewrite:
        share, shared, total = overlap(question.rewrite)
        line += f"; rewrite {share:.2f} ({shared} of {total})"
    return line


def _shape(question: Question) -> list[str]:
    problems = []
    if question.answerable and not question.passages:
        problems.append("an answerable question needs a Passage")
    if not question.answerable and question.passages:
        problems.append("an unanswerable question has no Passages")
    if question.type == "follow-up" and not (question.history and question.rewrite):
        problems.append("a follow-up needs a history and a rewrite")
    if question.type != "follow-up" and (question.history or question.rewrite):
        problems.append("only a follow-up has a history or a rewrite")
    # No agent-drafted question is scored before a person has checked it (spec #31, story 15).
    if not question.checked_by.strip():
        problems.append("nobody has checked this question (checked_by is empty)")
    return problems


def describe(questions: Sequence[Question], result: CheckResult) -> list[str]:
    """A line per question with its lexical overlap, each followed by a line per Passage with the Chunks holding it."""
    lines = []
    for question in questions:
        if question.passages:
            lines.append(_overlap_line(question))
        lines += [_passage_line(item) for item in result.passages if item.question is question]
    passages = len(result.passages)
    outcome = "failed" if result.problems else "passed"
    return [*lines, f"eval-check: {outcome}: {len(questions)} questions, {passages} Passage{'' if passages == 1 else 's'}"]


def _passage_line(item: PassageCheck) -> str:
    total = sum(item.holders.values())
    where = ", ".join(f"{pinned_id} ({count})" for pinned_id, count in sorted(item.holders.items()))
    return (
        f"{item.question.id} Passage {item.number}: {item.passage.edition_id} › {item.passage.section}:"
        f" held by {total} Chunk{'' if total == 1 else 's'}{': ' + where if where else ''}"
    )
