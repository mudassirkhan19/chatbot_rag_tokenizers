# 0004. arXiv keyword queries: paging, rate limit and query style

- **Date:** 2026-10-16
- **Status:** Accepted. Edition pinning partly superseded by [0006](0006-arxiv-records-via-oai-pmh.md), which pins to the latest Version in the arXiv record.

## Context
arXiv is the first source wired end to end. Its API ([user manual](https://info.arxiv.org/help/api/user-manual.html), [terms of use](https://info.arxiv.org/help/api/tou.html)) returns Atom XML, pages with `start` and `max_results` (at most 2,000 per call and 30,000 per query), and asks clients to make no more than one request every three seconds over a single connection.

## Decision
- **Endpoint:** `https://export.arxiv.org/api/query`, using `search_query` with field prefixes (`ti:`, `abs:`, `cat:`) and boolean operators.
- **Paging:** 500 entries per call, sorted by `submittedDate` **ascending**. New papers then land at the end of the list, so earlier pages stay stable between runs. Paging stops at the reported total, or at 30,000 with a warning to narrow the query.
- **Rate limit:** at least 3 s between requests, one at a time, with exponential backoff (honouring `Retry-After`) on 429, 5xx and connection errors. Requests carry a User-Agent that names the project.
- **Empty pages:** arXiv sometimes returns an empty page, sometimes even reporting zero total matches. An empty page is retried and never stored, so a transient glitch can't become part of the Snapshot. An empty first page is stored only after it has come back empty on every retry, which means the query really matches nothing.
- **Edition ids:** the feed's id includes the Version (`2004.03720v2`). That pinned id is the Edition id, and the unversioned id is kept as `arxiv_id`. Old-style ids (`hep-th/9901001v1`) are handled the same way. If a preprint is revised between two page fetches, it appears under two Versions. It is still one Edition, pinned to the newest Version seen.
- **Kept fields:** title, abstract (used by the rules, not written to the manifest), authors, the v1 submission year, comments, journal reference and DOI.
- **Queries live in `config/scope.toml`**, each tagged with a scope topic.

## Alternatives considered
- **The `arxiv` PyPI package:** convenient, but it hides the request and pages internally, so we couldn't key the Snapshot on the exact request or control what gets stored.
- **OAI-PMH bulk harvest:** right for harvesting a whole category, but we want targeted keyword queries, and the corpus doesn't need every cs.CL paper.
- **Sorting by relevance or by descending date:** each new paper shifts every later page, so a partial refresh would mix old and new orderings.
- **Prior work (research-bot):** it uses the plain-HTTP endpoint, sorts by descending date or relevance, and restricts queries to the last few months. We need the whole history (the spec has no date floor) and stable pages, so we sort ascending and use no date window. Like research-bot, we keep the comments field, since venue information often appears only there.

## Consequences
- The first query takes about 20 s for about 3.3k Candidates.
- arXiv's search stems terms, so `ti:tokenizer` also matches titles that only contain "token" (token-level labelling, token swapping). About two thirds of the first query's Candidates are off-topic for that reason. The rule pre-filter ([0005](0005-rule-pre-filter.md)) rejects them cheaply, and the reason is visible in the manifest.
