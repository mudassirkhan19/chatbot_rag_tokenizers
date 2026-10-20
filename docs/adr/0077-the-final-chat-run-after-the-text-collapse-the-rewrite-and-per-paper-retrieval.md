# 0077. The final chat run after the text collapse, the Rewrite and per-paper retrieval

- **Date:** 2026-10-21
- **Status:** Accepted; amends [0070](0070-the-chatbot-retrieves-collapsed-and-the-final-chat-numbers.md) (its final chat numbers and its committed Transcript) and [0064](0064-a-decline-in-the-models-own-words-is-an-abstention.md) (one more decline phrase).

## Context
#77's diagnosis planned three fixes: the collapse matches copies by their text (#80, [0074](0074-the-collapse-matches-copies-by-their-text.md)), the Rewrite names the paper the Conversation is about (#82, [0073](0073-the-rewrite-names-the-paper-the-conversation-is-about.md)), and the chatbot retrieves once for each paper a question names (#81, [0076](0076-retrieve-once-for-each-paper-a-question-names.md)). Each measured its change in its own branch and left the committed chat run alone. So the chat report, the answers, the runs file and the Transcript still described 0070's bot on `dense.bge-small+collapsed`. Issue #86 asks for one run on the merged main, with the old numbers kept for comparison.

## Decision
**The reports come from one run on the merged main.** `[chat]` names `dense.bge-small+per-paper+collapsed`, with the pool of 50 and the overlap of 0.4. `evaluate` was rerun; only the Cost table's latencies changed. Then `chat-eval --runs 3 --baseline data/eval/chat-answers.jsonl --judge`, with 0070's answers (`git show 301e28f:data/eval/chat-answers.jsonl`) as the baseline. From the chat report, with 95% Wilson intervals:

