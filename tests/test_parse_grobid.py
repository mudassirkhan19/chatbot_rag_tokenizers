"""The opt-in integration test (#21, ADR 0028): a real Seed PDF through the running GROBID container.

Skipped unless RUN_GROBID_TESTS=1. It needs the Seed PDFs in data/pdfs/seeds and GROBID up:

    just grobid-up
    RUN_GROBID_TESTS=1 just test tests/test_parse_grobid.py

GROBID's raw TEI differs from parse to parse (ADR 0024), so the test checks that two cold parses give
byte-identical Chunks and report, not TEI.
"""

import os
import re
from pathlib import Path

import httpx
import pytest

from chatbot_rag_tokenizers.cli import main
from chatbot_rag_tokenizers.parsing.config import load_grobid_config

ROOT = Path(__file__).parents[1]
REPO_CONFIG = ROOT / "config" / "parse.toml"
SEED_PDF = ROOT / "data" / "pdfs" / "seeds" / "wechsel_2112.06598v2.pdf"

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_GROBID_TESTS") != "1", reason="needs the GROBID container; set RUN_GROBID_TESTS=1"
)


@pytest.fixture(scope="module", autouse=True)
def grobid_is_up() -> None:
    url = load_grobid_config(REPO_CONFIG).url
    try:
        alive = httpx.get(f"{url}/api/isalive", timeout=5).text.strip() == "true"
    except httpx.HTTPError:
        alive = False
    if not alive:
        pytest.fail(f"GROBID is not answering at {url}. Start it with `just grobid-up`.")
    if not SEED_PDF.exists():
        pytest.fail(f"{SEED_PDF} is missing: the Seed PDFs belong in data/pdfs/seeds.")


def parse_cold(out: Path) -> dict[str, bytes]:
    """One parse from an empty cache: the Chunks files and the report, as bytes."""
    cache, report = out / "cache", out / "report.md"
    main(["parse", "--config", str(REPO_CONFIG), "--cache", str(cache), "--report", str(report), "--files", str(SEED_PDF)])
    chunks = {str(path.relative_to(cache)): path.read_bytes() for path in sorted(cache.rglob("*.chunks.jsonl"))}
    return chunks | {"report": report.read_bytes()}


def test_a_real_seed_pdf_passes_the_quality_gate_and_two_parses_are_byte_identical(tmp_path):
    first = parse_cold(tmp_path / "first")
    second = parse_cold(tmp_path / "second")

    report = first["report"].decode()
    [line] = [line for line in report.splitlines() if line.startswith("| 2112.06598v2 |")]
    status, sections, chunks = (cell.strip() for cell in line.split("|")[3:6])
    assert status == "parsed", line
    assert int(sections) >= 2 and int(chunks) > 0
    assert re.search(r"^- GROBID version: 0\.9\.1$", report, re.MULTILINE)

    assert len(first) == 2  # the file's Chunks and the report
    assert second == first
