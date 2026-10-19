# 0063. Versions and near-duplicates, measured before and after

- **Date:** 2026-10-20
- **Status:** Accepted. Amends [0051](0051-work-grouping-in-collect.md): titles are compared by `title_key`. Amends [0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md): rows may be checked by a blind agent.

## Context
Spec #49 asks the corpus to stop Versions, preprint–venue pairs and Survey restatements crowding the top 5 without merging different papers, and to show before and after with the duplicate rate. Its parts are built: `collect` groups Editions into Works ([0049](0049-normalised-arxiv-ids-and-borrowed-files.md), [0051](0051-work-grouping-in-collect.md)), every retriever has a `+collapsed` twin ([0053](0053-collapsed-ranking-and-collapsed-twins.md), [0057](0057-the-collapse-merges-copies-not-works.md)), and the eval report scores the grouping rule against the Work groups ([0060](0060-the-grouping-rule-scored-against-the-work-groups.md)). Issue #54 commits the before and after. This record collects what the stage decided and records three things #54 found:
- **The after numbers covered fewer questions.** The twins and the hybrid of [0058](0058-bm25-dense-hybrids-by-reciprocal-rank-fusion.md) put 55 Editions in a top 5 that had no Work group. So the twins' duplicate rates counted only the questions whose top 5 was fully grouped: 13 of 28 for BM25 and 20 of 28 for dense, against 28 of 28 raw. The two sides couldn't be quoted together.
- **Grouping those 55 found a second pair the rule misses.** Godey et al.'s MANTa preprint (2212.07284v1) says "Robust End-to-End"; its EMNLP Findings Edition (2022.findings-emnlp.207) says "End-to-End Robust". The two share no identifier, so they got two Works. The first miss was Purason et al.'s "Pre-trained" against "Pretrained" (#74, 0060). Both cost collapsed top-5 slots. BM25's twin put the two MANTa copies side by side on one question, and the dense and hybrid twins put Purason's on two questions and one.
- **The data had no single before-and-after table.** The duplicate rate was in one table per ranking, and the metrics in another.

## Decision
- **The stage, as built.** Grouping lives in `collect`, from Snapshot metadata only: identifiers, file hashes, titles and first authors. A rerun from the Snapshot rebuilds the manifest byte for byte, `work_id` included (0051). Two Editions are one Work when they share an arXiv id, DOI or ACL ID, a file's sha256, or a title and a first-author surname. A title match with a different first author is a Suspected pair: listed in the funnel report, never joined. Each Work has a Canonical Edition: the venue Edition, else the latest Version. The collapse merges copies of one passage across a Work's files into the slot of the best-ranked copy, and shows the Canonical Edition's copy when the pool holds it (0057). It over-fetches the raw top 50 (`pool` in `[collapse]`). Surveys are marked by a title word and never demoted.
- **A title is compared by its key** (`works.title_key`): normalised as before, with a hyphen inside a word dropped rather than made a space, and the words sorted. "Pre-trained" and "Pretrained" become one word. "Robust End-to-End" and "End-to-End Robust" become the same words in the same order. The key is used for the title-and-author signal and for finding Suspected pairs, so the two stay consistent. Slugs still come from the title as written. This closes #74, whose text is updated to match, as is #54's (209 Editions, not 154).
- **The Work groups cover every Edition any scored ranking puts in a top 5**, so the raw and collapsed rates are over the same 28 questions. The 55 new Editions were drafted as in 0047: identifier links and title matches, a Survey call from each abstract, and a note on each join made by title alone and on each close Survey call. A second agent then grouped the same 55 blind: it got the export without the draft's work_id or survey columns, plus the checked rows and the manifest. Its grouping and Survey calls matched the draft on every row. The rows record `checked_by` as `draft, matched by a blind agent check`. The developer asked for the agent check in place of checking on the page.
- **The eval report gains a *Before and after* section** after *Crowding*: one table, two rows per retriever (raw and collapsed). It gives the duplicate slots, split into another Edition or Version and same file, the grouped questions, and Recall@5, MRR@10 and Hit@5 on the *all answerable* row. It repeats the figures of the Crowding and Results tables, so it can't disagree with them.
- **Every disagreement in the Grouping section was read.** Both missed pairs are the same paper, and the rule is corrected for both. The Survey disagreements are left as they are:
  - The rule misses the Work groups' three Surveys, none of which has a survey word in its title: Mielke et al. (2112.10508v1), Libovický et al. (2110.08191v2) and Barolo's explainer chapter (2603.19269v1).
  - It flags Cognetta & Allauzen's "Tutorial: φ-Transductions" (2506.17942v1), which the check calls a tutorial with its own code.

  Nothing reads the rule's Survey flag for ranking, and restatement is measured against the Work groups, so these change no figure.

## Alternatives considered
- **Keep the rule and name the misses in this record** (0060 did for Purason). Before #54, the miss looked like it cost at most a slot. With the twins' top 5 grouped, it costs a slot on four collapsed top-5s across the three twins. The fix is two lines, and on the real manifest it moves exactly those two Editions.
- **Drop hyphens without sorting the words**, as #74 asked. That catches Purason but not MANTa.
- **A fuzzy title match** (edit distance or word overlap, with the first author). This catches more variants, such as MEGABYTE's "Predicting" against "Modeling". But it needs a threshold, and a threshold needs a measured error rate. Sorting the words loses only word order, and two different papers by one first author with the same title words in another order is a risk with no case in the corpus.
- **Compare raw and collapsed only over the questions grouped in both.** That needs no new rows, but BM25's twin had only 13 grouped questions. The after figure would then be over a different and smaller set than the before figure, and the grouping score would never see the Editions the twins reach.
- **Group the 55 by the manifest's work_id.** That is the rule being measured (0044).
- **The developer checks the 55 on the page**, as for the first 154. The developer asked for an agent check. A blind second grouping is independent of the draft, so it catches a draft error, which an approval of the draft wouldn't. A reader can still tell these rows from the person-checked ones by `checked_by`.
- **Demote Surveys.** Restatement takes 0 of 140 top-5 slots for BM25 and the hybrid, raw or collapsed, and 1 of 140 for dense. A demotion would have no measured number to move.
- **A deeper pool.** For no question did the raw top 50 hold fewer than 10 distinct Chunks once copies were merged, for any twin. So 50 is already deep enough.
- **Prior work (research-bot)**, used as inspiration only. It strips the `vN` suffix when extracting references, and relies on a database unique index on the arXiv id (and search category) to store a paper once. That is the whole of its duplicate handling: it has no venue Editions, no Surveys, no title or author signal and no ranking to collapse, since it retrieves papers rather than passages. Our corpus joins four sources. Here Version-stripping alone would miss the preprint–venue pairs that 50 Works need the title and first author to join, and these two pairs needed the title compared without hyphens or word order.

## Consequences
- **Before and after**, from the committed eval report (top-5 slots over the 28 answerable questions as a user asks them, every question grouped):

  | Retriever | Ranking | Duplicate | Another Edition or Version | Same file | Recall@5 | MRR@10 | Hit@5 |
  |---|---|---:|---:|---:|---:|---:|---:|
  | bm25 | raw | 59/140 | 38/140 | 21/140 | 0.16 | 0.118 | 0.18 |
  | bm25 | collapsed | 38/140 | 12/140 | 26/140 | 0.20 | 0.138 | 0.21 |
  | dense.bge-small | raw | 70/140 | 33/140 | 37/140 | 0.30 | 0.244 | 0.32 |
  | dense.bge-small | collapsed | 57/140 | 13/140 | 44/140 | 0.38 | 0.271 | 0.39 |
  | hybrid.bm25+bge-small | raw | 65/140 | 32/140 | 33/140 | 0.34 | 0.257 | 0.36 |
  | hybrid.bm25+bge-small | collapsed | 51/140 | 10/140 | 41/140 | 0.39 | 0.277 | 0.43 |

  The collapse removes two thirds or more of the copies from other Editions and Versions, and every retriever's Recall@5, MRR@10 and Hit@5 rise. What is left of that kind is copies the place rule misses, such as a Version chunked at other places (0057). The slots it frees go to the next Chunks in the raw order, most of them other passages of papers already ranked. So same-file duplicates rise for every retriever, as 0057 expected. Multi-paper Recall@5 stays at 0.06 for BM25 and dense: the second paper still doesn't reach the top 5.
- **Grouping**: over the 209 Editions in 179 Works of the Work groups, the rule joins 30 pairs and the Work groups 30, the same 30. Precision and recall are both 1.00. On the whole manifest, 2,705 included Editions are in 2,393 Works, two fewer than before, with 50 Works joined by title and first author. The Suspected pairs are the same five.
- **The Survey rule** agrees with the Work groups on 175 of 179 Works. The four it doesn't agree on are named above.
- A new retriever, such as the embedding comparison's candidates (#60, #61), may rank Editions the Work groups lack. `evaluate` names them, and the same draft-and-check loop groups them before its after numbers are quoted.
