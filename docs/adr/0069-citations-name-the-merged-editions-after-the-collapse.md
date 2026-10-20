# 0069. Citations name the merged Editions and mark Surveys after the collapse

- **Date:** 2026-10-20
- **Status:** Accepted; amends [0054](0054-pinned-local-answer-model-and-the-chat-page.md), whose `[chat]` named only a configured retriever

## Context
Spec #63 has the chatbot retrieve with the retriever #61 chose, collapsed (story 58), and #72 will point `[chat]` at it. Until now `[chat]` could name only a configured retriever, not a `+collapsed` twin, and a reference named only the file of the Chunk shown. The Collapsed ranking ([0057](0057-the-collapse-merges-copies-not-works.md)) folds copies of one passage from a Work's other files into that Chunk, so a reference to it stands for every one of those files. Issue #71 asks the reference to say so ("2112.06598v2, also v1 and 2022.acl-long.12") and to mark a Survey's Chunk. Without the collapse nothing should change.

## Decision
- **`[chat]` takes a `+collapsed` twin by name**, as `evaluate` names them: `retriever = "dense.bge-small+collapsed"`. It retrieves over its retriever's index with the `[collapse]` pool, and `chat` and `chat-eval` read the Works from the manifest (`--manifest`, default `data/manifest.csv`), as `evaluate` does. The repo's `[chat]` is unchanged here; #72 switches it.
- **A Turn keeps the collapse's side table**, what stands behind each retrieved Chunk. A raw retriever's Turn has none.
- **The anchor names the merged Editions after the Edition shown**, best-ranked first: "2112.06598v2, also v1", "P16-1162, also 1508.07909v5". A Version of a preprint already named is written as its Version alone; any other Edition by its pinned id; three or more read "a, b and c". The page's `/turn` adds `editions` (as written), `also` (the merged pinned ids) and `survey` to each reference and Chunk, only when the side table is there. A reference with no merged copies reads as before. The saved transcript ([0068](0068-the-transcript-saved-from-the-chat-page.md)) writes each reference as the page does, merged Editions and Survey mark included.
- **The Survey flag is the manifest's `survey` column** for the shown Chunk's Edition, the grouping rule's flag ([0051](0051-work-grouping-in-collect.md)), carried on the collapse's `Merged`. The page marks it beside the reference and the Chunk. Surveys are still not demoted.
- **`chat-eval` names the twin and its pool.** The report's Retriever line gives the twin's name and the collapse pool; the key stays the retriever's, since the index is its. The answers file's first line gains `collapse_pool` (null for the raw ranking, which is how files written before it read), so `--from-answers` refuses to re-score a collapsed run as a raw one or the reverse.

## Alternatives considered
- **Every merged Edition in full** ("2112.06598v2, also 2112.06598v1"): repeats the arXiv id the reader has just read; the issue's example writes "v1".
- **The Work groups' Survey flag**: it is the checked ground truth `evaluate` measures against, but `chat` would then need the Work groups file, and the collapse itself groups by the manifest. The page shows what the retriever acted on.
- **A sibling-Chunk panel** (story 54): dropped by 0057's rewording of #71. The merged copies hold the same text as the hit, and a paper's other passages are hits of their own.
- **A `CollapsedConfig` wrapping the retriever's config with its own key**: `index.load` finds the index by the key, so the twin would need a second lookup; keeping the retriever's config and the pool beside it is smaller.

## Consequences
- With #72's switch, a citation stands for the paper's copies, not one file of it.
- Answers files written before this have no `collapse_pool` and still re-score under a raw `[chat]`.
- The merged Editions are in rank order, so when two copies tie (equal text gives equal scores) their order is the retriever's tie order.
