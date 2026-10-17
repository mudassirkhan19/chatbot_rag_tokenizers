"""The Ollama judges against a stand-in Ollama server: the pin on digest and server version, and
the requests they send for a chat model and for a decision model."""

import json
import math

import httpx
import pytest

from chatbot_rag_tokenizers.collection.config import DecisionQuestion, JudgeConfig
from chatbot_rag_tokenizers.collection.editions import Edition
from chatbot_rag_tokenizers.collection.judge import OllamaDecisionJudge, OllamaJudge, OllamaModelError

DIGEST = "e98b54fe1913178321e1d9cd007d12a465de77a8f8eae37af69d2501ca03c6b5"
PIN = f"{DIGEST}@0.40.5"
PROMPT = "Title: {title}\n\nAbstract: {abstract}\n\nAnswer with Yes or No."
DECISION = DecisionQuestion(
    state="Title: {title}\n\nAbstract: {abstract}",
    instructions="Is this paper about tokenization?",
    true="It studies tokenization.",
    false="It does not.",
)
EDITION = Edition("2401.00001", "", "Byte Pair Encoding", "We study BPE.", [], "")


def config(revision: str = PIN, model: str = "gemma4:e2b-mlx", backend: str = "ollama") -> JudgeConfig:
    return JudgeConfig(model, revision, 0.5, PROMPT, backend=backend, decision=DECISION)


class StubOllama:
    """Ollama 0.40.5 with one installed model, answering chats with the given top logprobs and
    decisions with the given probability."""

    def __init__(self, top_logprobs: list[dict] | None = None, noul: float = 0.0) -> None:
        self.top_logprobs = top_logprobs or []
        self.noul = noul
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.5"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e2b-mlx", "digest": DIGEST}]})
        self.requests.append(json.loads(request.content))
        if request.url.path == "/api/chat":
            return httpx.Response(200, json={"message": {"content": "Yes"}, "logprobs": [{"top_logprobs": self.top_logprobs}]})
        assert request.url.path == "/v1/systemone"
        return httpx.Response(200, json={"answers": {"in_scope": {"type": "noul", "noul": self.noul}}})


def client(server: StubOllama) -> httpx.Client:
    return httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(server))


def test_scores_each_edition_from_one_answer_token_without_thinking():
    server = StubOllama([{"token": "Yes", "logprob": -1.0}, {"token": "No", "logprob": -2.0}])
    judge = OllamaJudge(config(), client(server))

    assert judge.score([EDITION, EDITION]) == [pytest.approx(1 / (1 + math.e**-1))] * 2

    [chat, _] = server.requests
    assert chat["model"] == "gemma4:e2b-mlx"
    assert chat["messages"] == [
        {"role": "user", "content": "Title: Byte Pair Encoding\n\nAbstract: We study BPE.\n\nAnswer with Yes or No."}
    ]
    assert chat["think"] is False
    assert chat["logprobs"] is True
    assert chat["options"]["num_predict"] == 1
    assert chat["options"]["temperature"] == 0


def test_a_decision_model_answers_one_true_or_false_question_about_the_state():
    server = StubOllama(noul=0.83)
    judge = OllamaDecisionJudge(config(backend="ollama-decision"), client(server))

    assert judge.score([EDITION]) == [0.83]

    [decision] = server.requests
    assert decision == {
        "model": "gemma4:e2b-mlx",
        "state": "Title: Byte Pair Encoding\n\nAbstract: We study BPE.",
        "questions": {
            "in_scope": {
                "type": "noul",
                "instructions": "Is this paper about tokenization?",
                "criteria": {"true": "It studies tokenization.", "false": "It does not."},
            }
        },
    }


@pytest.mark.parametrize("judge_class", [OllamaJudge, OllamaDecisionJudge])
def test_a_model_whose_installed_digest_differs_from_the_pin_is_refused(judge_class):
    with pytest.raises(OllamaModelError, match="has digest e98b54fe.*not the pinned 00000000"):
        judge_class(config(revision="0" * 64 + "@0.40.5"), client(StubOllama()))


@pytest.mark.parametrize("judge_class", [OllamaJudge, OllamaDecisionJudge])
def test_another_ollama_version_is_refused_because_it_changes_the_scores(judge_class):
    with pytest.raises(OllamaModelError, match="Ollama 0.40.5 is running, not the pinned 0.34.2"):
        judge_class(config(revision=f"{DIGEST}@0.34.2"), client(StubOllama()))


def test_a_pin_without_the_ollama_version_is_refused():
    with pytest.raises(OllamaModelError, match="<digest>@<Ollama version>"):
        OllamaJudge(config(revision=DIGEST), client(StubOllama()))


def test_a_model_that_is_not_installed_is_refused():
    with pytest.raises(OllamaModelError, match="ollama pull gemma4:e4b"):
        OllamaJudge(config(model="gemma4:e4b"), client(StubOllama()))