| | 0070 (`dense.bge-small+collapsed`) | Now (`dense.bge-small+per-paper+collapsed`) |
|---|---:|---:|
| Abstention rate, unanswerable | 7/8 (0.88 [0.53, 0.98]) | 7/8 (0.88 [0.53, 0.98]) |
| near-miss / out-of-topic | 5/6 / 2/2 | 5/6 / 2/2 |
| False-abstention rate, answerable | 4/28 (0.14 [0.06, 0.31]) | 2/28 (0.07 [0.02, 0.23]) |
| Grounded rate, every answer | 24/25 (0.96 [0.80, 0.99]) | 25/27 (0.93 [0.77, 0.98]) |
| Recall@5, answerable | 0.48 | 0.54 |
| Recall@5, single-paper | 0.75 | 0.75 |
| Recall@5, multi-paper | 0.06 | 0.25 |
| Recall@5, follow-up | 0.50 | 0.50 |
| Near-duplicate Turns (#77's `dups.py`) | 15/44 | 2/44 |
| Hand check agrees with the automatic verdict | 16/19 (0.84 [0.62, 0.94]) | 16/19 (0.84 [0.62, 0.94]) |

The three runs agree on every verdict and rate, Recall@5 included. 5 of the 44 replies changed wording from run 1, and no Turn's Chunks changed. The hand check and Tev1 ([0075](0075-tev1-as-a-grounding-judge-measured-against-the-hand-labels.md)) both still agree on 16 of 19: #84 scores the sample as stored, so a new run can't move it. The two near-duplicate Turns left are the boundary shifts 0074 names (tokenization-latency, byt5-learning-rate).

**What moved Recall@5.** Four questions gained a Passage, and one lost its only one:
- tokenizer-swap-budget, megabyte-and-blt-patches and renyi-efficiency gained theirs from per-paper retrieval, the three wins 0076 measured in `evaluate`.
- wechsel-neighbours gained its Passage because the Rewrite now ends "in the WECHSEL method" (0073).
- magikarp-norm-indicator lost its Passage. Its Rewrite now ends "in Fishing for Magikarp", and the five Chunks it retrieves are other passages. It abstains, as it did in 0070, now with nothing in its Chunks to answer from.

So follow-up Recall@5 stays at 0.50, and the gain on all answerable questions (0.48 to 0.54) is the multi-paper one.

**Verdicts that changed against the baseline.** The report's *Against the baseline* lists three:
- `one-sided-regularization`, multi-paper: abstained, now a grounded answer. It cites the same reworded § 5.2 of BPE-dropout's ACL Edition that 0070 found at rank 2, now at rank 5: "For large datasets, BPE-dropout should be used only on the source side." It answers only the BPE-dropout half, and the Passage matcher still finds none of the question's Passages (0/3).
- `superbpe-mmlu`, follow-up: abstained, now grounded, and wrong. The Rewrite now names SuperBPE ("How much did SuperBPE help on MMLU?"), where 0070's said "the two-pass tokenization strategy". It retrieves three of SuperBPE's Chunks, its results among them, but not the Introduction's "+8.2% on MMLU". The reply cites another paper's summary of SuperBPE (`2026.mellm-1.27`) and gives the 20.3-point gain on CommonsenseQA instead. The check passes it, since the number is in the cited Chunk. A grounded answer to another benchmark is a worse failure than 0070's decline.
- `canine-hashing`, follow-up: grounded, now not grounded. Same Rewrite, same five Chunks, and the reply states CANINE's multiple hashing correctly. But it has no marker, in all three runs, so it is uncited. Its history Turn now retrieves one copy of the NER result where it had two (0074), so the history's reply changed, and the answer model drops the markers on what follows.

So the false abstentions fall from 4 to 2 (llama2-70b-vocabulary and magikarp-norm-indicator, neither with a Passage in its Chunks). The grounded rate falls by one answer, and the intervals overlap widely. The gpt-4-number-tokens answer is still not grounded, for the "4" of GPT-4, and the near miss sentencepiece-korean-speed is still answered.

**One more decline phrase: "The papers do not answer this question."** In the first run, magikarp-norm-indicator's reply was the fixed sentence without "in this corpus". The decline pattern lacked "papers" and "answer", so the reply counted as an uncited, ungrounded answer. 0064 foresaw this: one more alternative in `_DECLINE`. The subject may now be "papers", and the verb "answer". Re-scored with the new rule, every stored reply in 0070's answers and runs and in this run kept its verdict, except that Turn in all three runs. The committed run is a second `chat-eval` with the rule in place, from the same baseline. Its verdicts are the first run's, apart from that Turn. Between the two processes, about ten replies changed wording, and one follow-up's Chunks changed order.

**The Transcript was asked again.** The committed Transcript's six questions were asked once through the page's endpoints, in one Conversation, and saved as they came, as 0068 and 0070 did. It was saved between the two `chat-eval` runs, before the decline phrase above was added. No Turn of it is affected: its two Abstentions open "The provided chunks do not contain", and its answers cite Chunks. It was not asked again, since 0068 asks a Transcript once. `docs/reports/2026-10-21-chat-transcript.md` replaces `2026-10-20-chat-transcript.md`; the old one is in git history. Turn by Turn:
1. CANINE's 50 F1 on Amharic NER is now one reference, "2022.tacl-1.5, also 2103.06874v4", where 0070's Transcript showed it twice.
2. "it" resolves to CANINE, and the answer cites CANINE's § 3.1, as before.
3. The Rewrite names both models now, if clumsily: "How does the comparison between CANINE's character handling and ByT5's character handling compare?" Neither model's own paper is retrieved. Two of its Chunks are from "Are Character-level Translations Worth the Wait? Comparing ByT5 and mT5", whose title holds "ByT5". The answer, a grounded one where 0070's bot abstained, cites "A Multi-dimensional Evaluation of Tokenizer-free Multilingual Pretrained Models", whose § 2 describes both: CANINE reads characters, ByT5 reads UTF-8 bytes.
4. The near miss `byt5-learning-rate` is an Abstention. ByT5's § 6.4 is retrieved twice, from the TACL and the arXiv Edition: one of the two near-duplicate pairs left.
5. Vitamin D is an Abstention.
6. SuperBPE's two-pass training is answered and grounded, but from Boundless BPE's description of it, as in 0070. SuperBPE's own Chunks are retrieved first and fifth and not cited.

## Alternatives considered
- **Commit the first run, with magikarp-norm-indicator scored as an answer.** The reply is a decline, by any reading. Counting it as an ungrounded answer would put a decline into the grounded rate (25/28) and take it out of the false-abstention rate (1/28), the error 0064 was written to remove.
- **Re-score the first run with `--from-answers` instead of asking again.** It would give the same verdicts, but a re-scored report has no timings, and #86 asks for one run with all its parts.
- **Leave the decline rule alone and file it.** It is the one-line change 0064 describes, and it changes no other stored verdict.

## Consequences
- The README's *The final chat numbers*, its Transcript paragraph and the domain page quote these numbers, with 0070's beside them.
- The Turn timings vary by about twice between processes on one machine. The committed run gives 0.75 s at p50 and 1.43 s at p95 for a whole Turn, and the first run 1.77 s and 2.64 s. The report says they depend on the machine, and 0070's run gave 1.58 s and 2.31 s.
- The failure analysis (#78) works from these answers. Two failures here are new kinds that the check can't see: superbpe-mmlu answers another benchmark than the one asked about, and canine-hashing answers right without citing.
- `chat-eval --from-answers` now re-scores the committed answers, which were asked with per-paper retrieval.
