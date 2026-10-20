"""The decision model as a grounding judge (#70) over the fixture corpus: `chat-eval --judge` scores each labelled
row of the developer's sample with a scripted fake decision model, and the chat report gives its agreement with the
hand labels.

The corpus, the scripted answers, the sample and the helpers are `test_chat_eval`'s and `test_grounding_check`'s.
"""

import hashlib
import json
import re
import tomllib
from dataclasses import replace

import pytest

from chatbot_rag_tokenizers.chat import grounding_judge
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.grounding_judge import OllamaGroundingJudge
from chatbot_rag_tokenizers.collection.config import load_config
from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.ollama import Ollama
from chatbot_rag_tokenizers.parsing.chunker import Chunk
from conftest import read_rows
import test_chat_eval
import test_grounding_check
from test_chat_eval import EVALUATION_SET, RETRIEVAL_CONFIG, ROOT, run_chat_eval, script
from test_grounding_check import hand_check, label, write_rows
from test_ollama_judge import PIN, StubOllama, client

indexed = test_chat_eval.indexed
exported = test_grounding_check.exported  # the fixture set asked, and its four answered Turns exported to check


class FakeDecisionModel:
    """A scripted decision model in place of Tev1: P(yes) for the first key found in the claim, 0.9 for any other,
    and every claim and Chunk it was asked about, in order."""

    def __init__(self) -> None:
        self.script: dict[str, float] = {}
        self.asked: list[tuple[str, str]] = []

    def support(self, claim: str, chunk: Chunk) -> float:
        self.asked.append((claim, chunk.chunk_id))
        return next((p for key, p in self.script.items() if key in claim), 0.9)


@pytest.fixture
def fake_judge(monkeypatch: pytest.MonkeyPatch) -> FakeDecisionModel:
    fake = FakeDecisionModel()
    monkeypatch.setattr(grounding_judge, "load_grounding_judge", lambda settings: fake)
    return fake


def judge_section(report: str) -> str:
    return hand_check(report).split("\n### The decision model\n", 1)[1]


def table(section: str) -> list[str]:
    return [line for line in section.splitlines() if line.startswith("| ") and "Question" not in line]


def test_the_judge_scores_each_labelled_row_and_the_report_gives_its_agreement_with_the_hand_labels(exported, fake_judge):
    label(
        exported,
        freezing=("grounded", ""),
        metrics_miss=("not grounded", "Chunk 1 never names WikiANN"),
        vocabulary_sizes=("grounded", "32,000 is Chunk 2's 32k"),
    )
    fake_judge.script = {"micro F1": 0.2, "32,000": 0.4}

    report, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported), "--judge")

    # Each sentence citing Chunks is one claim, judged against each Chunk it cites; the unlabelled row is not judged.
    assert [claim for claim, _ in fake_judge.asked] == [
        "WECHSEL does not need freezing.",
        *["WECHSEL reports micro F1 on WikiANN."] * 2,
        *["WECHSEL uses a vocabulary of 32,000 tokens."] * 2,
    ]
    section = judge_section(report)
    settings = tomllib.loads(RETRIEVAL_CONFIG.read_text())["chat"]["judge"]
    question = {field: settings[field] for field in ("state", "instructions", "true", "false", "threshold")}
    assert "- Decision model: tev1:4b@4d24c6f6d61a on Ollama 0.40.5" in section
    assert f"- Decision question and threshold sha256: `{hashlib.sha256(json.dumps(question, sort_keys=True).encode()).hexdigest()}`" in section
    assert f"- Threshold: {settings['threshold']}" in section
    assert "- Agreement with the hand labels: 2/3 (0.67 [0.21, 0.94])" in section
    assert "- Grounded by the decision model but not by hand: 0; not grounded by it but grounded by hand: 1" in section
    assert table(section) == [
        "| freezing | single-paper | 1 | 0.90 | grounded | grounded | grounded |",
        "| metrics-miss | single-paper | 2 | 0.20 | not grounded | grounded | not grounded |",
        "| vocabulary-sizes | multi-paper | 2 | 0.40 | not grounded | not grounded | grounded |",
        "| vocabulary-sizes | multi-paper | not grounded | grounded | 32,000 is Chunk 2's 32k |",
    ]


def test_without_the_flag_the_report_has_no_judge_and_asks_it_nothing(exported, fake_judge):
    label(exported, freezing=("grounded", ""))

    plain, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported))
    assert fake_judge.asked == []
    judged, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported), "--judge")

    assert [claim for claim, _ in fake_judge.asked] == ["WECHSEL does not need freezing."]
    assert "The decision model" not in plain
    start, end = judged.index("\n### The decision model\n"), judged.index("\n## Variation\n")
    assert judged[:start] + judged[end:] == plain


def test_a_run_that_asks_the_set_judges_the_sample_as_a_re_scored_one_does(exported, fake_answer_model, fake_judge):
    label(exported, freezing=("grounded", ""), vocabulary_sizes=("grounded", ""))
    fake_judge.script = {"32,000": 0.4}
    script(fake_answer_model, vocabulary="WECHSEL uses a vocabulary of 32,000 tokens [1][2].")

    report, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--check", str(exported), "--judge")

    assert "- Agreement with the hand labels: 1/2 (0.50 [0.09, 0.91])" in judge_section(report)


