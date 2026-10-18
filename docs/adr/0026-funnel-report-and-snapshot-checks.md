# 0026. The funnel report is written from the manifest, and collect checks the Snapshot

- **Date:** 2026-10-18
- **Status:** Accepted. Completes the size warning that [0003](0003-commit-the-snapshot.md) left for later. Amended by [0045](0045-index-marks-editions-indexed-from-a-committed-record.md): the report counts indexed Editions.

## Context
Issue #11 asks for the full run's funnel (discovered, rejected by the rules, rejected by the judge, included, full text) and its per-channel counts, committed, for the write-up. `collect` already printed these counts to stderr, and the first full run's report was a copy of that output saved by hand (`docs/reports/2026-10-17-first-full-run.txt`). A hand-saved copy can't be checked against a rerun.

The issue also asks for a warning when the Snapshot is over about 50 MB, and a check that it contains no credentials. [0003](0003-commit-the-snapshot.md) keeps keys out of the Snapshot by design: they are sent as headers and are never part of a request description. Nothing yet checked that this held.

## Decision
- **`collect` and `fetch` write `data/report.md`** (`--report`), a Markdown report built from the manifest rows alone. It has the funnel, the rule rejections by pattern, per-source and per-Discovery-channel tables (Editions found, included, found by no other, and of those how many pass the rules, are included or are pending), and what citation expansion adds beyond keyword search. It is committed with the manifest. Since it depends only on the rows, a rerun from the Snapshot rewrites it byte for byte. `fetch` rewrites it because fetching changes the full-text counts.
- **The stderr summary uses the same counts**, so the two can't disagree.
- **`collect` prints the Snapshot's size and warns above 50 MB** (decimal megabytes, file sizes as committed). It is a warning, not an error: it asks for a look at what grew before committing.
- **`collect` stops if any API key set in the environment is in the Snapshot.** It looks for the values of `S2_API_KEY` and `OPENALEX_API_KEY` in every Snapshot file, decompressed, and names the files and the variable but never the value. Without a key in the environment there is nothing to look for, so a reviewer's offline rerun skips the check.
- **The Snapshot is committed at its current size, over the warning.** The full run's Snapshot is 82.6 MB: 48 MB of ACL Anthology pages ([0012](0012-acl-anthology-venue-editions.md)) stored as the whole HTML page, 16.7 MB of Semantic Scholar pages, 9.5 MB of arXiv records, and under 10 MB for everything else, including the judge verdicts and the PDF hashes.

## Alternatives considered
- **Keep saving stderr by hand:** cheap, but not reproducible, and it depends on someone remembering to do it.
- **A separate `report` command:** one more step to forget, and the report would go stale whenever `collect` or `fetch` changed the manifest without it.
- **Shrinking the ACL pages to the metadata the parser reads:** it would bring the Snapshot under 50 MB, but it changes what a stored response is. The Snapshot would then no longer be the raw response, so [0003](0003-commit-the-snapshot.md) would have to change. It also rewrites 4.8k files. Left for later if the size becomes a problem; every file is far below GitHub's 100 MB per-file limit.
- **Scanning for anything that looks like a key** (long random strings, `key=` in URLs): Semantic Scholar's paging tokens and the hashes in file names look just like keys, so it would raise false alarms on every run.

## Consequences
- The write-up can cite `data/report.md` and a reviewer can regenerate it offline.
- Every `collect` on the committed Snapshot prints the size warning until the Snapshot is shrunk.
- With a key set, `collect` reads the whole Snapshot once more, a few seconds.
- The credential check finds only the keys this code sends. A future source with its own key must add its variable to `API_KEY_ENVS`.
