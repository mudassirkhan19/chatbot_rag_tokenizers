"""Whether a Chunk holds a Passage: a stand-in until the real Passage matcher (ADR 0039).

A Chunk holds a Passage when the quote, normalised, is a substring of the Chunk's text, normalised the
same way: unicode compatibility forms (NFKC), case folded and runs of whitespace made one space. Only the
text is compared, never the Edition, so a Chunk from any Edition of the Work can hold the Passage.
"""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def holds(chunk_text: str, quote: str) -> bool:
    return normalise(quote) in normalise(chunk_text)
