# 0066. The rewriter row of `evaluate`

- **Date:** 2026-10-20
- **Status:** Accepted; amends [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md) (a follow-up is run four ways) and [0056](0056-follow-ups-the-conversation-and-the-rewrite.md) (a Turn with no answer is shown to the rewriter as its question only).

## Context
`evaluate` scores each follow-up three ways: alone (the floor), its history and the follow-up joined, and its hand-written reference rewrite (the ceiling). Spec #63 and issue #66 ask for a fourth, "rewriter": the chatbot's own Rewrite of the stored history and the follow-up, so the rewriter's gain sits in the same table. The row needs the pinned answer model. Without Ollama, `evaluate` must say the row is skipped and write the rest.

An Evaluation-set follow-up stores its history as questions only. The rewriter of ADR 0056 is shown earlier Turns as `Question:` and `Answer:` pairs.

## Decision
**The rewriter is the `[chat]` answer model with its rewrite prompt.** It is shown the last `history` questions of the stored history as earlier Turns with no answers, then the follow-up. A Turn with an empty answer is shown as its `Question:` line only, with no empty `Answer:` line. The chat page's Turns always have answers, so it sends the same messages as before.

**Each follow-up is rewritten once per run, not once per retriever.** `evaluate` checks the model against its pin and writes every Rewrite before scoring. Every retriever and every `+collapsed` twin is then queried with the same Rewrites. The model runs at temperature 0 with a fixed seed. Three runs over the 8 follow-ups gave the same Rewrites.

**Without the model, the row is skipped, not failed.** If the retrieval config has no readable `[chat]` table, or the answer model can't be reached or doesn't match its pin, `evaluate` prints `the rewriter row is skipped: <reason>`. The report says the same under *Metrics*, leaves the row out of every Results table, and writes "None" under *Rewrites*. Every other row and section is unchanged.

**The report prints the Rewrites once.** A *Rewrites* table at the head of *Questions* gives each follow-up, its reference rewrite and its Rewrite. Each retriever's per-question table gives the `rewriter` query its own line, as it does the other three. *Metrics* names the rewriter's model, its settings and the rewrite prompt's sha256.

**The rewriter's queries are left out of *Editions without a Work group*.** The Comparison, Crowding, Before and after, and the all-answerable row already take each follow-up alone. Left in, the rewriter's queries added 22 Editions to the 77 to group, and the list would depend on whether the model answered. The `rewriter` lines' duplicate and restatement counts say `ungrouped` where their top 5 holds such an Edition.

## Alternatives considered
- **Have the answer model answer the stored history first, as `chat-eval` does.** That is `chat-eval`'s measure (spec #63, story 42), and its chat report already gives follow-up Recall@5 over the bot's own Conversations. The spec asks this row to rewrite the stored history, which keeps it free of the answer step's variation and costs 8 model calls, not 16.
- **An empty `Answer:` line after each history question.** It is the format of ADR 0056 unchanged, but it reads as a Turn the bot didn't answer.
- **Rewriting per retriever.** It would be 14 times the calls for the same text.
- **Keeping the row with dashes when the model is missing.** A row of dashes with a question count reads like a measurement. A line saying why the row is missing is clearer.

## Consequences
- On the committed run, the rewriter scores Recall@5 0.25 on the dense baseline (floor 0.12, reference rewrite 0.50), 0.25 on its `+collapsed` twin (0.12, 0.50) and 0.38 on `dense.bge-base+collapsed` (0.12, 0.50). It scores 0.00 on BM25 and on both OpenScholar retrievers. It is below the floor on `hybrid.bm25+bge-base` (0.12 against 0.25) and its twin.
- The *Rewrites* table shows why. With questions only, the model mostly keeps the follow-up's pointing words. "How does it give every possible character an embedding …" after a CANINE question became "How does the model give …". "How much did that help on MMLU?" lost SuperBPE. One Rewrite, wechsel-neighbours, repeats the history question before the follow-up. Only the magikarp follow-up gained the term ("the under-trained tokens") it needed.
- `chat-eval` measures the same rewriter with the bot's answers in the Conversation and gets follow-up Recall@5 0.50 on the dense baseline, against 0.25 here. The earlier answers name the paper when the questions don't. So this row is a lower bound on the rewriter in use, and the gap is the earlier answers' share of the work.
- `evaluate` needs Ollama for a complete report. The 8 Rewrites took 1.7 s with the model already loaded, against minutes of retrieval. A reviewer without Ollama gets every other row.
