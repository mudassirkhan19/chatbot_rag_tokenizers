# 0051. Work grouping in `collect`: work_id, Canonical Edition, Survey flag and Suspected pairs

- **Date:** 2026-10-19
- **Status:** Accepted. Fills the manifest's `work_id`, which [0041](0041-passage-matcher-eval-check-and-calibration.md)'s identifier rule stood in for.

## Context
The index holds the same paper several times on purpose: v1 and the latest Version of a preprint, a preprint and its venue Edition, and every Chunk of each file. The baseline eval report counts what that costs: 59 of 140 top-5 slots for BM25 and 70 of 140 for the dense baseline hold a Chunk from a Work already ranked higher ([0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md)). Spec #49 handles it in two steps: `collect` says which Editions are one Work (#51, this record), and a Collapsed ranking keeps one Chunk per Work (#52). The manifest had a `work_id` column that nothing filled, and `eval-check` grouped Editions by shared identifiers only, which the hand check showed misses four preprint–venue pairs.

## Decision
- **Grouping runs where the full-text record meets the manifest** (`fulltext.apply_record`, after the borrowed-file check of [0049](0049-normalised-arxiv-ids-and-borrowed-files.md)), so `collect` and `fetch` group alike and the manifest stays a pure function of the Snapshot ([0003](0003-commit-the-snapshot.md)). Only included rows are grouped; excluded and pending rows leave the new columns blank.
- **Two Editions are one Work when they share** (union-find over names, in `collection/works.py`):
  1. an identifier: the arXiv id (without an `arXiv:` prefix), DOI or ACL ID, all compared without case;
  2. a file's sha256 in the full-text record;
  3. a title and the first author's surname. Titles are compared without case, accents, punctuation or extra whitespace. The surname is the part before a comma when the name has one ("Vieira, Tim"), else the last word of the name ("Tim Vieira").
- **A title alone never joins.** Two Works that share a title but not a first author are a **Suspected pair**, listed in the funnel report with both sides' Edition ids, titles and first authors. "Character-based Neural Machine Translation" (Ling et al., 1511.04586, and Costa-jussà & Fonollosa, 1603.00810 / P16-2058) is the case the rule exists for.
- **Each Work records the weakest signal it needed**, in the order identifier < bytes < title-and-author: the first signal under which, with every stronger one, its Editions are already one Work.
- **The Canonical Edition** stands for the Work: the venue Edition when there is one, the latest year first, then the first by Edition id; otherwise the preprint whose latest Version was submitted last (a preprint's Edition id already names its latest Version, [0015](0015-pdf-fetcher-pinned-files-and-hashes.md)). The manifest marks it in a `canonical` column (`yes`/`no`).
- **`work_id` is a slug from the Canonical Edition** in the Work groups' style: first-author surname, year, first three title words, lower-case ASCII, with short words such as "a", "of" and "for" skipped (`sennrich-2016-neural-machine-translation`). Letters NFKD leaves alone are spelled out (ı → i, ł → l, ø → o, ß → ss, æ → ae). On a collision, Works are taken in their Canonical Edition's id order and the later ones get `-2`, `-3`. Re-pinning a preprint to a newer Version leaves the slug unchanged.
- **A Work is a Survey** when its Canonical Edition's title has survey, review, overview or tutorial as a whole word. The `survey` column (`yes`/`no`) is written on every Edition of the Work. Nothing is demoted for it: restatement is 0 and 1 of 140 top-5 slots in the baseline (0047).
- **The funnel report gains a *Works* section**: included Editions, Works, Works of several Editions by signal, Canonical Editions by kind, Surveys, and the Suspected pairs table. `collect` prints one line with the same totals.
- **`eval-check` and `evaluate` read `work_id`** through the existing `Works` interface, and fall back to the identifier rule only for a row where it is blank.

## Alternatives considered
- **Surname as the last word of the name, always** (as #49 first wrote it). On the real run it left three same-paper pairs as Suspected pairs, because one source wrote the name surname first: "Vieira, Tim" vs "Tim Vieira", "LIM, Jia Peng" vs "Jia-Peng Lim", "Kumar, Anshul" vs "Anshul Kumar". Reading the part before a comma joins all three and no other Work.
- **A title match alone**: joins Ling et al. with Costa-jussà & Fonollosa, two different papers.
- **Content similarity (MinHash or embeddings over Chunks)**: identifiers, bytes and title-and-author already reproduce the checked Works. A content signal has no measured need and would make grouping depend on `parse`, outside `collect`.
- **Group in a separate stage after `index`**: the manifest would then depend on more than the Snapshot, and `fetch` would write a manifest without Works.
- **Most recent Edition as canonical whatever its kind**: a preprint revised after publication would stand for a peer-reviewed paper.
- **Demote Surveys**: no measured restatement to move (0047).
- **Prior work (research-bot):** it strips the `vN` suffix and relies on a database unique index on the arXiv id. It has no venue Editions, files or titles to group by.

## Consequences
- On the real Snapshot: 2,705 included Editions in 2,395 Works. Of those, 260 Works of several Editions are joined by an identifier, none needs file bytes alone (the two same-bytes pairs of #44 share an ACL ID or were merged by 0049), and 48 need the title and first author. Each of the 48 was read and is the same paper. 1,174 Canonical Editions are venue Editions and 1,221 preprints. 15 Works are Surveys by the title rule, including at least one false positive ("…Modern Code Review Process"); #53 scores the rule against the Work groups.
- Five Suspected pairs remain, including the Ling / Costa-jussà trap. Two of the others look like the same paper with a differently written first author ("K H, Manodnya" vs "Manodyna K H") or none at all; they stay apart, which costs at most a duplicate slot.
- The manifest gains `canonical` and `survey` columns, so a manifest from before this change must be rebuilt with `collect`.
- The collapse (#52) and the grouping score against the Work groups (#53) read these columns.
