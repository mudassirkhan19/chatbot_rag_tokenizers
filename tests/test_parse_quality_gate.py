"""The quality gate and per-file errors of `parse`, run offline against the fake GROBID service.

Two hand-trimmed fixtures stand for PDFs that come out garbled or empty, both cut from GROBID 0.9.1-crf's
real output for Sennrich et al. v5 (arXiv 1508.07909v5, CC BY 4.0 in the manifest):
- `near-empty.tei.xml`: the abstract and one paragraph of the introduction, 2 Sections and 1,594 characters;
- `scanned.tei.xml`: the header only, no abstract and an empty body, as for a PDF with no text layer.
"""

from pathlib import Path

import pytest

from chatbot_rag_tokenizers.cli import main
from parse_support import run_parse, seed_pdf, sha256


def chunk_files(tmp_path: Path, pdf: Path) -> list[Path]:
    return list((tmp_path / "cache" / sha256(pdf.read_bytes())).glob("*.chunks.jsonl"))


def report(tmp_path: Path) -> str:
    return (tmp_path / "parse-report.md").read_text()


def test_a_garbled_file_fails_the_gate_with_its_reason_and_gets_no_chunks(tmp_path, wechsel, grobid):
    near_empty = seed_pdf(tmp_path, grobid, "near-empty_2401.00001v1.pdf", "near-empty.tei.xml")
    scanned = seed_pdf(tmp_path, grobid, "scanned_2401.00002v1.pdf", "scanned.tei.xml")

    with pytest.raises(SystemExit) as raised:
        run_parse(tmp_path, wechsel, near_empty, scanned)

    assert chunk_files(tmp_path, near_empty) == chunk_files(tmp_path, scanned) == []
    assert chunk_files(tmp_path, wechsel)
    text = report(tmp_path)
    assert (
        f"| 2112.06598v2 | `{sha256(wechsel.read_bytes())}` | parsed | 20 | 52 | 11 | 5 |\n"
        f"| 2401.00001v1 | `{sha256(near_empty.read_bytes())}` | failed: too little body text (1594 characters, minimum 2000) | 2 | 0 | 0 | 0 |\n"
        f"| 2401.00002v1 | `{sha256(scanned.read_bytes())}` | failed: too few Sections (0, minimum 2) | 0 | 0 | 0 | 0 |\n"
    ) in text
    assert "- Files: 3\n- Sections: 22\n- Chunks: 52\n- Table Chunks: 11\n- Caption Chunks: 5\n- Parsed: 1\n- Failed: 2\n" in text
    assert "## Failures by reason\n\n- too few Sections: 1\n- too little body text: 1\n" in text
    assert "- min_sections: `2`\n- min_body_characters: `2000`\n" in text
    message = str(raised.value.code)
    assert message.startswith("parse: 2 files failed.")
    assert "2401.00001v1: too little body text (1594 characters, minimum 2000)" in message
    assert "2401.00002v1: too few Sections (0, minimum 2)" in message


def test_one_failing_file_does_not_stop_the_run_and_every_failure_is_listed_at_the_end(tmp_path, wechsel, grobid, capsys):
    broken = seed_pdf(tmp_path, grobid, "broken_2401.00003v1.pdf", "wechsel_2112.06598v2.tei.xml")
    grobid.fail(broken.read_bytes(), 500, "[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1")
    slow = seed_pdf(tmp_path, grobid, "slow_2401.00004v1.pdf", "wechsel_2112.06598v2.tei.xml")
    grobid.time_out(slow.read_bytes())
    garbled = seed_pdf(tmp_path, grobid, "garbled_2401.00006v1.pdf", "wechsel_2112.06598v2.tei.xml")
    grobid.fail(garbled.read_bytes(), 200, "<TEI><teiHeader>")  # an answer cut off mid-way
    later = seed_pdf(tmp_path, grobid, "later_2401.00007v1.pdf", "wechsel_2112.06598v2.tei.xml")

    with pytest.raises(SystemExit) as raised:
        run_parse(tmp_path, wechsel, broken, slow, garbled, later)

    # The files after the failures were still parsed.
    assert chunk_files(tmp_path, wechsel) and chunk_files(tmp_path, later)
    assert chunk_files(tmp_path, broken) == chunk_files(tmp_path, slow) == chunk_files(tmp_path, garbled) == []
    message = str(raised.value.code)
    assert message.startswith("parse: 3 files failed.")
    assert "2401.00003v1: GROBID error (HTTP 500: [BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1)" in message
    assert "2401.00004v1: GROBID timeout (no answer within 300 s)" in message
    assert "2401.00006v1: GROBID error (unreadable TEI: no element found: line 1, column 16)" in message
    # The failures are printed together after the run's progress lines, not only as they happen.
    assert capsys.readouterr().out.rstrip().splitlines()[-1].startswith("parse: 5 files")
    text = report(tmp_path)
    assert "| 2401.00004v1 | `" + sha256(slow.read_bytes()) + "` | failed: GROBID timeout (no answer within 300 s) | 0 | 0 |" in text
    assert "## Failures by reason\n\n- GROBID error: 2\n- GROBID timeout: 1\n" in text


