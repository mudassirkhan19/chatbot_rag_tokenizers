# 0057. The collapse merges copies of a passage across a Work's files, not whole Works

- **Date:** 2026-10-19
- **Status:** Accepted. Supersedes "one Chunk per Work" in [0053](0053-collapsed-ranking-and-collapsed-twins.md) and the Section rule of [0055](0055-a-work-shows-its-best-ranked-section.md); spec #49 and issue #52 are updated to match. Its merge key (the same Section path and count of Chunks before it) is superseded by [0072](0072-the-collapse-matches-copies-by-their-text.md), which matches copies by their text.

## Context
[0053](0053-collapsed-ranking-and-collapsed-twins.md) kept one Chunk per Work, and [0055](0055-a-work-shows-its-best-ranked-section.md) made that Chunk the Work's best-ranked Section. Even so, BM25's collapsed Hit@5 was 0.07 against 0.18 raw, and multi-paper questions, which the collapse was for, gained nothing. Keeping one Chunk per Work also drops a paper's other Sections, and those are often the ones that answer. The assignment asks for something narrower: arXiv Versions, a preprint and its conference version, and Surveys "crowding the top results", with "Paper A, latest version *(3 versions merged)*" as its example. It does not ask to collapse different passages of one paper, and grades "awareness of what it might wrongly merge".

## Decision
- **The collapse merges copies.** A copy is a Chunk of the same Work (the manifest's `work_id`; an Edition with none is its own Work) from a different file, at the same place in the same Section: the same Section path, and the same count of Chunks before it in that Section of its file. A paper's Versions and its preprint and venue Editions repeat their passages at those places.
- **A Work's other Chunks keep their slots** in the raw order. Two Chunks of one file are never merged.
- **A slot takes the place of its best-ranked copy and shows the copy from the best file**: the Canonical Edition's own file, else any Edition's latest file, else as ranked. A v1 still stands for a passage only when no later copy of it was retrieved.
- **The side table names the merged Editions and the merged copies** (`Merged.copies`, which replaces `siblings`: a Work's other Chunks are now in the ranking).
- **The duplicate rate is reported in two parts**: a duplicate from another Edition or Version of a Work already ranked higher (what the collapse targets), and one from a file already ranked higher (more of the same paper, which it leaves alone). Both come from the Work groups and the Chunks' files, never from the collapse's own rule. The pool shortfall counts distinct Chunks once copies are merged.

## Alternatives considered
- **One Chunk per Work** (0053, 0055): measured above. It turns "five results are five papers" into fewer answers.
- **Copies by equal or near-equal text:** Versions reword sentences, so equal text misses most copies, and a similarity threshold would need tuning and a measured error rate. The place in the Section needs neither.
- **Copies by Section only:** merges different Chunks of one long Section from different files, which is different text.
- **A cap of n Chunks per Work:** keeps an arbitrary n of a paper's passages whether or not they are copies, and still lets v1 and v5 copies take two of them.

## Consequences
- On the real corpus, BM25 (not committed): the twin beats the raw ranking. All answerable: Hit@5 0.21 against 0.18, Recall@5 0.20 against 0.16, MRR@10 0.138 against 0.118. Single-paper Hit@5 0.42 against 0.33, the reference rewrite 0.75 against 0.62, and multi-paper the same Hit@5 (0.12) with MRR@10 0.167 against 0.153.
- Duplicates from another Edition or Version fall from 38 of 140 top-5 slots to 7 of 65 measured. The 7 left are copies the place rule misses: a Version whose Section was cut into Chunks at other places, or whose headings differ. Same-file duplicates stay (21 of 140 raw, 20 of 65), since they are other text.
- Only 13 of 28 questions have every Edition in the twin's top 5 grouped, because the twin reaches Works the raw top 5 did not. #54 groups them before the before/after report is committed.
- The top-5 duplicate rate of the twin is not 0 by design; the report shows which part is left.
