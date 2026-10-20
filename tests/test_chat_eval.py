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
from chatbot_rag_tokenizers.chat.chat_report import wilson
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


def script(fake_answer_model, **answers: str | list[str]) -> None:
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


def run_chat_eval(tmp_path: Path, evaluation_set: Path = EVALUATION_SET, name: str = "chat", *options: str) -> tuple[str, list[dict]]:
    """Run `chat-eval` on the corpus in tmp_path and return the chat report and the answers file's Turns, without
    its metadata line."""
    report, answers = tmp_path / f"{name}-report.md", tmp_path / f"{name}-answers.jsonl"
    main(
        [
            "chat-eval",
            *corpus_arguments(tmp_path),
            "--evaluation-set", str(evaluation_set),
            "--manifest", str(MANIFEST),
            "--report", str(report),
            "--answers", str(answers),
            *options,
        ]
    )  # fmt: skip
    return report.read_text(), [json.loads(line) for line in answers.read_text().splitlines()[1:]]


def before_timings(report: str) -> str:
    return report.split("\n## Timings\n")[0]


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
    """Question type to [questions, abstained, abstention rate, its interval, answers, grounded, grounded rate, its
    interval, Recall@5]."""
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
    assert results(report)["all"][4:7] == ["4", "2", "0.50"]
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
    assert "Abstention rate on the unanswerable questions: 1/2 (0.50 [0.09, 0.91]); near-miss 0/1 (0.00 [0.00, 0.79]), out-of-topic 1/1 (1.00 [0.21, 1.00])" in report
    assert "False-abstention rate on the answerable questions: 1/4 (0.25 [0.05, 0.70])" in report
    # A false Abstention is left out of the grounded rate, as a correct one is; the near-miss's answer is in it.
    assert questions(report)["freezing"][1:3] == ["yes", "—"]
    assert questions(report)["byt5-schedule"][1:3] == ["no", "yes"]
    assert rows["all"][4] == "4"  # six questions, two of them Abstentions


def test_a_decline_in_the_models_own_words_is_counted_as_an_abstention_and_one_followed_by_an_answer_is_not(indexed, fake_answer_model):
    script(
        fake_answer_model,
        byt5="[3][5]\n\nThe provided chunks do not explicitly state the learning rate schedule used by ByT5.",
        metrics="The provided chunks do not contain the XNLI and WikiANN micro F1.",
        freezing="The provided chunks do not contain TransInner's results. WECHSEL does not need freezing [1].",
    )

    report, turns = run_chat_eval(indexed)

    lines = questions(report)
    assert lines["byt5-schedule"][1:3] == ["yes", "—"]
    assert lines["metrics-miss"][1:3] == ["yes", "—"]
    assert lines["freezing"][1:3] == ["no", "yes"]
    abstained = {turn["question_id"]: turn["abstention"] for turn in turns if turn["scored"]}
    assert abstained == {"freezing": False, "metrics-miss": True, "vocabulary-sizes": False, "neighbours": False, "byt5-schedule": True}
    # The decline's stray markers stay in the answers file, but it has no grounding.
    [byt5] = [turn for turn in turns if turn["question_id"] == "byt5-schedule"]
    assert len(byt5["cited"]) == 2 and byt5["grounded"] is None


def test_a_question_line_names_its_invalid_citations_and_the_passages_in_its_chunks(indexed, fake_answer_model):
    script(fake_answer_model, freezing="WECHSEL does not need freezing [1][7]. It never did [0, 2].")

    report, turns = run_chat_eval(indexed)

    freezing = questions(report)["freezing"]
    assert freezing[2:4] == ["no", "[7], [0]"]
    assert freezing[5] == "1/1: 1"  # its Passage's Section is retrieved
    assert questions(report)["vocabulary-sizes"][5].endswith("/2")
    [turn] = [turn for turn in turns if turn["question_id"] == "freezing"]
    assert turn["invalid"] == [7, 0] and turn["cited"] == [turn["retrieved"][0], turn["retrieved"][1]]
    assert turn["passages_found"] == [1]


def test_two_runs_give_the_same_report_apart_from_timings_and_the_same_answers(indexed, fake_answer_model):
    script(fake_answer_model)

    first, first_turns = run_chat_eval(indexed, name="first")
    second, second_turns = run_chat_eval(indexed, name="second")

    assert "## Questions" in before_timings(first)
    assert before_timings(first) == before_timings(second)
    assert first_turns == second_turns


