"""The `audit label` page's HTTP interface: listing the Audit set and saving a developer's label."""

import csv
import json
import shutil
import threading
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.collection import audit_label
from chatbot_rag_tokenizers.collection.config import load_config
from conftest import FIXTURES


@pytest.fixture
def audit_set(tmp_path: Path) -> Path:
    path = tmp_path / "audit-set.csv"
    shutil.copy(FIXTURES / "audit" / "audit-set.csv", path)
    return path


@pytest.fixture
def page(audit_set: Path) -> Iterator[str]:
    server = audit_label.make_server(load_config(FIXTURES / "scope.toml"), audit_set, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def get(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def save(page: str, **payload: object) -> None:
    request = urllib.request.Request(
        f"{page}/save", json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST"
    )
    urllib.request.urlopen(request).read()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_page_lists_each_row_with_its_draft_label_and_the_judge(page):
    assert b"<title>" in get(page)
    listing = json.loads(get(f"{page}/rows"))

    assert listing["judge"] == {"model": "example/judge-model", "threshold": 0.5}
    rows = listing["rows"]
    assert [row["edition_id"] for row in rows] == ["r1", "r2", "e1", "e2", "i1", "i2", "i3", "i4"]
    r2 = rows[1]
    assert (r2["draft_label"], r2["label"]) == ("no", "yes")
    assert r2["reason"] == "segments rare words into learned units: a subword method the rules miss"
    # A file exported before the provenance columns existed reads as unreviewed pipeline drafts.
    assert (r2["labelled_by"], r2["review_note"]) == ("draft", "")


def test_saving_a_label_rewrites_only_that_row_and_marks_it_the_developers(page, audit_set, tmp_path):
    before = read_rows(audit_set)

    save(page, index=5, label="no", reason="about tokenizer fairness metrics only as a side note")

    after = read_rows(audit_set)
    assert after[5]["label"] == "no"
    assert after[5]["reason"] == "about tokenizer fairness metrics only as a side note"
    assert after[5]["labelled_by"] == "developer"
    for i, (old, new) in enumerate(zip(before, after, strict=True)):
        if i != 5:
            assert {k: new[k] for k in old} == old
            assert new["labelled_by"] == "draft"

    # The report still reads the file, and counts the new correction.
    main(
        [
            "audit", "report",
            "--config", str(FIXTURES / "scope.toml"),
            "--audit-set", str(audit_set),
            "--verdicts", str(FIXTURES / "audit" / "verdicts.jsonl"),
            "--output", str(tmp_path / "report.md"),
            "--no-judge",
        ]
    )
    assert "(4 labels changed from the draft, 0 unlabelled)" in (tmp_path / "report.md").read_text()


def test_saving_rejects_a_label_other_than_yes_no_or_empty(page, audit_set):
    before = audit_set.read_bytes()
    with pytest.raises(urllib.error.HTTPError, match="400"):
        save(page, index=0, label="maybe", reason="")
    assert audit_set.read_bytes() == before
