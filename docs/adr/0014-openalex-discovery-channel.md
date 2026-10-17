# 0014. OpenAlex as a separate, switchable Discovery channel

- **Date:** 2026-10-16
- **Status:** Accepted. The first live run kept OpenAlex on ([0019](0019-openalex-stays-on.md)).

## Context
#7 adds OpenAlex as a third keyword source. It indexes venues that arXiv and Semantic Scholar cover poorly, and it lists, for each work, where open-access copies are hosted. That matters for venue Editions not on arXiv or the ACL Anthology, which otherwise have no PDF source. OpenAlex also costs something: another source to page through, more Snapshot bytes, and Candidates that may be off topic. So it stays a separate channel that can be switched off, and the report shows what it adds on its own.

API facts, from the [OpenAlex docs](https://help.openalex.org/how-to-use-the-api) (checked 2026-10-16) and live calls:
- `GET /works` with `search.title_and_abstract=` does a stemmed search of title and abstract. It supports quoted phrases and uppercase `AND`/`OR`/`NOT`; a minus sign doesn't exclude.
- Cursor paging: start with `cursor=*`, then pass `meta.next_cursor`. Without a key, the first page works, but following `next_cursor` returns 401. `per_page` is at most 100.
- A key is free. It goes in an `api_key` query parameter or in `Authorization: Bearer`, and the docs say both work the same way. Limits are 30 requests per second with a key, but only 5 for searches with more than five boolean operators. Each list call costs $0.001 of a $1/day free budget.
- A work merges a Work's Editions, as a Semantic Scholar record does. SentencePiece is one work: its primary location is the EMNLP DOI, and it also lists `pmh:oai:arXiv.org:1808.06226`, `http://arxiv.org/abs/1808.06226` and `10.48550/arxiv.1808.06226`. DOIs come as lower-case `https://doi.org/…` URLs. Abstracts come as an inverted index (word → positions).

## Decision
- **Its own channel:** queries with `source = "openalex"` run as `openalex:<query id>`. `enabled = false` under `[sources.openalex]` skips them. `enabled` is read for every source, so arXiv or Semantic Scholar can be switched off the same way. The first query is the Semantic Scholar phrases rewritten in OpenAlex's syntax (about 1,540 works, so 16 pages).
- **Requests:** `search.title_and_abstract`, `select` limited to the fields we read, `sort=publication_date:asc`, `per_page=100`. Each page is stored under its request description, and the next page's description includes the cursor read from the stored page, so a replay follows the same chain of pages offline ([0008](0008-semantic-scholar-keyword-discovery.md) does the same with Semantic Scholar's token). The fixed sort makes a fresh fetch page in a repeatable order; relevance order can change between index updates. Requests are spaced 0.2 s apart, to stay under the 5-per-second limit for queries with many boolean operators.
- **Key:** `OPENALEX_API_KEY`, sent only as `Authorization: Bearer`, never in the query string that the request description and Snapshot record ([0003](0003-commit-the-snapshot.md)). Without a key, a run whose Snapshot already has the pages works offline. A run that needs to fetch stops before any request and says how to get a key or switch OpenAlex off. A keyless fetch could only ever get the first page, which would leave a Snapshot that looks complete but isn't.
- **Which Edition a work stands for:** the rule from [0008](0008-semantic-scholar-keyword-discovery.md).
  - A work with an arXiv location (OAI-PMH id, abs URL or arXiv DOI) is the **arXiv preprint** Edition, with its Version stripped. Venue and PDFs are left empty, because they belong to the merged venue Edition.
  - Any other work is a **venue** Edition, named by its DOI, otherwise by its OpenAlex id (`W…`), and linked to doi.org or openalex.org.
  - `openalex_id` is recorded on every row and is also a match key. DOIs already match case-insensitively, so OpenAlex's lower-case DOIs combine with Semantic Scholar's upper-case ones. OpenAlex reports no ACL ID. A venue row whose DOI is an ACL DOI (`10.18653/v1/…`) becomes the ACL Edition when the Anthology stage runs ([0012](0012-acl-anthology-venue-editions.md)), as it does for Semantic Scholar's.
- **Venue and open-access PDFs** (venue Editions only): `venue` is the primary location's source name. `oa_pdf_urls` lists every open-access location's `pdf_url`, OpenAlex's `best_oa_location` first and paywalled copies left out, joined with `|` in the manifest. When an OpenAlex Candidate combines with an existing venue Edition, it fills in `venue` and `oa_pdf_urls` only if they are empty, as with identifiers. Its other fields never displace the first Candidate's.
- **Report:** per Discovery channel and per source, `collect` prints how many Editions it found, how many no other channel or source found, and how many of those pass the rules and are included by the judge. The per-source line is what measures OpenAlex as a whole once it has more than one query. A Seed's own record and its citation hops count as one source, `seeds`, so an Edition counts as OpenAlex-only only if no Seed reached it either. Pending verdicts are counted separately, so a run without the judge doesn't make OpenAlex look worse than it is.
- **Whether OpenAlex earned its place** is decided on its first live run, with the judge, from the `openalex` source line. It stays on if at least 20 of its OpenAlex-only Editions are included, or if `oa_pdf_urls` gives at least 20 included venue Editions their only PDF source. Otherwise it is switched off. **Not yet measured:** the first live run needs the judge to have scored the corpus. The numbers and the verdict go in a new ADR.

## Alternatives considered
- **`api_key` as a query parameter:** documented as equivalent, but it would put the key in the request description, and so in every Snapshot key and stored record.
- **Plain `search=`:** it also searches full text and keywords, so it matches papers that only mention a tokenizer in passing. `search.title_and_abstract` matches what the Semantic Scholar channel searches.
- **One row per OpenAlex location (preprint and venue):** OpenAlex's locations do separate the Editions more clearly than a Semantic Scholar record. But that would get ahead of the dedup stage, for the same reasons given in 0008, and would bypass the ACL Anthology as the authority for ACL Editions ([0012](0012-acl-anthology-venue-editions.md)).
- **Look up every venue Edition by DOI to fill in venue and PDFs**, not just the ones OpenAlex's search found (a `doi:a|b|…` filter takes 100 DOIs per call): this would enrich far more rows, but it mixes a lookup stage into a discovery channel that is meant to be measured on its own. Left for later, once this channel's verdict is in.
- **Prior work (research-bot):** arXiv only; no OpenAlex client.

## Consequences
- The manifest gains `oa_pdf_urls` and `openalex_id`. Rows found by other channels are unchanged except where an OpenAlex Candidate combines with them.
- A first run with OpenAlex fetches 16 pages, about $0.016 of the free daily budget. Every author's institutions are stored in each record (`select` can't trim nested fields), so OpenAlex pages are larger per work than Semantic Scholar's.
- Works with neither a DOI nor an arXiv location are named by their OpenAlex id, as Semantic Scholar-only venue Editions are named by their paperId.
- Candidates include things that aren't papers at all, such as software packages registered with DOIs. The rule pre-filter and judge treat them like any other Candidate. No `type` filter is applied, so the report can show how much noise OpenAlex brings.
