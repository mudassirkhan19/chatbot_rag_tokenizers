# 0017. ACL volume IDs count as no paper

- **Date:** 2026-10-17
- **Status:** Accepted. Narrows the "not the paper page stops the run" rule of [0012](0012-acl-anthology-venue-editions.md). Amended by [0040](0040-the-corpus-keeps-only-papers.md): proceedings front matter is excluded at the `not a paper` stage.

## Context
[0012](0012-acl-anthology-venue-editions.md) stores a 404 from the Anthology as an empty body, because it is a permanent answer about the ID. Any other page that isn't the paper page for the ID stops the run. On the first full run, which reported 4,784 ACL IDs, the run stopped after about 2,200 pages on `2021.autosimtrans-1`. Semantic Scholar has records for whole proceedings volumes and gives them the volume's ACL ID. The Anthology answers `https://aclanthology.org/2021.autosimtrans-1/` with a redirect to `/volumes/2021.autosimtrans-1/`, a volume page with no `citation_title`.

## Decision
- **An ACL ID that the Anthology redirects to a `/volumes/` page is treated like a 404.** The empty body is stored in the Snapshot, the stderr line says "is a volume, not a paper", and the row stays as its source reported it.
- Any other page that isn't the paper page for the ID still stops the run.

## Alternatives considered
- **Recognise volume IDs from their shape** (a new-style ID with no paper number, such as `2021.autosimtrans-1`) and never fetch them: saves one request per volume, but rests on ID conventions we would have to get right for every era of the Anthology. The redirect is the Anthology's own answer.
- **Skip every page that isn't a paper page:** never stops, but hides real failures such as a changed page layout, which would quietly drop every ACL Edition.

## Consequences
- A volume ID costs one request on the first run and none on replays.
- Volume records stay in the manifest as Semantic Scholar reported them, without an ACL venue row. They are proceedings front matter, so the rules or the judge will usually reject them.
