"""The judge's guard that "Yes" and "No" are single tokens, checked with stand-in tokenizers."""

import pytest

from chatbot_rag_tokenizers.collection.judge import AnswerTokenError, answer_token_ids


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
