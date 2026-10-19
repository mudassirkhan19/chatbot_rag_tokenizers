# 0055. Follow-ups: the Conversation and the Rewrite

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0054](0054-pinned-local-answer-model-and-the-chat-page.md) (a Turn after the first is a follow-up).

## Context
Spec #63 asks that a follow-up like "how does that compare with WordPiece?" resolve against the Conversation. The baseline shows why this is a retrieval problem: a follow-up asked alone scores Recall@5 0.00 on BM25 and 0.12 on the dense baseline, and its hand-written reference rewrite scores 0.62 and 0.50. Issue #65 is the slice that adds the Conversation and the Rewrite to the chat page from #64. The spec fixes the shape: the answer model writes the Rewrite on every Turn after the first, from the earlier questions and answer texts and never the Chunks, retrieval sees the Rewrite, and the answer model sees the Rewrite, the Chunks and the earlier Turns.

## Decision
**The page server holds one Conversation.** `chat` keeps a list of Turns. `POST /reset` empties it, and the page posts it when it opens or reloads, so a follow-up is never read against Turns the page no longer shows. A "New conversation" button does the same. Turns are taken one at a time, so each sees the one before.

**The first Turn retrieves its question as asked.** It costs one model call and has no Rewrite. Every later Turn costs two.

**The rewriter is the answer model with its own prompt.** `rewrite_prompt` in `[chat]` asks for the last question rewritten to stand on its own, with every word that points back replaced by what it refers to, the question returned unchanged when it already stands alone, and the reply on one line with nothing else. The user message is the earlier Turns as `Question:` and `Answer:` pairs, then `Follow-up question:`. The questions are as the user asked them, as a reader of the transcript would see them. The reply's first non-empty line, without surrounding quotes, is the Rewrite. An empty reply falls back to the question as asked.

**Earlier answers are shown without their markers.** A marker numbered a Chunk of its own Turn. Left in, `[2]` from Turn 1 would read as this Turn's Chunk 2. The answer's text is its parts without the markers, with the space a marker left before punctuation taken out.

**One window, `history = 3`.** The answer model and the rewriter are shown the last three Turns. The answer model gets the system prompt, then each earlier Turn as a user message (`Question:` and its Rewrite, or its question on a first Turn) and an assistant message (its answer text), then this Turn's Rewrite with its Chunks. Only the last message holds Chunks, so the system prompt is unchanged: rule 1 still says to answer only from the Chunks. Three Turns keep the prompt small for a 5B model and cover a follow-up of a follow-up. `history` must be at least 1.

**A Turn records what the transcript and `chat-eval` need.** The question, the Rewrite (null on the first Turn), the retrieved Chunk ids in rank order, the raw reply, the parsed answer with its Citations, whether it is an Abstention, and the seconds spent rewriting, retrieving and answering. `POST /turn` returns all of it. The page shows the Rewrite under the question as "Searched as:", and the rewriting time beside the others.

## Alternatives considered
- **A separate, smaller rewriter model.** It would cut the follow-up's cost, but would be a second pin to check and pull, and memory at chat time is budgeted for one model. The answer model is already loaded.
- **Rewriting every Turn, the first included.** It would let the rewriter clean up a badly worded first question, but doubles the first Turn's cost for nothing to resolve, and the spec asks that a plain question be retrieved as asked.
- **Showing the rewriter the earlier Chunks.** They would let it name a paper an answer only cited. They are also five Chunks per Turn of text, and the spec asks the rewriter to resolve references as a reader of the transcript would. The answer texts name the paper when the answer did.
- **Retrieving with the question and the Conversation concatenated.** No model call, but the earlier Turns' words pull retrieval back to the earlier topic, and the page would have no standalone question to show.
- **A system prompt that names the earlier Turns.** Adding "Earlier questions and answers of the conversation may come first; use them only to understand what is asked now", and narrowing rule 1 to "the Chunks given with the last question", made the pinned model's reply to a first Turn vary between identical requests: the opt-in test's same-answer-twice check failed in 2 of 3 runs, and passed 4 of 4 with the prompt of 0054. A reproducible answer matters more here than the hint.
- **Separate windows for the rewriter and the answer model.** One setting is simpler to reason about. The spec asks for the answer model's window in the config, and nothing yet argues for the rewriter's being different.
- **The collapse's side table on each Turn.** The spec lists it, but `[chat]` can only name a configured retriever, not a `+collapsed` twin, so no Turn could carry one yet. It comes with the slice that lets `[chat]` name a collapsed twin.

## Consequences
- A follow-up costs a second model call. A smoke run of the rewrite prompt on the pinned model took 0.8 to 2.3 s per Rewrite once the model was loaded. It resolved "How much did that help on MMLU?" to "How much did freezing the non-embedding parameters at the start of training help on MMLU?", "Which of the two is faster?" after CANINE and ByT5 to "Which of the two, CANINE or ByT5, is faster?", and left a standalone off-topic question unchanged. The first rewrite lost the paper's name, WECHSEL, which the earlier answer text named. `evaluate`'s rewriter row (#63) measures how much that costs retrieval.
- The page's Conversation lives in the server, not the browser, so two open tabs share it, and opening a second tab resets it. One Conversation per page session is what the spec asks for.
- The Turn record is the shape the transcript save and `chat-eval` (#63) build on.
