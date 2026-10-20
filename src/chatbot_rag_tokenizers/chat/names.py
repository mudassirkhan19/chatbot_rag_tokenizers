"""The papers a question names (ADR 0076), as the answer model lists them, for per-paper retrieval.

The model gets the config's names prompt and the question alone, and replies with one name per line, or NONE. A line
is read without a list marker or quotes, and kept only when the question holds it, in any case: the 2B model also
lists methods a question never names, and a name it invents would send retrieval to a paper nobody asked about.
"""

import re

from .model import AnswerModel, Message


def name_papers(model: AnswerModel, names_prompt: str, question: str) -> tuple[str, ...]:
    """The papers, methods and models ``question`` names. Raises AnswerModelUnavailable."""
    return read_names(model.complete(names_messages(names_prompt, question)), question)


def names_messages(names_prompt: str, question: str) -> list[Message]:
    return [{"role": "system", "content": names_prompt}, {"role": "user", "content": question}]


_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")  # "1. ", "- ", "* "
_QUOTES = "\"'“”‘’"


def read_names(reply: str, question: str) -> tuple[str, ...]:
    names = (_MARKER.sub("", line).strip().strip(_QUOTES).strip() for line in reply.splitlines())
    held = (name for name in names if name and name.upper() != "NONE" and name.lower() in question.lower())
    return tuple(dict.fromkeys(held))
