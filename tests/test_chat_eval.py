"""Offline runs of `chat-eval` (#67) over the fixture corpus, with the scripted fake answer model.

The corpus is the retrieval tests' (WECHSEL v2 and a trimmed BPE paper, parsed through the fake GROBID service
and indexed with the fake embedder). Each test scripts the fake's answers, runs `chat-eval` and reads the chat
report and the answers file it writes.
"""

import hashlib
import json
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.chat import model as answer_model
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.model import AnswerModelUnavailable
from chatbot_rag_tokenizers.cli import main
from parse_support import REPO_CONFIG, FakeGrobid, run_parse, seed_pdf

ROOT = Path(__file__).parents[1]
RETRIEVAL_CONFIG = ROOT / "config" / "retrieval.toml"
FIXTURES = Path(__file__).parent / "fixtures" / "eval"
EVALUATION_SET = FIXTURES / "evaluation-set.jsonl"
MANIFEST = FIXTURES / "manifest.csv"
ABSTENTION = load_chat_config(RETRIEVAL_CONFIG).abstention

# The fixture Evaluation set's questions, as the fake answer model is keyed by them.
FREEZING = "Does WECHSEL need to freeze the non-embedding parameters at the start of training, as TransInner does?"
METRICS = "XNLI WikiANN micro F1"
VOCABULARY = "What vocabulary size and byte-level BPE do WECHSEL's target-language tokenizers use, compared with the translation systems?"
NEIGHBOURS_HISTORY = "How does WECHSEL pick the temperature and the number of neighbors?"
NEIGHBOURS = "And what did they settle on for those two?"
NEIGHBOURS_REWRITE = "Which temperature and number of neighbors does WECHSEL settle on?"
BYT5 = "Which learning rate schedule did ByT5 use for pre-training?"


@pytest.fixture
def indexed(tmp_path: Path, grobid: FakeGrobid) -> Path:
    """The fixture papers parsed into tmp_path and indexed with the chatbot's retriever."""
    files = [
        seed_pdf(tmp_path, grobid, "wechsel_2112.06598v2.pdf", "wechsel_2112.06598v2.tei.xml"),
        seed_pdf(tmp_path, grobid, "bpe_1508.07909v5.pdf", "missed-table.tei.xml"),
    ]
    run_parse(tmp_path, *files)
    main(["index", *corpus_arguments(tmp_path), "--retriever", "dense.bge-small",
          "--snapshot", str(tmp_path / "snapshot"), "--manifest", str(tmp_path / "manifest.csv"),
          "--funnel-report", str(tmp_path / "report.md")])  # fmt: skip
    return tmp_path


def corpus_arguments(tmp_path: Path) -> list[str]:
    return [
        "--config", str(RETRIEVAL_CONFIG),
        "--parse-config", str(REPO_CONFIG),
        "--cache", str(tmp_path / "cache"),
        "--parse-report", str(tmp_path / "parse-report.md"),
        "--index-cache", str(tmp_path / "index-cache"),
    ]  # fmt: skip


def script(fake_answer_model, **answers: str) -> None:
    """Every fixture question answered, with ``answers`` in place of the defaults, keyed by the names below. The
    fake answers the first key found in the last message, and the rewriter's holds the earlier question too, so
    the follow-up's key goes before the history's."""
    replies = {
        "neighbours_rewrite": NEIGHBOURS_REWRITE,
        "neighbours": "WECHSEL settles on a temperature of 0.1 and 10 neighbors [1][2][3][4][5].",
        "neighbours_history": "WECHSEL tunes both on a held-out language [1].",
        "freezing": "WECHSEL does not need freezing [1].",
        "metrics": "WECHSEL reports micro F1 on WikiANN [1][2].",
        "vocabulary": "WECHSEL's tokenizers use byte-level BPE with a vocabulary of 50k tokens [1][2][3][4][5].",
        "byt5": ABSTENTION,
    } | answers
    keys = {
        "neighbours_rewrite": NEIGHBOURS,
        "neighbours": NEIGHBOURS_REWRITE,
        "neighbours_history": NEIGHBOURS_HISTORY,
        "freezing": FREEZING,
        "metrics": METRICS,
        "vocabulary": VOCABULARY,
        "byt5": BYT5,
    }
    fake_answer_model.script.update({keys[name]: reply for name, reply in replies.items()})


