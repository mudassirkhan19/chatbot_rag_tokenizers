# 0038. Parse only the files of included Editions

- **Date:** 2026-10-18
- **Status:** Accepted. Amends [0031](0031-parse-reads-the-full-text-record.md): `parse` now reads the manifest to choose its files.

## Context
Spec #14 asks to "parse every pinned file of an included Edition". [0031](0031-parse-reads-the-full-text-record.md) has `parse` take every line of the full-text record that has a hash, without reading the manifest. The record keeps files that are no longer part of the corpus:

- the v1 PDFs of the four withdrawn preprints that [0037](0037-withdrawn-preprints-are-excluded.md) excludes;
- the old latest Version of an Edition that a refreshed Snapshot re-pinned ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md));
- in general, the files of any Edition whose Relevance verdict changes after it was fetched.

Parsing them costs GROBID time, puts papers in the parse report that aren't in the corpus, and leaves the indexing stage to remember to drop their Chunks (#30).

## Decision
- **With no `--files`, `parse` parses a recorded file only when an `included` row of the manifest lists it in `pdf_files`.** The manifest is `--manifest`, default `data/manifest.csv`. `pdf_files` lists only the files a row is currently pinned to, so one check skips excluded Editions and files no longer pinned.
- Everything else in 0031 holds: pinned ids and hashes come from the record, a missing or changed local file is listed with a `just fetch` hint, and **`parse` still writes nothing to the manifest**.
- **`--files` is unchanged.** It reads neither the record nor the manifest.

## Alternatives considered
- **Delete the record lines of excluded Editions by hand:** no code change, but every later exclusion or re-pin needs the same cleanup, and a forgotten one is parsed silently.
- **Filter at indexing:** no work now, but GROBID still parses files outside the corpus, the parse report counts them, and nothing tracks that indexing must filter.
- **Have `fetch` prune the record:** the record is also what lets a re-pin find v1 again without a download ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md)), and pruning would lose the hashes of a paper that comes back.

## Consequences
- `parse` depends on a manifest that `collect` or `fetch` wrote from the same Snapshot. Both rewrite it, so it is current after either.
- A paper that is reinstated (a withdrawal replaced by a new Version, a verdict that flips) is parsed again once its row is included, from the record's existing hash.
- The committed parse report is the `--files` run on the Seed PDFs, so it doesn't change.
