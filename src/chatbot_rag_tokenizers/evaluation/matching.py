"""The Passage matcher (ADR 0040): whether a Chunk holds a Passage, judged on the text alone.

Both texts are normalised the same way: unicode compatibility forms (NFKC), case folded, citations such as
"[47]" or "(Gage, 1994)" dropped, a word hyphenated at the end of a line joined again, and a hyphen between
two letters dropped, so "Ger-man", "Ger-\\nman" and "German" are one word. They are then cut into words: runs
of letters and digits, with a decimal or thousands-separated number kept whole, as BM25 cuts them (ADR 0039).

The quote's words and the Chunk's are lined up in order in matching blocks of at least two words; a number
may match alone. Of those, the run of blocks covering the most words within twice the quote's length of the
Chunk is kept. The Chunk holds the Passage when:
- the kept blocks cover at least ``threshold`` of the quote's words;
- every number in the quote is in a block: a v1 Chunk saying "4.8% recall" where the quote says "5.2% recall"
  doesn't hold it.

The edge rule: when the blocks run into the Chunk's first or last word, the quote may go on past that edge
into the next Chunk, so the quote's words beyond the first or last block are left out of the share. The
blocks must then cover at least ``edge_min_words`` words. This way both Chunks of a quote split across a
Chunk boundary hold it.

Only the text is compared, never the Edition, so a Chunk from any Edition of the Work can hold the Passage.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import Match, SequenceMatcher

MIN_BLOCK = 2  # a single shared word, such as "the", is not evidence of the same sentence
SPAN_RATIO = 2  # the blocks counted lie within twice the quote's length of the Chunk's words

# Citations are dropped: a later Version renumbers "[43]" to "[47]" and re-dates "(Jean et al., 2015a)".
_NUMBERED_CITATION = re.compile(r"\[\s*\d+(?:\s*[,;–-]\s*\d+)*\s*\]")  # [47], [23,55], [3-5]
_AUTHOR_YEAR = re.compile(r"\([^()]*\b(?:1[89]|20)\d\d[a-z]?\b[^()]*\)")  # (Gage, 1994), (2012), (Luong et al., 2015b)
# The hyphens: hyphen-minus, U+2010 hyphen and U+2011 non-breaking hyphen.
_LINE_END_HYPHEN = re.compile(r"(?<=[^\W\d_])[-‐‑]\s*\n\s*(?=[^\W\d_])")
_INNER_HYPHEN = re.compile(r"(?<=[^\W\d_])[-‐‑](?=[^\W\d_])")
_WORD = re.compile(r"\d+(?:[.,]\d+)+|[^\W_]+")


@dataclass(frozen=True)
class MatchingRule:
    threshold: float  # the share of the quote's words that must be in matching blocks
    edge_min_words: int  # the words a match running into a Chunk's edge must cover


def words(text: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = _AUTHOR_YEAR.sub(" ", _NUMBERED_CITATION.sub(" ", text))
    text = _INNER_HYPHEN.sub("", _LINE_END_HYPHEN.sub("", text))
    return tuple(_WORD.findall(text))


@dataclass(frozen=True)
class Words:
    """A text cut into words once, for matching against many others."""

    words: tuple[str, ...]
    pairs: frozenset[tuple[str, str]]  # each two words in a row

    @classmethod
    def of(cls, text: str) -> "Words":
        cut = words(text)
        return cls(cut, frozenset(zip(cut, cut[1:])))


def holds(chunk_text: str, quote: str, rule: MatchingRule) -> bool:
    return holds_words(Words.of(chunk_text), Words.of(quote), rule)


def holds_words(chunk: Words, quote: Words, rule: MatchingRule) -> bool:
    """`holds` on texts already cut into words."""
    return may_hold(chunk, quote, rule) and (found := align(chunk, quote)) is not None and found.meets(rule)


@dataclass(frozen=True)
class Alignment:
    """How a quote lines up with a Chunk, before any threshold is applied."""

    matched: int  # the quote's words in matching blocks
    counted: int  # the quote's words the share is taken over: all of them, or those on the Chunk's side of an edge
    at_edge: bool  # the blocks run into the Chunk's first or last word, and the quote goes on past it
    numbers_match: bool  # every number among the quote's counted words is in a block

    def meets(self, rule: MatchingRule) -> bool:
        return (
            self.numbers_match
            and self.matched >= rule.threshold * self.counted
            and (not self.at_edge or self.matched >= rule.edge_min_words)
        )


def align(chunk: Words, quote: Words) -> Alignment | None:
    """The quote's matching blocks in the Chunk, or None when there is none of at least MIN_BLOCK words."""
    quote_words, chunk_words = quote.words, chunk.words
    matcher = SequenceMatcher(None, quote_words, chunk_words, autojunk=False)
    # A number may match alone: rewording around it ("WMT 2015", "the 2015 Workshop") leaves it a block of one.
    blocks = [
        block
        for block in matcher.get_matching_blocks()
        if block.size >= MIN_BLOCK or (block.size == 1 and _is_number(quote_words[block.a]))
    ]
    blocks = _densest_run(blocks, SPAN_RATIO * len(quote_words))
    if not blocks:
        return None
    quote_start, quote_end = blocks[0].a, blocks[-1].a + blocks[-1].size
    chunk_start, chunk_end = blocks[0].b, blocks[-1].b + blocks[-1].size
    # The edge rule: the quote may go on past the Chunk's first or last word.
    low = quote_start if chunk_start == 0 else 0
    high = quote_end if chunk_end == len(chunk_words) else len(quote_words)
    # A number the Chunk changed leaves the quote's number out of every block. A number only the Chunk has,
    # such as a list's "(1)", changes nothing the quote says.
    in_quote = {i for block in blocks for i in range(block.a, block.a + block.size)}
    numbers_match = all(i in in_quote for i in range(low, high) if _is_number(quote_words[i]))
    matched = sum(block.size for block in blocks)
    return Alignment(matched, high - low, (low, high) != (0, len(quote_words)), numbers_match)


def _densest_run(blocks: list[Match], span: float) -> list[Match]:
    """The run of consecutive blocks covering the most words within ``span`` of the Chunk's words. Pairs such as
    "of the" scattered sentences apart are not a reworded quote; a reworded quote stays about as long as it was."""
    best: list[Match] = []
    first = covered = best_covered = 0
    for last, block in enumerate(blocks):
        covered += block.size
        while block.b + block.size - blocks[first].b > span:
            covered -= blocks[first].size
            first += 1
        if covered > best_covered:
            best, best_covered = blocks[first : last + 1], covered
    return best


def _is_number(word: str) -> bool:
    return any(character.isdigit() for character in word)


def may_hold(chunk: Words, quote: Words, rule: MatchingRule) -> bool:
    """A quick bound, so most Chunks are ruled out before they are aligned. A match covers at least
    min(edge_min_words, threshold × the quote's words); all but the quote's numbers are in blocks of at least
    two words, and such blocks covering m words hold at least m / 2 of the quote's word pairs."""
    if len(quote.words) < MIN_BLOCK:
        return False
    numbers = sum(1 for word in quote.words if _is_number(word))
    needed = min(rule.edge_min_words, rule.threshold * len(quote.words)) - numbers
    shared = sum(1 for pair in zip(quote.words, quote.words[1:]) if pair in chunk.pairs)
    return shared >= needed / MIN_BLOCK
