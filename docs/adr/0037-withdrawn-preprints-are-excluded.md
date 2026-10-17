# 0037. Withdrawn arXiv preprints are excluded from the corpus

- **Date:** 2026-10-18
- **Status:** Accepted. Amends [0015](0015-pdf-fetcher-pinned-files-and-hashes.md) and adds a stage to the Relevance verdict of [0005](0005-rule-pre-filter.md).

## Context
The full run (#11) included four arXiv preprints whose latest Version is a withdrawal (#29). arXiv serves no PDF for a withdrawal Version, so `https://export.arxiv.org/pdf/<id>v2` answers 404. [0015](0015-pdf-fetcher-pinned-files-and-hashes.md) counts that as "fetch failed", which shouldn't happen, so `fetch` exited non-zero on every run and the four rows stayed "still to fetch".

The authors or arXiv withdrew these papers because their content is wrong or can't be trusted: "Incorrect results", baselines "trained incorrectly", "disputed and unverifiable authorship". A chatbot grounded in the corpus should not cite them, so the question isn't only how to fetch them.

The arXivRaw record marks a withdrawal itself. The withdrawal Version is listed with `<size>0kb</size>` (and `<source_type>I</source_type>`). In the full Snapshot, 23 records have a 0kb latest Version, and every one carries a withdrawal comment. Another 10 have a 0kb Version that a later Version replaced, so a withdrawal can be undone. `source_type` `I` also appears once on a 3,665 kB Version, so it isn't a withdrawal marker by itself. The comments are free text in many wordings.

## Decision
- **A preprint whose latest Version is listed at 0kb is withdrawn**, read from the full arXiv record. An earlier 0kb Version followed by a real one is not.
- **A withdrawn preprint is excluded**: `relevance_verdict=excluded`, `relevance_stage=withdrawn`, and a reason naming the withdrawal Version and quoting the arXiv comments. The stage runs after the arXiv records, because rules run before them ([0010](0010-arxiv-records-for-rule-passes-only.md)), and before the judge, which never scores a withdrawn preprint. Its cached verdict, if any, stays in the cache and is unused.
- **The funnel report** counts withdrawn preprints on their own row, "Withdrawn from arXiv", between the rule and judge rejections.
- **The Fetcher** is unchanged. It fetches only `included` rows, so it never asks for a withdrawal Version. A pinned arXiv Version that isn't served as a PDF stays a fetch failure.

## Alternatives considered
- **Keep them, pinned to the last Version with a PDF:** they would reach "full text", but the corpus would then ground answers in results their authors disowned. It also breaks [0015](0015-pdf-fetcher-pinned-files-and-hashes.md)'s rule that the pin is the latest Version.
- **Keep them as `no_fulltext`:** honest about the PDF, but the row would still count as an included, relevant Edition.
- **A rule on the arXiv comments:** the wording varies ("withdrawn", "Incorrect results", "duplicate of …"), and many comments that aren't withdrawals mention errors or revisions. The 0kb marker is arXiv's own and has no false positives in the Snapshot.
- **A rule in the stage-1 pre-filter ([0005](0005-rule-pre-filter.md)):** the pre-filter sees only the finding source's title and abstract, before the arXiv record exists.
- **Prior work (research-bot):** it records no Version history, so it can't tell a withdrawn preprint apart and keeps it.

## Consequences
- On the full run, 15 rule passes are excluded as withdrawn: the four that were included, and 11 the judge had already excluded. Included Editions go from 2,798 to 2,794, and "still to fetch" from 6 to 2, the two venue PDFs whose hosts were down.
- The v1 PDFs fetched for the four stay in the Snapshot's record, like any file a row is no longer pinned to, and their rows list them in `pdf_files`.
- A preprint withdrawn after a Snapshot is only excluded once a refreshed Snapshot has its new record.
- A new Audit set export (`audit export --force`) would put withdrawn preprints in the `judge-excluded` stratum, since it has no stratum of its own. There are 15 against about 4.4k judge exclusions, and the committed Audit set is unchanged.
