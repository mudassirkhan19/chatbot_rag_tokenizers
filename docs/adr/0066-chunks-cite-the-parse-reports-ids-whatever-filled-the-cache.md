# 0066. Chunks cite the parse report's ids, whatever filled the parse cache

- **Date:** 2026-10-20
- **Status:** Accepted

## Context
The parse cache is keyed by file sha256 ([0030](0030-parse-cache-keys-and-determinism-checks.md)), but a Chunk also carries the ids it cites: its Edition id, pinned id and Version ([0032](0032-chunks-carry-their-edition-id.md)). One file pinned under two ids has one set of cached Chunks, stamped by whichever id `parse` chunked last. `load_corpus` took those Chunks as they were.

Issue #76 measured it on the committed corpus (2,689 parsed files, 141,348 Chunks). Three files' Chunks carry another id than the parse report's:
- `2022.nsurl-1.1` and `2301.06736v1` are a venue Edition and a preprint with one file. The report lists both; both rows' Chunks said `2301.06736v1`.
- `2409.17171v1` and `v2` are byte-identical Versions. Both rows' Chunks said `v2`.
- `2607.05691v1`'s Chunks said `arXiv:2607.05691v1`, an alias [0049](0049-normalised-arxiv-ids-and-borrowed-files.md) removed from the manifest. This checkout's cache was filled before then, from another checkout's run. The alias has no Work group, so `bm25+collapsed` showed 27 of 28 questions grouped ([0065](0065-the-embedding-comparison-on-the-raw-ranking.md)), and a chat Citation would show the alias.

So what a Chunk cites depended on the order the cache was filled, not just on the report. No metric moved: a Chunk holds a Passage whichever Edition it comes from ([0041](0041-passage-matcher-eval-check-and-calibration.md)).

Left to decide: does restamping change the corpus fingerprint, and so rebuild all seven indexes (about 3 hours)?

## Decision
**`load_corpus` restamps each report row's Chunks** with that row's pinned id, and with the Edition id and Version `parse` would give it:
- A report parsed from the full-text record takes them from the manifest, as `parse` does: each included Edition's `pdf_files`, read back through `pinned_id_of_file`. So `index`, `evaluate`, `chat`, `chat-eval` and `eval-check` all take `--manifest` (default `data/manifest.csv`).
- A `--files` report takes them from the pinned ids, by the rule `parse --files` uses (`editions_by_name`, shared with `from_paths`). It reads every file the report lists, the failed ones too, since `parse` took the Editions from every file given: a v1 whose v2 failed the quality gate still cites Edition v2.
- A record report whose manifest is missing, or no longer includes an Edition pinned to one of its files, stops the load with a pointer to `just parse` or `--manifest`. Its Chunks can't be stamped as the parse stamped them.

**The fingerprint stays over the Chunks as the cache holds them**, with the formula unchanged. An index holds Chunk ids, headers and text, and no Edition id, so restamping leaves every index as it was. The seven built indexes stay valid, and nothing is rebuilt.

**A file pinned under two ids keeps two copies of its Chunks**, one per report row, as before; each now cites its own row. The copies share Chunk ids. A lookup by Chunk id (the evaluation harness, the chat) keeps the later row's in report order, and that order is the pinned-id order, the same in every checkout.

## Alternatives considered
- **Put the Edition id in the parse report.** The report would then name everything a Chunk cites, with no manifest needed. But the report format changes, every checkout must rerun `parse`, and rewriting the alias file's cached Chunks changes the fingerprint, so all seven indexes are rebuilt. The manifest already says it, and `parse` reads it from there.
- **Fingerprint the restamped Chunks, or leave the ids out of it.** Either one is stable across checkouts. But both change the fingerprint now, and that costs the 3-hour rebuild, though no index changes. With this decision, two caches stamped differently give two fingerprints, so the second checkout rebuilds once: a spare rebuild, never a wrong index.
- **Derive the Edition from the report's pinned ids for record runs too.** This works only while each Edition's latest file is parsed. An Edition pinned to v2 whose v2 file failed the quality gate would be stamped v1.
- **Give each copy its own Chunk ids.** That changes the indexes, and the copies are deduplicated by the collapse anyway ([0057](0057-the-collapse-merges-copies-not-works.md)).

## Consequences
- The eval report rerun shows `2607.05691v1`, not the alias, and `bm25+collapsed` grouped on 28 of 28 questions, as #54's run did. Its crowding counts are over 140 slots again, not 135. 76 Editions in a top 5 have no Work group, down from 77. No other number changed apart from the latencies.
- The README's "two runs give the same report apart from timings" now holds across checkouts too, whatever order their caches were filled in.
- The cached Chunk files still carry the last id `parse` stamped. Read them through `load_corpus`, not straight from the cache.
- `indexed.mark`'s "there is no manifest" branch can't be reached from `index` any more: a record corpus without a manifest stops the load first, and a `--files` corpus marks nothing.