def test_from_answers_reproduces_the_report_apart_from_timings_and_rewrites_the_answers_byte_identically(indexed, fake_answer_model):
    script(fake_answer_model)
    asked, _ = run_chat_eval(indexed)
    answers = indexed / "chat-answers.jsonl"
    written = answers.read_bytes()
    fake_answer_model.chats.clear()

    rescored, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")

    assert fake_answer_model.chats == []
    assert before_timings(rescored) == before_timings(asked)
    assert "Not measured: this report was re-scored from" in rescored.split("\n## Timings\n")[1]
    assert answers.read_bytes() == written


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
    # The twin retrieves over its retriever's index, so the key is the raw retriever's; the pool tells them apart.
    assert f"- Retriever: dense.bge-small+collapsed (`{config.retriever.key}`), collapse pool 50, 5 Chunks per Turn" in report
    # Built from the [chat] revision the model was checked against, so a re-scored report names it without Ollama.
    assert "- Answer model: gemma4:e2b-mlx@e98b54fe1913 on Ollama 0.40.5, thinking off, temperature 0.0" in report
    assert f"`{hashlib.sha256(config.system_prompt.encode()).hexdigest()}`" in report
    assert f"`{hashlib.sha256(config.rewrite_prompt.encode()).hexdigest()}`" in report
    assert report.index("## Questions") < report.index("## Timings") and report.rstrip().endswith("s |")


def test_a_raw_chatbot_is_named_by_its_retriever_alone_and_its_answers_are_not_rescored_as_the_collapsed_ones(indexed, fake_answer_model):
    script(fake_answer_model)
    config = indexed / "retrieval-raw.toml"
    config.write_text(RETRIEVAL_CONFIG.read_text().replace('retriever = "dense.bge-small+collapsed"', 'retriever = "dense.bge-small"'))
    key = load_chat_config(config).retriever.key

    report, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--config", str(config))

    assert f"- Retriever: dense.bge-small (`{key}`), 5 Chunks per Turn" in report
    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")
    assert "collapse_pool None, not 50" in str(stopped.value.code)


def edit_answers(path: Path, edit) -> None:
    """Rewrite the answers file with ``edit`` applied to each Turn's record, its first line left as it is."""
    first, *records = path.read_text(encoding="utf-8").splitlines()
    path.write_text("".join(line + "\n" for line in [first, *(json.dumps(edit(json.loads(line)), ensure_ascii=False) for line in records)]), encoding="utf-8")


def test_from_answers_scores_a_hand_edited_reply_and_rewrites_its_stored_verdicts(indexed, fake_answer_model):
    script(fake_answer_model)
    run_chat_eval(indexed)
    answers = indexed / "chat-answers.jsonl"
    # The freezing reply loses its Citation and the ByT5 Abstention becomes an answer citing a Chunk not retrieved.
    replies = {"freezing": "WECHSEL does not need freezing.", "byt5-schedule": "ByT5 uses an inverse square root schedule [9]."}
    edit_answers(answers, lambda record: {**record, "reply": replies.get(record["question_id"], record["reply"])})

    report, turns = run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")

    assert questions(report)["freezing"][1:3] == ["no", "no"]
    assert questions(report)["byt5-schedule"][1:4] == ["no", "no", "[9]"]
    rewritten = {turn["question_id"]: turn for turn in turns if turn["scored"]}
    assert rewritten["freezing"]["grounded"] is False and rewritten["freezing"]["cited"] == []
    assert rewritten["byt5-schedule"]["abstention"] is False and rewritten["byt5-schedule"]["invalid"] == [9]
    assert rewritten["byt5-schedule"]["reply"] == replies["byt5-schedule"]


def test_from_answers_refuses_answers_asked_over_other_chunks_or_naming_a_chunk_the_corpus_lacks(indexed, fake_answer_model):
    script(fake_answer_model)
    run_chat_eval(indexed)
    answers = indexed / "chat-answers.jsonl"
    written = answers.read_text(encoding="utf-8")
    first, rest = written.split("\n", 1)
    for key in ("parser", "chunking"):
        answers.write_text(json.dumps({**json.loads(first), key: "other-key"}) + "\n" + rest, encoding="utf-8")

        with pytest.raises(SystemExit) as stopped:
            run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")

        assert f"{key} 'other-key', not " in str(stopped.value.code)
    answers.write_text(written, encoding="utf-8")
    edit_answers(answers, lambda record: {**record, "retrieved": ["0123456789abcdef-0000", *record["retrieved"][1:]]})

    with pytest.raises(SystemExit) as stopped:
        run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")

    assert "freezing Turn 1 retrieved 0123456789abcdef-0000, which this corpus lacks" in str(stopped.value.code)


