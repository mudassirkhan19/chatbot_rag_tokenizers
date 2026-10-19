"""The answer step (ADRs 0054 and 0055): what the answer model is sent for a Turn, and how its reply is read.

The model gets the config's system prompt, then the earlier Turns of the Conversation, each as its question and
its answer's text without the markers (which numbered that Turn's Chunks, not this one's), then the question with
the retrieved Chunks numbered from 1, each under its context header. It cites by number. The reply is cut into
text and markers: a marker naming a retrieved Chunk is a Citation, and any other number is kept as an invalid
marker, never dropped. A reply holding the fixed Abstention sentence, compared after the Passage matcher's
normalisation, is an Abstention.
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
        text = "".join(part for part in self.parts if isinstance(part, str))
        return _BEFORE_PUNCTUATION.sub(r"\1", re.sub(r"[ \t]+", " ", text)).strip()


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
    return Answer(tuple(part for part in parts if part != ""), _holds(words(reply), words(abstention)))


def _holds(text: tuple[str, ...], sentence: tuple[str, ...]) -> bool:
    return any(text[start : start + len(sentence)] == sentence for start in range(len(text) - len(sentence) + 1))
