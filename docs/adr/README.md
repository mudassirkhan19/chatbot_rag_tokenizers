# Decision log

Short records of design decisions and the reasoning behind them, so choices can be revisited with context.
One file per decision, numbered in the order they were made. If a decision is reversed, add a new record that supersedes the old one rather than editing history.

| # | Decision | Status |
|---|---|---|
| [0001](0001-python-3.12-with-uv.md) | Python 3.12, managed with uv | Accepted, setup superseded by 0022 |
| [0002](0002-no-pdfs-or-secrets-in-git.md) | Keep PDFs, downloaded data and secrets out of git | Partly superseded by 0003 |
| [0003](0003-commit-the-snapshot.md) | Commit the Snapshot of raw source responses | Accepted |
| [0004](0004-arxiv-keyword-queries.md) | arXiv keyword queries: paging, rate limit and query style | Partly superseded by 0006 |
| [0005](0005-rule-pre-filter.md) | Stage-1 rule pre-filter for the Relevance verdict | Accepted |
| [0006](0006-arxiv-records-via-oai-pmh.md) | arXiv Version history, comments and licence from OAI-PMH | Partly superseded by 0010 |
| [0007](0007-local-llm-judge.md) | Stage-2 local LLM judge and verdict cache | Accepted, amended by 0018 and 0021 |
| [0008](0008-semantic-scholar-keyword-discovery.md) | Semantic Scholar keyword discovery and combining Editions across sources | Retry limits superseded by 0016 |
| [0009](0009-seeds-and-citation-expansion.md) | Scope boundary, keyword query set, Seeds and citation expansion | Accepted |
| [0010](0010-arxiv-records-for-rule-passes-only.md) | Fetch arXiv records only for Editions that pass the rules | Accepted |
| [0011](0011-audit-set-and-relevance-metrics.md) | Audit set sampling and relevance metrics | Accepted, labelling amended by 0020 |
| [0012](0012-acl-anthology-venue-editions.md) | ACL Anthology venue Editions from per-paper pages | Accepted, narrowed by 0017 |
| [0013](0013-working-worktrees.md) | Fully working worktrees for parallel work | Accepted |
| [0014](0014-openalex-discovery-channel.md) | OpenAlex as a separate, switchable Discovery channel | Accepted, verdict in 0019 |
| [0015](0015-pdf-fetcher-pinned-files-and-hashes.md) | PDF Fetcher: pinned files, hashes in the Snapshot, open-access fallback | Accepted |
| [0016](0016-semantic-scholar-waits-out-long-throttles.md) | Semantic Scholar waits out long throttles | Accepted |
| [0017](0017-acl-volume-ids-count-as-no-paper.md) | ACL volume IDs count as no paper | Accepted |
| [0018](0018-judge-releases-mps-cache.md) | The judge releases the MPS allocator cache after every batch | Accepted |
| [0019](0019-openalex-stays-on.md) | OpenAlex stays on | Accepted |
| [0020](0020-blind-agent-labels-checked-by-the-developer.md) | Audit set labels from blind agents, checked by the developer | Accepted |
| [0021](0021-tev1-decision-model-judge.md) | Tev1 4B as the judge, served by Ollama and pinned with its runtime | Accepted |
| [0022](0022-uv-and-just-from-homebrew-docker-left-to-the-user.md) | uv and just from Homebrew, Docker left to the user | Accepted |
| [0023](0023-grobid-crf-image-pinned-by-digest.md) | GROBID's CRF image, pinned by digest in config/parse.toml | Accepted |

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
