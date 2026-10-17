"""The judge's guard that "Yes" and "No" are single tokens, checked with stand-in tokenizers, and
P("Yes") read from the top logprobs an Ollama model returns."""

import math
from dataclasses import replace

import pytest

from chatbot_rag_tokenizers.collection.config import DecisionQuestion, JudgeConfig
from chatbot_rag_tokenizers.collection.judge import (
    AnswerTokenError,
    answer_token_ids,
    p_yes_from_logprobs,
    prompt_hash,
    question_hash,
)


class StubTokenizer:
    def __init__(self, vocabulary: dict[str, list[int]]) -> None:
        self.vocabulary = vocabulary

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        assert not add_special_tokens, "special tokens would make every answer look multi-token"
        return self.vocabulary[text]


def test_single_token_answers_give_their_ids():
    assert answer_token_ids(StubTokenizer({"Yes": [9454], "No": [2753]})) == (9454, 2753)


def test_an_answer_split_into_several_tokens_is_refused():
    with pytest.raises(AnswerTokenError, match="'Yes' is 2 tokens"):
        answer_token_ids(StubTokenizer({"Yes": [56, 288], "No": [2753]}))


def test_answers_sharing_a_token_are_refused():
    with pytest.raises(AnswerTokenError, match="same token"):
        answer_token_ids(StubTokenizer({"Yes": [7], "No": [7]}))


def top(**logprobs: float) -> list[dict]:
    return [{"token": token, "logprob": logprob} for token, logprob in logprobs.items()]


def test_p_yes_is_the_softmax_over_the_two_answers_only():
    # e^-1 / (e^-1 + e^-2), whatever else the model might have said.
    assert p_yes_from_logprobs(top(Yes=-1.0, **{"**": -1.5}, No=-2.0)) == pytest.approx(1 / (1 + math.e**-1))


def test_an_answer_outside_the_top_logprobs_counts_as_the_least_likely_one_listed():
    # "No" is at most as likely as "Maybe", the last token listed: P("Yes") = 1 / (1 + e^-9).
    assert p_yes_from_logprobs(top(Yes=-1.0, Maybe=-10.0)) == pytest.approx(1 / (1 + math.e**-9))
    assert p_yes_from_logprobs(top(No=-0.5, Maybe=-8.5)) == pytest.approx(1 / (1 + math.e**8))


def test_a_decision_model_verdict_is_tied_to_its_question_and_a_chat_model_to_its_prompt():
    question = DecisionQuestion("{title} {abstract}", "Q?", "T", "F")
    chat = JudgeConfig("m", "r", 0.5, "{title} {abstract}", decision=question)
    decision = replace(chat, backend="ollama-decision")

    # A chat model is asked the prompt, whatever the decision question says, so earlier
    # verdicts keep their hash.
    assert question_hash(chat) == prompt_hash("{title} {abstract}")
    assert question_hash(chat) == question_hash(replace(chat, decision=replace(question, true="U")))
    # A decision model is asked the question, so editing any part of it re-scores.
    assert question_hash(decision) != question_hash(chat)
    assert question_hash(decision) == question_hash(replace(decision, prompt="other"))
    for edited in (replace(question, state="{abstract}"), replace(question, instructions="R?"), replace(question, false="G")):
        assert question_hash(decision) != question_hash(replace(decision, decision=edited))
