"""The developer's check of the grounding verdict (#69) over the fixture corpus: `chat-eval --export-check` draws the
sample from the answers file, the `chat-label` page labels it, and the chat report gives the agreement.

The corpus, the scripted answers and the helpers are `test_chat_eval`'s.
"""

import csv
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.chat import grounding_check
from chatbot_rag_tokenizers.cli import main
from conftest import read_rows
import test_chat_eval
from test_chat_eval import EVALUATION_SET, MANIFEST, corpus_arguments, edit_answers, run_chat_eval, script, table
from test_chat_page import SOCKETS

indexed = test_chat_eval.indexed  # the fixture corpus, parsed and indexed in tmp_path


def export_check(tmp_path: Path, *options: str) -> Path:
    """Export the sample from the answers file `run_chat_eval` wrote in tmp_path, and return the sample's path."""
    check = tmp_path / "grounding-check.csv"
    main(
        [
            "chat-eval",
            *corpus_arguments(tmp_path),
            "--evaluation-set", str(EVALUATION_SET),
            "--manifest", str(MANIFEST),
            "--answers", str(tmp_path / "chat-answers.jsonl"),
            "--check", str(check),
            "--export-check",
            *options,
        ]
    )  # fmt: skip
    return check


def test_the_export_samples_answered_turns_with_their_cited_chunks_and_the_automatic_verdict_as_the_draft(indexed, fake_answer_model):
    script(fake_answer_model, vocabulary="WECHSEL uses a vocabulary of 32,000 tokens [1][2].")
    _, turns = run_chat_eval(indexed)

    rows = read_rows(export_check(indexed, "--sample-size", "10"))

    # Every scored Turn that is not an Abstention, in the Evaluation set's order: the ByT5 one abstained.
    assert [row["question_id"] for row in rows] == ["freezing", "metrics-miss", "vocabulary-sizes", "neighbours"]
    scored = {turn["question_id"]: turn for turn in turns if turn["scored"]}
    for row in rows:
        turn = scored[row["question_id"]]
        assert row["reply"] == turn["reply"] and row["question"] == turn["question"]
        assert row["retrieved"].split() == turn["retrieved"]
        cited = json.loads(row["cited_chunks"])
        assert [chunk["chunk_id"] for chunk in cited] == turn["cited"]
        assert [chunk["number"] for chunk in cited] == [turn["retrieved"].index(chunk_id) + 1 for chunk_id in turn["cited"]]
        assert all(chunk["text"] and chunk["header"] for chunk in cited)
        assert row["draft_label"] == row["label"] == ("grounded" if turn["grounded"] else "not grounded")
        assert (row["checked_by"], row["note"]) == ("draft", "")
    vocabulary = rows[2]
    assert vocabulary["draft_label"] == "not grounded"
    assert vocabulary["draft_reason"] == "numbers in no cited Chunk: 32,000"
    assert rows[3]["rewrite"] == scored["neighbours"]["rewrite"]


def test_the_export_is_reproducible_for_a_seed_and_never_overwrites_labels_without_force(indexed, fake_answer_model):
    script(fake_answer_model)
    run_chat_eval(indexed)
    check = export_check(indexed, "--sample-size", "2", "--seed", "3")
    first = check.read_bytes()
    assert len(read_rows(check)) == 2

    check.write_text(first.decode().replace(",draft,", ",developer,"), encoding="utf-8")
    labelled = check.read_bytes()
    with pytest.raises(SystemExit) as stopped:
        export_check(indexed, "--sample-size", "2", "--seed", "3")
    assert "--force" in str(stopped.value.code)
    assert check.read_bytes() == labelled

    export_check(indexed, "--sample-size", "2", "--seed", "3", "--force")
    assert check.read_bytes() == first
    samples = set()
    for seed in range(6):
        export_check(indexed, "--sample-size", "2", "--seed", str(seed), "--force")
        samples.add(tuple(row["question_id"] for row in read_rows(check)))
    assert len(samples) > 1


@pytest.fixture
def exported(indexed: Path, fake_answer_model) -> Path:
    """The fixture set asked, and its four answered Turns exported to check."""
    script(fake_answer_model, vocabulary="WECHSEL uses a vocabulary of 32,000 tokens [1][2].")
    run_chat_eval(indexed)
    return export_check(indexed)


