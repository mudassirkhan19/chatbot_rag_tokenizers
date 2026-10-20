"""The answer step (ADRs 0054, 0056 and 0064): what the answer model is sent for a Turn, and how its reply is read.

The model gets the config's system prompt, then the earlier Turns of the Conversation, each as its question and
its answer's text without the markers (which numbered that Turn's Chunks, not this one's), then the question with
the retrieved Chunks numbered from 1, each under its context header. It cites by number. The reply is cut into
text and markers: a marker naming a retrieved Chunk is a Citation, and any other number is kept as an invalid
marker, never dropped. A reply is an Abstention when it holds the fixed Abstention sentence, or when its text
is a single sentence declining in the model's own words, such as "The provided chunks do not contain …", that
neither goes on to answer nor cites. Both are compared after the Passage matcher's normalisation. Markers before
a decline are kept as written. Each sentence that cites a Chunk is a claim, which the grounding judge checks against
each Chunk it cites (ADR 0075).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..evaluation.matching import words
from ..parsing.chunker import Chunk
from .model import Message

# "[2]", and "[1, 3]" read as two markers.
_MARKER = re.compile(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]")
# The space a marker leaves before the punctuation that followed it: "freezing [1]." reads "freezing .".
_BEFORE_PUNCTUATION = re.compile(r" +([.,;:!?)])")
# How the model declines in its own words, on the matcher's words: "the provided chunks do not explicitly state".
_DECLINE = re.compile(
    r"(?:the )?(?:(?:provided|given|retrieved) )?(?:chunks|excerpts) (?:do not|does not|don t|doesn t) "
    r"(?:(?:explicitly|specifically|directly|clearly) )?(?:contain|state|mention|include|provide|specify|say)\b"
)
# A sentence ends at ".", "!" or "?" followed by a space or a line break.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# What is left between markers in a row: "[2], [3]".
_BETWEEN_MARKERS = re.compile(r"[\s,;]*")
# How a decline goes on to answer within its sentence: "… do not state it, but mT5 used 0.01 [2]."
_GOES_ON = re.compile(r"[;:]|\b(?:but|however|although|though|instead|whereas)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Marker:
    number: int
    valid: bool  # names a Chunk retrieved for the Turn


@dataclass(frozen=True)
class Answer:
    parts: tuple[str | Marker, ...]  # the reply's text with each marker in its place
    abstention: bool

    @property
    def cited(self) -> list[int]:
        """The numbers of the Chunks cited, each once, in the order first cited."""
        return list(dict.fromkeys(part.number for part in self.parts if isinstance(part, Marker) and part.valid))

    @property
    def invalid(self) -> list[int]:
        return list(dict.fromkeys(part.number for part in self.parts if isinstance(part, Marker) and not part.valid))

    @property
    def text(self) -> str:
        """The answer without its markers, as a later Turn is shown it."""
        return _text(self.parts)

    @property
    def claims(self) -> list[tuple[str, list[int]]]:
        """Each sentence that cites a retrieved Chunk, without its markers, and the Chunks it cites, each once, in
        the order first cited. A marker that opens a sentence, as in "… for BPE. [2] It …", cites the sentence
        before it."""
        sentences: list[list[str | Marker]] = [[]]
        for part in self.parts:
            if isinstance(part, Marker):
                opens = not _text(sentences[-1]) and len(sentences) > 1
                sentences[-2 if opens else -1].append(part)
            elif not (sentences[-1] and isinstance(sentences[-1][-1], Marker) and _BETWEEN_MARKERS.fullmatch(part)):
                first, *rest = _SENTENCE_END.split(part)
                sentences[-1].append(first)
                sentences += [[piece] for piece in rest]
        claims = []
        for sentence in sentences:
            cited = list(dict.fromkeys(part.number for part in sentence if isinstance(part, Marker) and part.valid))
            if cited and _text(sentence):
                claims.append((_text(sentence), cited))
        return claims


Earlier = Sequence[tuple[str, str]]  # the Conversation's earlier Turns, oldest first, as (question, answer text)


def messages(system_prompt: str, question: str, chunks: Sequence[Chunk], earlier: Earlier = ()) -> list[Message]:
    numbered = "\n\n".join(f"[{number}] {chunk.header}\n{chunk.text}" for number, chunk in enumerate(chunks, start=1))
    history: list[Message] = []
    for asked, answered in earlier:
        history += [{"role": "user", "content": f"Question: {asked}"}, {"role": "assistant", "content": answered}]
    return [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": f"Question: {question}\n\nChunks:\n\n{numbered}"},
    ]


def read_answer(reply: str, retrieved: int, abstention: str) -> Answer:
    """The reply cut into text and markers, a marker valid when it numbers one of the ``retrieved`` Chunks."""
    parts: list[str | Marker] = []
    end = 0
    for match in _MARKER.finditer(reply):
        parts.append(reply[end : match.start()])
        parts += [Marker(int(number), 1 <= int(number) <= retrieved) for number in match[1].split(",")]
        end = match.end()
    parts.append(reply[end:])
    kept = tuple(part for part in parts if part != "")
    return Answer(kept, _holds(words(reply), words(abstention)) or _declines(kept))


def _text(parts: Sequence[str | Marker]) -> str:
    text = "".join(part for part in parts if isinstance(part, str))
    return _BEFORE_PUNCTUATION.sub(r"\1", re.sub(r"[ \t]+", " ", text)).strip()


def _declines(parts: Sequence[str | Marker]) -> bool:
    """The reply is one sentence opening with a decline, with no clause going on past it and no marker after it.
    Markers before it, on a line of their own, cite no sentence. A decline that goes on to answer is an answer."""
    text = _text(parts)
    if len(_SENTENCE_END.split(text)) != 1 or _DECLINE.match(" ".join(words(text))) is None or _GOES_ON.search(text):
        return False
    start = next(place for place, part in enumerate(parts) if isinstance(part, str) and part.strip())
    return not any(isinstance(part, Marker) for part in parts[start:])


def _holds(text: tuple[str, ...], sentence: tuple[str, ...]) -> bool:
    return any(text[start : start + len(sentence)] == sentence for start in range(len(text) - len(sentence) + 1))
