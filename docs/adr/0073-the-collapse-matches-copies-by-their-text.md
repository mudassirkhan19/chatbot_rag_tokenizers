# 0073. The collapse matches copies by their text, not their place in the Section

- **Date:** 2026-10-21
- **Status:** Accepted. Supersedes the merge key of [0057](0057-the-collapse-merges-copies-not-works.md) (the same Section path and the same count of Chunks before it); the rest of 0057 stands.

## Context
#77's diagnosis (`docs/reports/2026-10-21-chat-failure-diagnosis.md`, kind 8) found that 15 of the 44 committed chat Turns still held two copies of one passage from different files of one Work, some 96–100% identical. 0057's key needs the same Section path and the same count of Chunks before it in that Section. Editions and Versions break it in four ways: GROBID nests a Section in one Edition only (`4.4 NER Results` against `4 Experiments › 4.4 NER Results`), headings change case or punctuation (`2 BACKGROUND` against `2. Background`), Sections are renumbered (`5.4.2` against `5.3`), and a revision adds or splits paragraphs. 0057 rejected a text match because "a similarity threshold would need tuning and a measured error rate". Issue #80 asks for the text match, measured.

## Decision
**Two Chunks of one Work from different files are copies when they share at least `overlap` of their word 5-grams, and one of them is the other's closest Chunk in its file.**
- Words are lower-cased runs of letters and digits. The share is counted on the smaller Chunk's 5-grams, so a v1 paragraph that a later Version extended is still a copy.
- *The closest-Chunk condition*: a Chunk's closest Chunk in a file is the one it shares the largest share with. A table cut into two Chunks repeats its caption in both, so the first rows of v1 share 0.69 with the last rows of v2. But v1's first rows are closer to v2's first rows (1.00), and v2's last rows are closer to v1's last rows, so the pair stays apart. Each holds rows the other lacks.
- **`overlap` is 0.4**, in `[collapse]` of `config/retrieval.toml`, and the eval report and chat report print it beside the pool.
- **Going down the pool, a Chunk joins the best-ranked slot of its Work that holds a copy of it and no Chunk of its own file**, or it opens a slot. Two Chunks of one file are never merged, as in 0057, so a slot holds one Chunk per file. Which copy a slot shows (the tier order), the side table and Surveys are as in 0057.
- **The answers file's first line records `collapse_overlap`**, as it records `collapse_pool`, so `chat-eval --from-answers` refuses answers that another rule retrieved. The committed answers were retrieved with 0057's key and have no `collapse_overlap`, so `--from-answers` refuses them until #86 regenerates the chat run. #86 has to rerun it anyway, and #84, which rescored them, has already merged.

## How the threshold was chosen
For every Chunk of a Work with more than one file, its closest and second-closest Chunk in each other file of the Work (`docs/reports/2026-10-21-collapse-by-text/overlaps.py`). That gives 107,807 (Chunk, other file) pairs:

| Overlap | 0–0.1 | 0.1–0.2 | 0.2–0.3 | 0.3–0.4 | 0.4–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | 0.9–1.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Closest Chunk | 11,453 | 2,594 | 2,385 | 2,482 | 2,863 | 3,740 | 4,400 | 5,107 | 7,672 | 65,111 |
| Second closest | 75,227 | 9,250 | 6,301 | 4,485 | 3,494 | 3,178 | 2,183 | 1,551 | 972 | 1,166 |

