"""Offline runs of `fetch` against the fixture manifest and Snapshot, with an in-memory web."""

import csv
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from chatbot_rag_tokenizers.cli import main
from conftest import FIXTURES


def pdf(name: str) -> bytes:
    return f"%PDF-1.5\n% {name}\n%%EOF\n".encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeWeb:
    """URL → (status, body). Every request is recorded; an unknown URL is a 404."""

    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, bytes]] = {}
        self.unreachable: set[str] = set()
        self.requested: list[str] = []

    def serve(self, url: str, body: bytes, status: int = 200) -> None:
        self.pages[url] = (status, body)

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        if url in self.unreachable:
            raise httpx.ConnectError("nodename nor servname provided, or not known", request=request)
        status, body = self.pages.get(url, (404, b"not found"))
        return httpx.Response(status, content=body, request=request)


ARXIV_PDFS = {
    "1508.07909": ["v1", "v5"],
    "1804.10959": ["v1"],
    "1808.06226": ["v1", "v2"],
    "2004.03720": ["v1", "v3"],
    "2410.20771": ["v1", "v3"],
}


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch) -> FakeWeb:
    """Stand in for the network: every HTTP request goes to an in-memory web, and rate-limit waits are skipped.

    It serves the pinned Versions of each included preprint, the ACL Anthology PDFs and some
    open-access copies of venue Editions.
    """
    fake = FakeWeb()
    for arxiv_id, versions in ARXIV_PDFS.items():
        for version in versions:
            fake.serve(f"https://export.arxiv.org/pdf/{arxiv_id}{version}", pdf(f"{arxiv_id}{version}"))
    for acl_id in ["2020.findings-emnlp.414", "D18-2012", "P16-1162", "P18-1007"]:
        fake.serve(f"https://aclanthology.org/{acl_id}.pdf", pdf(acl_id))
    fake.serve("https://direct.mit.edu/tacl/article-pdf/doi/10.1162/tacl_a_00999/tacl_a_00999.pdf", pdf("tacl"))
    # The first open-access copy of the LRM paper is gone; the second one serves it.
    fake.serve("https://lrm.example.org/articles/7.pdf", pdf("lrm-7"))
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: fake.handle(request))
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    return fake


@pytest.fixture
def collected(fixture_snapshot: Path, no_network, tmp_path: Path) -> Path:
    """The manifest `collect` writes from the fixture Snapshot."""
    manifest = tmp_path / "manifest.csv"
    main(["collect", "--config", str(FIXTURES / "scope.toml"), "--snapshot", str(fixture_snapshot), "--manifest", str(manifest)])
    return manifest


def run_fetch(snapshot: Path, manifest: Path, pdfs: Path, *flags: str) -> None:
    main(["fetch", "--snapshot", str(snapshot), "--manifest", str(manifest), "--pdfs", str(pdfs), *flags])


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        return {row["edition_id"]: row for row in csv.DictReader(f)}


def test_multi_version_preprint_gets_v1_and_its_latest_version(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)

    assert (pdfs / "2004.03720v1.pdf").read_bytes() == pdf("2004.03720v1")
    assert (pdfs / "2004.03720v3.pdf").read_bytes() == pdf("2004.03720v3")
    assert not (pdfs / "2004.03720v2.pdf").exists()
    bpe = read_manifest(collected)["2004.03720v3"]
    assert bpe["pdf_files"] == (
        f"2004.03720v1.pdf {sha256(pdf('2004.03720v1'))}|2004.03720v3.pdf {sha256(pdf('2004.03720v3'))}"
    )
    assert bpe["funnel_status"] == "full text"


def test_venue_editions_get_their_acl_pdf_or_else_an_open_access_copy(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)
    rows = read_manifest(collected)

    assert (pdfs / "P16-1162.pdf").read_bytes() == pdf("P16-1162")
    assert rows["P16-1162"]["pdf_files"] == f"P16-1162.pdf {sha256(pdf('P16-1162'))}"
    assert rows["P16-1162"]["funnel_status"] == "full text"
    # No ACL PDF: the first open-access copy that serves a PDF, here the second one.
    assert rows["10.5555/lrm.2022.7"]["pdf_files"] == f"10.5555_lrm.2022.7.pdf {sha256(pdf('lrm-7'))}"
    assert rows["10.5555/lrm.2022.7"]["funnel_status"] == "full text"
    # The Anthology has no page for this ACL ID, so there is no PDF anywhere: the row stays, as no_fulltext.
    assert rows["2022.findings-acl.99"]["pdf_files"] == ""
    assert rows["2022.findings-acl.99"]["funnel_status"] == "no_fulltext"


