# 0045. `index` marks Editions indexed, from a record committed in the Snapshot

- **Date:** 2026-10-19
- **Status:** Accepted

## Context
Spec #2 (user story 15) promises a funnel count of **indexed** Editions, and the manifest's `funnel_status` names the stage: discovered → relevant → full text (or `no_fulltext`) → indexed. Nothing set `indexed` until now. Issue #46 asks `index` to set it on every included Edition whose pinned files are all in the built index, and asks the funnel report to count them.

Three things were left to decide:
- **Where the state lives.** `collect` rebuilds the manifest from the Snapshot, and the README promises that `just collect` leaves `data/manifest.csv` byte-identical. A status written only into the manifest would be reset by the next `collect`. The index cache is gitignored, so `collect` can't read it on a fresh clone.
- **Editions whose files fail the parse quality gate**, such as `2508.13058v1`: they have no Chunks, so they can't be indexed. The report should show the gap rather than leave it unexplained.
- **An Edition with several pinned files, some of which fail.**

## Decision
**`index` writes an index record into the Snapshot** at `data/snapshot/index/files.jsonl`.
- It holds one JSON line per file of the corpus it indexed, `{"pinned_id", "sha256"}`, sorted.
- The files are those the parse report lists as parsed, which is the corpus `index` builds over ([0039](0039-retrieval-tracer-bm25-index-and-evaluate.md)).
- Two pinned ids can hold the same bytes. The parse cache keeps one set of Chunks for both, so the record is taken from the parse report rather than from the Chunks, and lists both.
- Each `index` run replaces the record with its corpus. This also happens when the indexes were already up to date.

**`index` then marks the manifest and rewrites the funnel report** (`--snapshot`, `--manifest`, `--funnel-report`, defaulting to `data/snapshot`, `data/manifest.csv` and `data/report.md`).
- **A Seed `--files` run marks nothing.** Its corpus isn't the manifest's, and marking from it would send nearly every indexed Edition back to `full text`. So the parse report now records its input on an `- Input:` line: the full-text record, or the files given with `--files`. `index` marks only a corpus parsed from the full-text record. Otherwise it says why it marked nothing and leaves the record, the manifest and the funnel report alone. A parse report written before this line existed counts as a `--files` run until `parse` runs again.
- Without a manifest at that path, `index` also says so and marks nothing.

**`collect` and `fetch` apply the record** after the full-text record, the way they apply the full-text record ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md)). So rebuilding from the Snapshot keeps the mark, and `just collect` stays byte-identical.

**The rule is strict.** An included row at `full text` becomes `indexed` when the sha256 of every file in its `pdf_files` is in the record. One file that failed the gate keeps the whole Edition at `full text`.
- Matching is by sha256, the same identity the parse cache uses.
- A row marked `indexed` before goes back to `full text` once its files are no longer all in the record.
- No other row is touched, so an excluded Edition is never `indexed`.

**The funnel report** keeps *With full text* as the count of Editions with every pinned file fetched, indexed or not.
- It adds two rows, *Indexed* and *With full text, not indexed*.
- It adds a section listing the Editions with full text that aren't indexed. For each one, either a file failed the parse quality gate, so the parse report names it, or `index` hasn't run since the Edition was fetched.

## Alternatives considered
- **Compute "indexed" only in the funnel report**, from the parse report and the index, and never store it. That leaves `funnel_status` without its last stage, which the spec names and #46's first criterion asks for. It also makes the report depend on the gitignored index cache.
- **Have `collect` read the parse report.** That would mark files as indexed when they were parsed but not yet indexed. The parse report also belongs to the parsing stage, not the Snapshot that `collect` rebuilds from.
- **"Any pinned file indexed" counts the Edition.** Then a preprint whose latest Version failed to parse would count as indexed on its v1 alone. The strict rule keeps the count honest about what the index holds.

## Consequences
- On the full corpus, 2,067 of the 2,068 included Editions with full text are indexed. The one that isn't is `2508.13058v1`, whose only file fails the quality gate ([0029](0029-parse-quality-gate-and-per-file-errors.md)).
- The record is 2,690 lines, about 280 kB, in the committed Snapshot.
- A `parse` that changes which files pass the gate marks nothing until `index` runs again. Until then the report shows the old count, the same way it shows full text only once `fetch` has run.
- An `index` run with `--retriever` builds fewer retrievers but records the same corpus. "Indexed" means in the corpus `index` last built over, not in every retriever.
