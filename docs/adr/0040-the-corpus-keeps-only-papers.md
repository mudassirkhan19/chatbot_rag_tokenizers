# 0040. The corpus keeps only papers

- **Date:** 2026-10-18
- **Status:** Accepted. Adds a stage to the Relevance verdict of [0005](0005-rule-pre-filter.md), after [0037](0037-withdrawn-preprints-are-excluded.md)'s, and amends [0017](0017-acl-volume-ids-count-as-no-paper.md): proceedings front matter is now excluded, not left to the rules or the judge.

## Context
The full-corpus parse audit (`docs/reports/2026-10-18-full-corpus-parse-audit.md`, #47) found included Editions that are not papers: six CRAN package manuals and three more Editions named "… [R package … version …]", two proceedings volumes or their front matter (`2025.wnut-1.0`, and a Semantic Scholar record of the 2018 SCLeM proceedings), a 136-page textbook on arXiv (`2605.03799v3`), and theses of 40 to 200 pages. The judge asks whether a document is *about* tokenization, and these are, so it includes them. [0017](0017-acl-volume-ids-count-as-no-paper.md) expected the rules or the judge to reject proceedings front matter. They don't.

The developer decided that the corpus keeps only papers (#45, question 5): journal, conference and workshop papers and preprints. The boundary for theses was left to this ADR.

Every source records some of what a document is, but none records it completely:

- **OpenAlex** gives each work a `type`. On the 7,203 rule passes, the types that never name a paper are `dissertation` (38), `dataset` (27), `software` (16), `peer-review` (11), `paratext` (3), `conference-abstract` (3) and `book` (1). `book-chapter` holds Springer LNCS conference papers as well as textbook chapters. `other` holds Underline's records of ACL talks, a Wiley chapter and a code release. `report` holds HAL technical reports and Zenodo self-deposits. Its primary location also keeps the repository's own type (`raw_type`) and citation (`raw_source_name`). For DataCite records, `raw_type` is the resource type, such as `Audiovisual` for the 36 Underline and Zenodo talk and podcast recordings. One PhD thesis, `W7135572887`, is typed `other`, but its repository citation names the degree: "…, Doctor of Philosophy, Universiteit van Amsterdam."
- **Semantic Scholar** has `publicationTypes`, but the Snapshot's requests never asked for it. Adding it to `fields` changes every request, so every stored response would miss and `collect` would no longer rebuild offline. For its records only the title tells.
- **arXiv** has no document type. Authors write it in the comments: "PhD thesis", "MSc Thesis, 44 pages", "A dissertation submitted to …", "… Textbook for senior undergraduates".
- **CRAN** mints its package DOIs under `10.32614/cran.package.` (the R Journal's are `10.32614/RJ-…`).
- **The ACL Anthology** gives a volume's front matter paper number 0: `2025.wnut-1.0`, `W18-1200`, `P16-1000`.

## Decision
- **A paper is a journal, conference or workshop paper, or a preprint of one.** Out are theses of every degree, books and textbooks, proceedings volumes and their front matter, software and package manuals, datasets, peer reviews, abstracts, recordings, and the other OpenAlex types that never name a paper (editorial, erratum, letter, grant, standard, retraction, reference entry, supplementary materials, library guides).
- **Theses are out at every degree: honours, master's and PhD alike.** A thesis is not peer-reviewed as a paper is, and its quality varies the most at the lower degrees. A PhD thesis usually restates papers its author also published, and those are already in the corpus or can be. A thesis also runs to 100 or 200 pages, so the few that get in would outweigh many papers in the index. One rule for every degree also needs no degree detection, which the metadata gives unreliably (honours theses are typed `dissertation` like PhDs). A report taken from a thesis ("technical report, extraction from PhD thesis") is a paper of its own and stays.
- **Detection reads only the metadata the sources recorded.** An Edition is not a paper, in this order, when:
  1. its DOI starts with `10.32614/cran.package.`;
  2. it is a venue Edition whose ACL ID is a front-matter ID;
  3. its OpenAlex `type` is one of those above;
  4. its OpenAlex primary location's `raw_source_name` names a degree (Doctor of Philosophy, Master or Bachelor of Science or Arts, Master of Philosophy);
  5. its OpenAlex primary location's `raw_type` is `Audiovisual`;
  6. its arXiv comments have a clause that starts with a thesis or dissertation, optionally after "a" and a degree ("PhD thesis", "MSc Thesis, 44 pages", "A dissertation submitted …"), or with "textbook";
  7. its title contains "[R package" or "Proceedings of the".
- **It is its own stage**: `relevance_verdict=excluded`, `relevance_stage=not a paper`, and a reason naming the signal, such as `not a paper: OpenAlex type dissertation`. Like the withdrawn stage, it runs after the arXiv records, because the comments come from them, and before the judge, which never scores such an Edition. Withdrawn comes first. A cached verdict stays in the cache and is unused.
- **The funnel report** counts these Editions on their own row, "Not a paper", after "Withdrawn from arXiv".
- **OpenAlex's three fields are carried on the Edition** and follow its `openalex_id` when Candidates combine. They are not manifest columns: the reason names the one that fired.

## Alternatives considered
- **Decide by parsing** (page count, a table of contents, no references): the issue rules it out. It would only work for Editions with full text, and a 4-page workshop paper and a 4-page CRAN manual look alike to GROBID.
- **Ask the judge**, with a decision question that also requires a paper: the verdicts would have to be scored again (about 2.5 h), and the judge was chosen and measured on topical relevance ([0021](0021-tev1-decision-model-judge.md), [0011](0011-audit-set-and-relevance-metrics.md)). Metadata is deterministic and cites its evidence.
- **A rule in the pre-filter ([0005](0005-rule-pre-filter.md))**: the pre-filter sees only the finding source's title and abstract, before the arXiv record and its comments exist. Kept apart, the funnel also shows how many Editions are excluded for what they are rather than what they are about.
- **Keep PhD theses, drop the lower degrees**: it would need a degree from metadata that types every thesis `dissertation`, and PhD theses are the longest documents.
- **An allow-list of OpenAlex types**: excluding `other` and `report` would drop real papers (Underline's ACL records sit beside the papers; HAL's technical reports are papers). Leaving them out of the deny-list keeps the stage free of false positives.
- **Fetch Semantic Scholar's `publicationTypes`**: it breaks the offline rebuild for every stored response, and only two included Editions known only to Semantic Scholar turned out to be non-papers, both caught by their titles.
- **Prior work (research-bot):** it keeps whatever its sources return and has no document-type filter.

## Consequences
- On the full run, 152 rule passes are excluded as not papers: 88 that were included and 64 the judge had already excluded. Included Editions go from 2,794 to 2,706; with full text, from 2,086 to 2,068; with no open PDF, from 706 to 636. Most of the 88 had no open PDF: talk recordings, peer reviews, datasets and theses whose repositories serve none.
- Every non-paper the parse audit listed is excluded, and of the 37 files it sampled, only those six (`2025.wnut-1.0`, `2605.03799v3`, three CRAN manuals and `W7165988237`) are. Four included arXiv preprints whose comments say they are theses go too: `1611.04358v2`, `2403.01580v1`, `2508.15807v2` and `2603.24955v1`.
- `parse` reruns from the cached TEI in about 4 minutes. The parse report drops 21 files (18 Editions and their v1 files), and with them `10.32614/cran.package.rtiktoken`, one of its two quality-gate failures.
- Some non-papers stay. Textbook chapters typed `book-chapter` (for example "Fundamentals of Large Language Models" in *An Introduction to Large Language Models*) can't be told from LNCS papers by their metadata, and Zenodo self-deposits typed `other` or `report` include blog-like pieces. They are left to the judge.
- An Audit set export would put these Editions in the `judge-excluded` stratum, as with withdrawn preprints ([0037](0037-withdrawn-preprints-are-excluded.md)). The committed Audit set is unchanged. Two of its rows labelled relevant, the BPEmb dataset deposit and an Underline talk recording, are now excluded, because the labels say what a document is about, not what kind it is.
- A source that starts recording a type for an Edition (a refreshed Snapshot) can move it into this stage.
