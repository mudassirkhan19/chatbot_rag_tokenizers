# 0015. PDF Fetcher: pinned files, hashes in the Snapshot, open-access fallback

- **Date:** 2026-10-16
- **Status:** Accepted. Amended by [0037](0037-withdrawn-preprints-are-excluded.md): a withdrawn preprint is excluded, so it is never fetched.

## Context
Issue #10 asks for the full-text PDFs of included Editions, each pinned to an exact Version: the latest arXiv Version, plus v1 when a preprint has several, plus the ACL Anthology Edition when there is one. The dedup stage needs those real version and venue duplicates. The sha256 of each file goes in the manifest, and a re-download is checked against it. A missing file or a hash mismatch must say whether the source changed (upstream drift) or the pipeline failed. Rows move to funnel status "full text", or `no_fulltext` when there is no open PDF. PDFs are never committed ([0002](0002-no-pdfs-or-secrets-in-git.md)).

The manifest must stay reproducible offline ([0003](0003-commit-the-snapshot.md)): a `collect` rerun from the Snapshot must rebuild it byte for byte, hashes and funnel status included, without the PDFs.

Venue Editions that are on neither arXiv nor the ACL Anthology have no PDF source except the open-access locations OpenAlex lists in `oa_pdf_urls`. [0014](0014-openalex-discovery-channel.md) already counts on the Fetcher using them.

## Decision
- **A separate `fetch` command** reads the manifest `collect` wrote, downloads the files of every `included` row in Edition id order, and rewrites the manifest. `--limit N` caps the number of files downloaded, for a smoke test. PDFs go to `data/pdfs/` (`--pdfs`), which is gitignored.
- **Which files:**
  - **arXiv preprint:** the pinned Version (the latest at Snapshot time, from `edition_id`) and v1 when they differ, always from a versioned URL, `https://export.arxiv.org/pdf/<id>vN`. arXiv asks harvesters to use the export host. A preprint with no Version history is never fetched, because there would be no Version to pin.
  - **Venue Edition:** one file, from the ACL Anthology `pdf_link` when there is one, otherwise from the first `oa_pdf_urls` link that serves a PDF, best first. An arXiv link among `oa_pdf_urls` is skipped: it is the unversioned preprint, which is a different Edition.
  - File names are the pinned id with `/` and other unsafe characters replaced by `_` (`2004.03720v1.pdf`, `hep-th_9901001v1.pdf`, `10.5555_lrm.2022.7.pdf`).
- **The record:** `data/snapshot/fulltext/pdfs.jsonl` holds one JSON line per fetched file, sorted, with the Edition id, file name, URL, sha256, size and fetch date. It is committed with the Snapshot. `collect` and `fetch` both fill in the manifest from it, so the two always write the same manifest. A file is looked up by its name, which is its pinned id. So when a refreshed Snapshot re-pins a preprint to a newer Version, v1 is still found, only the new Version is fetched, and the old latest Version stays in the record but leaves the manifest.
- **A response counts as a PDF** when it is HTTP 200 and the body starts with `%PDF-`. Publishers often answer a PDF link with a login or captcha page and status 200.
- **Manifest:** a new `pdf_files` column lists `<file> <sha256>` per recorded file, joined with `|`. An included row is `full text` once every file it is pinned to is recorded. It is `no_fulltext` when it has no PDF source, or when its venue sources all answered that they have none. Otherwise it stays `relevant` until fetched.
- **Recorded "no open PDF":** when every source of a venue Edition answers 4xx (except 408 and 429, which mean "try later") or with a non-PDF, a line is recorded with an empty file and hash, the sources tried and an `unavailable` reason. That is a permanent answer, like the Anthology's 404s in [0012](0012-acl-anthology-venue-editions.md), so a rerun doesn't ask again unless the Edition's sources change. To retry anyway, delete the line.
- **Errors**, each naming the file, URL and cause. They are collected so one bad file never stops the run, and printed together at the end. Progress is saved, and the command exits non-zero.
  - **Upstream drift**, for a file in the record: its URL now answers 404 or 410, or serves bytes with a different hash. The changed bytes are never saved, and the record keeps the pinned hash. The message says it is drift, not a pipeline failure, and that deleting the record line re-pins the file to what the source serves now.
  - **Fetch failed**: a network error, a server error (5xx), throttling (408 or 429), or a preprint's pinned Version that isn't served as a PDF, which shouldn't happen. A recorded file that now answers 403 or an error page counts here too, since it isn't clearly gone. The record isn't changed, so a rerun tries again. A venue Edition's next source is tried before a network error counts as a failure.
- **Re-downloads are checked:** a file already in `data/pdfs/` with the recorded hash is kept without a request. A missing or corrupted local file is downloaded again and must match the record.
- **Rate limits:** arXiv requests are spaced 3 s apart, as its terms of use require. Every other host (the ACL Anthology, open-access repositories) gets 1 s, the gap [0012](0012-acl-anthology-venue-editions.md) uses for the Anthology. Each runs on its own clock over one connection, with retry and backoff on 429 and 5xx (`RateLimitedHttp`).

## Alternatives considered
- **Hashes only in the manifest:** the manifest is rebuilt by `collect`, so the hashes would be lost on every rerun, or `collect` would have to read the old manifest back in. A record in the Snapshot keeps the manifest a pure function of the Snapshot.
- **Fetching inside `collect`:** a reviewer's rerun would then need the network and hours of downloads just to check the counts. Fetching on its own also lets `--limit` cap downloads without changing what `collect` writes.
- **`arxiv.org/pdf/<id>` without a Version:** it serves whatever the latest Version is on the day, so the file could change under the record. It also isn't the host arXiv asks harvesters to use.
- **Unpaywall or Semantic Scholar's `openAccessPdf` for venue Editions:** more lookups for each Edition. OpenAlex's locations are already in the manifest, and Unpaywall comes from the same team (OurResearch), so it would mostly repeat them.
- **Stopping at the first error:** a 3,000-file run would stop for every dead link. Collecting the errors and exiting non-zero at the end still makes them impossible to miss.
- **Prior work (research-bot):** it links to `arxiv.org/pdf/<id>.pdf` with whatever Version it stored and keeps uploaded PDFs named by id. It records no hashes, so it can't tell a changed file from the one it used. We keep its id-based file names, with `/` replaced, and add pinning and hashes.

## Consequences
- A full fetch takes about 3 s per arXiv file, so roughly 1.5 to 2.5 hours for 1–3k included Editions, about half of them with two Versions. It resumes where it stopped.
- arXiv rebuilds some PDFs from source when its TeX setup changes, so an old pin can later report upstream drift even though the Version didn't change. The message says so, and re-pinning means deleting one line.
- Publishers that block scripted downloads (MIT Press answered 403 in a live smoke test) are recorded as having no open PDF. The funnel shows how many there are. Adding such a file by hand is not supported yet.
- The record grows by about 250 bytes per file, so under 1 MB for the corpus.
- Adding LaTeX source later means one more `PinnedFile` per arXiv Version, with its own URL.
