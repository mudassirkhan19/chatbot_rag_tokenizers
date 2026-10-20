# 0076. Retrieve once for each paper a question names

- **Date:** 2026-10-21
- **Status:** Accepted; amends [0070](0070-the-chatbot-retrieves-collapsed-and-the-final-chat-numbers.md) (the chatbot's retriever) and [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md) (a third twin in `evaluate`).

## Context
The diagnosis of #77 ([report](../reports/2026-10-21-chat-failure-diagnosis.md), kind 2) found that a question naming two papers reaches the embedder as one query, and the query lands on whichever paper restates both. In megabyte-and-blt-patches, MEGABYTE's Introduction ranks 8th on the Collapsed ranking, and BLT's Abstract isn't in the top 50. compression-and-accuracy never retrieves "Tokenization Is More Than Compression", though both its Editions are indexed. With the paper's title in front of the query, its Passage ranks 1st or 2nd, so the Chunks are fine. On the committed eval report, the chat retriever `dense.bge-small+collapsed` has a Recall@5 of 0.06 on the 8 multi-paper questions, against 0.75 on the single-paper ones.

Issue #81 asks for two ideas to be tried: (a) retrieve once for each paper or method a question names, then merge the slots; (b) a hybrid or BM25 weighting that matches the name. It asks for Recall@5 on the multi-paper questions before and after, with the overall Recall@5 not dropping.

## Decision
**Per-paper retrieval, on the chatbot's retriever as it is.** `[chat]` names `dense.bge-small+per-paper+collapsed`. The retriever stays bge-small (ADR 0065), and the Collapsed ranking (0070) wraps the per-paper one. Each Turn (on a follow-up, its Rewrite) is handled in four steps:

1. **The names.** The answer model gets `names_prompt` from `[chat]` and the query alone. It replies with the papers, methods and models the query names, one per line, or NONE (`chat/names.py`). A line is read without a list marker or quotes. It is kept only if the query holds it, in any case.
2. **The Works.** Each name is looked up among the Works of the indexed Chunks (`retrieval/per_paper.py`, `NamedWorks`). "<Surname> et al. …" could be any Work whose Edition's first author has that surname. Any other name could be any Work whose Edition's title holds all its words, as BM25 tokenises them, with a possessive "'s" dropped. A name no Work matches is dropped. Two names that find the same Works count once.
3. **The turns.** When two or more names are left, the retriever's whole ranking for the query is split by name: each name's stream holds the Chunks of its Works in the raw order. The streams take turns at the slots, in the order the names were given, each Chunk once. A query naming fewer than two is ranked as it is.
4. **The collapse.** The Collapsed ranking then merges copies in the top `pool` of that ranking, as for any retriever.

The answers file records `per_paper` and the names prompt's sha256, so answers retrieved another way aren't re-scored as these. The chat report gives the names prompt's hash.

**Why (a), and not (b) alone, or both.** `evaluate` now scores every retriever a third way, as a `+per-paper+collapsed` twin. The names are asked once per query, and the report lists them in a *Names* table. On the committed eval report (28 answerable questions as a user asks them, 8 of them multi-paper):

| Retriever | Multi-paper Recall@5, collapsed | Per paper | All answerable Recall@5, collapsed | Per paper | Per paper vs `dense.bge-small+collapsed` |
|---|---:|---:|---:|---:|---|
| **dense.bge-small** (the chatbot's) | **0.06** | **0.25** | **0.38** | **0.43** | **+0.05 [+0.00, +0.11]**, 3 wins, 0 losses |
| hybrid.bm25+bge-small, idea (b) | 0.10 | 0.29 | 0.39 | 0.44 | +0.07 [−0.10, +0.23], 7 wins, 3 losses |
| bm25 | 0.10 | 0.23 | 0.21 | 0.24 | −0.13 [−0.34, +0.07] |
| dense.bge-base | 0.00 | 0.12 | 0.32 | 0.36 | −0.02 [−0.16, +0.11] |
| dense.openscholar | 0.04 | 0.10 | 0.12 | 0.14 | −0.24 [−0.45, −0.04] |
| hybrid.bm25+bge-base | 0.10 | 0.17 | 0.35 | 0.37 | −0.01 [−0.18, +0.16] |
| hybrid.bm25+openscholar | 0.10 | 0.23 | 0.32 | 0.35 | −0.02 [−0.22, +0.17] |

Per-paper retrieval raises multi-paper Recall@5 for every retriever, and the overall Recall@5 drops for none. On the chatbot's retriever it loses no question and wins 3: tokenizer-swap-budget (Dagan et al.'s Passage, now 1st), megabyte-and-blt-patches (MEGABYTE's Introduction, now 4th) and renyi-efficiency (the Tokenization Is More Than Compression Passage, now 2nd). The paired interval runs from +0.00 to +0.11, so the gain sits at the edge of the noise on 28 questions, and on MRR@10 too (+0.054 [−0.004, +0.143]).

Idea (b), the hybrid on its own, is 0.10 on multi-paper against bge-small's 0.06. It finds a Passage in bpe-and-wechsel-vocabularies and one-sided-regularization, where BM25 matches "WECHSEL" and "BPE-dropout", and loses the one bge-small finds in api-cost-by-language. With per-paper retrieval on top, the hybrid finds a Passage in 5 multi-paper questions, against bge-small's 4: the same two gains and the same loss. On all answerable questions it is 0.44 against 0.43, within noise of bge-small (and of bge-small per paper). ADR 0065 keeps bge-small unless a retriever beats it beyond noise, and the hybrid queries in about eight times bge-small's time. So the chatbot keeps bge-small, and per-paper retrieval is the change. The hybrid also ranks only its members' top 100 each, so a named paper's Chunks outside them are not reached.

**Prototypes before the design.** The scripts that chose it are not committed. Their numbers were on the same Evaluation set and the chat retriever, with the same Collapsed ranking:
- **Splitting the question into sub-questions** (one per paper, written by the answer model) dropped multi-paper Recall@5 to 0.00 and the overall to 0.32. The sub-questions lost the context the question shared ("In Sennrich et al.'s subword NMT paper…" became a question without the paper), and the 2B model also split questions that name one paper.
- **Names found by BM25 over the titles**, keeping each name's best Work, sent four names to the wrong Work: "Dagan et al.'s code study" to an Arabic paper, "Byte Latent Transformer" to *Fast* Byte Latent Transformer alone. That gave 0.19 on multi-paper. Matching all of a name's title words, or the first author for "et al.", and keeping every Work that matches, gave the 0.25 above.
- **Without the check that the question holds the name**, the 2B model invented papers and methods for questions that name none ("Attention Is All You Need", or a list of BPE, WordPiece and SentencePiece), which split single-paper questions. With these names, the overall Recall@5 dropped to 0.29.
- **The title in front of each name's query, or a third stream with the question's own ranking**, each scored below the turns alone in the same setup, on multi-paper and overall.

## Alternatives considered
- **Idea (b) alone: the hybrid as the chatbot's retriever.** Measured above: one more multi-paper Passage than bge-small, within noise overall, at about eight times the latency. Not adopted.
- **The hybrid with per-paper retrieval.** It finds a Passage in one more multi-paper question than bge-small per paper, and the difference between them is within noise overall. Not adopted, for the reasons of 0065. Its row in the eval report keeps it measured.
- **Weighting a name's tokens in BM25.** Not tried: the hybrid already gives BM25's match of a name a full vote, and gained one Passage.
- **Sub-questions, BM25 over titles, the title in front of the query** (the prototypes above). Each scored below the turns.

## Consequences
- Each Turn costs one more call to the answer model. On the 36 questions of the Evaluation set it took 0.15 s at the median, 1.0 s at most, before retrieval. A model that can't answer it fails the Turn, as the rewriter does.
- The name lister is now the limit. The 2B model misses names in 2 of the 8 multi-paper questions. In bpe-and-wechsel-vocabularies it lists only "BPE-dropout", which the question doesn't hold. In one-sided-regularization it folds both methods into one long phrase each. Two name no paper (api-cost-by-language, and gpt-4-number-tokens, which names GPT-4's tokenizer), and compression-and-accuracy names both its papers but finds no Passage: Tokenization Is More Than Compression's Passage ranks 107th of that Work's 296 Chunks for the question. A lookup by title words can also find too much: "BPE-dropout" finds two other Works whose titles hold both words. A name of one paper alone does nothing, so that costs nothing on a single-paper question. "Scaling Laws for Vocabulary Size" finds the wrong Work, but alone.
- The eval report has a third twin for every retriever: 21 Results, Crowding and Questions sections instead of 14, a third row in *Before and after* and in the Comparison, and a *Names* table under Questions. Without the `[chat]` table or the answer model, `evaluate` says the per-paper twins are skipped, and the rest of the report is unchanged. The existing raw and collapsed rows are unchanged on the committed report.
- Two runs of the names, at temperature 0, gave the same names and the same Recall@5: a prototype run, and the `evaluate` run of the committed report.
- The chat run isn't regenerated here (#81's coordination note). The committed answers were asked without per-paper retrieval, so `chat-eval --from-answers` refuses them until #86 re-runs `chat-eval` on the merged main.