def test_runs_ask_the_set_again_and_report_each_rate_s_range_the_flaky_questions_and_the_changed_wording(indexed, fake_answer_model):
    # Run 2 answers the freezing question uncited; runs 1 and 3 cite in different words.
    freezing = ["WECHSEL does not need freezing [1].", "WECHSEL does not need freezing.", "No freezing is needed with WECHSEL [1]."]
    script(fake_answer_model, freezing=list(freezing))

    report, turns = run_chat_eval(indexed, EVALUATION_SET, "chat", "--runs", "3")

    assert questions(report)["freezing"][2] == "yes"  # the report is run 1's
    variation = report.split("\n## Variation\n", 1)[1].split("\n## ", 1)[0]
    assert "3 runs of the whole set" in variation
    rates = {row[0]: row[1:] for row in table(report, "## Variation")[:6]}
    # Four answers, the ByT5 Abstention left out; freezing and neighbours are grounded by default.
    assert rates["Grounded rate"] == ["2/4", "1/4", "2/4", "0.25–0.50"]
    assert rates["False-abstention rate, answerable"] == ["0/4", "0/4", "0/4", "0.00–0.00"]
    flaky = {row[0]: row[1:] for row in table(report, "### Questions whose verdict changed")}
    assert flaky == {"freezing": ["single-paper", "0/3", "2/3", "grounded, not grounded, grounded"]}
    assert "- Turns whose reply changed wording from run 1: 1 of 6 (freezing)" in variation
    assert "- Turns whose retrieved Chunks changed from run 1: 0 of 6" in variation
    stored = [json.loads(line) for line in (indexed / "chat-answers-runs.jsonl").read_text().splitlines()]
    assert [record["run"] for record in stored] == [2] * 6 + [3] * 6
    assert [record["reply"] for record in stored if record["question_id"] == "freezing"] == freezing[1:]
    assert len(turns) == 6

    # Re-scoring rebuilds the Variation section from the runs file.
    rescored, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers")

    assert before_timings(rescored) == before_timings(report)


def test_the_wilson_interval_matches_worked_values():
    # 0 of n has the upper bound z²/(n + z²), n of n the lower bound n/(n + z²); 27/34 is ADR 0059's grounded rate.
    assert [round(bound, 4) for bound in wilson(0, 28)] == [0.0, 0.1206]
    assert [round(bound, 4) for bound in wilson(8, 8)] == [0.6756, 1.0]
    assert [round(bound, 2) for bound in wilson(27, 34)] == [0.63, 0.90]


def test_every_rate_in_the_results_has_a_95_percent_interval_and_an_empty_group_shows_a_dash(indexed, fake_answer_model):
    script(fake_answer_model)

    report, _ = run_chat_eval(indexed)

    assert "| Question type | Questions | Abstained | Abstention rate | 95% interval | Answers | Grounded | Grounded rate | 95% interval | Recall@5 |" in report
    rows = results(report)
    assert rows["all"] == ["5", "1", "0.20", "[0.04, 0.62]", "4", "2", "0.50", "[0.15, 0.85]", rows["all"][-1]]
    # The out-of-topic group has no question; the near miss abstained, so it has no answer to ground.
    assert rows["unanswerable: out-of-topic"] == ["0", "0", "—", "—", "0", "0", "—", "—", "—"]
    assert rows["unanswerable: near-miss"][4:8] == ["0", "0", "—", "—"]
    assert "- Grounded rate over every answer that is not an Abstention: 2/4 (0.50 [0.15, 0.85])" in report
    assert "Recall@5 is a mean of per-question shares, not a proportion, and has no interval here" in report


def test_a_baseline_lists_the_questions_whose_verdict_changed_and_marks_those_flaky_in_it_even_when_it_is_the_file_overwritten(indexed, fake_answer_model):
    # The baseline: three runs, the freezing question grounded in runs 1 and 3 only.
    script(fake_answer_model, freezing=["WECHSEL does not need freezing [1].", "WECHSEL does not need freezing.", "No freezing [1]."])
    run_chat_eval(indexed, EVALUATION_SET, "chat", "--runs", "3")
    answers = indexed / "chat-answers.jsonl"
    # Now freezing is never cited, and the ByT5 near miss is answered instead of abstained on.
    fake_answer_model.script.clear()
    script(fake_answer_model, freezing="WECHSEL does not need freezing.", byt5="ByT5 uses an inverse square root schedule [1].")

    report, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--baseline", str(answers))

    assert f"Baseline: `{answers}`, 3 runs" in report
    changed = {row[0]: row[1:] for row in table(report, "## Against the baseline")}
    assert changed == {
        "freezing": ["single-paper", "grounded", "not grounded", "flaky in the baseline: grounded, not grounded, grounded"],
        "byt5-schedule": ["unanswerable", "abstained", "grounded", "—"],
    }
    assert report.index("## Against the baseline") < report.index("## Timings")
    assert "asked over other settings" not in report

    # Re-scored against itself, nothing changed.
    rescored, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers", "--baseline", str(answers))

    assert "No question's verdict changed from the baseline's run 1." in rescored


def test_a_baseline_asked_over_another_chatbot_is_compared_and_the_settings_that_differ_are_named(indexed, fake_answer_model):
    script(fake_answer_model)
    run_chat_eval(indexed)
    baseline = indexed / "baseline-answers.jsonl"
    first, rest = (indexed / "chat-answers.jsonl").read_text(encoding="utf-8").split("\n", 1)
    baseline.write_text(json.dumps({**json.loads(first), "k": 3}) + "\n" + rest, encoding="utf-8")

    report, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--from-answers", "--baseline", str(baseline))

    assert "The baseline was asked over other settings: k 3, here 5." in report
    assert "No question's verdict changed from the baseline's run 1." in report
