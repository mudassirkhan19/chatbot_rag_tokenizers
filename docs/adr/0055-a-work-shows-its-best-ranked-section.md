# 0055. A collapsed Work shows its best-ranked Chunk's Section; the Canonical Edition only picks the copy

- **Date:** 2026-10-19
- **Status:** Superseded by [0057](0057-the-collapse-merges-copies-not-works.md). It had superseded the "which Chunk stands for a Work" rule of [0053](0053-collapsed-ranking-and-collapsed-twins.md); spec #49 and issue #52 are updated to match.

## Context
[0053](0053-collapsed-ranking-and-collapsed-twins.md) showed, for each Work, the best-ranked Chunk of its Canonical Edition's file whenever the pool held any, whatever its Section. On the real corpus that cost most of BM25's hits: Hit@5 0.18 raw, 0.04 collapsed. The Canonical Edition's best-ranked Chunk was often a Section the retriever had ranked far lower than the one that answered: for `wechsel-freezing` the preprint v1's "Is freezing necessary?" held the Passage, and the venue Edition's "Cross-lingual transfer" was shown. The rule chose the right file but the wrong text.

## Decision
- **A Work shows its best-ranked Chunk's Section.** The Work keeps its place in the raw order, and the Section shown is the one in its best-ranked Chunk, which is what the retriever found.
- **The Canonical Edition and the latest Version only choose among copies of that Section.** When the pool holds the same Section (the same Section path) from several of the Work's files, the copy shown is, by tier, then by rank: from the Canonical Edition's own file; else from any Edition's latest file; else as ranked. A v1 still stands for a paper only when no later copy of its Section was retrieved, and a venue Edition's copy of a Section stands in for the preprint's.
- **A copy is the same Section path, not the same text.** Versions reword sentences and Chunk boundaries shift between files, so equal text would miss most copies. Two files of one Work with the same Section path hold the same part of the paper.

## Alternatives considered
- **0053's rule, the Canonical Edition's best-ranked Chunk of any Section:** measured above.
- **The best-ranked Chunk, with no preference at all:** a v1's Chunk would stand for the paper whenever it out-ranked the latest Version's copy of the same text, which #52's acceptance criteria rule out.
- **Copies by equal or near-equal text:** misses reworded Versions (`missed-table-v1` differs from v5 in single words) unless a similarity threshold is tuned, which the Section path makes unnecessary.

## Consequences
- On the real corpus, BM25 (not committed): Hit@5 0.18 raw and 0.07 collapsed (0.04 under 0053), MRR@10 0.118 and 0.077 (0.042). Multi-paper questions keep their raw Hit@5 (0.12) and nearly their MRR@10 (0.146 against 0.153), and the collapsed top 5 has no duplicate slot.
- Single-paper questions still lose most of their hits (Hit@5 0.33 raw, 0.08 collapsed). That loss comes from one Chunk per Work itself: the Chunk that answers is often another Chunk of the same file, which the collapse moves to the side table as a sibling. The metrics score only the shown Chunk.
- The collapsed top 5 brings Works the raw top 5 never reached, and many of their Editions have no Work group yet: 4 of 28 questions are fully grouped for the twin. #54 groups them before the before/after report is committed.
