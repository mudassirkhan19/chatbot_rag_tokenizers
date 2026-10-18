# 0031. Parse reads the full-text record: pinned ids from the record, local problems outside the report

- **Date:** 2026-10-18
- **Status:** Accepted. Amended by [0038](0038-parse-only-the-files-of-included-editions.md): only the files of included Editions are parsed.

## Context
Issue #22 makes `parse` with no `--files` parse exactly the files whose hashes the Snapshot's full-text record holds ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md)). The record keeps, per file, the Edition id, the file name and the sha256, plus lines for Editions with no open PDF. File names are pinned ids with unsafe characters replaced (`hep-th_9901001v1.pdf`, `10.5555_lrm.2022.7.pdf`), so a file name can't always be turned back into the id a Chunk must cite. A file in `data/pdfs/` may also be missing or differ from the record, for example after a partial fetch or a hand edit.

## Decision
- **Inputs:** with no `--files`, `parse` reads `<snapshot>/fulltext/pdfs.jsonl` (`--snapshot`, default `data/snapshot`) and the PDFs directory (`--pdfs`, default `data/pdfs`), and takes every line that has a hash, in the record's order (the pipeline sorts them again by pinned id). Lines recorded as having no open PDF are skipped. `--files` stays as the route for the Seed PDFs ([0027](0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md)).
- **Pinned ids from the record.** When the Edition id is an arXiv id pinned to a Version (new-style `2112.06598v2` or old-style `hep-th/9901001v2`), the file is one of its Versions: the pinned id is the arXiv id plus the Version that follows the arXiv id's file name in the file name (`hep-th_9901001v1.pdf` → `hep-th/9901001v1`, Version `v1`). Otherwise the file is the venue Edition itself: the pinned id is the Edition id (`10.5555/lrm.2022.7`) and the Version is empty.
- **The bytes must match the record.** Each file's sha256 is computed on the spot. A recorded file missing locally, or whose hash differs from the record, is not parsed. Every such file is listed together at the end, with the recorded hash, a hint to run `just fetch` (which re-downloads and checks against the record), and a non-zero exit. The other files are parsed as usual.
- **These problems stay out of the parse report.** They describe the local PDFs directory, not the corpus, so a reviewer's committed report doesn't change because one machine has an incomplete download.
- **The manifest is untouched.** `parse` doesn't read or write it.
- **`just parse`** forwards its arguments to the CLI, like `just collect` and `just fetch`.

## Alternatives considered
- **Pinned ids from file names, as for `--files`.** Wrong for old-style arXiv ids and DOIs, whose `/` the file name replaces, and it would ignore the record the parse is meant to follow.
- **Re-downloading a missing or changed file from `parse`.** That is `fetch`'s job, with its rate limits and drift checks; `parse` stays offline apart from GROBID.
- **Reading the manifest's `pdf_files` instead of the record.** The manifest holds only files the current Snapshot pins and is derived from the record anyway; the record is the source of the hashes.
- **A report line for each missing file.** It would make the committed report depend on the machine.

## Consequences
- An old latest Version that a refreshed Snapshot no longer pins stays in the record, so it is still parsed. Its Chunks cite their own pinned id, so nothing is mixed up.
- A mismatched file needs `just fetch`, which reports upstream drift if the source changed too.