def test_only_pinned_files_of_included_editions_are_requested(fixture_snapshot, collected, web, tmp_path):
    # An arXiv copy among a venue Edition's open-access links is the unversioned preprint: never fetched.
    text = collected.read_text()
    tacl = "https://direct.mit.edu/tacl/article-pdf/doi/10.1162/tacl_a_00999/tacl_a_00999.pdf"
    collected.write_text(text.replace(tacl, f"https://arxiv.org/pdf/2301.99999|{tacl}"))
    web.serve("https://arxiv.org/pdf/2301.99999", pdf("unversioned"))

    run_fetch(fixture_snapshot, collected, tmp_path / "pdfs")

    arxiv = sorted(url for url in web.requested if "arxiv.org" in url)
    assert arxiv == [
        "https://export.arxiv.org/pdf/1508.07909v1",
        "https://export.arxiv.org/pdf/1508.07909v5",
        "https://export.arxiv.org/pdf/1804.10959v1",
        "https://export.arxiv.org/pdf/1808.06226v1",
        "https://export.arxiv.org/pdf/1808.06226v2",
        "https://export.arxiv.org/pdf/2004.03720v1",
        "https://export.arxiv.org/pdf/2004.03720v3",
        "https://export.arxiv.org/pdf/2410.20771v1",
        "https://export.arxiv.org/pdf/2410.20771v3",
    ]
    rows = read_manifest(collected)
    excluded = [row for row in rows.values() if row["relevance_verdict"] != "included"]
    assert excluded and all(row["pdf_files"] == "" and row["funnel_status"] == "discovered" for row in excluded)
    assert sorted(row["funnel_status"] for row in rows.values() if row["relevance_verdict"] == "included") == (
        ["full text"] * 11 + ["no_fulltext"]
    )


def test_collect_rebuilds_the_fetched_manifest_byte_for_byte(fixture_snapshot, collected, web, no_network, tmp_path):
    run_fetch(fixture_snapshot, collected, tmp_path / "pdfs")

    # The hashes live in the Snapshot, so a rerun needs neither the PDFs nor the network.
    rebuilt = tmp_path / "rebuilt.csv"
    main(["collect", "--config", str(FIXTURES / "scope.toml"), "--snapshot", str(fixture_snapshot), "--manifest", str(rebuilt)])
    assert rebuilt.read_bytes() == collected.read_bytes()
    assert read_manifest(rebuilt)["P18-1007"]["funnel_status"] == "full text"


def test_limit_caps_downloads_and_a_rerun_carries_on(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs, "--limit", "3")

    # Three files, in Edition id order: two venue Editions, then the first of a preprint's two Versions.
    assert sorted(p.name for p in pdfs.iterdir()) == ["10.1162_TACL_A_00999.pdf", "10.5555_lrm.2022.7.pdf", "1508.07909v1.pdf"]
    rows = read_manifest(collected)
    assert rows["1508.07909v5"]["pdf_files"] == f"1508.07909v1.pdf {sha256(pdf('1508.07909v1'))}"
    assert rows["1508.07909v5"]["funnel_status"] == "relevant"  # v5 still to fetch

    web.requested.clear()
    run_fetch(fixture_snapshot, collected, pdfs)
    assert "https://export.arxiv.org/pdf/1508.07909v1" not in web.requested
    assert read_manifest(collected)["1508.07909v5"]["funnel_status"] == "full text"


def test_rerun_with_every_file_in_place_downloads_nothing(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)
    before = collected.read_bytes()

    web.requested.clear()
    run_fetch(fixture_snapshot, collected, pdfs)
    assert web.requested == []
    assert collected.read_bytes() == before


def test_a_corrupted_local_copy_is_downloaded_again_and_checked(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)
    (pdfs / "P18-1007.pdf").write_bytes(b"%PDF-1.5 truncated")

    web.requested.clear()
    run_fetch(fixture_snapshot, collected, pdfs)
    assert web.requested == ["https://aclanthology.org/P18-1007.pdf"]
    assert (pdfs / "P18-1007.pdf").read_bytes() == pdf("P18-1007")