@pytest.fixture
def base_url(exported: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The label page served on a free port, with the sockets the offline parse blocked given back."""
    for owner, name, real in SOCKETS:
        monkeypatch.setattr(owner, name, real)
    server = grounding_check.make_server(exported, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def get(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def save(base_url: str, **payload: object) -> None:
    request = urllib.request.Request(f"{base_url}/save", json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(request).read()


def test_the_page_lists_each_turn_with_its_answer_and_cited_chunks(base_url, exported):
    assert b"<title>" in get(base_url)
    rows = json.loads(get(f"{base_url}/rows"))["rows"]

    assert [(row["index"], row["question_id"]) for row in rows] == [(0, "freezing"), (1, "metrics-miss"), (2, "vocabulary-sizes"), (3, "neighbours")]
    vocabulary = rows[2]
    assert vocabulary["reply"] == "WECHSEL uses a vocabulary of 32,000 tokens [1][2]."
    assert [chunk["number"] for chunk in vocabulary["cited_chunks"]] == [1, 2]
    assert all(chunk["text"] for chunk in vocabulary["cited_chunks"])
    assert (vocabulary["draft_label"], vocabulary["draft_reason"]) == ("not grounded", "numbers in no cited Chunk: 32,000")


def test_saving_a_label_rewrites_only_that_row_and_marks_it_the_developers(base_url, exported):
    before = read_rows(exported)

    save(base_url, index=2, label="grounded", note="  32,000 is the 32k of Chunk 2, written out  ")

    after = read_rows(exported)
    assert (after[2]["label"], after[2]["checked_by"], after[2]["note"]) == ("grounded", "developer", "32,000 is the 32k of Chunk 2, written out")
    assert {**after[2], "label": before[2]["label"], "checked_by": "draft", "note": ""} == before[2]
    assert after[:2] + after[3:] == before[:2] + before[3:]


def test_saving_rejects_a_label_other_than_grounded_not_grounded_or_empty(base_url, exported):
    before = exported.read_bytes()
    for payload in ({"index": 0, "label": "yes"}, {"index": 0, "label": "maybe", "note": ""}, {"index": 9, "label": "grounded"}):
        with pytest.raises(urllib.error.HTTPError, match="400"):
            save(base_url, **payload)
    assert exported.read_bytes() == before
    save(base_url, index=0, label="", note="can't tell from the Chunk")
    assert (read_rows(exported)[0]["label"], read_rows(exported)[0]["checked_by"]) == ("", "developer")


def label(check: Path, **labels: tuple[str, str]) -> None:
    """Set the developer's label and note on the rows of these question ids, as the page saves them."""
    rows = read_rows(check)
    for row in rows:
        if row["question_id"].replace("-", "_") in labels:
            row["label"], row["note"] = labels[row["question_id"].replace("-", "_")]
            row["checked_by"] = "developer"
    with check.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def hand_check(report: str) -> str:
    return report.split("\n## Grounding checked by hand\n", 1)[1].split("\n## ", 1)[0]


def test_the_report_gives_the_agreement_over_the_rows_the_developer_labelled_and_lists_every_disagreement(exported):
    label(
        exported,
        freezing=("grounded", ""),
        metrics_miss=("not grounded", "Chunk 1 never names WikiANN"),
        vocabulary_sizes=("grounded", "32,000 is Chunk 2's 32k"),
    )

    report, turns = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported))

    grounded = {turn["question_id"]: turn["grounded"] for turn in turns if turn["scored"]}
    assert (grounded["freezing"], grounded["metrics-miss"], grounded["vocabulary-sizes"]) == (True, True, False)
    section = hand_check(report)
    assert f"Sample: `{exported}`, 4 Turns: 3 labelled by the developer, 0 left unsure, 1 not checked by the developer" in section
    assert "Agreement with the automatic verdict: 1/3 (0.33 [0.06, 0.79])" in section
    assert "Grounded by the automatic check but not by hand: 1; not grounded by the check but grounded by hand: 1" in section
    assert table(report, "## Grounding checked by hand") == [
        ["metrics-miss", "single-paper", "grounded", "not grounded", "Chunk 1 never names WikiANN"],
        ["vocabulary-sizes", "multi-paper", "not grounded", "grounded", "32,000 is Chunk 2's 32k"],
    ]


def test_a_row_whose_reply_changed_since_the_sample_is_not_compared_and_unsure_rows_are_left_out(exported):
    label(exported, freezing=("not grounded", ""), metrics_miss=("", "can't tell"), vocabulary_sizes=("not grounded", ""))
    edit_answers(exported.parent / "chat-answers.jsonl", lambda record: {**record, "reply": record["reply"].replace("does not need", "never needs")})

    report, _ = run_chat_eval(exported.parent, EVALUATION_SET, "chat", "--from-answers", "--check", str(exported))

    section = hand_check(report)
    assert "4 Turns: 2 labelled by the developer, 1 left unsure, 1 not checked by the developer" in section
    assert "Agreement with the automatic verdict: 1/1 (1.00 [0.21, 1.00])" in section
    assert "Not compared, as this run's reply or Chunks differ from the sample's: freezing" in section
    assert "No disagreements." in section


def test_without_a_sample_the_report_says_how_to_draw_one(indexed, fake_answer_model):
    script(fake_answer_model)

    report, _ = run_chat_eval(indexed, EVALUATION_SET, "chat", "--check", str(indexed / "none.csv"))

    assert "No sample to compare with: `chat-eval --export-check` draws one" in hand_check(report)