def test_a_failure_is_permanent_for_the_file_parser_and_config(tmp_path, wechsel, grobid, capsys):
    broken = seed_pdf(tmp_path, grobid, "broken_2401.00003v1.pdf", "wechsel_2112.06598v2.tei.xml")
    grobid.fail(broken.read_bytes(), 500, "[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1")
    near_empty = seed_pdf(tmp_path, grobid, "near-empty_2401.00001v1.pdf", "near-empty.tei.xml")
    with pytest.raises(SystemExit):
        run_parse(tmp_path, wechsel, broken, near_empty)
    first_report = report(tmp_path)
    assert len(grobid.requests) == 3
    capsys.readouterr()

    # A rerun asks GROBID for nothing, even though it would now answer, and reports the same outcome.
    del grobid.errors[sha256(broken.read_bytes())]
    with pytest.raises(SystemExit) as raised:
        run_parse(tmp_path, wechsel, broken, near_empty)

    assert len(grobid.requests) == 3
    assert chunk_files(tmp_path, broken) == []
    assert report(tmp_path) == first_report
    # Recorded failures still count: they are listed at the end and the exit is non-zero.
    message = str(raised.value.code)
    assert message.startswith("parse: 2 files failed, on an earlier run.")
    assert "2401.00001v1: too little body text (1594 characters, minimum 2000)" in message
    assert "2401.00003v1: GROBID error (HTTP 500: [BAD_INPUT_DATA]" in message


def test_an_unreachable_grobid_stops_the_run_straight_away_and_points_to_grobid_up(tmp_path, wechsel, grobid):
    other = seed_pdf(tmp_path, grobid, "sennrich-bpe_1508.07909v5.pdf", "wechsel_2112.06598v2.tei.xml")
    grobid.down = True

    with pytest.raises(SystemExit) as raised:
        run_parse(tmp_path, wechsel, other)

    assert str(raised.value.code) == (
        "parse: the GROBID service isn't reachable at http://localhost:8070."
        " Start it with `just grobid-up` and run parse again."
    )
    assert len(grobid.requests) == 1  # the second file was never tried
    # Nothing is recorded as failed, so the files are parsed once the service is up.
    assert not (tmp_path / "parse-report.md").exists()
    grobid.down = False
    run_parse(tmp_path, wechsel, other)
    assert chunk_files(tmp_path, wechsel) and chunk_files(tmp_path, other)


def test_limit_caps_the_number_of_files_parsed_taking_them_in_order(tmp_path, wechsel, grobid):
    first = seed_pdf(tmp_path, grobid, "sennrich-bpe_1508.07909v5.pdf", "wechsel_2112.06598v2.tei.xml")
    last = seed_pdf(tmp_path, grobid, "later_2401.00005v1.pdf", "wechsel_2112.06598v2.tei.xml")

    main(
        [
            "parse",
            "--cache", str(tmp_path / "cache"),
            "--report", str(tmp_path / "parse-report.md"),
            "--limit", "2",
            "--files", *map(str, [last, wechsel, first]),
        ]
    )  # fmt: skip

    assert len(grobid.requests) == 2
    assert chunk_files(tmp_path, first) and chunk_files(tmp_path, wechsel)
    assert chunk_files(tmp_path, last) == []
    assert "- Files: 2\n" in report(tmp_path)