Copies sit at 0.9–1.0, and other text below 0.1. Between them, no threshold is clean. Counted over every pair of Chunks instead (each unordered pair once, not only the closest), 58,699 pairs share 0.4 or more, and the closest-Chunk condition keeps 11,607 of them apart, such as an Abstract and an Introduction that share a sentence. In samples of the closest-Chunk pairs that pass, 4 of 5 at 0.5–0.6 and 6 of 8 at 0.4–0.5 were one passage, reworded or extended by a revision. The others were a boundary shift (half of one Chunk lies in the other's neighbour) and, at 0.46–0.48, one wrong merge: two different appendix Sections of one paper that share table rows.

The eval report decided between 0.5 and 0.4. At 0.5, bge-small's Collapsed Recall@5 fell from 0.38 to 0.34, all of it on one question. `magikarp-verified-share`'s Passage is a sentence the EMNLP Edition and v2 added to a paragraph of "3 Results". v1's shorter paragraph shares 0.42 with it. The place key merged the two and showed the EMNLP copy. At 0.5 v1's copy stands alone, without the sentence. 0.4 and 0.3 give the same eval report, timings aside, on BM25, bge-small and their hybrid. 0.4 is the higher one, so it lets in fewer of the boundary-shift and wrong merges below it.

## Results
`evaluate` on the full corpus, Collapsed rankings, 0057's key against this one (the raw rankings are unchanged). Duplicates are top-5 slots counted against the Work groups over the grouped questions. Recall@5, MRR@10 and Hit@5 are over the answerable questions as asked:

| Retriever +collapsed | Another Edition or Version | Recall@5 | MRR@10 | Hit@5 |
|---|---|---|---|---|
| bm25 | 12/140 → 5/125 | 0.20 → 0.21 | 0.138 → 0.133 | 0.21 → 0.25 |
| dense.bge-small (the chatbot's) | 13/140 → 5/130 | 0.38 → 0.38 | 0.271 → 0.276 | 0.39 → 0.39 |
| dense.bge-base | 11/95 → 5/90 | 0.32 → 0.32 | 0.258 → 0.261 | 0.32 → 0.32 |
| dense.openscholar | 6/60 → 2/60 | 0.08 → 0.12 | 0.061 → 0.070 | 0.11 → 0.14 |
| hybrid.bm25+bge-small | 10/140 → 4/130 | 0.39 → 0.39 | 0.277 → 0.282 | 0.43 → 0.43 |
| hybrid.bm25+bge-base | 8/90 → 4/90 | 0.35 → 0.35 | 0.270 → 0.271 | 0.39 → 0.39 |
| hybrid.bm25+openscholar | 5/80 → 3/80 | 0.32 → 0.32 | 0.227 → 0.230 | 0.36 → 0.36 |

No Recall@5 drops. BM25's MRR@10 falls by 0.005.

`chat-eval`, one run with the real model in this branch, against the committed answers (0070), not committed (#86 regenerates the chat run):
- **Near-duplicate Turns (#77's `dups.py`): 15/44 → 2/44.** The two left are boundary shifts that the closest-Chunk condition keeps apart on purpose. `tokenization-latency`'s v1 Chunk `9102…-0056` shares 0.51 with v2's `2a86…-0028`, but its own copy is v2's `-0029` (0.90). `byt5-learning-rate`'s `93fe…-0041` and `518d…-0050` share 0.67, and each has a copy of its own (1.00) in the other file.
- Recall@5 0.48 → 0.48 (single-paper 0.75 → 0.75). False abstentions 4/28 → 2/28: `one-sided-regularization` and `magikarp-norm-indicator`, 0070's two new declines, now answer, grounded. Grounded 24/25 → 25/26.

## Alternatives considered
- **0057's place key**: it misses the four kinds of difference above (15/44 Turns).
- **The place key or the text match**: it would keep 0057's merges of different text at the same place, the merge that 0057 itself called a risk.
- **A threshold alone, without the closest-Chunk condition**: it merges a table's later rows into another file's first rows whenever the later rows' own copy isn't in the pool.
- **0.5, the threshold `dups.py` counts with**: it drops `magikarp-verified-share`'s Passage, as measured above.
- **Overlap counted on the union (Jaccard)**: a v1 paragraph inside a longer v2 Chunk would score its length ratio, not its containment.

## Consequences
- The near-duplicate count uses the same 5-gram share as the rule, so its fall is partly by construction. The independent checks are the Work-group duplicate rates and Recall@5 above, and the samples.
- The merges free slots, and 8 Editions with no Work group now reach a top 5 (84 against 76): `2022.findings-acl.194`, `2025.acl-srw.57`, `2025.findings-acl.275`, `2025.findings-emnlp.595`, `2508.11857v3`, `2509.18750v2`, `2603.22774v3` and `2608.07249v1`. So the Collapsed duplicate rates cover fewer questions: bge-small 26 of 28 against 28. They need the developer's grouping (`evaluate --export-ungrouped`) before the duplicate rates of both keys cover the same questions.
- Wrong merges are possible near 0.4: the sample found one in eight at 0.4–0.5. A wrong merge hides a passage behind another of the same paper. It never hides another paper.
- A query now costs up to a few thousand 5-gram set intersections in the pool (the closest-Chunk condition compares against a whole file). Each Chunk's 5-grams are computed once.
