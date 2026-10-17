# 0030. Chunks carry their Edition id

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
#14 asks that each Chunk carry its "pinned Edition id and Version". The Chunk shape of [0025](0025-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md) has `pinned_id` (the id pinned to the Version the file holds) and `version`, but not the Edition. For a preprint, `fetch` pins two files to one Edition: v1 and the latest Version ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md)). So the v1 file of Edition `2112.06598v2` gave Chunks citing `2112.06598v1`, with nothing saying they belong to the Edition `2112.06598v2` that the manifest, the relevance verdict and later the dedup stage are keyed by. Recovering it would mean re-deriving `fetch`'s pinning rule downstream.

## Decision
- **`edition_id` is a Chunk field**, beside `pinned_id` and `version`, and a field of the file identity the Chunker takes. Every other field is as in 0025 and [0026](0026-element-rules-and-chunk-kinds.md).
  - v1 of `2112.06598v2`: `edition_id` `2112.06598v2`, `pinned_id` `2112.06598v1`, `version` `v1`.
  - A venue Edition: `edition_id` and `pinned_id` are both the Edition id (`10.5555/lrm.2022.7`), `version` empty.
- **From the full-text record** ([0029](0029-parse-reads-the-full-text-record.md)): `edition_id` is the record line's Edition id, as `fetch` wrote it.
- **From `--files`**, which has no record: the Edition is worked out the way `fetch` pins one. An arXiv Version's Edition is the latest Version of the same arXiv id among the files given; any other file (a venue Edition, or a name with no Version) is its own Edition. For the 34 Seed PDFs, all given together, this gives the manifest's Edition id for each of the 19 Seeds the manifest has (the 20th, FOCUS 2305.14481, isn't in it).
- **The parse report doesn't change.** It names files by pinned id, which is what a reader checks against the PDFs; the Edition is in the Chunks, where retrieval and citation need it.

## Alternatives considered
- **Derive the Edition later from the pinned id.** It would put `fetch`'s rule (v1 plus the latest Version) in a second place, and the latest Version isn't knowable from one file name.
- **For `--files`, each file its own Edition.** Simple and independent of the other arguments, but v1 of every two-Version Seed would cite a non-existent Edition (`1910.13267v1` instead of `1910.13267v2`).
- **For `--files`, look the Edition up in the manifest.** ADR 0029 keeps `parse` off the manifest, and `--files` is the route for files outside the record.
- **For `--files`, leave `edition_id` empty.** Honest, but the Seed Chunks are the ones the first index is built from, and they would lack the field the dedup stage groups by.

## Consequences
- `--files` with only a v1 file names v1 as the Edition, even when a later Version exists upstream. Give the files of a Work together, as the Seed run does, or use the full-text record.
- Changing the Chunk shape changes the Chunks' bytes but not their key: Chunks are rebuilt from the cached TEI on every run ([0028](0028-parse-cache-keys-and-determinism-checks.md)), so the cache needs no clearing.
