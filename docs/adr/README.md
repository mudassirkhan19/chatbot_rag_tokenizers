# Decision log

Short records of design decisions and the reasoning behind them, so choices can be revisited with context.
One file per decision, numbered in the order they were made. If a decision is reversed, add a new record that supersedes the old one rather than editing history.

| # | Decision | Status |
|---|---|---|
| [0001](0001-python-3.12-with-uv.md) | Python 3.12, managed with uv | Accepted, setup superseded by 0022 |
| [0002](0002-no-pdfs-or-secrets-in-git.md) | Keep PDFs, downloaded data and secrets out of git | Partly superseded by 0003; amended by 0033 and 0046 |
| [0003](0003-commit-the-snapshot.md) | Commit the Snapshot of raw source responses | Accepted, size and credential checks in 0026 |
| [0004](0004-arxiv-keyword-queries.md) | arXiv keyword queries: paging, rate limit and query style | Partly superseded by 0006 |
| [0005](0005-rule-pre-filter.md) | Stage-1 rule pre-filter for the Relevance verdict | Accepted, amended by 0037, 0040 and 0049 |
| [0006](0006-arxiv-records-via-oai-pmh.md) | arXiv Version history, comments and licence from OAI-PMH | Partly superseded by 0010 |
| [0007](0007-local-llm-judge.md) | Stage-2 local LLM judge and verdict cache | Accepted, amended by 0018, 0021 and 0042; a stage after it in 0049 |
| [0008](0008-semantic-scholar-keyword-discovery.md) | Semantic Scholar keyword discovery and combining Editions across sources | Retry limits superseded by 0016; arXiv ids normalised by 0049 |
| [0009](0009-seeds-and-citation-expansion.md) | Scope boundary, keyword query set, Seeds and citation expansion | Accepted |
| [0010](0010-arxiv-records-for-rule-passes-only.md) | Fetch arXiv records only for Editions that pass the rules | Accepted |
| [0011](0011-audit-set-and-relevance-metrics.md) | Audit set sampling and relevance metrics | Accepted, labelling amended by 0020 |
| [0012](0012-acl-anthology-venue-editions.md) | ACL Anthology venue Editions from per-paper pages | Accepted, narrowed by 0017 |
| [0013](0013-working-worktrees.md) | Fully working worktrees for parallel work | Accepted, amended by 0042 |
| [0014](0014-openalex-discovery-channel.md) | OpenAlex as a separate, switchable Discovery channel | Accepted, verdict in 0019 |
| [0015](0015-pdf-fetcher-pinned-files-and-hashes.md) | PDF Fetcher: pinned files, hashes in the Snapshot, open-access fallback | Accepted, amended by 0037 |
| [0016](0016-semantic-scholar-waits-out-long-throttles.md) | Semantic Scholar waits out long throttles | Accepted |
| [0017](0017-acl-volume-ids-count-as-no-paper.md) | ACL volume IDs count as no paper | Accepted, amended by 0040 |
| [0018](0018-judge-releases-mps-cache.md) | The judge releases the MPS allocator cache after every batch | Accepted |
| [0019](0019-openalex-stays-on.md) | OpenAlex stays on | Accepted |
| [0020](0020-blind-agent-labels-checked-by-the-developer.md) | Audit set labels from blind agents, checked by the developer | Accepted |
| [0021](0021-tev1-decision-model-judge.md) | Tev1 4B as the judge, served by Ollama and pinned with its runtime | Accepted, amended by 0025 and 0054 |
| [0022](0022-uv-and-just-from-homebrew-docker-left-to-the-user.md) | uv and just from Homebrew, Docker and Ollama left to the user | Accepted |
| [0023](0023-grobid-crf-image-pinned-by-digest.md) | GROBID's CRF image, pinned by digest in config/parse.toml | Accepted |
| [0024](0024-grobid-stays-the-parser-after-the-docling-spike.md) | GROBID stays the parser after the spike against Docling | Accepted |
| [0025](0025-judge-cuts-only-refused-inputs.md) | The decision judge cuts an abstract only when the model refuses it | Accepted |
| [0026](0026-funnel-report-and-snapshot-checks.md) | The funnel report is written from the manifest, and collect checks the Snapshot | Accepted, amended by 0045 |
| [0027](0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md) | Parse tracer: paragraph packing, a pinned tokenizer, the parse cache and the report | Accepted, amended by 0045 |
| [0028](0028-element-rules-and-chunk-kinds.md) | Element rules: tables, captions, references, appendices and the Chunk kinds | Accepted, amended by 0043 |
| [0029](0029-parse-quality-gate-and-per-file-errors.md) | Parse quality gate, permanent failures and per-file errors | Accepted, amended by 0036 |
| [0030](0030-parse-cache-keys-and-determinism-checks.md) | Parse cache keys and determinism checks | Accepted |
| [0031](0031-parse-reads-the-full-text-record.md) | Parse reads the full-text record: pinned ids from the record, local problems outside the report | Accepted, amended by 0038 |
| [0032](0032-chunks-carry-their-edition-id.md) | Chunks carry their Edition id | Accepted |
| [0033](0033-cc-by-tei-fixtures-may-be-committed.md) | CC BY TEI fixtures may be committed; the parse cache may not | Accepted, Evaluation set quotes in 0046 |
| [0034](0034-parse-files-stops-on-a-path-that-is-not-a-file.md) | `parse --files` stops on a path that isn't a file | Accepted |
| [0035](0035-missed-table-cells-stay-in-text-chunks.md) | The cells of a missed table stay in text Chunks and are counted | Accepted |
| [0036](0036-a-dropped-grobid-connection-stops-the-run.md) | A reset or dropped GROBID connection stops the run, like a refused one | Accepted |
| [0037](0037-withdrawn-preprints-are-excluded.md) | Withdrawn arXiv preprints are excluded from the corpus | Accepted |
| [0038](0038-parse-only-the-files-of-included-editions.md) | Parse only the files of included Editions | Accepted |
| [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md) | Retrieval tracer: BM25, the index cache and the evaluate harness | Accepted, Passage matching and the loader's shape checks superseded by 0041; amended by 0043, 0053, 0058, 0061 and 0067 |
| [0040](0040-the-corpus-keeps-only-papers.md) | The corpus keeps only papers | Accepted |
| [0041](0041-passage-matcher-eval-check-and-calibration.md) | The Passage matcher, eval-check and the v1/vN calibration | Accepted, amended by 0051 |
| [0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md) | Dense baseline: bge-small behind the embedder boundary, on MPS by default | Accepted, amended by 0050 |
| [0043](0043-recover-numbered-headings-grobid-left-in-paragraphs.md) | Recover numbered headings GROBID left in paragraphs | Accepted |
| [0044](0044-duplicate-rate-restatement-and-numeric-share-in-evaluate.md) | Duplicate rate, Survey restatement and the numeric-Chunk share in evaluate | Accepted, Work groups filled by 0047; amended by 0053 |
| [0045](0045-index-marks-editions-indexed-from-a-committed-record.md) | `index` marks Editions indexed, from a record committed in the Snapshot | Accepted |
| [0046](0046-evaluation-set-quotes-checked-by-and-absence-evidence.md) | The Evaluation set: short quotes committed, a check per question, and absence evidence | Accepted |
| [0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md) | Hand-checked Work groups are the ground truth for the duplicate rate | Accepted, a blind agent check added by 0063 |
| [0048](0048-hand-curated-domain-model-page.md) | A hand-curated domain model page, refreshed by the issue that changes a number | Accepted |
| [0049](0049-normalised-arxiv-ids-and-borrowed-files.md) | Normalised arXiv ids, and Editions that hold another Edition's file | Accepted |
| [0050](0050-named-dense-tables-and-a-configurable-embedder.md) | Named dense tables and a configurable embedder; `dense` becomes `dense.bge-small` | Accepted, amended by 0052 |
| [0051](0051-work-grouping-in-collect.md) | Work grouping in `collect`: work_id, Canonical Edition, Survey flag and Suspected pairs | Accepted, title comparison amended by 0063 |
| [0052](0052-bge-base-and-openscholar-pinned-and-verified.md) | bge-base and OpenScholar_Retriever pinned, and checked by the opt-in model test | Accepted |
| [0053](0053-collapsed-ranking-and-collapsed-twins.md) | The Collapsed ranking: one Chunk per Work, scored as a `+collapsed` twin of every retriever | Accepted, the Chunk a Work shows superseded by 0055, one Chunk per Work by 0057 |
| [0054](0054-pinned-local-answer-model-and-the-chat-page.md) | The pinned local answer model, the shared Ollama module and the chat page | Accepted, amended by 0056, 0064 and 0069 |
| [0055](0055-a-work-shows-its-best-ranked-section.md) | A collapsed Work shows its best-ranked Chunk's Section; the Canonical Edition only picks the copy | Superseded by 0057 |
| [0056](0056-follow-ups-the-conversation-and-the-rewrite.md) | Follow-ups: the Conversation and the Rewrite | Accepted, amended by 0067; the transcript in 0068 |
| [0057](0057-the-collapse-merges-copies-not-works.md) | The collapse merges copies of a passage across a Work's files, not whole Works | Accepted |
| [0058](0058-bm25-dense-hybrids-by-reciprocal-rank-fusion.md) | BM25 + dense hybrids by reciprocal rank fusion, stored as a record that points to their members | Accepted |
| [0059](0059-abstention-by-instruction-and-the-chat-report.md) | Abstention by instruction, and the chat report that measures it | Accepted, reproducibility amended by 0062, the Abstention rule by 0064 |
| [0060](0060-the-grouping-rule-scored-against-the-work-groups.md) | The grouping rule scored against the Work groups, pair by pair | Accepted |
| [0061](0061-the-comparison-paired-bootstrap-against-a-baseline.md) | The Comparison: wins, ties, losses and paired bootstrap intervals against a baseline, and the Cost table | Accepted |
| [0062](0062-re-scoring-run-to-run-variation-and-wilson-intervals.md) | Re-scoring from the answers, run-to-run variation, and Wilson intervals on the chat report's rates | Accepted |
| [0063](0063-versions-and-near-duplicates-measured-before-and-after.md) | Versions and near-duplicates, measured before and after | Accepted |
| [0064](0064-a-decline-in-the-models-own-words-is-an-abstention.md) | A decline in the model's own words is an Abstention | Accepted |
| [0065](0065-the-embedding-comparison-on-the-raw-ranking.md) | The embedding comparison, raw and collapsed: bge-small stays | Accepted |
| [0066](0066-chunks-cite-the-parse-reports-ids-whatever-filled-the-cache.md) | Chunks cite the parse report's ids, whatever filled the parse cache | Accepted |
| [0067](0067-the-rewriter-row-of-evaluate.md) | The rewriter row of `evaluate`: the chatbot's Rewrite of each stored follow-up, skipped without the model | Accepted |
| [0068](0068-the-transcript-saved-from-the-chat-page.md) | The transcript, saved from the chat page under docs/reports from the page's own Turn records | Accepted, its Transcript replaced by 0070's |
| [0069](0069-citations-name-the-merged-editions-after-the-collapse.md) | Citations name the merged Editions and mark Surveys after the collapse | Accepted |
| [0070](0070-the-chatbot-retrieves-collapsed-and-the-final-chat-numbers.md) | The chatbot retrieves with bge-small's `+collapsed` twin, and the final chat numbers | Accepted |

## Template

```markdown
# NNNN. Title

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by NNNN

## Context
What problem or constraint forced a choice.

## Decision
What we chose.

## Alternatives considered
What else we looked at and why we didn't pick it.

## Consequences
What this makes easier or harder.
```
