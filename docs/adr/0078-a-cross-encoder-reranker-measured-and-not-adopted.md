# 0078. A cross-encoder reranker over bge-small: measured, and not adopted by the chatbot

- **Date:** 2026-10-21
- **Status:** Accepted; amends [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md) (three more twins in `evaluate`) and [0061](0061-the-comparison-paired-bootstrap-against-a-baseline.md) (the baseline a reranked twin is compared with). Corrected the same day: the lead on the chatbot's own queries is within noise, not beyond it (*The chatbot's own queries*).

## Context
[0065](0065-the-embedding-comparison-on-the-raw-ranking.md) chose `dense.bge-small` as the first stage and left a reranker to its own issue, #62: a wrapper over any retriever that over-fetches, scores each (query, Chunk) pair with a cross-encoder and reorders, pinned like the embedders, and scored as `<retriever>+rerank` beside the other twins with its latency. The failure analysis ([report](../reports/2026-10-21-failure-analysis.md)) found that most missed Passages sit in bge-small's top 50, below the top 5. OpenScholar publishes a cross-encoder for this step, and the assignment lists a reranker as optional.

## Decision
**The reranker.** `retrieval/rerank.py`'s `Reranked` wraps a retriever. A query asks the retriever for its top `pool` Chunks (at least k), and the cross-encoder scores the query against each Chunk's context header and text, the text every retriever indexes. The pool is ranked by that score, with ties kept in the raw order. Any Chunks past the pool follow in the raw order with their raw scores, so only the order is comparable across the boundary. The scorer is a boundary like the embedder ([0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md)): the tests use a word-overlap fake, and the real one shares the embedder's pinned-model loader.

