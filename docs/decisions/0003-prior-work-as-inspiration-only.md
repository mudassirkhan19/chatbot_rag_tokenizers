# 0003. Treat earlier internal work as inspiration only

- **Date:** 2026-10-15
- **Status:** Accepted

## Context
An earlier internal project ("research-bot") already covers part of this problem space: it crawls arXiv, converts PDFs to Markdown with Marker, extracts structured metadata with an LLM, and answers questions over a ChromaDB index with citations.

It does not do several things this assignment is graded on:
- full-text, section-aware chunking (it embeds one LLM summary per paper)
- merging of arXiv versions or conference versions
- Semantic Scholar, ACL Anthology or OpenReview sources
- comparing embedding models, or retrieval evaluation (Recall@k, MRR)

It also depends on paid APIs (OpenRouter LLMs, Mistral OCR), while the brief expects free tiers or open models on CPU. And the brief requires that we can explain and change every line of this codebase.

## Decision
- Keep a read-only copy of that project under `tmp/research-bot/` (gitignored) for reference while we work. Its git history, databases, PDFs and `.env` files are excluded from the copy.
- Do **not** import or copy its code into this repository.
- For each component, do our own research first, then compare our approach against what research-bot did before settling on a design. Record the comparison in the decision record for that component.

## Ideas worth evaluating against our own research
- arXiv Atom API crawling with pagination, rate limiting and incremental updates.
- Marker for converting PDFs to Markdown with headings and separate table output, as a basis for section-aware chunking.
- Stripping arXiv version suffixes, and normalising and fuzzy-matching titles, as a starting point for detecting versions and duplicates.
- LLM-based relevance scoring for deciding which papers belong in the corpus.

## Consequences
- More code to write ourselves, but every component is designed for this assignment's grading criteria and is fully explainable.
- The `tmp/` folder is local only; a fresh clone won't have it, and nothing in this repo depends on it.
