# 0010. Fetch arXiv records only for Editions that pass the rules

- **Date:** 2026-10-16
- **Status:** Accepted. Supersedes the "rule rejects included" part of [0006](0006-arxiv-records-via-oai-pmh.md).

## Context
[0006](0006-arxiv-records-via-oai-pmh.md) gives every arXiv Edition its OAI-PMH record, rule rejects included, at one request every three seconds. That was about 3.3k records for the keyword queries. Citation expansion from the Seeds ([0009](0009-seeds-and-citation-expansion.md)) adds roughly 15–20k Candidates. The Sennrich BPE paper alone has about 9.1k citing papers and SentencePiece about 4.4k, and most of their citers only use the tool. If about half of those Candidates are arXiv preprints, fetching every record would add 5–7 hours to the first run, mostly for rows the rules throw away.

## Decision
- **The rule pre-filter runs before the arXiv record stage, and only Editions that pass it get their record.** Rules read only the title and abstract, which the finding source already supplies, so the order doesn't change any rule outcome.
- **A rule-rejected arXiv Edition keeps the id its source reported.** That is the pinned Version from an arXiv search page, or the bare arXiv id when only Semantic Scholar found it. Its `versions` column is empty, its `licence` is `unknown`, and its comments are whatever the source reported (arXiv search does report them; Semantic Scholar doesn't).
- This applies to every Discovery channel, keyword queries included, so all rejected rows behave the same way.

## Alternatives considered
- **Keep fetching every record (0006):** complete rows everywhere, but hours of fetching for Editions that never reach the judge, and a Snapshot several megabytes larger.
- **Skip records only for Candidates that expansion found:** keeps 0006's behaviour for keyword rows, but leaves two kinds of rejected row that differ only by how they were found.
- **Prior work (research-bot):** it records no Version history or licence for any row, so it has no such cost and no such field.

## Consequences
- The first full run fetches records only for rule passes. On the keyword queries alone that is about 1.8k instead of 4.3k.
- Changing the rules so that a reject flips to pass makes the next run fetch that Edition's record, a few seconds per newly passing arXiv Edition.
- Rejected rows can't be told apart by Version, so an audit of rule rejects (#9) reads the source's id. A bare id without a Version means Semantic Scholar was the only source.
- Records already in a Snapshot for rejected Editions are harmless: they are never read, and they stay valid if the Edition later passes.