**The model.** [`OpenSciLM/OpenScholar_Reranker`](https://huggingface.co/OpenSciLM/OpenScholar_Reranker) (the repo formerly at `OpenScholar/`) is BAAI/bge-reranker-large, an XLM-RoBERTa large sequence classifier with 560M parameters, fine-tuned for OpenScholar on scientific passages with synthetic queries. OpenScholar uses it the same way, to rerank its first stage's passages, with the passage's title in front of its text. Ours gets the context header, which starts with the title. The `[rerank]` table of `config/retrieval.toml` pins the model like a dense table: revision `f371d9d9…` and the sha256 of `model.safetensors`. A mismatch stops `evaluate`, and so does a checkpoint that doesn't fill the network or gives more than one logit. The score is that one logit, in float32. A pair over `max_tokens = 512` has its Chunk cut. In the full run that happened to 2 of the 50 Chunks for 6 queries, and the reranker says so on stderr. CPU and MPS give the same scores to three decimals on a smoke test. The tokenizer is a SentencePiece model with no `tokenizer.json`, so `sentencepiece` and `protobuf` are now project dependencies.

**Where it sits.** `[rerank] retrievers` names the retrievers to rerank: `dense.bge-small`, the chosen first stage, with `pool = 50`. Each of them gets three more twins: `+rerank`, `+rerank+collapsed` and `+rerank+per-paper+collapsed`. The issue asked only for the first; the other two are there because the chatbot retrieves per paper and collapsed ([0076](0076-retrieve-once-for-each-paper-a-question-names.md)). The reranker is the innermost wrapper, so the Collapsed ranking merges copies in the reranked pool. Per-paper retrieval splits the reranked ranking, so a named paper's Chunks past the top 50 keep their raw order. One cross-encoder is loaded for all three twins, and only when a retriever it reranks is scored.

**The Comparison.** A reranked twin is set against the baseline's same ranking without the reranker: `+rerank` against `dense.bge-small`, `+rerank+collapsed` against `+collapsed`, and `+rerank+per-paper+collapsed` against `+per-paper+collapsed`. That way the difference is the reranker's alone. Every other row is compared as before.

**The numbers**, from the committed eval report (`data/eval/eval-report.md`). The run was the full corpus, 141,348 Chunks, and the 36-question Evaluation set. It gives 28 answerable questions as a user asks them, with paired 95% bootstrap intervals (10,000 resamples, seed 55). Every figure of the report it replaces is unchanged but the latencies; the new twins add rows, and columns in the first-hit tables.

| Ranking | Without | With the reranker | Difference [95%] | W/T/L | MRR@10 without → with | MRR difference [95%] |
|---|---:|---:|---|---|---|---|
| raw | 0.30 | 0.46 | **+0.16 [+0.05, +0.29], beyond noise** | 6/22/0 | 0.244 → 0.360 | +0.115 [−0.013, +0.257] |
| collapsed | 0.38 | 0.48 | **+0.10 [+0.02, +0.20], beyond noise** | 5/23/0 | 0.276 → 0.387 | +0.111 [−0.005, +0.233] |
| per paper, collapsed (the chatbot's) | 0.43 | 0.48 | +0.05 [−0.03, +0.14], within noise | 3/24/1 | 0.329 → 0.421 | +0.092 [−0.023, +0.217] |

All the Recall@5 figures are *all answerable*. By question type, on the chatbot's ranking, Recall@5 goes from 0.75 to 0.83 on single-paper questions and from 0.25 to 0.29 on multi-paper ones. The follow-ups move differently depending on the query:

- alone: 0.12, unchanged;
- with their history: 0.12 to 0.50;
- as the reference rewrite: 0.50 to 0.75;
- as the rewriter's Rewrite: 0.25 to 0.62.

The *all answerable* row scores a follow-up alone, and a pronoun with nothing to point to gives the cross-encoder nothing to rank on. On the chatbot's ranking the reranker loses one question: `megabyte-and-blt-patches`, whose first hit drops from rank 4 to rank 10, so neither of its two Passages is in the top 5. Why the reranked order within its papers' streams drops it is not measured.

**Cost**, from the Cost table on an M1 Max with MPS: parameters go from 33.4M to 593.3M, with the same index on disk and no build time, since the reranker indexes nothing. The p50 query time goes from 28 ms to 2.43 s raw, and from 42 ms to 2.87 s on the chatbot's ranking (p95 3.30 s). That is the 50 pairs at up to 512 tokens.

**The rule, applied as #55 fixed it** ([0065](0065-the-embedding-comparison-on-the-raw-ranking.md)): recommend the best *all answerable* Recall@5, unless its lead over a cheaper retriever is within noise. On the raw and Collapsed rankings the reranker leads beyond noise. On the ranking the chatbot uses, `dense.bge-small+rerank+per-paper+collapsed` leads `dense.bge-small+per-paper+collapsed` by +0.05, within noise. The cheaper ranking is about 70 times faster, so **the chatbot keeps `dense.bge-small+per-paper+collapsed`**. Per-paper retrieval already recovers most of what the reranker adds on that row. `[chat]` is unchanged, and the chat numbers of [0077](0077-the-final-chat-run-after-the-text-collapse-the-rewrite-and-per-paper-retrieval.md) still describe the chatbot.

**The chatbot's own queries, measured after the decision.** The chatbot doesn't send a follow-up alone; it sends the rewriter's Rewrite, made with the earlier Turns' answers in its history. A first version of this record took the follow-ups from `evaluate`'s rewriter row instead and reported a lead beyond noise, +0.16 [+0.03, +0.30]. That row's Rewrites are made from the earlier questions alone (0067). Given only questions, the rewriter pasted the previous question in front of the follow-up on 3 of the 8 (wechsel-neighbours, digits-fourth-digit, tokenization-latency), and two questions in one bge-small vector rank the Passage low. The reranker rescued those, and the chatbot never sends them.

[`chat_ranking.py`](../reports/2026-10-21-reranker-follow-ups/chat_ranking.py) scores the committed chat run's Rewrites, which hold no pasted question in any of the 3 runs, on the chatbot's ranking with and without the reranker. Without it, the script reproduces that run's results on every follow-up. The follow-ups stay at Recall@5 0.50 with the reranker. It gains superbpe-mmlu and loses tokenization-latency, whose Passage falls from rank 1 to 11 in [`ranks.py`](../reports/2026-10-21-reranker-follow-ups/ranks.py).

Over the 28 queries the chatbot sends (questions as asked, follow-ups as the chat run's Rewrite), Recall@5 goes from 0.54 to 0.58, **+0.05 [−0.08, +0.19], within noise** (4/22/2), with the same draws. So both rows agree, and the decision stands. The reranker helps the questions the first stage ranks right but low; on follow-ups the rewriter given the answers already does most of that. #89 had asked to adopt the reranker on the first figure; it is answered by this paragraph.

## Alternatives considered
- **Adopt it on the chatbot's own queries.** That row was chosen after the run, and, measured on the Rewrites the chatbot makes, it is within noise too. A Turn would also slow from under a second of retrieval to about 3 s.
- **Rerank every retriever.** The issue asks for the reranker over the chosen first stage, and each reranked retriever adds about 3 s per query for 180 queries. `[rerank] retrievers` takes more names when they are wanted.
- **bge-reranker-large itself, or a smaller cross-encoder** (bge-reranker-base, MiniLM). OpenScholar's model is the one fine-tuned on scientific passages, and the issue names it. The baseline reranker would be the size-and-domain control, as bge-base was for the embedders. Not run.
- **float16 on MPS**, as OpenScholar runs it through FlagEmbedding. It would be about twice as fast but change the scores; float32 keeps the pin's numbers exact. Worth timing only if the reranker is adopted.
- **A reranker score for the Chunks past the pool**, so the whole ranking sorts by one score. Nothing reads the scores past the pool, and scoring all of them is the cost the pool exists to avoid.

## Consequences
- `evaluate` loads a 2.2 GB model on its first run (downloaded into the Hugging Face cache) and takes about 8 minutes more on an M1 Max for the three reranked twins (180 queries at 2.4 to 2.9 s; the whole run took 14 minutes). A config with `[rerank] retrievers = []` skips them.
- The reranker brings Editions into the top 5 that no Work group covers: 112 Editions are ungrouped, against 85 before. The reranked twins' duplicate counts therefore rest on fewer questions: 18 of 28 raw, 14 collapsed, 15 per paper and collapsed. The report says so per twin. Grouping those Editions by hand ([0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md)) would complete them. The rule reads only Recall@5.
- `chat/config.py` doesn't accept a `+rerank` name in `[chat]`.
- `evaluate`'s rewriter row understates the chatbot's Rewrite: from questions only it pastes earlier questions, which the chat run with answers never did. The row reads 0.25 on the chatbot's ranking where the chat run's Rewrites reach 0.50, as [0073](0073-the-rewrite-names-the-paper-the-conversation-is-about.md) found. A reranked twin's rewriter row gains most from that artefact.
