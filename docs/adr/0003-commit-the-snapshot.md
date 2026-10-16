# 0003. Commit the Snapshot of raw source responses

- **Date:** 2026-10-16
- **Status:** Accepted. Supersedes the "downloaded data stays out of git" part of [0002](0002-no-pdfs-or-secrets-in-git.md).

## Context
ADR 0002 kept all downloaded data out of git and relied on rerunning the collection pipeline to rebuild the corpus. But source APIs change their answers over time: new papers arrive, arXiv adds Versions, and Semantic Scholar re-ranks results. A reviewer who reruns the pipeline months later would get a different manifest and couldn't check our counts. The spec (#2) asks for a rerun that reproduces the manifest byte for byte, with no API keys and no network access for metadata.

## Decision
- Every raw source response is stored in a **Snapshot** under `data/snapshot/`, and the Snapshot is committed.
- Each response is one gzip file at `responses/<source>/<sha256>.json.gz`. The hash is taken over a canonical JSON **request description** (`source`, `url`, `params`), and the file holds that description, a `collected_at` date and the response body. Gzip is written with a fixed mtime so the same response always compresses to the same bytes.
- The request description never contains credentials. Clients send API keys as HTTP headers, which are not part of the description, so a key can't reach the cache key or the stored record.
- Collection always reads the Snapshot first and only calls the network on a miss, so each request is fetched once. A rerun against a complete Snapshot makes no network calls.
- The rest of 0002 still holds: PDFs and `.env` stay out of git, and `data/raw/` and `data/pdfs/` stay ignored.

## Alternatives considered
- **Keep raw data out of git (0002 as written):** the manifest is reproducible only while the upstream APIs answer the same way, which they don't.
- **Commit only the manifest and treat it as the record:** this shows what was collected but not how, so a reviewer can't rerun the rule pre-filter or the judge on the same inputs.
- **One SQLite file or a single JSON-lines archive:** fewer files, but every new response rewrites one large binary blob in git. One file per response keeps diffs small and lets git deduplicate unchanged responses.
- **Prior work (research-bot):** it re-queries arXiv on every run and stores no raw responses, so its results can't be reproduced. We keep its practice of saving what the API returned, but as committed, content-addressed files.

## Consequences
- A reviewer reproduces the manifest offline after `uv sync`.
- The repository grows with the Snapshot. The first arXiv query (about 3.3k Candidates) takes 2 MB compressed. The spec sets a warning at about 50 MB, to be added when more sources land.
- `--refresh` (a later ticket) must write new responses alongside or over the old ones deliberately, since the Snapshot is the record of what the corpus depended on.
