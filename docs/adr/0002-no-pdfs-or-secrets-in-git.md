# 0002. Keep PDFs, downloaded data and secrets out of git

- **Date:** 2026-10-15
- **Status:** Accepted; the part about downloaded data is superseded by [0003](0003-commit-the-snapshot.md); text from CC BY papers in test fixtures is allowed by [0033](0033-cc-by-tei-fixtures-may-be-committed.md); short quotes in the Evaluation set are allowed by [0045](0045-evaluation-set-quotes-checked-by-and-absence-evidence.md)

## Context
The brief asks us not to commit the paper PDFs, but to commit the script that downloads them, and to keep API keys out of the repository. Papers also carry their own licences, so redistributing them is not ours to decide.

## Decision
- `.gitignore` excludes `*.pdf`, `data/raw/`, `data/pdfs/` and `.env`.
- The corpus is reproduced by running the collection pipeline. The **manifest** (paper metadata and inclusion status) is committed, so it is clear what was collected without shipping the files.
- API keys (if any) are read from environment variables or a local `.env`, never hard-coded.

## Consequences
- A fresh clone needs a download step before indexing; the README must document it.
- Reproducibility depends on upstream sources staying available. The manifest records source links and versions so the corpus can be rebuilt or audited.