def test_a_pinned_file_that_changed_upstream_is_reported_as_drift(fixture_snapshot, collected, web, tmp_path):
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)
    for name in ["P18-1007.pdf", "2004.03720v1.pdf", "D18-2012.pdf"]:
        (pdfs / name).unlink()
    web.serve("https://aclanthology.org/P18-1007.pdf", pdf("P18-1007, corrected"))
    del web.pages["https://export.arxiv.org/pdf/2004.03720v1"]

    with pytest.raises(SystemExit) as raised:
        run_fetch(fixture_snapshot, collected, pdfs)

    message = str(raised.value.code)
    assert "fetch: 2 pinned files changed upstream since the record was made. This is upstream drift, not a pipeline failure." in message
    assert (
        f"upstream drift: hash mismatch for P18-1007.pdf from https://aclanthology.org/P18-1007.pdf"
        f" (sha256 {sha256(pdf('P18-1007'))}, recorded {datetime.now(UTC).date().isoformat()}):"
        f" it now serves sha256 {sha256(pdf('P18-1007, corrected'))}"
    ) in message
    assert "upstream drift: 2004.03720v1.pdf from https://export.arxiv.org/pdf/2004.03720v1" in message
    assert "is no longer available: HTTP 404" in message
    assert "fetch failed" not in message
    # The changed bytes are never saved, the other files still are, and the record keeps the pinned hashes.
    assert not (pdfs / "P18-1007.pdf").exists()
    assert (pdfs / "D18-2012.pdf").read_bytes() == pdf("D18-2012")
    assert read_manifest(collected)["P18-1007"]["pdf_files"] == f"P18-1007.pdf {sha256(pdf('P18-1007'))}"


def test_a_file_that_could_not_be_fetched_is_a_failure_not_drift(fixture_snapshot, collected, web, tmp_path):
    web.serve("https://export.arxiv.org/pdf/1808.06226v2", b"<html>Service unavailable</html>", status=503)
    web.serve("https://export.arxiv.org/pdf/2410.20771v3", b"<html>PDF unavailable</html>")
    pdfs = tmp_path / "pdfs"

    with pytest.raises(SystemExit) as raised:
        run_fetch(fixture_snapshot, collected, pdfs)

    message = str(raised.value.code)
    assert "2 files couldn't be fetched. Nothing was recorded for them, so a rerun tries again." in message
    assert "fetch failed: 1808.06226v2.pdf: https://export.arxiv.org/pdf/1808.06226v2: HTTP 503" in message
    assert "fetch failed: 2410.20771v3.pdf: https://export.arxiv.org/pdf/2410.20771v3: not a PDF" in message
    assert "upstream drift" not in message
    rows = read_manifest(collected)
    assert rows["1808.06226v2"]["funnel_status"] == "relevant"
    assert rows["1808.06226v2"]["pdf_files"] == f"1808.06226v1.pdf {sha256(pdf('1808.06226v1'))}"
    assert rows["P16-1162"]["funnel_status"] == "full text"

    web.serve("https://export.arxiv.org/pdf/1808.06226v2", pdf("1808.06226v2"))
    web.serve("https://export.arxiv.org/pdf/2410.20771v3", pdf("2410.20771v3"))
    run_fetch(fixture_snapshot, collected, pdfs)
    assert read_manifest(collected)["1808.06226v2"]["funnel_status"] == "full text"


def test_a_venue_edition_whose_open_access_links_all_fail_has_no_fulltext(fixture_snapshot, collected, web, tmp_path):
    tacl = "https://direct.mit.edu/tacl/article-pdf/doi/10.1162/tacl_a_00999/tacl_a_00999.pdf"
    web.serve(tacl, b"<html>Sign in to download</html>", status=403)
    pdfs = tmp_path / "pdfs"
    run_fetch(fixture_snapshot, collected, pdfs)

    row = read_manifest(collected)["10.1162/TACL_A_00999"]
    assert row["funnel_status"] == "no_fulltext"
    assert row["pdf_files"] == ""

    # The answer is recorded, like the ACL Anthology's 404s, so a rerun doesn't ask again.
    web.requested.clear()
    run_fetch(fixture_snapshot, collected, pdfs)
    assert tacl not in web.requested


def test_an_unreachable_open_access_host_falls_through_to_the_next_copy(fixture_snapshot, collected, web, tmp_path):
    web.unreachable.add("https://repo.example.edu/1234/lrm-7.pdf")
    web.unreachable.add("https://direct.mit.edu/tacl/article-pdf/doi/10.1162/tacl_a_00999/tacl_a_00999.pdf")
    with pytest.raises(SystemExit) as raised:
        run_fetch(fixture_snapshot, collected, tmp_path / "pdfs")

    rows = read_manifest(collected)
    assert rows["10.5555/lrm.2022.7"]["funnel_status"] == "full text"
    # With no other copy, an unreachable host is a failure to retry, never a recorded "no open PDF".
    assert "fetch failed: 10.1162_TACL_A_00999.pdf: https://direct.mit.edu/" in str(raised.value.code)
    assert rows["10.1162/TACL_A_00999"]["funnel_status"] == "relevant"