def test_a_sampled_reply_citing_no_chunk_has_no_score_and_is_not_grounded_by_the_judge(exported, fake_judge):
    rows = read_rows(exported)
    for row in rows:
        if row["question_id"] == "freezing":
            row["reply"] = "WECHSEL does not need freezing. It trains every parameter [7]."
    write_rows(exported, rows)
    label(exported, freezing=("not grounded", "cites nothing"))

    report, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported), "--judge")

    assert fake_judge.asked == []
    section = judge_section(report)
    assert "- Agreement with the hand labels: 1/1 (1.00 [0.21, 1.00])" in section
    assert table(section) == ["| freezing | single-paper | 0 | — | not grounded | not grounded | not grounded |"]
    assert "The decision model agrees with every hand label." in section


def test_a_judge_that_cant_judge_stops_chat_eval_with_the_reason_before_anything_is_asked(exported, fake_answer_model, monkeypatch):
    def unavailable(settings):
        raise grounding_judge.JudgeUnavailable("Ollama is not answering at http://localhost:11434")

    monkeypatch.setattr(grounding_judge, "load_grounding_judge", unavailable)
    asked = len(fake_answer_model.chats)

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--check", str(exported), "--judge")

    assert stopped.value.code == "chat-eval: Ollama is not answering at http://localhost:11434"
    assert len(fake_answer_model.chats) == asked


def test_judge_needs_a_chat_judge_table(exported, fake_judge, tmp_path):
    config = tmp_path / "no-judge.toml"
    config.write_text(RETRIEVAL_CONFIG.read_text().split("\n[chat.judge]\n")[0])

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported), "--judge", "--config", str(config))

    assert stopped.value.code == f"chat-eval: --judge needs a [chat.judge] table in {config}"


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("threshold = 0.5", "threshold = 1.5", "[chat.judge] threshold 1.5 is not between 0 and 1"),
        ("Claim: {claim}", "Claim:", "[chat.judge] state has no {claim} placeholder"),
        ('revision = "4d24c6f6', 'revision = "', "[chat.judge] revision"),
    ],
)
def test_the_judge_config_is_checked(tmp_path, old, new, message):
    text = RETRIEVAL_CONFIG.read_text()
    head, judge = text.split("\n[chat.judge]\n")
    config = tmp_path / "retrieval.toml"
    config.write_text(f"{head}\n[chat.judge]\n{judge.replace(old, new, 1)}")

    with pytest.raises(ConfigError, match=re.escape(message)):
        load_chat_config(config)


def test_the_judge_is_the_scope_configs_pinned_decision_model():
    scope = load_config(ROOT / "config" / "scope.toml").judge
    judge = load_chat_config(RETRIEVAL_CONFIG).judge

    assert judge is not None and (judge.model, judge.revision) == (scope.model, scope.revision)
    assert scope.backend == "ollama-decision"


def test_the_ollama_judge_asks_tev1_whether_the_chunk_header_and_text_support_the_claim():
    server = StubOllama(noul=0.83)
    settings = load_chat_config(RETRIEVAL_CONFIG).judge
    assert settings is not None
    settings = replace(settings, model="gemma4:e2b-mlx", revision=PIN, state="Chunk: {chunk}\n\nClaim: {claim}")
    chunk = Chunk("c1", "e1", "e1", "v1", "f" * 64, "3", "Results", ("Results",), False, "text", None, None, "Paper › Results", "WECHSEL uses {braces} and 32k tokens.", 9)

    judge = OllamaGroundingJudge(settings, Ollama(client(server)))

    assert judge.support("WECHSEL uses 32,000 tokens.", chunk) == 0.83
    [decision] = server.requests
    assert decision == {
        "model": "gemma4:e2b-mlx",
        "state": "Chunk: Paper › Results\nWECHSEL uses {braces} and 32k tokens.\n\nClaim: WECHSEL uses 32,000 tokens.",
        "questions": {"supported": {"type": "noul", "instructions": settings.instructions, "criteria": {"true": settings.true, "false": settings.false}}},
    }


def test_the_ollama_judge_refuses_a_model_other_than_the_pinned_one():
    settings = load_chat_config(RETRIEVAL_CONFIG).judge
    assert settings is not None

    with pytest.raises(grounding_judge.JudgeUnavailable, match="tev1:4b is not installed"):
        OllamaGroundingJudge(settings, Ollama(client(StubOllama())))


def test_a_claim_and_chunk_too_long_for_the_judge_stop_it_with_the_reason_not_a_pull():
    settings = load_chat_config(RETRIEVAL_CONFIG).judge
    assert settings is not None
    settings = replace(settings, model="gemma4:e2b-mlx", revision=PIN)
    chunk = Chunk("c1", "e1", "e1", "v1", "f" * 64, "3", "Results", ("Results",), False, "text", None, None, "Paper", "word " * 80, 80)

    judge = OllamaGroundingJudge(settings, Ollama(client(StubOllama(max_tokens=50))))

    with pytest.raises(grounding_judge.JudgeUnavailable, match="refused a claim and its Chunk: the input has \\d+ tokens, more than the model's 50-token context"):
        judge.support("WECHSEL uses 32,000 tokens.", chunk)


def test_judge_without_a_sample_stops_before_anything_is_asked(indexed, fake_answer_model, fake_judge):
    script(fake_answer_model)
    missing = indexed / "none.csv"

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(indexed, EVALUATION_SET, "chat", "--check", str(missing), "--judge")

    assert stopped.value.code == f"chat-eval: --judge scores the hand-checked sample, and {missing} doesn't exist; draw it with `chat-eval --export-check`"
    assert fake_answer_model.chats == []
