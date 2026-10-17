"""Cache invalidation and determinism of `parse` (#21, ADR 0028), run offline against the fake GROBID service.

Cached TEI is keyed by file hash and parser version, Chunks by those and the chunking-config hash: a
chunking-config change re-chunks from the cached TEI, and a parser change re-parses.
"""

import json
from pathlib import Path

from chatbot_rag_tokenizers.cli import main
from parse_support import REPO_CONFIG, config_with_budget, fake_pdf, run_parse, sha256

REPO_DIGEST = "sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd"


def chunk_files(tmp_path: Path, pdf: Path) -> dict[str, list[dict]]:
    """Every set of Chunks the parse cache holds for one file, by file name."""
    folder = tmp_path / "cache" / sha256(pdf.read_bytes())
    return {
        path.name: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for path in sorted(folder.glob("*.chunks.jsonl"))
    }


def test_a_chunking_config_change_rechunks_from_the_cached_tei_without_calling_grobid(tmp_path, wechsel, grobid):
    run_parse(tmp_path, wechsel)
    [(default_name, default_chunks)] = chunk_files(tmp_path, wechsel).items()

    run_parse(tmp_path, wechsel, config=config_with_budget(tmp_path, 100))

    assert len(grobid.requests) == 1
    files = chunk_files(tmp_path, wechsel)
    # The Chunks of each config are kept apart, so the old ones are never read as the new ones.
    assert len(files) == 2 and files[default_name] == default_chunks
    [small] = [chunks for name, chunks in files.items() if name != default_name]
    assert len(small) > len(default_chunks)
    assert max(c["token_count"] for c in small) <= 100 < max(c["token_count"] for c in default_chunks)

    # Going back to the first config finds its Chunks where they were.
    run_parse(tmp_path, wechsel)
    assert len(grobid.requests) == 1
    assert chunk_files(tmp_path, wechsel) == files


def config_with_grobid_digest(tmp_path: Path, digest: str) -> Path:
    """The repo's parse config pinned to another GROBID image, as a GROBID upgrade would change it."""
    text = REPO_CONFIG.read_text()
    text = text.replace(REPO_DIGEST, digest).replace('tokenizer_file = "', f'tokenizer_file = "{REPO_CONFIG.parent}/')
    path = tmp_path / "parse-new-grobid.toml"
    path.write_text(text)
    return path


def test_a_parser_version_change_reparses(tmp_path, wechsel, grobid):
    run_parse(tmp_path, wechsel)
    [old] = chunk_files(tmp_path, wechsel).values()

    run_parse(tmp_path, wechsel, config=config_with_grobid_digest(tmp_path, "sha256:" + "0" * 64))

    # The new image is asked again, and neither its TEI nor its Chunks overwrite the old image's.
    assert len(grobid.requests) == 2
    folder = tmp_path / "cache" / sha256(wechsel.read_bytes())
    assert len(list(folder.glob("*.tei.xml"))) == 2
    files = chunk_files(tmp_path, wechsel)
    assert len(files) == 2 and old in files.values()
    report = (tmp_path / "parse-report.md").read_text()
    assert f"`grobid/grobid@sha256:{'0' * 64}`" in report

    # A rerun under the new image uses its own cached TEI.
    run_parse(tmp_path, wechsel, config=config_with_grobid_digest(tmp_path, "sha256:" + "0" * 64))
    assert len(grobid.requests) == 2


def output_bytes(cache: Path, report: Path) -> dict[str, bytes]:
    """Every Chunks file in a parse cache, by its path inside the cache, and the report."""
    files = {str(path.relative_to(cache)): path.read_bytes() for path in sorted(cache.rglob("*.chunks.jsonl"))}
    return files | {"report": report.read_bytes()}


def run_parse_into(out: Path, *files: Path) -> dict[str, bytes]:
    main(["parse", "--config", str(REPO_CONFIG), "--cache", str(out / "cache"), "--report", str(out / "report.md"),
          "--files", *map(str, files)])  # fmt: skip
    return output_bytes(out / "cache", out / "report.md")


def as_grobid_varies(tei: str) -> str:
    """The same parse as GROBID sends it at another time: a new request timestamp and new random funder ids
    (ADR 0024). The content the Chunks are built from is unchanged."""
    tei = tei.replace('when="2000-01-01T00:00+0000"', 'when="2026-10-18T09:41+0000"')
    for old, new in [("_q7kuZgJ", "_Zr81bQe"), ("_bf954cw", "_m0Pq2Lx"), ("_XQvxFtu", "_aa3Kd9T")]:
        assert old in tei
        tei = tei.replace(old, new)
    return tei


def test_two_runs_give_byte_identical_chunks_and_report(tmp_path, wechsel, grobid):
    seed = tmp_path / "pdfs" / "sennrich-bpe_1508.07909v5.pdf"
    seed.write_bytes(fake_pdf("sennrich v5"))
    grobid.serve(seed.read_bytes(), "wechsel_2112.06598v2.tei.xml")

    first = run_parse_into(tmp_path / "first", wechsel, seed)
    # A second run from an empty cache, somewhere else, given the files in the other order, while GROBID's
    # answers differ in the parts that change from parse to parse.
    grobid.tei_by_hash = {sha: as_grobid_varies(tei) for sha, tei in grobid.tei_by_hash.items()}
    second = run_parse_into(tmp_path / "second", seed, wechsel)

    assert len(grobid.requests) == 4
    assert len(first) == 3  # two files' Chunks and the report
    assert second == first
    # A rerun on the warm cache rewrites the same bytes.
    assert run_parse_into(tmp_path / "first", seed, wechsel) == first
    assert len(grobid.requests) == 4
