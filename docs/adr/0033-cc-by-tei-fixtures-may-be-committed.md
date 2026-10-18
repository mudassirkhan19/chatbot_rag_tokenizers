# 0033. CC BY TEI fixtures may be committed; the parse cache may not

- **Date:** 2026-10-18
- **Status:** Accepted; short quotes in the Evaluation set are covered by [0045](0045-evaluation-set-quotes-checked-by-and-absence-evidence.md), not by this rule

## Context
[0002](0002-no-pdfs-or-secrets-in-git.md) keeps PDFs and downloaded data out of git because each paper carries its own licence, so redistributing it isn't ours to decide. [0027](0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md) keeps the parse cache local for the same reason: its TEI and Chunks are text derived from the papers. Yet the offline `parse` tests answer with five committed TEI fixtures in `tests/fixtures/tei/`, which hold real paper text: WECHSEL v2 whole, three files trimmed or rearranged from it or from Sennrich et al. v5. #14 asks for CC BY fixtures with the licence checked in the manifest. Until now the licence was named only in test docstrings and one file's comment, with no attribution of the authors and no check.

## Decision
- **A fixture holding paper text may be committed when the Version it comes from is under CC BY 4.0, as the manifest's `licence` column records it** (the arXiv record's licence for the Edition's current Version, [0006](0006-arxiv-records-via-oai-pmh.md), or the ACL Anthology's, [0012](0012-acl-anthology-venue-editions.md); either spelling of the CC BY 4.0 URL counts). CC BY 4.0 lets anyone share and adapt the work, commercially or not, given attribution, a link to the licence, and a note of any changes. Nothing else the corpus holds is shared this way: share-alike, non-commercial and unknown licences are not used for fixtures, and arXiv's default non-exclusive licence grants nothing to third parties.
- **Both fixture papers qualify.** `data/manifest.csv` records `http://creativecommons.org/licenses/by/4.0/` for `2112.06598v2` (WECHSEL, Minixhofer, Paischer and Rekabsaz) and `1508.07909v5` (Sennrich, Haddow and Birch).
- **Attribution lives beside the files**: `tests/fixtures/tei/README.md` gives each fixture's paper title, authors, arXiv pinned id, licence with its link, and the changes made (request time fixed, Sections trimmed, parts rearranged or made up).
- **A test keeps it true.** `tests/test_parse_fixtures.py` fails when a `*.tei.xml` fixture has no row in that README, or when its licence is not CC BY 4.0 or not the licence the manifest records for its pinned id.
- **The parse cache stays uncommitted.** It holds the whole corpus, under whatever licence each paper has: of the 3,615 included Editions in the manifest, 832 are under arXiv's non-exclusive licence and 1,268 have no known licence. Checking and attributing each file would be a per-paper licence audit for data that `parse` rebuilds from the PDFs anyway. The fixtures are five hand-picked files with a test of their licence.

## Alternatives considered
- **Synthetic TEI only.** Free of licences, but the fixtures' point is GROBID's real layout of a real paper (lost headings, run-in Sections, tables at the end of the body), which a made-up file would only imitate.
- **Fixtures stripped to the structure, with the words replaced.** It would keep the layout but break the tests that check Chunks against the printed text and the token counts.
- **Committing the parse cache for CC BY files only.** A partial cache would be confusing to reuse, and nothing needs it: the Seed run takes under two minutes.

## Consequences
- Adding a fixture means picking a CC BY 4.0 paper in the manifest and adding its row to the README; the test enforces both.
- If a later Snapshot recorded another licence for one of these Versions, the test would fail and the fixture would need replacing.
