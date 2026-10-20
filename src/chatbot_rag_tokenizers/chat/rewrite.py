"""The rewriter (ADR 0056): a follow-up question made standalone from the Conversation before it, for retrieval.

The answer model gets the config's rewrite prompt, then one user message holding the earlier Turns' questions and
answer texts, never their Chunks, and the follow-up. Its reply, cut to its first line without quotes, is the
Rewrite. A reply with nothing left falls back to the follow-up as asked, so retrieval always has a query.
`evaluate` rewrites a stored follow-up from its history's questions alone, which have no answers: an earlier Turn
with an empty answer is shown as its question only (ADR 0067).
"""

from .answer import Earlier
from .model import AnswerModel, Message


def rewrite(model: AnswerModel, rewrite_prompt: str, earlier: Earlier, question: str) -> str:
    """The Rewrite of ``question`` after the ``earlier`` Turns. Raises AnswerModelUnavailable."""
    return read_rewrite(model.complete(rewrite_messages(rewrite_prompt, earlier, question)), question)


def rewrite_messages(rewrite_prompt: str, earlier: Earlier, question: str) -> list[Message]:
    conversation = "\n\n".join(f"Question: {asked}" + (f"\nAnswer: {answered}" if answered else "") for asked, answered in earlier)
    return [
        {"role": "system", "content": rewrite_prompt},
        {"role": "user", "content": f"Conversation so far:\n\n{conversation}\n\nFollow-up question: {question}"},
    ]


def read_rewrite(reply: str, question: str) -> str:
    line = next((line.strip() for line in reply.splitlines() if line.strip()), "")
    return line.strip("\"'“”").strip() or question
