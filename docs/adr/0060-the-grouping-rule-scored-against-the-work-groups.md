# 0060. The grouping rule scored against the Work groups, pair by pair

- **Date:** 2026-10-19
- **Status:** Accepted

## Context
`collect` fills the manifest's `work_id` and `survey` columns with the grouping rule of [0051](0051-work-grouping-in-collect.md), and the Collapsed ranking reads them ([0057](0057-the-collapse-merges-copies-not-works.md)). The eval report measures the top-5 duplicate rate against the hand-checked Work groups ([0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md)), but nothing scored the rule itself against them. A low duplicate rate after collapsing says little unless the rule is also shown to join the Editions the check joins. Issue #53 adds that score.

## Decision
- **A *Grouping* section after *Crowding*** in the eval report, computed in `evaluation/grouping.py` from the Work groups and the manifest rows `evaluate` already reads.
- **Pairwise precision and recall, over the Editions in the Work groups.** A pair is two Editions one Work holds. The rule's pairs are those with the same non-blank `work_id`; an Edition the manifest gives no `work_id`, or has no row for, is its own Work, as in the collapse. Precision is the share of the rule's pairs the Work groups join too, and recall the share of the Work groups' pairs the rule joins. The section gives the counts behind both, and names the Editions with no `work_id`.
- **Every disagreement is named**, in two tables: pairs the rule joins and the Work groups keep apart, and pairs the Work groups join and the rule misses. Each row gives both Editions' ids and manifest titles, the rule's `work_id` for each and the Work groups' Work for each. Rows are sorted by Edition id, so two runs give the same section.
- **Surveys are compared per Work of the Work groups.** The rule's flag for a Work is its `survey` column on each of the Work's Editions, with blank read as no. A Work is named when any of those differs from the check's flag. The line above the table counts the check's Surveys, the Works the rule flags on every Edition, and the Works the two agree on.
- **A manifest with no `work_id` filled** gives a section of one line saying so, and no score. That is a manifest from before 0051, which `collect` rebuilds.

## Alternatives considered
- **Score the Work groups' Works rather than pairs** (e.g. the share of Works reproduced exactly). One stray Edition would fail a whole Work, and the count says nothing about how far apart the two groupings are. Pairs weigh each join once and name each disagreement as two Editions a reader can check.
- **B-cubed or adjusted Rand index.** Both summarise the same pairs or memberships into one number. Neither names a disagreement, and the corpus is small enough that the disagreements are the useful output.
- **Score over every included Edition in the manifest.** Only the Editions in the Work groups have a checked Work, so pairs outside them have no ground truth.
- **Skip Editions with no `work_id` instead of making each its own Work.** The rule would then never be charged for an Edition it left ungrouped. Treating it as its own Work matches what the collapse does with it.

## Consequences
- On the real data, 154 Editions in 130 Works, every Edition with a `work_id`: the rule joins 23 pairs and the Work groups 24, all 23 of the rule's among them. Precision is 1.00 and recall 0.96.
- The missed pair is Purason et al.'s "Teaching Old Tokenizers New Words" (2512.03989v2 and 2026.findings-eacl.341). The titles differ by "Pre-trained" against "Pretrained", which normalise to different words, and the two Editions share no identifier. The cost is at most a duplicate slot, so the rule is left as it is. A title comparison that ignores hyphens inside words would join the pair.
- The Survey rule agrees on 127 of the 130 Works. It misses both of the check's Surveys, Mielke et al.'s history of open-vocabulary modelling (2112.10508v1) and Libovický et al.'s survey of character-level MT (2110.08191v2), since neither title has a survey word. Of the four near-misses 0047 drafted as not Surveys (a journal article, a position paper, an essay and a tutorial), it leaves three unflagged. It flags the fourth, Cognetta & Allauzen's "Tutorial: φ-Transductions in OpenFst" (2506.17942v1), for the word "tutorial". Nothing reads the rule's flag for ranking: the collapse doesn't demote Surveys, and restatement is measured against the Work groups. So the disagreement changes no figure in the report.
- The 55 Editions the hybrid of [0058](0058-bm25-dense-hybrids-by-reciprocal-rank-fusion.md) adds to the top 5 have no Work group yet, so they are outside the score until they are grouped.
