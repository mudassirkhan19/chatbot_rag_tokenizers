"""The Passage matcher (ADR 0040): whether a Chunk holds a Passage, judged on the text alone.

Both texts are normalised the same way: unicode compatibility forms (NFKC), case folded, a word hyphenated at
the end of a line joined again, and a hyphen between two letters dropped, so "Ger-man", "Ger-\\nman" and
"German" are one word. They are then cut into words: runs of letters and digits, with a decimal or
thousands-separated number kept whole, as BM25 cuts them (ADR 0039).

A Chunk holds a Passage when the quote's words and the Chunk's line up in order in matching blocks of at
least two words, and:
- the blocks cover at least ``threshold`` of the quote's words;
- every number in the quote, and every number in the Chunk between the first block and the last, is in a
  block: a v1 Chunk saying "4.8% recall" where the quote says "5.2% recall" doesn't hold it.

The edge rule: when the blocks run into the Chunk's first or last word, the quote may go on past that edge
into the next Chunk, so the quote's words beyond the first or last block are left out of the share. The
blocks must then cover at least ``edge_min_words`` words. This way both Chunks of a quote split across a
Chunk boundary hold it.

Only the text is compared, never the Edition, so a Chunk from any Edition of the Work can hold the Passage.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

MIN_BLOCK = 2  # a single shared word, such as "the", is not evidence of the same sentence

_LINE_END_HYPHEN = re.compile(r"(?<=[^\W\d_])[-‐‑]\s*\n\s*(?=[^\W\d_])")
_INNER_HYPHEN = re.compile(r"(?<=[^\W\d_])[-‐‑](?=[^\W\d_])")
_WORD = re.compile(r"\d+(?:[.,]\d+)+|[^\W_]+")


@dataclass(frozen=True)
class MatchingRule:
    threshold: float  # the share of the quote's words that must be in matching blocks
    edge_min_words: int  # the words a match running into a Chunk's edge must cover

    def describe(self) -> dict[str, object]:
        return {"threshold": self.threshold, "edge_min_words": self.edge_min_words, "min_block_words": MIN_BLOCK}


def words(text: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", text).casefold()
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
    quote_words, chunk_words = quote.words, chunk.words
    if not _may_hold(chunk, quote, rule):
        return False
    matcher = SequenceMatcher(None, quote_words, chunk_words, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= MIN_BLOCK]
    if not blocks:
        return False
    quote_start, quote_end = blocks[0].a, blocks[-1].a + blocks[-1].size
    chunk_start, chunk_end = blocks[0].b, blocks[-1].b + blocks[-1].size
    # The edge rule: the quote may go on past the Chunk's first or last word.
    low = quote_start if chunk_start == 0 else 0
    high = quote_end if chunk_end == len(chunk_words) else len(quote_words)
    matched = sum(block.size for block in blocks)
    if (low, high) != (0, len(quote_words)) and matched < rule.edge_min_words:
        return False
    if matched < rule.threshold * (high - low):
        return False
    in_quote = {i for block in blocks for i in range(block.a, block.a + block.size)}
    in_chunk = {i for block in blocks for i in range(block.b, block.b + block.size)}
    return all(i in in_quote for i in range(low, high) if _is_number(quote_words[i])) and all(
        i in in_chunk for i in range(chunk_start, chunk_end) if _is_number(chunk_words[i])
    )


def _is_number(word: str) -> bool:
    return any(character.isdigit() for character in word)


def _may_hold(chunk: Words, quote: Words, rule: MatchingRule) -> bool:
    """A quick bound, so most Chunks are ruled out before they are aligned. Blocks of at least two words that
    cover m of the quote's words hold at least m / 2 of its word pairs, and a match covers at least
    min(edge_min_words, threshold × the quote's words)."""
    if len(quote.words) < MIN_BLOCK:
        return False
    needed = min(rule.edge_min_words, rule.threshold * len(quote.words))
    shared = sum(1 for pair in zip(quote.words, quote.words[1:]) if pair in chunk.pairs)
    return shared >= needed / MIN_BLOCK