def run_chat_eval(tmp_path: Path, evaluation_set: Path = EVALUATION_SET, name: str = "chat") -> tuple[str, list[dict]]:
    """Run `chat-eval` on the corpus in tmp_path and return the chat report and the answers file's Turns."""
    report, answers = tmp_path / f"{name}-report.md", tmp_path / f"{name}-answers.jsonl"
    main(
        [
            "chat-eval",
            *corpus_arguments(tmp_path),
            "--evaluation-set", str(evaluation_set),
            "--manifest", str(MANIFEST),
            "--report", str(report),
            "--answers", str(answers),
        ]
    )  # fmt: skip
    return report.read_text(), [json.loads(line) for line in answers.read_text().splitlines()]


def test_a_follow_up_is_a_conversation_whose_history_is_answered_first_and_every_other_question_is_one_turn(indexed, fake_answer_model):
    script(fake_answer_model)

    _, turns = run_chat_eval(indexed)

    assert [(turn["question_id"], turn["turn"], turn["scored"]) for turn in turns] == [
        ("freezing", 1, True),
        ("metrics-miss", 1, True),
        ("vocabulary-sizes", 1, True),
        ("neighbours", 1, False),
        ("neighbours", 2, True),
        ("byt5-schedule", 1, True),
    ]
    history, follow_up = turns[3:5]
    assert history["question"] == NEIGHBOURS_HISTORY and history["rewrite"] is None
    assert history["reply"] == "WECHSEL tunes both on a held-out language [1]."
    assert follow_up["question"] == NEIGHBOURS and follow_up["rewrite"] == NEIGHBOURS_REWRITE
    # The rewriter was shown the bot's own answer to the history, as it would be on the page.
    rewriting = [chat for chat in fake_answer_model.chats if NEIGHBOURS in chat[-1]["content"]]
    assert len(rewriting) == 1 and "WECHSEL tunes both on a held-out language." in rewriting[0][-1]["content"]
    assert all(len(turn["retrieved"]) == 5 for turn in turns)


def table(report: str, heading: str) -> list[list[str]]:
    """The body rows of the Markdown table under a heading, each as its cells."""
    lines = report.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].splitlines()
    rows = [line for line in lines if line.startswith("|")][2:]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]


def results(report: str) -> dict[str, list[str]]:
    """Question type to [questions, abstained, abstention rate, answers, grounded, grounded rate, Recall@5]."""
    return {row[0]: row[1:] for row in table(report, "## Results")}


def questions(report: str) -> dict[str, list[str]]:
    """Question id to [type, abstained, grounded, invalid Citations, numbers not in cited Chunks, Passages in its Chunks]."""
    return {row[0]: row[1:] for row in table(report, "## Questions")}


def test_an_uncited_answer_and_one_with_a_number_no_cited_chunk_holds_are_not_grounded_and_abstentions_are_left_out(indexed, fake_answer_model):
    script(
        fake_answer_model,
        # The freezing question retrieves its Passage's Section, 5.3, whose context header holds the number.
        freezing="Section 5.3 finds no need for freezing with WECHSEL [1][2][3][4][5].",
        metrics="WECHSEL is evaluated on XNLI and WikiANN.",
        vocabulary="WECHSEL uses a vocabulary of 32,000 tokens [1][2][3][4][5].",
        neighbours="WECHSEL settles on both [1].",
    )

    report, turns = run_chat_eval(indexed)

    lines = questions(report)
    assert lines["freezing"][2] == "yes"
    assert lines["metrics-miss"][2] == "no" and lines["metrics-miss"][4] == "—"  # uncited, with no number to miss
    assert lines["vocabulary-sizes"][2:5] == ["no", "—", "32,000"]
    assert lines["neighbours"][2] == "yes"
    assert lines["byt5-schedule"][1:3] == ["yes", "—"]
    # Four answers, the Abstention left out, of which the two above are grounded.
    assert results(report)["all"][3:6] == ["4", "2", "0.50"]
    assert "Not grounded: 1 uncited, 0 with an invalid Citation, 1 with a number in no cited Chunk" in report
    grounded = {turn["question_id"]: turn["grounded"] for turn in turns if turn["scored"]}
    assert grounded == {"freezing": True, "metrics-miss": False, "vocabulary-sizes": False, "neighbours": True, "byt5-schedule": None}


VITAMIN = "How much vitamin D should an adult take each day?"


