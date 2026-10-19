# 0049. Normalised arXiv ids, and Editions that hold another Edition's file

- **Date:** 2026-10-19
- **Status:** Accepted. Adds a stage to the Relevance verdict of [0005](0005-rule-pre-filter.md), after the judge of [0007](0007-local-llm-judge.md), and amends how [0008](0008-semantic-scholar-keyword-discovery.md) combines Candidates.

## Context
The full-corpus parse audit (`docs/reports/2026-10-18-full-corpus-parse-audit.md`, #44) found four files each held by two Edition ids. Two are expected: a venue PDF that is its preprint's v1 (`2022.nsurl-1.1` and `2301.06736v1`), and byte-identical Versions of one preprint (`2409.17171v1` and `v2`). Two are bugs:

- **`arXiv:2607.05691v1` beside `2607.05691v1`.** OpenAlex names some arXiv locations in the citation form, `pmh:oai:arXiv.org:arXiv:2607.05691` and `arxiv.org/abs/arXiv:2607.05691v1`. The prefix went into the arXiv id, so the Candidate never matched the bare id's Edition. A second case, `arXiv:2603.13547v1`, was judged excluded and had no file. Semantic Scholar's `ArXiv` external id goes through the same path.
- **`10.32614/cran.package.sentencepiece` holding `L18-1473`'s PDF.** The CRAN package's OpenAlex open-access link pointed at an LREC paper's PDF, so the Fetcher recorded another paper's bytes under the CRAN Edition.

DOIs are already compared without case: `match_keys` lower-cases them when Candidates combine, `add_acl_editions` looks venue Editions up by a lower-cased DOI, and `eval-check`'s `Works` casefolds every identifier.

## Decision
- **An arXiv id loses an `arXiv:` prefix where it enters**, in the OpenAlex and Semantic Scholar parsers, through one helper (`editions.bare_arxiv_id`). The arXiv API and the ACL Anthology never report one. Normalising at the source means the Edition id, source link, match keys and arXiv record request all see the bare id.
- **DOIs keep the case their source reported.** Every comparison already ignores case. Lower-casing the stored value would rename every venue Edition named by a DOI with capitals (`10.1162/TACL_A_00999`), which would orphan its cached verdict and full-text record line.
- **An included Edition whose only file belongs to another Edition is excluded**, as its own stage: `relevance_stage=borrowed file`, with the reason `file belongs to another Edition: <file>, from <url>, has the same bytes as <file> of <Edition>, and no identifier or title links the two`. The judge's probability stays on the row. An Edition's file is borrowed when all of the following hold:
  1. it is the Edition's only file;
  2. it came from an open-access location, not from the Edition's own source (its ACL Anthology PDF, or arXiv for a preprint);
  3. another Edition's recorded file has the same sha256;
  4. none of the Editions holding those bytes shares an arXiv id, DOI or ACL ID with it, or has the same title once case, accents, punctuation and whitespace are dropped.
- **The check runs where the full-text record meets the manifest** (`fulltext.apply_record`), so `collect` and `fetch` apply it alike and the manifest stays a pure function of the Snapshot. It comes after the judge because only included Editions have files.
- **The funnel report** counts these Editions on their own row, "File belongs to another Edition", after "Rejected by the judge", and leaves them out of the judge's counts.

## Alternatives considered
- **Strip the prefix in `Edition` itself, or in `_EditionIndex.add`**: the Edition id and source link are built from the arXiv id in the parsers, so those would need rewriting after the fact. Doing it where the id is read keeps one place per source.
- **Refuse the file in `fetch`** (#44's suggestion): the record would then have no line for the bad file, and `collect` could not explain the exclusion from the Snapshot. A refused download would also be retried on every run.
- **Exclude both Editions of an unlinked same-bytes pair, or the later one by id**: either would exclude `L18-1473`, which got its own PDF from the ACL Anthology, had the CRAN row been included. Where the bytes came from tells which Edition is right. When both copies came from open-access locations, both are excluded: neither source can vouch for its file.
- **Link by the grouping rule of #49** (title and first author): that rule is not built yet. Identifiers and title alone are enough to keep the two expected cases, and a title-and-author check would only keep more Editions.
- **Prior work (research-bot):** it strips the `vN` suffix and relies on a database unique index on the arXiv id; it has no other source and no file-level check.

## Consequences
- On the full run, the two `arXiv:` rows join their bare-id rows: Discovered goes from 26,388 to 26,386, and Included from 2,706 to 2,705 (`arXiv:2607.05691v1` was included). With full text goes from 2,068 to 2,067, and Indexed from 2,067 to 2,066. The joined `2607.05691v1` gains the OpenAlex channel.
- No real Edition is excluded as borrowed: the CRAN package was already excluded as not a paper ([0040](0040-the-corpus-keeps-only-papers.md)), which comes first, and the nsurl pair shares an ACL ID. The stage is in place for a future run or Snapshot refresh.
- `parse`, `index` and `evaluate` were rerun: the parse report drops `arXiv:2607.05691v1`'s file (2,690 files, 141,348 Chunks, from 2,691 and 141,512), the index drops its 164 Chunks, and the eval report's Recall@5, MRR@10, Hit@5 and duplicate rate are unchanged.
- A borrowed Edition's file stays in the full-text record. `parse` and `index` skip it, as they skip every excluded Edition's files.
