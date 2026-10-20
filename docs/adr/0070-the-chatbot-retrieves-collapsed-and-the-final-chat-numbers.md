# 0070. The chatbot retrieves with bge-small's Collapsed twin, and the final chat numbers

- **Date:** 2026-10-20
- **Status:** Accepted; amends [0068](0068-the-transcript-saved-from-the-chat-page.md), whose committed Transcript it replaces

## Context
[0065](0065-the-embedding-comparison-on-the-raw-ranking.md) chose `dense.bge-small` on the Collapsed ranking, and [0069](0069-citations-name-the-merged-editions-after-the-collapse.md) let `[chat]` name a `+collapsed` twin. But `[chat]` still named the raw retriever, so the chat report, its answers and the Transcript described a bot that ranks copies of one passage in separate slots. Spec #63 (story 58) and issue #72 ask for the final numbers on the retriever #61 chose, collapsed: in the chat report, the answers file, the eval report's rewriter row and the Transcript, each saying so in its header.

## Decision
**`[chat]` names `dense.bge-small+collapsed`**, with the `[collapse]` pool of 50. No index changes: the twin retrieves over bge-small's index.

**The eval report names the chatbot's retriever.** Its Retrievers section ends with "The chatbot's retriever, from `[chat]`: dense.bge-small+collapsed, 5 Chunks per Turn" whenever the `[chat]` table can be read. The rewriter row itself doesn't depend on the retriever, since the rewriter writes from the stored history alone ([0067](0067-the-rewriter-row-of-evaluate.md)). The rerun changed nothing in the report but this line and the timings. The chat report and the answers file already name the twin and its pool (0069).

**The reports were regenerated with the real model.** `evaluate` was rerun, then `chat-eval --runs 3 --baseline` with the committed raw run as the baseline. From the chat report:

| | Raw (`dense.bge-small`) | Collapsed (`dense.bge-small+collapsed`) |
|---|---:|---:|
| Abstention rate, unanswerable | 7/8 (0.88 [0.53, 0.98]) | 7/8 (0.88 [0.53, 0.98]) |
| near-miss / out-of-topic | 5/6 / 2/2 | 5/6 / 2/2 |
| False-abstention rate, answerable | 2/28 (0.07 [0.02, 0.23]) | 4/28 (0.14 [0.06, 0.31]) |
| Grounded rate | 27/27 (1.00 [0.88, 1.00]) | 24/25 (0.96 [0.80, 0.99]) |
| Recall@5, answerable | 0.41 | 0.48 |
| Recall@5, single-paper | 0.58 | 0.75 |

The three runs agree on every verdict and rate. Three questions changed verdict against the raw run:
- `one-sided-regularization` now abstains. The collapse shows BPE-dropout's § 5.2 from its Canonical ACL Edition (`2020.acl-main.170`), where the venue reworded the arXiv text into bullets ("for large datasets, BPE-dropout should be used only on the source side"). It is at rank 2, and the model says the Chunks don't answer it.
- `magikarp-norm-indicator` now abstains with its Passage in its Chunks. The reply declines the previous Turn's question (the share of flagged tokens confirmed), not this one.
- `gpt-4-number-tokens` is not grounded ("4" of GPT-4 is in no cited Chunk). It was flaky in the raw run already: grounded in 1 of 3 runs.

So the collapse helps retrieval and, on two questions, costs the answer model. Both new false abstentions are declines with the answer in the Chunks, not retrieval misses. The false-abstention intervals overlap widely ([0.02, 0.23] and [0.06, 0.31]). The choice stays with the retrieval evidence the decision rule was written for.

**The Transcript was asked again, on the collapsed retriever.** These were the committed Transcript's six questions, asked once through the page's endpoints and saved as they came, as 0068 committed its Transcript. It replaces `docs/reports/2026-10-20-chat-transcript.md`. The raw-retriever Transcript is in git history.

## Alternatives considered
- **Keep the raw retriever for the chatbot.** Its false-abstention rate is lower on this set (2/28 against 4/28), but its five Chunks are often two or three copies of one passage. Its Recall@5 is lower (0.41 against 0.48). And the choice in 0065 was made on the Collapsed ranking because the chatbot would use it. Picking the ranking by the answer model's declines would fit the choice to two verdicts.
- **Ask the Transcript until it looks right.** Rejected, as in 0068. The questions were the old Transcript's, so the two can be read side by side, and it was asked once.
- **A new transcript file beside the old one.** Two committed Transcripts from two bots would leave the reader to work out which one the README means.

## Consequences
- The committed Transcript has six Turns. Turn 2's follow-up resolves to CANINE, and its reference reads "2022.tacl-1.5, also 2103.06874v4 and v1". Turn 3's Rewrite fails: "How does the method described in the previous answer compare with how ByT5 handles characters?" names neither model. It retrieves four ByT5 per-language result tables, and the bot abstains. With the raw retriever, the bot gave a wrong answer there. Turn 4 (the near miss `byt5-learning-rate`) and Turn 5 (vitamin D) are Abstentions. Turn 6's answer about SuperBPE is grounded, but in Boundless BPE's description of SuperBPE, not SuperBPE's own Chunk, which it retrieved first and didn't cite.
- Turn 1 shows the CANINE NER result twice, from `2022.tacl-1.5` and `2103.06874v4`: the collapse merges copies only at the same place in the same Section ([0057](0057-the-collapse-merges-copies-not-works.md)), and these two are not at the same place.
- `chat` and `chat-eval` now read the manifest for the Works by default (`data/manifest.csv`). The page tests pass the fixture manifest.
- A rerun of `chat-eval --baseline` against these answers measures a later change against the collapsed bot.
