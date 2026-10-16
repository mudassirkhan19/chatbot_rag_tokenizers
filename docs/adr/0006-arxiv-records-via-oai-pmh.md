# 0006. arXiv Version history, comments and licence from OAI-PMH

- **Date:** 2026-10-16
- **Status:** Accepted

## Context
Issue #5 asks that every arXiv Edition row, whichever Discovery channel found it, carry its full arXiv record: every Version with its date, the latest Version pinned as the Edition id, the comments field and the licence (`unknown` when there is none). The dedup stage needs the Version history even for Versions it never downloads. The evaluation author needs the comments, because venue information such as "To be published in Findings of EMNLP 2020" often appears only there. Licences must be recorded so the reviewer can see they were respected.

The search API used for keyword queries ([0004](0004-arxiv-keyword-queries.md)) returns one Version per entry and no licence. arXiv's [OAI-PMH interface](https://info.arxiv.org/help/oa/index.html) offers an `arXivRaw` metadata format that lists every Version with its submission time, plus the comments and licence of the current Version.

## Decision
- **One `GetRecord` call per arXiv Edition** at `https://oaipmh.arxiv.org/oai` with `metadataPrefix=arXivRaw` and the unversioned id (`oai:arXiv.org:2004.03720`). Each response is stored in the Snapshot under `responses/arxiv-oai/`, keyed like every other request ([0003](0003-commit-the-snapshot.md)), so replays stay offline and deterministic.
- **Every arXiv Edition row gets its record, rule rejects included.** The spec collects metadata exhaustively. When the rules change later, a row that flips to pass already has its record, and no fetch is needed.
- **The record is the authority.** The Edition is re-pinned to the latest Version the record lists, and the record's comments and licence replace whatever the finding source reported. If a preprint was revised between the search page and the record fetch, the Edition id follows the record. This replaces 0004's rule of pinning to the newest Version seen in search results.
- **Manifest columns:** `versions` holds every Version oldest first as `v1 2020-04-07T21:21:06Z|v2 …` (UTC, from the record's RFC 2822 dates). `licence` is the licence URL as arXiv gives it, or `unknown`. `arxiv_comments` is the record's comments field.
- **Rate limit:** arXiv's [terms of use](https://info.arxiv.org/help/api/tou.html) put OAI-PMH under the same limit as the search API: one request every three seconds over one connection. Both clients share one rate-limited HTTP client so the gap holds across them.
- **Error responses are never stored.** An OAI-PMH `<error>` (such as `idDoesNotExist`) or a record with no Versions stops the run before anything is saved, so a glitch can't become part of the Snapshot. Records already fetched stay saved, so a rerun resumes.

## Alternatives considered
- **Search API with `id_list`:** it gives only the requested or latest Version and no licence. Querying each `vN` separately would need one call per Version and still no licence.
- **OAI-PMH `ListRecords` over a set such as `cs`:** fewer calls per paper, but it harvests hundreds of thousands of records we don't need, makes the Snapshot far too large to commit, and misses Editions outside the set (`hep-th` and others).
- **The `arXiv` OAI format:** it has the licence and comments but only the latest Version, so no history.
- **Scraping the abstract page:** it shows the Version history and licence, but HTML is unstable and arXiv asks machine clients to use the APIs.
- **Fetching records only for rule-passing Editions:** about three times fewer calls (about 1k instead of 3.3k), but rejected rows would lack the fields the issue asks for, and every rule change would trigger fetches.
- **Prior work (research-bot):** it stores ids with their Version suffix and keeps the comments, but records no Version history or licence. We keep the comments too, and take all four fields from one authoritative record.

## Consequences
- The first full run makes one extra request per arXiv Edition. For about 3.3k Editions at three seconds each, that is about 2¾ hours, paid once. Later runs read the Snapshot.
- Each record adds about 1–2 kB compressed to the Snapshot, so about 5 MB for the current corpus.
- arXiv Editions found by later channels (Semantic Scholar, OpenAlex, citation expansion) get the same record as long as they are normalised to `edition_kind = "arxiv-preprint"` with their `arxiv_id`.
- Only the latest Version is pinned here. Choosing which Versions to download (v1 plus latest for a multi-Version preprint) is the Fetcher's job (#10), which reads them from `versions`.