def with_questions(tmp_path: Path, *records: dict) -> Path:
    """The fixture Evaluation set with these questions after its own."""
    path = tmp_path / "evaluation-set.jsonl"
    lines = [json.dumps({**record, "checked_by": "developer"}) for record in records]
    path.write_text(EVALUATION_SET.read_text(encoding="utf-8") + "".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def test_abstention_is_rated_on_the_unanswerable_questions_by_kind_and_false_abstention_on_the_answerable_ones(indexed, fake_answer_model):
    out_of_topic = {"id": "vitamin-d", "type": "unanswerable", "question": VITAMIN, "passages": [], "unanswerable_kind": "out-of-topic"}
    script(fake_answer_model, freezing=ABSTENTION, byt5="ByT5 uses an inverse square root schedule [1].")
    fake_answer_model.script[VITAMIN] = ABSTENTION

    report, _ = run_chat_eval(indexed, with_questions(indexed, out_of_topic))

    rows = results(report)
    assert rows["all answerable"][:3] == ["4", "1", "0.25"]
    assert rows["single-paper"][:3] == ["2", "1", "0.50"]
    assert rows["unanswerable: near-miss"][:3] == ["1", "0", "0.00"]
    assert rows["unanswerable: out-of-topic"][:3] == ["1", "1", "1.00"]
    assert rows["all unanswerable"][:3] == ["2", "1", "0.50"]
    assert "Abstention rate on the unanswerable questions: 1/2 (0.50); near-miss 0/1 (0.00), out-of-topic 1/1 (1.00)" in report
    assert "False-abstention rate on the answerable questions: 1/4 (0.25)" in report
    # A false Abstention is left out of the grounded rate, as a correct one is; the near-miss's answer is in it.
    assert questions(report)["freezing"][1:3] == ["yes", "—"]
    assert questions(report)["byt5-schedule"][1:3] == ["no", "yes"]
    assert rows["all"][3] == "4"  # six questions, two of them Abstentions


def test_a_question_line_names_its_invalid_citations_and_the_passages_in_its_chunks(indexed, fake_answer_model):
    script(fake_answer_model, freezing="WECHSEL does not need freezing [1][7]. It never did [0, 2].")

    report, turns = run_chat_eval(indexed)

    freezing = questions(report)["freezing"]
    assert freezing[2:4] == ["no", "[7], [0]"]
    assert freezing[5] == "1/1"  # its Passage's Section is retrieved
    assert questions(report)["vocabulary-sizes"][5].endswith("/2")
    [turn] = [turn for turn in turns if turn["question_id"] == "freezing"]
    assert turn["invalid"] == [7, 0] and turn["cited"] == [turn["retrieved"][0], turn["retrieved"][1]]
    assert turn["passages_found"] == [1]


def test_two_runs_give_the_same_report_apart_from_timings_and_the_same_answers(indexed, fake_answer_model):
    script(fake_answer_model)

    first, first_turns = run_chat_eval(indexed, name="first")
    second, second_turns = run_chat_eval(indexed, name="second")

    before_timings = first.split("\n## Timings\n")[0]
    assert "## Questions" in before_timings
    assert before_timings == second.split("\n## Timings\n")[0]
    assert first_turns == second_turns


def test_chat_eval_refuses_a_set_that_fails_eval_check_and_asks_nothing(indexed, fake_answer_model, tmp_path):
    no_kind = {"id": "no-kind", "type": "unanswerable", "question": VITAMIN, "passages": []}

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(indexed, with_questions(tmp_path, no_kind))

    assert "fails eval-check" in str(stopped.value.code)
    assert "no-kind: an unanswerable question needs an unanswerable_kind" in str(stopped.value.code)
    assert fake_answer_model.chats == []
    assert not (indexed / "chat-report.md").exists() and not (indexed / "chat-answers.jsonl").exists()


def test_chat_eval_stops_with_the_reason_when_the_answer_model_cant_answer(indexed, monkeypatch):
    def unavailable(settings):
        raise AnswerModelUnavailable("Ollama is not answering at http://localhost:11434")

    monkeypatch.setattr(answer_model, "load_answer_model", unavailable)

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(indexed)

    assert stopped.value.code == "chat-eval: Ollama is not answering at http://localhost:11434"
    assert not (indexed / "chat-report.md").exists()


def test_the_report_names_the_retriever_the_model_pin_the_prompts_hashes_and_the_set_sha256(indexed, fake_answer_model):
    script(fake_answer_model)
    config = load_chat_config(RETRIEVAL_CONFIG)

    report, _ = run_chat_eval(indexed)

    assert f"- sha256: `{hashlib.sha256(EVALUATION_SET.read_bytes()).hexdigest()}`" in report
    assert f"- Retriever: dense.bge-small (`{config.retriever.key}`), 5 Chunks per Turn" in report
    assert "- Answer model: fake-answer-model, thinking off, temperature 0.0" in report
    assert f"`{hashlib.sha256(config.system_prompt.encode()).hexdigest()}`" in report
    assert f"`{hashlib.sha256(config.rewrite_prompt.encode()).hexdigest()}`" in report
    assert report.index("## Questions") < report.index("## Timings") and report.rstrip().endswith("s |")
