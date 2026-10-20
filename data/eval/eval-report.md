# Eval report

Written by `evaluate`. Each retriever ranks the Chunks for every question of the Evaluation set, and the raw ranking and its Collapsed ranking (`<retriever>+collapsed`, each passage once across a Work's files) are scored against the question's Passages.

## Evaluation set

- File: `data/eval/evaluation-set.jsonl`
- sha256: `19bd5da54270b0c4998294ca275394ea9bc2f70ffd2443f3fda489057d44c5b7`
- Questions: 36 (12 single-paper, 8 multi-paper, 8 follow-up, 8 unanswerable)

## Chunks

- Parser: `grobid-0.9.1-crf-223957791ac2`
- Chunking config: `chunking-215005ae4889`
  - token_budget: `350`
  - tokenizer: `google-bert/bert-base-uncased`
  - tokenizer_revision: `86b5e0934494bd15c9632b12f734a8a67f723594`
  - tokenizer_sha256: `ce64fce797c24f68df90b40a3f74f579b336a493db14bd583fd520ea0d8c9a98`
  - min_sections: `2`
  - min_body_characters: `2000`
- Files: 2689
- Chunks: 141348

## Retrievers

- bm25: `bm25-abfdc4a74910`
  - k1: `1.2`
  - b: `0.75`
  - tokens: `lower-cased letter and digit runs, decimals whole, no stemming, no stop words`
- bm25+collapsed: bm25's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- dense.bge-small: `dense-784e5a0da1b5`
  - model: `BAAI/bge-small-en-v1.5`
  - revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
  - model_sha256: `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`
  - query_instruction: `Represent this sentence for searching relevant passages: `
  - pooling: `[CLS] vector of the last layer, L2-normalised`
  - max_tokens: `512`
  - search: `exact dot product over every Chunk's float32 vector`
- dense.bge-small+collapsed: dense.bge-small's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- dense.bge-base: `dense-7fa306867c3e`
  - model: `BAAI/bge-base-en-v1.5`
  - revision: `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a`
  - model_sha256: `c7c1988aae201f80cf91a5dbbd5866409503b89dcaba877ca6dba7dd0a5167d7`
  - query_instruction: `Represent this sentence for searching relevant passages: `
  - pooling: `[CLS] vector of the last layer, L2-normalised`
  - max_tokens: `512`
  - search: `exact dot product over every Chunk's float32 vector`
- dense.bge-base+collapsed: dense.bge-base's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- dense.openscholar: `dense-93a6ab523c22`
  - model: `OpenScholar/OpenScholar_Retriever`
  - revision: `ef4f3120d33b3ca57e12fce2b369f5982a7bb929`
  - model_sha256: `fb5226976e362e070ad5b3f6c5bd38ed03a770b7d349b9334e4db8d61cc5f8fa`
  - query_instruction: ``
  - pooling: `mean of the last layer over non-padding tokens, L2-normalised`
  - max_tokens: `512`
  - search: `exact dot product over every Chunk's float32 vector`
- dense.openscholar+collapsed: dense.openscholar's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- hybrid.bm25+bge-small: `hybrid-01e5a9f225b9`
  - members: `bm25 (bm25-abfdc4a74910), dense.bge-small (dense-784e5a0da1b5)`
  - k: `60`
  - pool: `100`
  - fusion: `reciprocal rank fusion: the sum of 1 / (k + rank) over the members, ties to the member listed first`
- hybrid.bm25+bge-small+collapsed: hybrid.bm25+bge-small's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- hybrid.bm25+bge-base: `hybrid-38deefeb5f83`
  - members: `bm25 (bm25-abfdc4a74910), dense.bge-base (dense-7fa306867c3e)`
  - k: `60`
  - pool: `100`
  - fusion: `reciprocal rank fusion: the sum of 1 / (k + rank) over the members, ties to the member listed first`
- hybrid.bm25+bge-base+collapsed: hybrid.bm25+bge-base's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- hybrid.bm25+openscholar: `hybrid-954860d0d8b2`
  - members: `bm25 (bm25-abfdc4a74910), dense.openscholar (dense-93a6ab523c22)`
  - k: `60`
  - pool: `100`
  - fusion: `reciprocal rank fusion: the sum of 1 / (k + rank) over the members, ties to the member listed first`
- hybrid.bm25+openscholar+collapsed: hybrid.bm25+openscholar's index, with copies from other files of a Work merged
  - pool: `50`
  - overlap: `0.4`
- The chatbot's retriever, from `[chat]`: dense.bge-small+collapsed, 5 Chunks per Turn

## Metrics

- Recall@5: the share of a question's Passages held by a Chunk in the top 5, averaged over questions.
- MRR@10: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top 10.
- Hit@5: the share of questions with a Passage held by a Chunk in the top 5.
- A Chunk holds a Passage when, after unicode, case, whitespace and hyphenation are normalised and citations dropped, at least 65% of the quote's words match the Chunk's in order, in blocks of at least 2 words (a number may match alone) within twice the quote's length, and every number in the quote matches (ADR 0041). A match running into the Chunk's first or last word counts only the quote's words on the Chunk's side, and must cover at least 6 words. The Chunk may come from any Edition.
- A retriever's own ranking is scored raw: duplicates of one Work all take their slots.
- Its `+collapsed` twin is scored on the Collapsed ranking (ADRs 0053, 0057 and 0074) over the same index: from the raw top *pool* Chunks, with Works from the manifest's work_id (an Edition with none is its own Work), in the raw order, it merges copies: the Chunks of a Work from different files that share at least *overlap* of their word 5-grams, counted on the smaller Chunk's, where one is the other's closest Chunk in its file (another Version's or Edition's copy of the passage, wherever its file puts it), into the slot of the best-ranked one, shown from the Canonical Edition's file when the pool holds a copy from it, else from an Edition's latest file, else as ranked. A Work's other Chunks keep their slots. Surveys are not demoted.
- Unanswerable questions are run but left out of the metrics.
- A follow-up is run four ways: follow-up alone, history + follow-up (its prior turns, then the follow-up, joined by spaces), reference rewrite and rewriter, the chatbot's Rewrite: the answer model, given the `[chat]` rewrite prompt, the last `history` prior turns as earlier questions with no answers, and the follow-up (ADR 0067). The *all answerable* row takes each follow-up alone, as a user would ask it.
- Rewriter: gemma4:e2b-mlx@e98b54fe1913 on Ollama 0.40.5, thinking off, temperature 0.0, rewrite prompt sha256 `667083844bf2a3deeb25ed76510b41f884d360d9767a39e098829b30c6c1dfab`

## Results

### Results: bm25

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.33 | 0.173 | 0.33 |
| multi-paper | as asked | 8 | 0.06 | 0.153 | 0.12 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | reference rewrite | 8 | 0.62 | 0.583 | 0.62 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.16 | 0.118 | 0.18 |
| unanswerable | left out | 8 | — | — | — |

### Results: bm25+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.42 | 0.197 | 0.42 |
| multi-paper | as asked | 8 | 0.10 | 0.171 | 0.25 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | reference rewrite | 8 | 0.75 | 0.617 | 0.75 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.21 | 0.133 | 0.25 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.bge-small

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.462 | 0.58 |
| multi-paper | as asked | 8 | 0.06 | 0.038 | 0.12 |
| follow-up | follow-up alone | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | history + follow-up | 8 | 0.12 | 0.031 | 0.12 |
| follow-up | reference rewrite | 8 | 0.50 | 0.400 | 0.50 |
| follow-up | rewriter | 8 | 0.25 | 0.250 | 0.25 |
| all answerable | as asked, follow-ups alone | 28 | 0.30 | 0.244 | 0.32 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.bge-small+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.75 | 0.514 | 0.75 |
| multi-paper | as asked | 8 | 0.06 | 0.069 | 0.12 |
| follow-up | follow-up alone | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | history + follow-up | 8 | 0.12 | 0.063 | 0.12 |
| follow-up | reference rewrite | 8 | 0.50 | 0.370 | 0.50 |
| follow-up | rewriter | 8 | 0.25 | 0.268 | 0.25 |
| all answerable | as asked, follow-ups alone | 28 | 0.38 | 0.276 | 0.39 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.bge-base

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.399 | 0.58 |
| multi-paper | as asked | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | follow-up alone | 8 | 0.12 | 0.141 | 0.12 |
| follow-up | history + follow-up | 8 | 0.00 | 0.021 | 0.00 |
| follow-up | reference rewrite | 8 | 0.38 | 0.411 | 0.38 |
| follow-up | rewriter | 8 | 0.12 | 0.167 | 0.12 |
| all answerable | as asked, follow-ups alone | 28 | 0.29 | 0.211 | 0.29 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.bge-base+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.67 | 0.503 | 0.67 |
| multi-paper | as asked | 8 | 0.00 | 0.016 | 0.00 |
| follow-up | follow-up alone | 8 | 0.12 | 0.143 | 0.12 |
| follow-up | history + follow-up | 8 | 0.00 | 0.042 | 0.00 |
| follow-up | reference rewrite | 8 | 0.62 | 0.369 | 0.62 |
| follow-up | rewriter | 8 | 0.38 | 0.202 | 0.38 |
| all answerable | as asked, follow-ups alone | 28 | 0.32 | 0.261 | 0.32 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.openscholar

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.17 | 0.093 | 0.17 |
| multi-paper | as asked | 8 | 0.00 | 0.021 | 0.00 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.12 | 0.062 | 0.12 |
| follow-up | reference rewrite | 8 | 0.12 | 0.042 | 0.12 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.07 | 0.046 | 0.07 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense.openscholar+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.25 | 0.126 | 0.25 |
| multi-paper | as asked | 8 | 0.04 | 0.056 | 0.12 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | reference rewrite | 8 | 0.12 | 0.080 | 0.12 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.12 | 0.070 | 0.14 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+bge-small

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.67 | 0.454 | 0.67 |
| multi-paper | as asked | 8 | 0.06 | 0.094 | 0.12 |
| follow-up | follow-up alone | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | history + follow-up | 8 | 0.12 | 0.025 | 0.12 |
| follow-up | reference rewrite | 8 | 0.62 | 0.493 | 0.62 |
| follow-up | rewriter | 8 | 0.12 | 0.062 | 0.12 |
| all answerable | as asked, follow-ups alone | 28 | 0.34 | 0.257 | 0.36 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+bge-small+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.75 | 0.490 | 0.75 |
| multi-paper | as asked | 8 | 0.10 | 0.125 | 0.25 |
| follow-up | follow-up alone | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | history + follow-up | 8 | 0.25 | 0.100 | 0.25 |
| follow-up | reference rewrite | 8 | 0.88 | 0.479 | 0.88 |
| follow-up | rewriter | 8 | 0.12 | 0.092 | 0.12 |
| all answerable | as asked, follow-ups alone | 28 | 0.39 | 0.282 | 0.43 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+bge-base

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.401 | 0.58 |
| multi-paper | as asked | 8 | 0.06 | 0.039 | 0.12 |
| follow-up | follow-up alone | 8 | 0.25 | 0.188 | 0.25 |
| follow-up | history + follow-up | 8 | 0.00 | 0.021 | 0.00 |
| follow-up | reference rewrite | 8 | 0.50 | 0.455 | 0.50 |
| follow-up | rewriter | 8 | 0.12 | 0.042 | 0.12 |
| all answerable | as asked, follow-ups alone | 28 | 0.34 | 0.237 | 0.36 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+bge-base+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.447 | 0.58 |
| multi-paper | as asked | 8 | 0.10 | 0.089 | 0.25 |
| follow-up | follow-up alone | 8 | 0.25 | 0.188 | 0.25 |
| follow-up | history + follow-up | 8 | 0.12 | 0.059 | 0.12 |
| follow-up | reference rewrite | 8 | 0.62 | 0.430 | 0.62 |
| follow-up | rewriter | 8 | 0.12 | 0.057 | 0.12 |
| all answerable | as asked, follow-ups alone | 28 | 0.35 | 0.271 | 0.39 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+openscholar

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.340 | 0.58 |
| multi-paper | as asked | 8 | 0.10 | 0.156 | 0.25 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.00 | 0.016 | 0.00 |
| follow-up | reference rewrite | 8 | 0.50 | 0.304 | 0.50 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.28 | 0.190 | 0.32 |
| unanswerable | left out | 8 | — | — | — |

### Results: hybrid.bm25+openscholar+collapsed

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.67 | 0.391 | 0.67 |
| multi-paper | as asked | 8 | 0.10 | 0.218 | 0.25 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.12 | 0.025 | 0.12 |
| follow-up | reference rewrite | 8 | 0.50 | 0.390 | 0.50 |
| follow-up | rewriter | 8 | 0.00 | 0.000 | 0.00 |
| all answerable | as asked, follow-ups alone | 28 | 0.32 | 0.230 | 0.36 |
| unanswerable | left out | 8 | — | — | — |

## Comparison

Each retriever against the baseline, dense.bge-small, and each `+collapsed` twin against dense.bge-small+collapsed, on the 28 answerable questions as a user asks them (the *all answerable* row's queries). The report names no winner: the decision rule of spec #55 is applied in an ADR.

- Wins, ties and losses count the questions where the retriever's Recall@5 (or reciprocal rank, for MRR@10) is higher than the baseline's, the same, or lower.
- The intervals are 95% percentile bootstrap intervals: the questions drawn with replacement, 10000 times, by NumPy's default generator seeded with 55. Every retriever is scored on the same draws, so a difference is paired question by question.
- A difference whose interval holds 0 is within noise.

### Comparison: Recall@5

| Retriever | Baseline | Recall@5 | 95% interval | Difference | Difference's 95% interval | Noise | Wins | Ties | Losses |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| bm25 | dense.bge-small | 0.16 | [0.04, 0.30] | -0.14 | [-0.32, +0.02] | within noise | 2 | 20 | 6 |
| bm25+collapsed | dense.bge-small+collapsed | 0.21 | [0.07, 0.36] | -0.17 | [-0.36, +0.01] | within noise | 3 | 18 | 7 |
| dense.bge-small | dense.bge-small | 0.30 | [0.14, 0.48] | +0.00 | [+0.00, +0.00] | within noise | 0 | 28 | 0 |
| dense.bge-small+collapsed | dense.bge-small+collapsed | 0.38 | [0.20, 0.55] | +0.00 | [+0.00, +0.00] | within noise | 0 | 28 | 0 |
| dense.bge-base | dense.bge-small | 0.29 | [0.14, 0.46] | -0.02 | [-0.12, +0.09] | within noise | 1 | 25 | 2 |
| dense.bge-base+collapsed | dense.bge-small+collapsed | 0.32 | [0.14, 0.50] | -0.05 | [-0.18, +0.07] | within noise | 1 | 24 | 3 |
| dense.openscholar | dense.bge-small | 0.07 | [0.00, 0.18] | -0.23 | [-0.41, -0.05] | beyond noise | 1 | 19 | 8 |
| dense.openscholar+collapsed | dense.bge-small+collapsed | 0.12 | [0.01, 0.25] | -0.26 | [-0.45, -0.07] | beyond noise | 2 | 17 | 9 |
| hybrid.bm25+bge-small | dense.bge-small | 0.34 | [0.18, 0.52] | +0.04 | [-0.09, +0.16] | within noise | 3 | 23 | 2 |
| hybrid.bm25+bge-small+collapsed | dense.bge-small+collapsed | 0.39 | [0.21, 0.57] | +0.01 | [-0.14, +0.16] | within noise | 4 | 21 | 3 |
| hybrid.bm25+bge-base | dense.bge-small | 0.34 | [0.18, 0.52] | +0.04 | [-0.09, +0.16] | within noise | 3 | 23 | 2 |
| hybrid.bm25+bge-base+collapsed | dense.bge-small+collapsed | 0.35 | [0.19, 0.52] | -0.02 | [-0.20, +0.14] | within noise | 4 | 20 | 4 |
| hybrid.bm25+openscholar | dense.bge-small | 0.28 | [0.13, 0.44] | -0.02 | [-0.20, +0.14] | within noise | 4 | 20 | 4 |
| hybrid.bm25+openscholar+collapsed | dense.bge-small+collapsed | 0.32 | [0.15, 0.48] | -0.06 | [-0.25, +0.12] | within noise | 4 | 19 | 5 |

### Comparison: MRR@10

| Retriever | Baseline | MRR@10 | 95% interval | Difference | Difference's 95% interval | Noise | Wins | Ties | Losses |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| bm25 | dense.bge-small | 0.118 | [0.033, 0.228] | -0.126 | [-0.284, +0.025] | within noise | 4 | 13 | 11 |
| bm25+collapsed | dense.bge-small+collapsed | 0.133 | [0.044, 0.242] | -0.142 | [-0.297, +0.009] | within noise | 4 | 10 | 14 |
| dense.bge-small | dense.bge-small | 0.244 | [0.114, 0.393] | +0.000 | [+0.000, +0.000] | within noise | 0 | 28 | 0 |
| dense.bge-small+collapsed | dense.bge-small+collapsed | 0.276 | [0.147, 0.421] | +0.000 | [+0.000, +0.000] | within noise | 0 | 28 | 0 |
| dense.bge-base | dense.bge-small | 0.211 | [0.083, 0.358] | -0.033 | [-0.125, +0.041] | within noise | 4 | 18 | 6 |
| dense.bge-base+collapsed | dense.bge-small+collapsed | 0.261 | [0.128, 0.408] | -0.015 | [-0.098, +0.058] | within noise | 5 | 17 | 6 |
| dense.openscholar | dense.bge-small | 0.046 | [0.010, 0.093] | -0.199 | [-0.343, -0.074] | beyond noise | 3 | 14 | 11 |
| dense.openscholar+collapsed | dense.bge-small+collapsed | 0.070 | [0.027, 0.122] | -0.206 | [-0.343, -0.082] | beyond noise | 2 | 12 | 14 |
| hybrid.bm25+bge-small | dense.bge-small | 0.257 | [0.127, 0.400] | +0.013 | [-0.091, +0.111] | within noise | 6 | 17 | 5 |
| hybrid.bm25+bge-small+collapsed | dense.bge-small+collapsed | 0.282 | [0.152, 0.425] | +0.006 | [-0.097, +0.106] | within noise | 7 | 13 | 8 |
| hybrid.bm25+bge-base | dense.bge-small | 0.237 | [0.119, 0.372] | -0.008 | [-0.122, +0.114] | within noise | 5 | 14 | 9 |
| hybrid.bm25+bge-base+collapsed | dense.bge-small+collapsed | 0.271 | [0.151, 0.403] | -0.005 | [-0.119, +0.117] | within noise | 6 | 11 | 11 |
| hybrid.bm25+openscholar | dense.bge-small | 0.190 | [0.080, 0.315] | -0.054 | [-0.208, +0.091] | within noise | 6 | 14 | 8 |
| hybrid.bm25+openscholar+collapsed | dense.bge-small+collapsed | 0.230 | [0.116, 0.357] | -0.046 | [-0.193, +0.098] | within noise | 6 | 12 | 10 |

### First hit: raw ranking

The rank of each question's first hit within the top 10, by retriever.

| Question | Type | bm25 | dense.bge-small | dense.bge-base | dense.openscholar | hybrid.bm25+bge-small | hybrid.bm25+bge-base | hybrid.bm25+openscholar |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | 5 | 2 | 4 | none | 1 | 3 | 1 |
| sentencepiece-whitespace | single-paper | none | 4 | 3 | none | none | 10 | none |
| bpe-dropout-rate | single-paper | 8 | 2 | 1 | 6 | 1 | 1 | 2 |
| bpe-cyrillic | single-paper | none | 1 | 1 | none | 4 | 3 | none |
| canine-amharic | single-paper | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| byt5-span-length | single-paper | none | 6 | none | none | 6 | 9 | none |
| digits-right-to-left | single-paper | none | none | none | none | none | none | none |
| llama2-70b-vocabulary | single-paper | 2 | none | 5 | none | 2 | 2 | 2 |
| xlm-r-tokens-per-language | single-paper | none | 1 | none | none | 3 | 3 | 3 |
| magikarp-verified-share | single-paper | none | none | none | 9 | none | none | 6 |
| superbpe-curriculum | single-paper | none | 8 | none | 3 | 5 | 10 | 4 |
| fast-wordpiece-speed | single-paper | 4 | 1 | 1 | none | 1 | 1 | 3 |
| bpe-and-wechsel-vocabularies | multi-paper | 10 | none | none | none | 2 | none | none |
| compression-and-accuracy | multi-paper | none | none | none | none | none | none | none |
| one-sided-regularization | multi-paper | 8 | none | none | 6 | 7 | 9 | 1 |
| tokenizer-swap-budget | multi-paper | 1 | none | none | none | none | 5 | 4 |
| megabyte-and-blt-patches | multi-paper | none | 10 | none | none | none | none | none |
| api-cost-by-language | multi-paper | none | 5 | none | none | 9 | none | none |
| renyi-efficiency | multi-paper | none | none | none | none | none | none | none |
| gpt-4-number-tokens | multi-paper | none | none | none | none | none | none | none |
| wechsel-neighbours | follow-up | none | none | none | none | none | none | none |
| canine-hashing | follow-up | none | none | none | none | none | none | none |
| digits-fourth-digit | follow-up | none | none | none | none | none | none | none |
| vocabulary-with-scarce-data | follow-up | none | none | 8 | none | none | 1 | none |
| code-tokenizer-initialisation | follow-up | none | none | none | none | none | none | none |
| magikarp-norm-indicator | follow-up | none | none | none | none | none | none | none |
| superbpe-mmlu | follow-up | none | none | none | none | none | none | none |
| tokenization-latency | follow-up | none | 1 | 1 | none | 1 | 2 | none |

### First hit: Collapsed ranking

The rank of each question's first hit within the top 10, by retriever.

| Question | Type | bm25+collapsed | dense.bge-small+collapsed | dense.bge-base+collapsed | dense.openscholar+collapsed | hybrid.bm25+bge-small+collapsed | hybrid.bm25+bge-base+collapsed | hybrid.bm25+openscholar+collapsed |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | 3 | 2 | 2 | 7 | 1 | 2 | 1 |
| sentencepiece-whitespace | single-paper | none | 3 | 2 | none | none | 7 | none |
| bpe-dropout-rate | single-paper | 5 | 2 | 1 | 4 | 1 | 1 | 2 |
| bpe-cyrillic | single-paper | none | 1 | 1 | none | 4 | 3 | 9 |
| canine-amharic | single-paper | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| byt5-span-length | single-paper | none | 3 | 8 | none | 3 | 6 | none |
| digits-right-to-left | single-paper | none | none | none | none | none | none | none |
| llama2-70b-vocabulary | single-paper | 2 | none | 4 | none | 2 | 2 | 2 |
| xlm-r-tokens-per-language | single-paper | none | 1 | 6 | none | 2 | 2 | 2 |
| magikarp-verified-share | single-paper | none | 3 | 2 | 6 | 10 | 10 | 4 |
| superbpe-curriculum | single-paper | none | 6 | none | 3 | 5 | 8 | 3 |
| fast-wordpiece-speed | single-paper | 3 | 1 | 1 | 8 | 1 | 1 | 2 |
| bpe-and-wechsel-vocabularies | multi-paper | 6 | none | none | none | 2 | none | none |
| compression-and-accuracy | multi-paper | none | 8 | none | 9 | none | none | 7 |
| one-sided-regularization | multi-paper | 5 | none | none | 3 | 4 | 4 | 1 |
| tokenizer-swap-budget | multi-paper | 1 | none | none | none | 7 | 3 | 2 |
| megabyte-and-blt-patches | multi-paper | none | 8 | 8 | none | none | none | none |
| api-cost-by-language | multi-paper | none | 5 | none | none | 9 | none | 10 |
| renyi-efficiency | multi-paper | none | none | none | none | none | 8 | none |
| gpt-4-number-tokens | multi-paper | none | 10 | none | none | none | none | none |
| wechsel-neighbours | follow-up | none | none | none | none | none | none | none |
| canine-hashing | follow-up | none | none | none | none | none | none | none |
| digits-fourth-digit | follow-up | none | none | none | none | none | none | none |
| vocabulary-with-scarce-data | follow-up | none | none | 7 | none | none | 1 | none |
| code-tokenizer-initialisation | follow-up | none | none | none | none | none | none | none |
| magikarp-norm-indicator | follow-up | none | none | none | none | none | none | none |
| superbpe-mmlu | follow-up | none | none | none | none | none | none | none |
| tokenization-latency | follow-up | none | 1 | 1 | none | 1 | 2 | none |

## Crowding

What takes the top 5 slots of each answerable question, as a user would ask it (the *all answerable* row's queries), on the raw ranking and on the Collapsed ranking (ADR 0044). Both are measured against the same Work groups, never the manifest's work_id the collapse uses.

- Work groups: `data/eval/work-groups.csv` (sha256 `34f0268e19e1a8d8ea3d3fe48d1662846f6df9ed32cdc4b3c6841a3afd7b4cf3`), 209 Editions in 179 Works, 209 of the Editions checked (who checked each is in checked_by), never computed by the system being measured.
- A duplicate slot holds a Chunk from a Work already ranked higher: another Edition or Version of it, or another Chunk of the same file. The two are counted apart too: the first repeats a paper, the second is more of it. A Collapsed ranking merges only copies, the first kind.
- A restatement slot holds a Chunk from a Survey. A Survey is always its own Work, and its Chunks are never duplicates.
- Duplicates and restatement count only the questions whose top 5 Editions all have a Work group.
- A mostly-numeric slot holds a text Chunk with more than 35% of its words numbers, as the parse report counts them (ADR 0035). It counts every question.

### Crowding: bm25

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 59/140 | 0.42 | 27/28 | 0.96 |
| duplicate: another Edition or Version | 38/140 | 0.27 | 25/28 | 0.89 |
| duplicate: same file | 21/140 | 0.15 | 12/28 | 0.43 |
| restatement | 0/140 | 0.00 | 0/28 | 0.00 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 28 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1

### Crowding: bm25+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 30/125 | 0.24 | 15/25 | 0.60 |
| duplicate: another Edition or Version | 5/125 | 0.04 | 5/25 | 0.20 |
| duplicate: same file | 25/125 | 0.20 | 14/25 | 0.56 |
| restatement | 0/125 | 0.00 | 0/25 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 25 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: dense.bge-small

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 70/140 | 0.50 | 27/28 | 0.96 |
| duplicate: another Edition or Version | 33/140 | 0.24 | 22/28 | 0.79 |
| duplicate: same file | 37/140 | 0.26 | 20/28 | 0.71 |
| restatement | 1/140 | 0.01 | 1/28 | 0.04 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 28 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2

### Crowding: dense.bge-small+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 52/130 | 0.40 | 23/26 | 0.88 |
| duplicate: another Edition or Version | 5/130 | 0.04 | 5/26 | 0.19 |
| duplicate: same file | 47/130 | 0.36 | 22/26 | 0.85 |
| restatement | 1/130 | 0.01 | 1/26 | 0.04 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 26 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: dense.bge-base

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 57/100 | 0.57 | 20/20 | 1.00 |
| duplicate: another Edition or Version | 24/100 | 0.24 | 16/20 | 0.80 |
| duplicate: same file | 33/100 | 0.33 | 15/20 | 0.75 |
| restatement | 1/100 | 0.01 | 1/20 | 0.05 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 20 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1

### Crowding: dense.bge-base+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 54/90 | 0.60 | 18/18 | 1.00 |
| duplicate: another Edition or Version | 5/90 | 0.06 | 4/18 | 0.22 |
| duplicate: same file | 49/90 | 0.54 | 18/18 | 1.00 |
| restatement | 0/90 | 0.00 | 0/18 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 2/28 | 0.07 |

- Grouped: 18 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: dense.openscholar

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 47/75 | 0.63 | 15/15 | 1.00 |
| duplicate: another Edition or Version | 21/75 | 0.28 | 12/15 | 0.80 |
| duplicate: same file | 26/75 | 0.35 | 12/15 | 0.80 |
| restatement | 0/75 | 0.00 | 0/15 | 0.00 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 15 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1

### Crowding: dense.openscholar+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 30/60 | 0.50 | 11/12 | 0.92 |
| duplicate: another Edition or Version | 2/60 | 0.03 | 2/12 | 0.17 |
| duplicate: same file | 28/60 | 0.47 | 11/12 | 0.92 |
| restatement | 0/60 | 0.00 | 0/12 | 0.00 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 12 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: hybrid.bm25+bge-small

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 65/140 | 0.46 | 25/28 | 0.89 |
| duplicate: another Edition or Version | 32/140 | 0.23 | 21/28 | 0.75 |
| duplicate: same file | 33/140 | 0.24 | 17/28 | 0.61 |
| restatement | 0/140 | 0.00 | 0/28 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 28 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2

### Crowding: hybrid.bm25+bge-small+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 45/130 | 0.35 | 20/26 | 0.77 |
| duplicate: another Edition or Version | 4/130 | 0.03 | 4/26 | 0.15 |
| duplicate: same file | 41/130 | 0.32 | 19/26 | 0.73 |
| restatement | 0/130 | 0.00 | 0/26 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 26 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: hybrid.bm25+bge-base

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 54/95 | 0.57 | 18/19 | 0.95 |
| duplicate: another Edition or Version | 26/95 | 0.27 | 17/19 | 0.89 |
| duplicate: same file | 28/95 | 0.29 | 14/19 | 0.74 |
| restatement | 0/95 | 0.00 | 0/19 | 0.00 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 19 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1

### Crowding: hybrid.bm25+bge-base+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 46/90 | 0.51 | 15/18 | 0.83 |
| duplicate: another Edition or Version | 4/90 | 0.04 | 4/18 | 0.22 |
| duplicate: same file | 42/90 | 0.47 | 15/18 | 0.83 |
| restatement | 0/90 | 0.00 | 0/18 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 18 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

### Crowding: hybrid.bm25+openscholar

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 60/100 | 0.60 | 20/20 | 1.00 |
| duplicate: another Edition or Version | 29/100 | 0.29 | 18/20 | 0.90 |
| duplicate: same file | 31/100 | 0.31 | 17/20 | 0.85 |
| restatement | 0/100 | 0.00 | 0/20 | 0.00 |
| mostly numeric | 2/140 | 0.01 | 2/28 | 0.07 |

- Grouped: 20 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2

### Crowding: hybrid.bm25+openscholar+collapsed

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 41/80 | 0.51 | 14/16 | 0.88 |
| duplicate: another Edition or Version | 3/80 | 0.04 | 3/16 | 0.19 |
| duplicate: same file | 38/80 | 0.47 | 14/16 | 0.88 |
| restatement | 0/80 | 0.00 | 0/16 | 0.00 |
| mostly numeric | 3/140 | 0.02 | 2/28 | 0.07 |

- Grouped: 16 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 3
- Pool: the top 50 raw Chunks held fewer than 5 distinct Chunks, once copies were merged, for 0 of 28 questions, and fewer than 10, the depth each query asks for, for 0.

## Before and after

Each retriever's raw ranking and its Collapsed ranking, over the answerable questions as a user asks them: the duplicate slots in the top 5 as *Crowding* counts them, over the questions whose top 5 is grouped, and the *all answerable* row of *Results*.

| Retriever | Ranking | Duplicate | Another Edition or Version | Same file | Grouped questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | raw | 59/140 | 38/140 | 21/140 | 28/28 | 0.16 | 0.118 | 0.18 |
| bm25 | collapsed | 30/125 | 5/125 | 25/125 | 25/28 | 0.21 | 0.133 | 0.25 |
| dense.bge-small | raw | 70/140 | 33/140 | 37/140 | 28/28 | 0.30 | 0.244 | 0.32 |
| dense.bge-small | collapsed | 52/130 | 5/130 | 47/130 | 26/28 | 0.38 | 0.276 | 0.39 |
| dense.bge-base | raw | 57/100 | 24/100 | 33/100 | 20/28 | 0.29 | 0.211 | 0.29 |
| dense.bge-base | collapsed | 54/90 | 5/90 | 49/90 | 18/28 | 0.32 | 0.261 | 0.32 |
| dense.openscholar | raw | 47/75 | 21/75 | 26/75 | 15/28 | 0.07 | 0.046 | 0.07 |
| dense.openscholar | collapsed | 30/60 | 2/60 | 28/60 | 12/28 | 0.12 | 0.070 | 0.14 |
| hybrid.bm25+bge-small | raw | 65/140 | 32/140 | 33/140 | 28/28 | 0.34 | 0.257 | 0.36 |
| hybrid.bm25+bge-small | collapsed | 45/130 | 4/130 | 41/130 | 26/28 | 0.39 | 0.282 | 0.43 |
| hybrid.bm25+bge-base | raw | 54/95 | 26/95 | 28/95 | 19/28 | 0.34 | 0.237 | 0.36 |
| hybrid.bm25+bge-base | collapsed | 46/90 | 4/90 | 42/90 | 18/28 | 0.35 | 0.271 | 0.39 |
| hybrid.bm25+openscholar | raw | 60/100 | 29/100 | 31/100 | 20/28 | 0.28 | 0.190 | 0.32 |
| hybrid.bm25+openscholar | collapsed | 41/80 | 3/80 | 38/80 | 16/28 | 0.32 | 0.230 | 0.36 |

## Grouping

The grouping rule (ADR 0051), as the manifest's work_id and survey columns hold it, scored against the Work groups. Over the Editions in the Work groups, a pair is two Editions one Work holds; an Edition the manifest gives no work_id is its own Work. Precision is the share of the rule's pairs the Work groups join too, recall the share of the Work groups' pairs the rule joins. A Work of the Work groups is named under *Surveys* when its Survey flag differs from the rule's survey column on any of its Editions (blank reads as no).

- Editions: 209 in the Work groups, all with a work_id in the manifest
- Pairs the rule joins: 30
- Pairs the Work groups join: 30
- Pairs both join: 30
- Precision: 30/30 = 1.00
- Recall: 30/30 = 1.00

### Pairs the rule joins and the Work groups keep apart

None.

### Pairs the Work groups join and the rule misses

None.

### Surveys

- Surveys: 3 of 179 Works in the Work groups, 1 flagged by the rule; the two agree on 175 of 179 Works

| Work | Work groups | Rule | Editions |
|---|---|---|---|
| barolo-2026-tokens-agents | yes | no | 2603.19269v1 |
| cognetta-2025-tutorial-varphi | no | yes | 2506.17942v1 |
| libovicky-2021-don-t | yes | no | 2110.08191v2 |
| mielke-2021-between-words | yes | no | 2112.10508v1 |

## Editions without a Work group

Editions in any retriever's top 5 for an answerable question, in any query but the rewriter's, with no Work group. `evaluate --export-ungrouped` writes them, with their titles, for grouping.

- 10.5121/ijci.2024.130204
- 10.54254/2755-2721/2026.37609
- 1506.02338v3
- 1603.00810v3
- 1707.06961v1
- 2001.05316v1
- 2004.02334v2
- 2004.06343v1
- 2012.15613v2
- 2020.aacl-main.17
- 2021.acl-long.243
- 2021.emnlp-main.161
- 2021.mrl-1.3
- 2021.naacl-main.17
- 2021.wat-1.21
- 2022.findings-acl.194
- 2022.naacl-main.179
- 2023.acl-long.326
- 2023.acl-long.699
- 2023.acl-short.34
- 2023.americasnlp-1.9
- 2023.eamt-1.14
- 2023.findings-acl.548
- 2023.findings-eacl.128
- 2023.icon-1.19
- 2023.paclic-1.64
- 2024.emnlp-main.230
- 2024.findings-eacl.9
- 2024.findings-emnlp.860
- 2024.ltedi-1.16
- 2024.mrl-1.1
- 2024.tacl-1.22
- 2025.acl-srw.57
- 2025.findings-acl.275
- 2025.findings-emnlp.379
- 2025.findings-emnlp.595
- 2025.latechclfl-1.22
- 2026.mellm-1.27
- 2109.02550v2
- 2202.12142v1
- 2204.04748v1
- 2206.02608v1
- 2208.05225v2
- 2212.11281v2
- 2305.05461v1
- 2306.01393v3
- 2310.08754v4
- 2402.10712v3
- 2403.16854v3
- 2404.18810v2
- 2406.11214v3
- 2408.04653v1
- 2408.08541v2
- 2410.16410v1
- 2411.18553v3
- 2501.10322v2
- 2502.20273v4
- 2506.11115v1
- 2506.14123v3
- 2508.11857v3
- 2509.18750v2
- 2511.20849v2
- 2512.12641v2
- 2601.11518v1
- 2602.05347v1
- 2602.07698v2
- 2603.22774v3
- 2607.29065v1
- 2608.00582v1
- 2608.03494v1
- 2608.07249v1
- 2608.12756v1
- 2608.13129v1
- 2608.17325v1
- 2608.29930v1
- 2609.01151v1
- 2609.01386v1
- C16-1301
- D19-1141
- D19-1534
- P16-2058
- W17-4109
- W18-1205
- W19-4602

## Questions

First hit is the rank of the first Chunk holding a Passage, within the top 10; Passages found counts those held in the top 5. The slot counts are within the top 5; a question with an Edition there that has no Work group has its duplicates and restatements marked ungrouped. A Collapsed ranking's lines name the file of each top-5 Chunk, with the other files of its Work in the pool after a +.

### Rewrites

Each follow-up's reference rewrite and the rewriter's Rewrite, which are its last two queries below.

| Question | Follow-up | Reference rewrite | Rewrite |
|---|---|---|---|
| wechsel-neighbours | When it builds the new subword embeddings from similar source subwords, what temperature and how many neighbours does it use? | Which temperature and number of nearest neighbours does WECHSEL use to initialise subword embeddings? | When a model is transferred to a new language with WECHSEL, do its non-embedding weights have to be held fixed early in training? When it builds the new subword embeddings from similar source subwords, what temperature and how many neighbours does it use? |
| canine-hashing | How does it give every possible character an embedding without an enormous table? | How does CANINE embed every Unicode codepoint without a vocabulary-sized embedding matrix? | How does the model give every possible character an embedding without an enormous table? |
| digits-fourth-digit | And when the answer is longer than the numbers being added, where does the left-to-right version go wrong? | In the study of number tokenization direction in GPT models, which digit does the model get wrong under left-to-right tokenization when the answer has more digits than the addends? | When the answer is longer than the numbers being added, where does the left-to-right version go wrong? |
| vocabulary-with-scarce-data | What happens to that optimum when there isn't much training data? | In the work on scaling laws for vocabulary size, how does the optimal vocabulary size change when the available training data is the bottleneck? | What happens to the optimum when there isn't much training data? |
| code-tokenizer-initialisation | In the code study, how were the embeddings for the new tokens set up before that training? | How did Dagan et al. initialise the embeddings of the new tokens when changing a pre-trained code model's tokenizer? | How were the embeddings for the new tokens set up before that training in the code study? |
| magikarp-norm-indicator | Is there a signal in the weights that spots them without already knowing some? | In Fishing for Magikarp, which embedding-based indicator flags under-trained tokens without needing a set of known untrained tokens? | Is there a signal in the weights that spots the under-trained tokens without already knowing some? |
| superbpe-mmlu | How much did that help on MMLU? | How much does the SuperBPE model improve over the BPE baseline on MMLU? | How much did the improvement on MMLU look like? |
| tokenization-latency | Do the longer token sequences also slow processing down, and how does the time grow with length? | In Petrov et al.'s study of tokenizer unfairness across languages, do languages with longer tokenizations also take longer to process, and how does processing time grow with tokenization length? | Do longer token sequences slow processing down, and how does the time grow with length? |

### Questions: bm25

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 5 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| bpe-dropout-rate | single-paper | as asked | 8 | 0/2 | 2 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 1 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 4 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | 10 | 0/2 | 2 | 0 | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 2 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | 8 | 0/3 | 3 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | 1 | 1/2 | 3 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 2 | 0 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | 2 | 1 | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 1 | 1/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 0 | 0 | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | 6 | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | 1 | 1 | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: bm25+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 3 | 1/1 | 3 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2410.06898v1; 2022.naacl-main.293 + 2112.06598v2 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | 2608.08847v2 + 2608.08847v1; 2606.18717v2; 2608.00837v3 + 2608.00837v1; 2606.23566v2 + 2606.23566v1; 2610.12144v1 |
| bpe-dropout-rate | single-paper | as asked | 5 | 2/2 | 1 | 0 | 0 | 2204.14268v2; 2024.emnlp-main.925; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2023.acl-srw.5 + 2306.09572v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2 |
| bpe-cyrillic | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | W17-4102 + 1610.06510v3 + 1610.06510v1; 1911.00317v1; W19-6620 + 1905.10453v1 + 1905.10453v2; 2021.wat-1.29; 2022.amta-research.9 + 2208.05225v2 + 2208.05225v1 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | ungrouped | ungrouped | 2 | 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5; 2103.06874v4; 2608.07249v1 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | 2411.11808v1; 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2022.findings-emnlp.207 + 2212.07284v1; 2410.11627v2 + 2410.11627v1; 2410.20771v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 1 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2305.14201v1; 2608.18062v3 + 2608.18062v1; 2604.11582v3 + 2604.11582v1 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| xlm-r-tokens-per-language | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2608.07727v1; 2609.22097v1; 2607.15209v3; 2607.05691v1 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2405.05417v1; 2405.05417v1; 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | none | 0/1 | 2 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2610.01984v1; 2503.13423v3 + 2503.13423v1; 2025.babylm-main.16; 2503.13423v1 |
| fast-wordpiece-speed | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2012.15524v1; 2021.emnlp-main.160 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | 6 | 0/2 | 0 | 0 | 0 | 1809.02223v1; W19-6620 + 1905.10453v1 + 1905.10453v2; 2022.emnlp-main.434 + 2211.12781v1; W18-1207; 2023.insights-1.7 + 2305.03029v1 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 2 | 0 | 0 | 2024.emnlp-main.40 + 2402.18376v2; 2024.emnlp-main.40 + 2402.18376v2; 2024.emnlp-main.925 + 2409.04599v1; 2508.08424v3 + 2508.08424v1; 2024.emnlp-main.40 + 2402.18376v2 |
| one-sided-regularization | multi-paper | as asked | 5 | 1/3 | 2 | 0 | 0 | 2020.acl-main.275 + 2005.06606v1 + 2005.06606v2; 2020.acl-main.170 + 1910.13267v2; 2004.14109v1; 2020.acl-main.275 + 2005.06606v2 + 2005.06606v1; 2020.acl-main.170 + 1910.13267v2 |
| tokenizer-swap-budget | multi-paper | as asked | 1 | 1/2 | ungrouped | ungrouped | 0 | 2405.07883v2 + 2405.07883v1; 2607.15232v1; 2405.07883v2 + 2405.07883v1; 2025.acl-srw.57; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 | 2412.09871v1; 2412.09871v1; 2404.14408v3 + 2404.14408v1; 2605.09630v1; 2604.07466v2 + 2604.07466v1 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2410.10665v1; 2607.24276v1; 2403.05434v2 + 2403.05434v1 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 | 2507.06378v1; 2512.03989v1; 2025.findings-acl.572 + 2502.15343v2; 2411.14198v1; 2504.00178v2 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2610.19801v1; 2610.19801v1; 2609.08703v2 + 2609.08703v1; 2610.12144v1; 2610.12144v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2311.08849v2; 2024.conll-1.8 + 2407.05841v1 + 2407.05841v2; 2311.08849v2 + 2311.08849v1; 2311.05741v2 + 2311.05741v1; 1712.01807v1 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2025.findings-acl.109; 2410.06898v1 |
| wechsel-neighbours | follow-up | reference rewrite | 10 | 0/1 | 1 | 0 | 0 | 2020.lrec-1.475 + 2002.11004v1; 2407.00894v2 + 2407.00894v1; 2025.findings-acl.109; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2025.findings-acl.109; 2410.06898v1 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | Q17-1026 + 1610.03017v3; 1908.05344v1; 2610.19801v1; 2103.00074v4 + 2103.00074v1; 2607.01239v1 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 1 | 1 | 1 | 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5; 2603.19269v1; 2608.21106v3 + 2608.21106v1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 1 | 0 | 0 | 2507.04886v4 + 2507.04886v1; 2103.06874v4; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2305.15425v2 + 2305.15425v1; 2022.emnlp-main.536 |
| canine-hashing | follow-up | rewriter | none | 0/1 | 0 | 1 | 0 | Q17-1026 + 1610.03017v3; 2603.19269v1; 2103.00074v4 + 2103.00074v1; 1908.05344v1; 2607.01239v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 1909.07940v2 + 1909.07940v1; 2507.06195v1; 2602.10416v1; 2402.14903v1; 2601.08808v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2305.14201v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 | 2402.14903v1; 2602.10416v1; 2402.14903v1; 2604.11582v3 + 2604.11582v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 0 | 0 | 0 | 1909.07940v2 + 1909.07940v1; 2507.06195v1; 2402.14903v1; 2602.10416v1; 2601.08808v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2602.13266v1; 2407.16607v4; 2024.repl4nlp-1.10 + 2401.07923v1 + 2401.07923v2; 2603.16077v1; 2024.repl4nlp-1.10 + 2401.07923v2 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2603.20854v1; 2507.15773v2 + 2507.15773v1; 2407.13623v3 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2605.01188v2 + 2605.01188v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2602.13266v1; 2407.16607v4; 2411.14198v1; 2024.repl4nlp-1.10 + 2401.07923v1 + 2401.07923v2; 2610.19294v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 2003.07914v1; 2601.13328v1; 10.1186/s12859-026-06562-5; 2211.08192v1; 2402.14714v1 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 1 | 0 | 0 | 2024.iwclul-1.13 + 2501.02631v1; 2405.07883v2 + 2405.07883v1; 2607.15232v1; 2607.15232v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 1 | 1/1 | 0 | 0 | 0 | 2402.01035v2 + 2402.01035v1; 2024.iwclul-1.13 + 2501.02631v1; 2406.14670v2 + 2406.14670v1; 2607.15232v1; 2605.11774v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 0 | 0 | 0 | 2003.07914v1; 2601.13328v1; 10.1186/s12859-026-06562-5; 2211.08192v1; 2402.14714v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2510.06244v1; 2610.14427v1; 2608.21106v3 + 2608.21106v1; 2608.21106v1; 2508.11260v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | W17-4106; 2609.15528v1; 2510.09947v2 + 2510.09947v1; 2609.29045v1; N16-1155 + 1512.00103v1 + 1512.00103v2 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 2607.15232v1; 2305.15108v1; 2405.13929v1; 2024.lrec-main.89 + 2404.08018v1; 2107.08091v1 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v1; 2610.01984v1; 2025.babylm-main.16 |
| superbpe-mmlu | follow-up | reference rewrite | 3 | 1/1 | ungrouped | ungrouped | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2508.11857v3 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2506.14761v1; 1808.02608v1; 2401.13660v3; 2412.10924v1; 2412.10924v11 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2024.emnlp-main.925 + 2409.04599v1; 2411.17669v1; 2511.04952v1; 2603.22774v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 | 2305.13707v1; 2305.13707v1; 2305.15425v2 + 2305.15425v1; 10.1007/s00146-026-02990-2; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 1 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v1; 2026.acl-demo.41; 2608.25904v3 + 2608.25904v1; 2607.24276v1 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2024.emnlp-main.925 + 2409.04599v1; 2411.17669v1; 2022.findings-acl.194 + 2110.08191v1 + 2110.08191v2; 2023.acl-long.406 + 2212.10474v1 + 2212.10474v2 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | P16-1162 + 1508.07909v5; 2020.wmt-1.9; 2020.wmt-1.9; 2402.00786v5 + 2402.00786v1; 2020.wmt-1.9 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2410.01930v2 + 2410.01930v1; 2305.07185v2 + 2305.07185v1; 2412.09871v1; 2609.00463v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2023.acl-long.402; 2412.09871v1; 2412.09871v1; 2203.09963v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2606.17358v3; 2610.19801v1; 2610.13325v1; 2607.29678v3 + 2607.29678v1; 2610.19801v1 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | 2302.09207v3; 2302.09207v1; 1812.08621v4 + 1812.08621v1; 2502.12560v2 + 2502.12560v1; 2502.12560v2 + 2502.12560v1 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2308.09440v3; 2022.findings-emnlp.207 + 2212.07284v1; 2606.30140v1; W19-6620 + 1905.10453v1; 2510.21372v2 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2604.22709v2 + 2604.22709v1; 2404.05892v4 + 2404.05892v1; 2407.03232v1; 2602.03195v2 + 2602.03195v1; 2606.15521v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2408.07065v1; 2607.17689v1; 2106.06297v1; 2205.05093v1; 2601.22710v2 + 2601.22710v1 |

### Questions: dense.bge-small

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | 4 | 1/1 | 1 | 0 | 0 |
| bpe-dropout-rate | single-paper | as asked | 2 | 2/2 | 2 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | 1 | 1/1 | 2 | 0 | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 2 |
| byt5-span-length | single-paper | as asked | 6 | 0/1 | 3 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | 8 | 0/1 | 2 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | 2 | 1 | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | 10 | 0/2 | 3 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | 5 | 1/2 | 3 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | 5 | 1/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 1 | 2 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 3 | 1 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 4 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | 1 | 1/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 1 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | rewriter | 1 | 1/1 | 3 | 0 | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: dense.bge-small+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 |
| sentencepiece-whitespace | single-paper | as asked | 3 | 1/1 | 0 | 0 | 0 | 10.22260/isarc2023/0057; 2101.09635v2 + 2101.09635v1; 2405.17067v2 + 2405.17067v1; 1812.08621v1; D18-2012 + 1808.06226v1 |
| bpe-dropout-rate | single-paper | as asked | 2 | 2/2 | 1 | 0 | 0 | 2023.insights-1.7 + 2305.03029v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2025.loresmt-1.8; 2305.03029v1; 2202.13590v2 + 2202.13590v1 |
| bpe-cyrillic | single-paper | as asked | 1 | 1/1 | 0 | 0 | 0 | P16-1162 + 1508.07909v5 + 1508.07909v1; W18-1207; W17-4102 + 1610.06510v3; W18-6303 + 1809.02694v1; W19-6620 + 1905.10453v1 + 1905.10453v2 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2103.06874v4; 2024.naacl-srw.14 + 2404.18810v2; 2024.naacl-srw.14 + 2404.18810v1 + 2404.18810v2 |
| byt5-span-length | single-paper | as asked | 3 | 1/1 | 2 | 0 | 0 | 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2025.findings-emnlp.297 + 2505.17102v1; 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2201.13242v2 + 2201.13242v1; 2201.13242v2 + 2201.13242v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2512.20757v2 + 2512.20757v1; 2402.14903v1; 2402.14903v1; 2402.14903v1 |
| llama2-70b-vocabulary | single-paper | as asked | none | 0/1 | 1 | 0 | 0 | 2407.13623v3; 2402.01035v2 + 2402.01035v1; 2510.17001v1; 2406.11477v3; 2407.13623v3 |
| xlm-r-tokens-per-language | single-paper | as asked | 1 | 1/1 | 3 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2024.iwclul-1.11 |
| magikarp-verified-share | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | 6 | 0/1 | 1 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2510.21909v1; 2504.00178v2 + 2504.00178v1; 2604.05192v2; 2503.13423v3 + 2503.13423v1 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2012.15524v1; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | 2 | 1 | 0 | 2112.10508v1; 2020.lrec-1.450; W19-6620 + 1905.10453v2 + 1905.10453v1; 2020.lrec-1.450; 1905.10453v2 + 1905.10453v1 |
| compression-and-accuracy | multi-paper | as asked | 8 | 0/3 | 3 | 0 | 0 | 2403.06265v2 + 2403.06265v1; 2510.21909v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1 |
| one-sided-regularization | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2023.ranlp-1.62; 2020.acl-main.170 + 1910.13267v2 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2607.15232v1; 2405.07883v2 + 2405.07883v1; 2607.15232v1; 2405.07883v2 + 2405.07883v1 |
| megabyte-and-blt-patches | multi-paper | as asked | 8 | 0/2 | 2 | 0 | 0 | 2412.09871v1; 2412.09871v1; 2412.09871v1; 2404.14408v3 + 2404.14408v1; 2305.07185v2 + 2305.07185v1 |
| api-cost-by-language | multi-paper | as asked | 5 | 1/2 | 3 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2506.06446v2; 2506.06446v2; 2305.15425v2 + 2305.15425v1 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2512.03989v1; 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2411.14198v1; 2510.21909v1 |
| gpt-4-number-tokens | multi-paper | as asked | 10 | 0/2 | 0 | 0 | 0 | 2608.18062v3 + 2608.18062v1; 2402.14903v1; 2505.14178v1; 2512.20757v2 + 2512.20757v1; 2304.14780v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 1805.03710v1; 1805.03710v1; K19-1021 + 1909.12375v1; 2020.lrec-1.330; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | history + follow-up | 7 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| wechsel-neighbours | follow-up | reference rewrite | 3 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1 |
| wechsel-neighbours | follow-up | rewriter | 7 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2024.findings-acl.302; 2602.21377v1; 2602.21377v1; 2010.09997v1; 2010.12730v1 |
| canine-hashing | follow-up | history + follow-up | 9 | 0/1 | 2 | 1 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2103.06874v4; 2110.08191v2 + 2110.08191v1; 2024.naacl-srw.14 + 2404.18810v1 + 2404.18810v2 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 3 | 1 | 0 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2112.10508v1; 2103.06874v1; 2022.tacl-1.5 + 2103.06874v4 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 1508.06615v4 + 1508.06615v1; 2610.04002v1; 2605.09751v1; 2605.09751v1; 2010.12730v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 | 2502.19981v1; 2402.14903v1; 2402.14903v1; 2502.19981v1; 2602.10416v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2602.10416v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 | 2602.10416v1; 2402.14903v1; 2305.14201v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 2502.19981v1; 2402.14903v1; 2402.14903v1; 2602.10416v1; 2602.10416v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2405.14159v2 + 2405.14159v1; 2405.14159v2 + 2405.14159v1; 1806.09089v2; 2402.02791v1; 2507.22543v1 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 4 | 1/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3; 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 2405.14159v2 + 2405.14159v1; 2405.14159v2 + 2405.14159v1; 2402.02791v1; 1806.09089v2; 2405.14159v2 + 2405.14159v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2505.20133v3 + 2505.20133v1; 2505.20133v3 + 2505.20133v1; 2505.20133v3 + 2505.20133v1; 2412.10924v1; 2025.findings-acl.275 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 1 | 0 | 0 | 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2607.15232v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2510.21954v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | 1 | 0 | 0 | 2510.21954v1; 2026.findings-eacl.341 + 2512.03989v1 + 2512.03989v2; 2512.03989v1; 2405.07883v2 + 2405.07883v1; 2505.20133v3 + 2505.20133v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 2505.20133v3 + 2505.20133v1; 2505.20133v3 + 2505.20133v1; 2505.20133v3 + 2505.20133v1; 2412.10924v1; 2510.21954v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 | 2010.01003v1; 2112.09348v1; 2506.17942v1; 2010.01003v1; 2010.01003v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | 8 | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | rewriter | 1 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 | 2509.15020v1; 2603.15953v1; 2603.15953v1; 2603.15953v1; 2410.09644v3 + 2410.09644v1 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 1 | 0 | 0 | 2510.21909v1; 2504.00178v2 + 2504.00178v1; 2503.13423v3 + 2503.13423v1; 2604.05192v2; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 | 2603.15953v1; 2410.09644v3 + 2410.09644v1; 2603.15953v1; 2509.15020v1; 2607.15232v1 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | ungrouped | ungrouped | 0 | 2305.15425v2 + 2305.15425v1; 2511.04952v1; 2305.15425v1; 2607.26831v1; 2022.naacl-main.179 + 2206.02608v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2; 2305.15425v1 |
| tokenization-latency | follow-up | rewriter | 1 | 1/1 | 3 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2511.04952v1; 2305.15425v1; 2511.04952v1; 2511.04952v1 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | 2023.icon-1.19; W7218093374; 2505.16868v1; 2020.wmt-1.92; 2505.16868v1 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2501.10322v2 + 2501.10322v1; 2412.09871v1; 2502.14553v1; 2412.09871v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2402.18376v2 + 2402.18376v1; 2610.01984v2 + 2610.01984v1; 2023.acl-long.353 + 2211.09761v2; 2211.09761v1; 2507.22543v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2021.emnlp-main.160 + 2012.15524v3; 2606.20993v1; 2603.02597v1; 2021.emnlp-main.160 + 2012.15524v3; 2603.02597v1 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | D18-2012 + 1808.06226v1; 2025.loresmt-1.8; D18-2012 + 1808.06226v1; D18-2012 + 1808.06226v1; 1905.13656v3 + 1905.13656v1 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2506.04079v2 + 2506.04079v1; 2022.tacl-1.17; 2602.05879v1; 2105.13626v3 + 2105.13626v1; 2023.findings-emnlp.923 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2502.03275v2; 2603.15644v1; 2603.15644v1; 2402.12030v1; 2405.04163v2 + 2405.04163v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2408.07065v1; 2408.07065v1; 2408.07065v1; 2022.tacl-1.5 + 2103.06874v4 + 2103.06874v1; 2408.07065v1 |

### Questions: dense.bge-base

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 4 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | 3 | 1/1 | ungrouped | ungrouped | 0 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 2 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | 1 | 1/1 | ungrouped | ungrouped | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | ungrouped | ungrouped | 0 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | 5 | 1/1 | 3 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | 2 | 1 | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | 7 | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 1 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | 8 | 0/1 | ungrouped | ungrouped | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 6 | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | 6 | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 7 | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | 6 | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | rewriter | 1 | 1/1 | ungrouped | ungrouped | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: dense.bge-base+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 |
| sentencepiece-whitespace | single-paper | as asked | 2 | 1/1 | ungrouped | ungrouped | 0 | 2101.09635v2 + 2101.09635v1; 2405.17067v2 + 2405.17067v1; 2508.01685v1; 2501.10322v2 + 2501.10322v1; 2024.emnlp-main.40 + 2402.18376v1 + 2402.18376v2 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 2 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2023.insights-1.7 + 2305.03029v1; 2005.06606v1; 2023.insights-1.7 + 2305.03029v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2 |
| bpe-cyrillic | single-paper | as asked | 1 | 1/1 | ungrouped | ungrouped | 0 | P16-1162 + 1508.07909v1 + 1508.07909v5; W18-1207; 2023.icon-1.19; W19-4602; W17-4102 + 1610.06510v1 + 1610.06510v3 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 2 | 0 | 1 | 2022.tacl-1.5 + 2103.06874v4; 2024.naacl-srw.14 + 2404.18810v2 + 2404.18810v1; 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1 |
| byt5-span-length | single-paper | as asked | 8 | 0/1 | 3 | 0 | 0 | 2022.tacl-1.17 + 2105.13626v1 + 2105.13626v3; 2025.findings-emnlp.297 + 2505.17102v1; 2022.tacl-1.17 + 2105.13626v1 + 2105.13626v3; 2105.13626v1; 2105.13626v3 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2512.20757v2 + 2512.20757v1 |
| llama2-70b-vocabulary | single-paper | as asked | 4 | 1/1 | 3 | 0 | 0 | 2407.13623v3; 2402.01035v2 + 2402.01035v1; 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| xlm-r-tokens-per-language | single-paper | as asked | 6 | 0/1 | 4 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1 |
| magikarp-verified-share | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1; 2405.05417v1; 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | none | 0/1 | 1 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2025.babylm-main.16; 2510.21909v1; 2504.00178v2 + 2504.00178v1; 2503.13423v3 + 2503.13423v1 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2112.10508v1; 2023.insights-1.7 + 2305.03029v1; 2020.lrec-1.450; 2020.lrec-1.450; D19-1141 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 | 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1 |
| one-sided-regularization | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2510.21954v2 + 2510.21954v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1 |
| megabyte-and-blt-patches | multi-paper | as asked | 8 | 0/2 | 3 | 0 | 0 | 2412.09871v1; 2412.09871v1; 2412.09871v1; 2305.07185v2 + 2305.07185v1; 2412.09871v1 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2506.06446v2; 2410.10665v1; 2506.06446v2 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2512.03989v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2512.03989v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2026.findings-eacl.341 + 2512.03989v2 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2402.14903v1; 2512.20757v2 + 2512.20757v1; 2608.18062v3; 2505.14178v1; 2025.findings-emnlp.595 + 2510.15517v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 | 2021.findings-emnlp.141 + 2010.12730v3; 2025.findings-emnlp.379; 2024.ltedi-1.16; W18-1205; 2025.findings-emnlp.379 |
| wechsel-neighbours | follow-up | history + follow-up | 6 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | reference rewrite | 5 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 |
| wechsel-neighbours | follow-up | rewriter | 6 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2001.05316v1; 2010.09997v1; 1506.02338v3 + 1506.02338v1; 2023.acl-long.326 + 2305.05461v1; 1506.02338v3 + 1506.02338v1 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 1 | 2022.tacl-1.5 + 2103.06874v4; 2024.naacl-srw.14 + 2404.18810v2 + 2404.18810v1; 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | ungrouped | ungrouped | 0 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2023.findings-eacl.128; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2021.naacl-main.17 + 2008.09396v2 + 2008.09396v1; 1506.02338v3 + 1506.02338v1; 2001.05316v1; 2023.acl-long.326 + 2305.05461v1; 2602.21377v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 | 2602.10416v1; 2402.14903v1; 2602.10416v1; 2602.10416v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2602.10416v1; 2608.13129v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2602.10416v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 3 | 0 | 0 | 2602.10416v1; 2402.14903v1; 2402.14903v1; 2602.10416v1; 2602.10416v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | 7 | 0/1 | ungrouped | ungrouped | 0 | 2405.14159v2 + 2405.14159v1; 2004.06343v1; 2407.13623v3 + 2407.13623v1; 2025.latechclfl-1.22; 2502.20273v1 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 6 | 0/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3; 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | 5 | 1/1 | ungrouped | ungrouped | 0 | 2405.14159v2 + 2405.14159v1; 2004.06343v1; 2025.latechclfl-1.22; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2405.07883v2 + 2405.07883v1; 2510.21954v2 + 2510.21954v1; 2510.21954v1; 2505.20133v3 + 2505.20133v1; 2024.mrl-1.1 + 2404.05829v1 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 | 2510.21954v2 + 2510.21954v1; 2405.07883v2 + 2405.07883v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2512.03989v1; 2405.07883v2 + 2405.07883v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 | 2510.21954v2 + 2510.21954v1; 2405.07883v2 + 2405.07883v1; 2510.21954v1; 2608.00582v1; 2512.03989v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 | 2405.07883v2 + 2405.07883v1; 2510.21954v1; 2510.21954v1; 2505.20133v3 + 2505.20133v1; 2410.18836v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2506.11115v1; 2608.29930v1; 2506.11115v1; 2112.09348v1; 2112.09348v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | reference rewrite | 4 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | rewriter | 4 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 | 2603.15953v1; 2603.15953v1; 2603.15953v1; 2410.09644v3 + 2410.09644v1; 2607.15232v1 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 | 2025.babylm-main.16; 2510.21909v1; 2503.13423v3 + 2503.13423v1; 2510.21909v1; 2026.mellm-1.27 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 | 2026.mellm-1.27; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2603.15953v1; 2403.01858v3; 2410.09644v1; 2025.acl-long.100 + 2412.12310v2; 2506.06607v1 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | ungrouped | ungrouped | 0 | 2305.15425v2 + 2305.15425v1; 2511.20849v2 + 2511.20849v1; 2305.15425v1; 2601.11518v1; 2511.04952v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1 |
| tokenization-latency | follow-up | rewriter | 1 | 1/1 | ungrouped | ungrouped | 0 | 2305.15425v2 + 2305.15425v1; 2511.20849v2 + 2511.20849v1; 2607.26831v1; 2511.04952v1; 2601.11518v1 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | W18-6459; 2023.icon-1.19; W18-1207; 2020.lrec-1.444 + 2004.13819v1; 1612.04629v1 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2501.10322v2 + 2501.10322v1; 2412.09871v1; 2412.09871v1; 2412.09871v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2023.emnlp-main.459 + 2305.05480v3; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2311.00522v1; 2409.13920v1; 2605.08044v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2021.emnlp-main.160 + 2012.15524v3; 2603.02597v1; 2408.15793v1; 2603.02597v1; 2512.21933v1 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | D18-2012 + 1808.06226v1; 2025.loresmt-1.8; D18-2012 + 1808.06226v1; 2008.03979v2 + 2008.03979v1; 2112.10508v1 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2201.13242v2 + 2201.13242v1; 2506.04079v2 + 2506.04079v1; 2507.15773v2 + 2507.15773v1; 2602.05879v1; 2022.tacl-1.17 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2403.01858v3; 2604.26951v1; 2401.18034v1; 2403.01858v3; 2510.15346v2 + 2510.15346v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2106.06297v1; 2106.06297v1; 2408.07065v1; 2402.00786v5; 2408.07065v1 |

### Questions: dense.openscholar

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 |
| bpe-dropout-rate | single-paper | as asked | 6 | 0/2 | 4 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-amharic | single-paper | as asked | 2 | 1/1 | ungrouped | ungrouped | 0 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | 9 | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | 4 | 0 | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | ungrouped | ungrouped | 0 |
| one-sided-regularization | multi-paper | as asked | 6 | 0/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 4 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-hashing | follow-up | reference rewrite | none | 0/1 | 3 | 1 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 |
| superbpe-mmlu | follow-up | history + follow-up | 2 | 1/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | 3 | 1/1 | 4 | 0 | 1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 1 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: dense.openscholar+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 7 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 | D18-2012 + 1808.06226v1; 2204.04748v1; D18-2012 + 1808.06226v1; 2206.02608v1; 2023.ranlp-1.62 |
| bpe-dropout-rate | single-paper | as asked | 4 | 2/2 | 3 | 0 | 0 | 2023.insights-1.7 + 2305.03029v1; 2023.insights-1.7 + 2305.03029v1; 2023.insights-1.7; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2 |
| bpe-cyrillic | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 | 1610.06510v1; 2023.eamt-1.14 + 2306.01393v1 + 2306.01393v3; 2023.eamt-1.14 + 2306.01393v1 + 2306.01393v3; 2004.02334v1; 2022.findings-acl.194 + 2110.08191v2 + 2110.08191v1 |
| canine-amharic | single-paper | as asked | 2 | 1/1 | ungrouped | ungrouped | 0 | 2404.18810v1; 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2024.naacl-srw.14 + 2404.18810v2; 2024.findings-eacl.9 |
| byt5-span-length | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 | 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2025.findings-emnlp.297 + 2505.17102v1; 2024.tacl-1.22 + 2302.14220v3; 2105.13626v3; 2410.11627v2 + 2410.11627v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 1 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2512.20757v2 + 2512.20757v1; 2407.00894v2 + 2407.00894v1; 2304.14780v1 |
| llama2-70b-vocabulary | single-paper | as asked | none | 0/1 | 1 | 0 | 0 | 2407.13623v3; 2407.13623v3; 2508.11260v1; 2406.11477v3; 2402.01035v2 + 2402.01035v1 |
| xlm-r-tokens-per-language | single-paper | as asked | none | 0/1 | 4 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1 |
| magikarp-verified-share | single-paper | as asked | 6 | 0/1 | 4 | 0 | 0 | 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1; 2024.emnlp-main.649; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | 3 | 1/1 | ungrouped | ungrouped | 0 | 2503.13423v3; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2026.mellm-1.27 |
| fast-wordpiece-speed | single-paper | as asked | 8 | 0/1 | ungrouped | ungrouped | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2202.12142v1; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2023.insights-1.7 + 2305.03029v1; 2023.insights-1.7 + 2305.03029v1; 2023.insights-1.7; W19-6620 + 1905.10453v2; 2023.insights-1.7 + 2305.03029v1 |
| compression-and-accuracy | multi-paper | as asked | 9 | 0/3 | ungrouped | ungrouped | 0 | 2403.06265v2 + 2403.06265v1; 2512.12641v1; 2403.06265v1; 2608.17325v1; 2403.06265v2 + 2403.06265v1 |
| one-sided-regularization | multi-paper | as asked | 3 | 1/3 | 4 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 1910.13267v1 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2402.01035v2 + 2402.01035v1; 2310.08754v4 + 2310.08754v1; 2405.07883v1; 2405.07883v1 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2305.07185v2 + 2305.07185v1; 2305.07185v2 + 2305.07185v1; 2305.07185v2 + 2305.07185v1; 2305.07185v2 + 2305.07185v1; 2412.09871v1 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2410.10665v1; 2506.06446v2; 2305.13707v1 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 | 2504.00178v2 + 2504.00178v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2512.03989v1; 2507.06378v1; 2411.14198v1 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2402.01035v2 + 2402.01035v1; 2406.11214v3; 2512.20757v2 + 2512.20757v1; 2408.04653v1; 2025.findings-emnlp.595 + 2510.15517v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 1707.06961v1; 2410.16410v1; 2020.lrec-1.330; 2609.01151v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | P16-2058 + 1603.00810v1 + 1603.00810v3; 2023.acl-long.326 + 2305.05461v1; 2010.12730v1; 2206.02608v1; W17-4109 + 1709.00028v1 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 | 2022.tacl-1.5 + 2103.06874v4; 2404.18810v1; 2022.tacl-1.5 + 2103.06874v4; 10.5121/ijci.2024.130204; 2023.mrl-1.6 + 2310.08078v1 |
| canine-hashing | follow-up | reference rewrite | 7 | 0/1 | 3 | 1 | 0 | 2022.tacl-1.5 + 2103.06874v4 + 2103.06874v1; 2112.10508v1; 2103.06874v1; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2103.06874v1 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | D18-1278 + 1808.09180v1; P16-2058 + 1603.00810v3 + 1603.00810v1; 2023.acl-long.326 + 2305.05461v1; 2010.12730v1; 2302.14220v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2602.10416v1; 2402.14903v1; 1909.07940v2 + 1909.07940v1; 1909.07940v2 + 1909.07940v1; 2305.14201v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2407.00894v2 + 2407.00894v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 2602.10416v1; 2402.14903v1; 1909.07940v2 + 1909.07940v1; 1909.07940v2 + 1909.07940v1; 2402.14903v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2212.11281v1; 2502.20273v1; 2021.emnlp-main.161 + 2109.02550v1 + 2109.02550v2; 2212.11281v1; 2402.01035v2 + 2402.01035v1 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v1; 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2502.20273v1; 2502.20273v1; 2608.17325v1; 2004.04002v2 + 2004.04002v1; 2022.amta-research.8 + 2204.14268v1 + 2204.14268v2 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2607.29065v1; 2021.acl-long.243 + 2012.15613v2; 2022.naacl-main.179 + 2206.02608v1; 2610.04002v1; 2024.mrl-1.1 + 2404.05829v1 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2512.03989v1; 2402.01035v2 + 2402.01035v1; 2607.29065v1; 2310.08754v4 + 2310.08754v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 | 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2402.01035v2 + 2402.01035v1; 2310.08754v4 + 2310.08754v1; 2607.29065v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2607.29065v1; 2022.naacl-main.179 + 2206.02608v1; 2021.acl-long.243 + 2012.15613v2; 2610.04002v1; 2023.acl-short.1 + 2306.17757v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v2 + 2408.08541v1; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 | 2406.11477v3; 2411.18553v1; 2507.04886v4 + 2507.04886v1; 2403.16854v3 + 2403.16854v1; 2411.18553v1 |
| superbpe-mmlu | follow-up | history + follow-up | 1 | 1/1 | 4 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 |
| superbpe-mmlu | follow-up | reference rewrite | 2 | 1/1 | 4 | 0 | 1 | 2503.13423v3; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 1 | 2507.04886v4 + 2507.04886v1; 2406.11477v3; 2403.01858v3 + 2403.01858v1; 2403.01858v3; 2506.04079v2 + 2506.04079v1 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2601.11518v1; 2601.11518v1; 2601.11518v1; 2602.05347v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | none | 0/1 | ungrouped | ungrouped | 0 | 2601.11518v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2305.15425v2; 2305.15425v2 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v2 + 2408.08541v1; 2601.11518v1; 2601.11518v1; 2602.05347v1; 2601.11518v1 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | 2302.14220v1; 2302.14220v1; 2302.14220v1; 2024.tacl-1.22 + 2302.14220v1 + 2302.14220v3; W18-1207 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2412.09871v1; 2507.04886v4 + 2507.04886v1; 2412.09871v1; 2412.09871v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2310.08754v4; 2023.acl-long.402; 2412.09871v1; 2605.08044v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2202.12142v1; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 + 2012.15524v1; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | 10.7469/JKSQM.2020.48.3.421; D18-2012 + 1808.06226v1; D18-2012 + 1808.06226v1; 2021.naacl-industry.13; D18-2012 + 1808.06226v1 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2024.tacl-1.22 + 2302.14220v3; 2024.findings-eacl.9; 2022.tacl-1.17 + 2105.13626v1 + 2105.13626v3; 2020.wmt-1.90 + 2008.08769v1; 2506.04079v2 + 2506.04079v1 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2403.03814v2; 2510.15346v2 + 2510.15346v1; 2403.03814v1; 2503.10883v1; 2503.10883v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | D19-1534 + 1909.07940v1 + 1909.07940v2; 2205.05093v1; 2212.09912v1; 2503.02174v2 + 2503.02174v1; 2107.03006v3 + 2107.03006v1 |

### Questions: hybrid.bm25+bge-small

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | 1 | 0 | 0 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 3 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | 4 | 1/1 | 0 | 0 | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 2 |
| byt5-span-length | single-paper | as asked | 6 | 0/1 | 3 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | 5 | 1/1 | 2 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | 2 | 1/2 | 1 | 0 | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 4 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | 7 | 0/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | 9 | 0/2 | 3 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | 3 | 1/1 | 3 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 2 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 5 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 6 | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 3 | 1/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | 3 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | 9 | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 |
| tokenization-latency | follow-up | rewriter | 2 | 1/1 | ungrouped | ungrouped | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: hybrid.bm25+bge-small+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | 2505.16868v1; D18-2012 + 1808.06226v1; 2610.12144v1; 2008.09396v1; W7217633576 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 2 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2005.06606v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2022.amta-research.8 |
| bpe-cyrillic | single-paper | as asked | 4 | 1/1 | 0 | 0 | 0 | C18-1052; W18-1207; 2508.01685v1; P16-1162 + 1508.07909v5 + 1508.07909v1; W19-6620 + 1905.10453v1 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 2 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2024.naacl-srw.14 + 2404.18810v1 + 2404.18810v2 |
| byt5-span-length | single-paper | as asked | 3 | 1/1 | 1 | 0 | 0 | 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2025.findings-emnlp.297 + 2505.17102v1; 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2411.11808v1; 2410.20771v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2512.20757v2 + 2512.20757v1 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| xlm-r-tokens-per-language | single-paper | as asked | 2 | 1/1 | ungrouped | ungrouped | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2024.iwclul-1.11; 2509.18750v2 + 2509.18750v1 |
| magikarp-verified-share | single-paper | as asked | 10 | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1; 2405.05417v1; 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | 5 | 1/1 | 2 | 0 | 0 | 2025.babylm-main.16; 2604.05192v2 + 2604.05192v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2012.15524v1; 2021.emnlp-main.160 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | 2 | 1/2 | 1 | 0 | 0 | 2020.lrec-1.450; P16-1162 + 1508.07909v5; W18-1207; 2023.insights-1.7 + 2305.03029v1; 2020.lrec-1.450 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 | 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2609.15528v1 |
| one-sided-regularization | multi-paper | as asked | 4 | 1/3 | 2 | 0 | 0 | 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2023.ranlp-1.62; 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.275 + 2005.06606v1 + 2005.06606v2 |
| tokenizer-swap-budget | multi-paper | as asked | 7 | 0/2 | 2 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2405.07883v2 + 2405.07883v1; 2607.15232v1; 2607.15232v1; 2405.07883v2 + 2405.07883v1 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2412.09871v1; 2412.09871v1; 2404.14408v3 + 2404.14408v1; 2412.09871v1; 2412.09871v1 |
| api-cost-by-language | multi-paper | as asked | 9 | 0/2 | 3 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2506.06446v2; 2506.06446v2; 2609.39001v1 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 | 2512.03989v1; 2411.14198v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2504.00178v1; 2609.12960v1 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 | 2610.19801v1; 2610.12144v1; 2608.18062v3 + 2608.18062v1; 2402.14903v1; 2610.13325v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2311.08849v2 + 2311.08849v1; 2010.12730v1; 2311.08849v2; 1805.03710v1 |
| wechsel-neighbours | follow-up | history + follow-up | 8 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| wechsel-neighbours | follow-up | reference rewrite | 3 | 1/1 | 3 | 0 | 0 | 2025.findings-acl.109; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 |
| wechsel-neighbours | follow-up | rewriter | 8 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2010.12730v1; 2021.findings-emnlp.141 + 2010.12730v3; 2610.04002v1; Q17-1026 + 1610.03017v3; 2024.findings-acl.302 |
| canine-hashing | follow-up | history + follow-up | 5 | 1/1 | 3 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5; 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5 + 2103.06874v1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 1 | 0 | 0 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2305.15425v2 + 2305.15425v1; 2507.04886v4 + 2507.04886v1; 2022.emnlp-main.536 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2605.09751v2; 2610.04002v1; 2021.naacl-main.17 + 2008.09396v2; 2610.04002v1; 2010.12730v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2402.14903v1; 2602.10416v1; 2502.19981v1; 2502.19981v1; 2102.13019v3 + 2102.13019v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2510.06824v2 + 2510.06824v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2305.14201v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 | 2402.14903v1; 2602.10416v1; 2502.19981v1; 2502.19981v1; 2102.13019v3 + 2102.13019v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2602.13266v1; 2405.14159v2 + 2405.14159v1; 2407.16607v4; 2024.repl4nlp-1.10 + 2401.07923v1 + 2401.07923v2; 2405.14159v2 + 2405.14159v1 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 4 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 | 2602.13266v1; 2405.14159v2 + 2405.14159v1; 2407.16607v4; 2411.14198v1; 2405.14159v2 + 2405.14159v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 | 2505.20133v3 + 2505.20133v1; 2511.14365v1; 2601.13260v2; 2003.07914v1; 2505.20133v3 + 2505.20133v1 |
| code-tokenizer-initialisation | follow-up | history + follow-up | 10 | 0/1 | 1 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2607.15232v1; 2024.iwclul-1.13 + 2501.02631v1; 2607.15232v1; 2405.07883v2 + 2405.07883v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 4 | 1/1 | 1 | 0 | 0 | 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2607.15232v1; 2402.01035v2 + 2402.01035v1; 2024.iwclul-1.13 + 2501.02631v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2505.20133v3 + 2505.20133v1; 2511.14365v1; 2604.02324v2 + 2604.02324v1; 2003.07914v1; 2505.20133v3 + 2505.20133v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 2510.06244v1; 2010.01003v1; 2610.14427v1; 2112.09348v1; 2608.21106v3 + 2608.21106v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | 2 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | rewriter | 9 | 0/1 | 3 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.925 + 2409.04599v1; 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 2510.13481v2 + 2510.13481v1; 2509.05486v1; 2410.18836v1; 2607.15232v1; 2509.15020v1 |
| superbpe-mmlu | follow-up | history + follow-up | 8 | 0/1 | 3 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2025.babylm-main.16; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | reference rewrite | 4 | 1/1 | 4 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2410.18836v1; 2509.15020v1; 2407.12869v2 + 2407.12869v1; 2607.15232v1; 2510.13481v2 + 2510.13481v1 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | ungrouped | ungrouped | 0 | 2305.15425v2 + 2305.15425v1; 2511.04952v1; 2305.15425v1; 2510.15346v2; 2603.22774v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2305.13707v1; 2305.13707v1; 2305.15425v2 + 2305.15425v1; 2305.13707v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v1; 2608.25904v3 + 2608.25904v1; 2305.15425v1; 2305.15425v2 + 2305.15425v1 |
| tokenization-latency | follow-up | rewriter | 2 | 1/1 | ungrouped | ungrouped | 0 | 2511.04952v1; 2305.15425v2 + 2305.15425v1; 2510.15346v2; 2602.07698v2 + 2602.07698v1; 2305.15425v1 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | 2020.wmt-1.9; P16-1162 + 1508.07909v5; 2017.mtsummit-papers.18 + 1704.04520v6 + 1704.04520v1; 2023.icon-1.24; 2020.emnlp-main.203 + 2004.14280v2 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2412.09871v1; 2305.07185v1; 2412.09871v1; 2605.08044v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2610.01984v2 + 2610.01984v1; 2402.18376v2 + 2402.18376v1; 2310.08754v4; 2023.emnlp-main.459 + 2305.05480v3; 2004.06343v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2606.20993v1; 2021.emnlp-main.160 + 2012.15524v3; 2607.29678v3 + 2607.29678v1; P16-1160 + 1603.06147v4; 2606.17358v3 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | 2025.loresmt-1.8; 2020.aacl-main.17 + 2010.02534v1; 2021.naacl-industry.13; D18-2012 + 1808.06226v1; 2008.03979v2 + 2008.03979v1 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2410.03730v3; 2508.15390v3; 2022.tacl-1.17 + 2105.13626v3; 2410.03730v3; 2602.05879v1 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2502.03275v2 + 2502.03275v1; 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2408.07065v1; 2106.06297v1; 2205.05093v1; 2607.17689v1; 2205.05093v1 |

### Questions: hybrid.bm25+bge-base

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | 10 | 0/1 | ungrouped | ungrouped | 0 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 3 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | 3 | 1/1 | ungrouped | ungrouped | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 1 |
| byt5-span-length | single-paper | as asked | 9 | 0/1 | 3 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | none | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | 10 | 0/1 | 2 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | 9 | 0/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | 5 | 1/2 | 3 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 1 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | 1 | 1/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 6 | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | 1 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 7 | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 2 | 1/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | 0 | 0 | 0 |
| tokenization-latency | follow-up | follow-up alone | 2 | 1/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | rewriter | 3 | 1/1 | ungrouped | ungrouped | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: hybrid.bm25+bge-base+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2112.06598v1 |
| sentencepiece-whitespace | single-paper | as asked | 7 | 0/1 | ungrouped | ungrouped | 0 | 10.54254/2755-2721/2026.37609; D18-2012 + 1808.06226v1; 2608.08847v2 + 2608.08847v1; 2101.09635v2 + 2101.09635v1; 2020.aacl-main.17 + 2010.02534v1 |
| bpe-dropout-rate | single-paper | as asked | 1 | 2/2 | 3 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2005.06606v1; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2 |
| bpe-cyrillic | single-paper | as asked | 3 | 1/1 | ungrouped | ungrouped | 0 | 2023.icon-1.19; W18-1207; P16-1162 + 1508.07909v5 + 1508.07909v1; 2022.amta-research.9 + 2208.05225v2 + 2208.05225v1; W19-6620 + 1905.10453v1 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5 + 2103.06874v4; 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1 |
| byt5-span-length | single-paper | as asked | 6 | 0/1 | 0 | 0 | 0 | 2022.tacl-1.17 + 2105.13626v1 + 2105.13626v3; 2025.findings-emnlp.297 + 2505.17102v1; 2411.11808v1; 2410.20771v1; 2410.11627v2 + 2410.11627v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2512.20757v2 + 2512.20757v1 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| xlm-r-tokens-per-language | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1 |
| magikarp-verified-share | single-paper | as asked | 10 | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1 |
| superbpe-curriculum | single-paper | as asked | 8 | 0/1 | 2 | 0 | 0 | 2025.babylm-main.16; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2504.00178v2 + 2504.00178v1 |
| fast-wordpiece-speed | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3; 2012.15524v1 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2020.lrec-1.450; 2024.findings-emnlp.860; 2023.insights-1.7 + 2305.03029v1; W18-1207; 2020.lrec-1.450 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 | 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2024.emnlp-main.40 + 2402.18376v2 + 2402.18376v1; 2024.emnlp-main.40 + 2402.18376v2; 2024.emnlp-main.40 + 2402.18376v2 |
| one-sided-regularization | multi-paper | as asked | 4 | 1/3 | 3 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2; 2023.ranlp-1.62 |
| tokenizer-swap-budget | multi-paper | as asked | 3 | 1/2 | 3 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 3 | 0 | 0 | 2412.09871v1; 2412.09871v1; 2412.09871v1; 2305.07185v2 + 2305.07185v1; 2305.07185v2 + 2305.07185v1 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2506.06446v2; 2506.06446v2; 2403.05434v2 + 2403.05434v1; 2410.10665v1; 2506.06446v2 |
| renyi-efficiency | multi-paper | as asked | 8 | 0/2 | 1 | 0 | 0 | 2512.03989v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2507.06378v1; 2508.08424v3 + 2508.08424v1 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2402.14903v1; 2608.18062v3; 2610.19801v1; 2610.12144v1; 2608.12756v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2021.mrl-1.3; 2311.08849v2; 2021.findings-emnlp.141 + 2010.12730v3; 2024.conll-1.8 + 2407.05841v1 + 2407.05841v2; 2025.findings-emnlp.379 |
| wechsel-neighbours | follow-up | history + follow-up | 8 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 |
| wechsel-neighbours | follow-up | reference rewrite | 8 | 0/1 | 3 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2410.06898v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | rewriter | 8 | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2010.12730v1; 2021.naacl-main.17 + 2008.09396v2; 2610.04002v1; 2021.findings-emnlp.141 + 2010.12730v3; 2010.12730v1 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 3 | 0 | 0 | 2022.tacl-1.5 + 2103.06874v4; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2507.04886v4 + 2507.04886v1; 2103.06874v1; 2022.tacl-1.5 + 2103.06874v4 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2021.naacl-main.17 + 2008.09396v2 + 2008.09396v1; 2610.04002v1; 2010.12730v1; Q17-1026 + 1610.03017v3; 2603.19269v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2402.14903v1; 1909.07940v2 + 1909.07940v1; 2602.10416v1; 2502.19981v1; D19-1534 + 1909.07940v1 + 1909.07940v2 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2608.18062v3 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2402.14903v1; 1909.07940v2 + 1909.07940v1; 2602.10416v1; 2502.19981v1; D19-1534 + 1909.07940v1 + 1909.07940v2 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | 1 | 1/1 | 0 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2602.13266v1; 2405.14159v2 + 2405.14159v1; 2407.16607v4; 2024.repl4nlp-1.10 + 2401.07923v1 + 2401.07923v2 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 4 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2602.13266v1; 2405.14159v2 + 2405.14159v1; 2407.16607v4; 2411.14198v1; 2004.06343v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2505.20133v3 + 2505.20133v1; 2510.21954v1; 2608.03494v1; 2003.07914v1; 2405.07883v2 + 2405.07883v1 |
| code-tokenizer-initialisation | follow-up | history + follow-up | 10 | 0/1 | 2 | 0 | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2510.21954v2 + 2510.21954v1; 2405.07883v2 + 2405.07883v1 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 5 | 1/1 | 1 | 0 | 0 | 2607.15232v1; 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2510.21954v2 + 2510.21954v1; 2402.01035v2 + 2402.01035v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2505.20133v3 + 2505.20133v1; 2510.21954v1; 2608.03494v1; 2003.07914v1; 2405.07883v2 + 2405.07883v1 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2609.01386v1; 2510.06244v1; 2506.11115v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2405.05417v1; 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | 2 | 1/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 | 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 | 2410.18836v1; 2509.05486v1; 2607.15232v1; 2603.15953v1; 2305.15108v1 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2025.babylm-main.16; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | reference rewrite | 9 | 0/1 | 4 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | 0 | 0 | 0 | 2410.18836v1; 2510.13481v2 + 2510.13481v1; 2405.14159v2; 2509.15020v1; 2607.15232v1 |
| tokenization-latency | follow-up | follow-up alone | 2 | 1/1 | ungrouped | ungrouped | 0 | 2511.04952v1; 2305.15425v2 + 2305.15425v1; 2411.17669v1; 2602.07698v2 + 2602.07698v1; 2305.15425v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2608.25904v3 + 2608.25904v1; 2305.15425v2 + 2305.15425v1 |
| tokenization-latency | follow-up | rewriter | 3 | 1/1 | ungrouped | ungrouped | 0 | 2511.04952v1; 2602.07698v2 + 2602.07698v1; 2305.15425v2 + 2305.15425v1; 2411.17669v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | 2022.aacl-short.12; P16-1162 + 1508.07909v5; 2110.01938v1; 1711.04457v1; 2017.mtsummit-papers.18 + 1704.04520v6 + 1704.04520v1 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2412.09871v1; 2412.09871v1; 2305.07185v1; 2412.09871v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2023.emnlp-main.459 + 2305.05480v3; 2203.09963v1; 2310.08754v4; 2412.09871v1; 2402.18376v2 + 2402.18376v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2302.09207v3 + 2302.09207v1; 2021.emnlp-main.160 + 2012.15524v3; 2607.29678v3 + 2607.29678v1; 2606.20993v1; 2606.17358v3 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | 2025.loresmt-1.8; 2502.12560v2 + 2502.12560v1; 2020.aacl-main.17 + 2010.02534v1; 2008.03979v2 + 2008.03979v1; 10.1109/ACCESS.2020.3004879 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | W19-6620 + 1905.10453v1 + 1905.10453v2; 2410.03730v3; 2507.15773v2 + 2507.15773v1; 2508.15390v3; 2201.13242v2 + 2201.13242v1 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2403.05434v2 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2408.07065v1; 2106.06297v1; 2106.06297v1; 2205.05093v1; 2607.17689v1 |

### Questions: hybrid.bm25+openscholar

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots |
|---|---|---|---:|---:|---:|---:|---:|
| wechsel-freezing | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 |
| bpe-dropout-rate | single-paper | as asked | 2 | 2/2 | 4 | 0 | 0 |
| bpe-cyrillic | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | 3 | 0 | 1 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 2 | 0 | 0 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 |
| xlm-r-tokens-per-language | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| magikarp-verified-share | single-paper | as asked | 6 | 0/1 | 4 | 0 | 0 |
| superbpe-curriculum | single-paper | as asked | 4 | 1/1 | 4 | 0 | 0 |
| fast-wordpiece-speed | single-paper | as asked | 3 | 1/1 | 4 | 0 | 0 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 |
| compression-and-accuracy | multi-paper | as asked | none | 0/3 | 3 | 0 | 0 |
| one-sided-regularization | multi-paper | as asked | 1 | 1/3 | 4 | 0 | 0 |
| tokenizer-swap-budget | multi-paper | as asked | 4 | 1/2 | 3 | 0 | 0 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| api-cost-by-language | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 1 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 2 | 0 | 0 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 10 | 0/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 3 | 1/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 |
| superbpe-mmlu | follow-up | history + follow-up | 8 | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | 2 | 1/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 2 | 1/1 | ungrouped | ungrouped | 0 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: hybrid.bm25+openscholar+collapsed

| Question | Type | Query | First hit | Passages found | Duplicate slots | Restatement slots | Numeric slots | Top-5 files + merged |
|---|---|---|---:|---:|---:|---:|---:|---|
| wechsel-freezing | single-paper | as asked | 1 | 1/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| sentencepiece-whitespace | single-paper | as asked | none | 0/1 | ungrouped | ungrouped | 0 | 2023.paclic-1.64; 2606.23566v2 + 2606.23566v1; C16-1301; 2608.08847v2 + 2608.08847v1; D18-2012 + 1808.06226v1 |
| bpe-dropout-rate | single-paper | as asked | 2 | 2/2 | 3 | 0 | 0 | 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2022.amta-research.9 + 2208.05225v1 + 2208.05225v2 |
| bpe-cyrillic | single-paper | as asked | 9 | 0/1 | ungrouped | ungrouped | 0 | W17-4102 + 1610.06510v3 + 1610.06510v1; C18-1052; 1911.00317v1; W19-6620; 2021.wat-1.21 |
| canine-amharic | single-paper | as asked | 1 | 1/1 | ungrouped | ungrouped | 2 | 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5; 2103.06874v4; 2404.18810v1 |
| byt5-span-length | single-paper | as asked | none | 0/1 | 0 | 0 | 0 | 2022.tacl-1.17 + 2105.13626v3 + 2105.13626v1; 2411.11808v1; 2025.findings-emnlp.297 + 2505.17102v1; 2410.11627v2 + 2410.11627v1; 2410.20771v1 |
| digits-right-to-left | single-paper | as asked | none | 0/1 | 3 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2512.20757v2 + 2512.20757v1 |
| llama2-70b-vocabulary | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2407.13623v3; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| xlm-r-tokens-per-language | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1; 2301.10472v2 + 2301.10472v1 |
| magikarp-verified-share | single-paper | as asked | 4 | 1/1 | 4 | 0 | 0 | 2405.05417v1; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1; 2024.emnlp-main.649 |
| superbpe-curriculum | single-paper | as asked | 3 | 1/1 | 3 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2025.babylm-main.16; 2503.13423v3 + 2503.13423v1 |
| fast-wordpiece-speed | single-paper | as asked | 2 | 1/1 | 4 | 0 | 0 | 2021.emnlp-main.160 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 + 2012.15524v1; 2012.15524v1; 2021.emnlp-main.160 + 2012.15524v1 + 2012.15524v3; 2021.emnlp-main.160 + 2012.15524v3 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | none | 0/2 | ungrouped | ungrouped | 0 | 2023.insights-1.7 + 2305.03029v1; 1809.02223v1; 2023.americasnlp-1.9; 2023.insights-1.7 + 2305.03029v1; W19-6620 + 1905.10453v1 + 1905.10453v2 |
| compression-and-accuracy | multi-paper | as asked | 7 | 0/3 | 3 | 0 | 0 | 2403.06265v2 + 2403.06265v1; 2024.emnlp-main.40 + 2402.18376v2; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1; 2403.06265v2 + 2403.06265v1 |
| one-sided-regularization | multi-paper | as asked | 1 | 1/3 | 3 | 0 | 0 | 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2 + 1910.13267v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2020.acl-main.170 + 1910.13267v2; 2020.acl-main.275 + 2005.06606v2 + 2005.06606v1 |
| tokenizer-swap-budget | multi-paper | as asked | 2 | 1/2 | ungrouped | ungrouped | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2405.07883v2 + 2405.07883v1; 2405.07883v2 + 2405.07883v1; 2506.14123v3; 2502.20273v4 |
| megabyte-and-blt-patches | multi-paper | as asked | none | 0/2 | 2 | 0 | 0 | 2404.14408v3 + 2404.14408v1; 2412.09871v1; 2412.09871v1; 2305.07185v2 + 2305.07185v1; 2305.07185v2 + 2305.07185v1 |
| api-cost-by-language | multi-paper | as asked | 10 | 0/2 | 1 | 0 | 0 | 2506.06446v2; 2410.10665v1; 2403.05434v2 + 2403.05434v1; 2506.06446v2; 2305.13707v1 |
| renyi-efficiency | multi-paper | as asked | none | 0/2 | 0 | 0 | 0 | 2507.06378v1; 2512.03989v1; 2024.lrec-main.1469 + 2402.14614v1 + 2402.14614v2; 2508.08424v3 + 2508.08424v1; 2609.12960v1 |
| gpt-4-number-tokens | multi-paper | as asked | none | 0/2 | 1 | 0 | 0 | 2610.12144v1; 2610.12144v1; 2402.14903v1; 2610.19801v1; 2402.01035v2 + 2402.01035v1 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2311.08849v2; 1707.06961v1; 2024.conll-1.8 + 2407.05841v1 + 2407.05841v2 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| wechsel-neighbours | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1 |
| wechsel-neighbours | follow-up | rewriter | none | 0/1 | 4 | 0 | 0 | 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v2 + 2112.06598v1; 2022.naacl-main.293 + 2112.06598v1 + 2112.06598v2 |
| canine-hashing | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2010.12730v1; 2610.04002v1; 2021.naacl-main.17 + 2008.09396v2; Q17-1026 + 1610.03017v3; P16-2058 + 1603.00810v1 + 1603.00810v3 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 2 | 2022.tacl-1.5 + 2103.06874v4; 2023.mrl-1.6 + 2310.08078v1; 2022.tacl-1.5; 2103.06874v4; 2103.06874v4 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 1 | 1 | 0 | 2103.06874v4; 2022.emnlp-main.536; 2022.tacl-1.5 + 2103.06874v1 + 2103.06874v4; 2305.15425v2 + 2305.15425v1; 2112.10508v1 |
| canine-hashing | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2010.12730v1; 2610.04002v1; Q17-1026 + 1610.03017v3; D18-1278 + 1808.09180v1; 2603.19269v1 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 | 1909.07940v2 + 1909.07940v1; 2602.10416v1; 2402.14903v1; 1909.07940v2 + 1909.07940v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 | 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1; 2402.14903v1 |
| digits-fourth-digit | follow-up | rewriter | none | 0/1 | 2 | 0 | 0 | 1909.07940v2 + 1909.07940v1; 2602.10416v1; 2402.14903v1; 1909.07940v2 + 1909.07940v1; 2402.14903v1 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2212.11281v1; 2402.01035v2 + 2402.01035v1; 2602.13266v1; 2407.16607v4; 2502.20273v1 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3; 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 7 | 0/1 | 4 | 0 | 0 | 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1; 2407.13623v3 + 2407.13623v1 |
| vocabulary-with-scarce-data | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2212.11281v1; 2407.16607v4; 2402.01035v2 + 2402.01035v1; 2602.13266v1; 2502.20273v1 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2003.07914v1; 2607.29065v1; 2601.13328v1; 2021.acl-long.243 + 2012.15613v2; 10.1186/s12859-026-06562-5 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | ungrouped | ungrouped | 0 | 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2024.iwclul-1.13 + 2501.02631v1; 2405.07883v2 + 2405.07883v1; 2506.14123v3; 2026.findings-eacl.341 + 2512.03989v1 + 2512.03989v2 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 7 | 0/1 | 2 | 0 | 0 | 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v2 + 2512.03989v1; 2026.findings-eacl.341 + 2512.03989v1 + 2512.03989v2; 2406.14670v2 + 2406.14670v1; 2024.iwclul-1.13 + 2501.02631v1 |
| code-tokenizer-initialisation | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2003.07914v1; 2607.29065v1; 2601.13328v1; 2022.naacl-main.179 + 2206.02608v1; 10.1186/s12859-026-06562-5 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.230 + 2408.08541v2; 2510.06244v1; 2024.emnlp-main.230 + 2408.08541v2; 2610.14427v1 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 | 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v2 + 2405.05417v1 |
| magikarp-norm-indicator | follow-up | reference rewrite | 3 | 1/1 | 4 | 0 | 0 | 2405.05417v1; 2024.emnlp-main.649 + 2405.05417v1 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2; 2024.emnlp-main.649 + 2405.05417v2 |
| magikarp-norm-indicator | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; W17-4106; 2024.emnlp-main.230 + 2408.08541v2 + 2408.08541v1; 2609.15528v1; 2510.09947v2 + 2510.09947v1 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 1 | 2509.05486v1; 2406.11477v3; 2023.findings-acl.548; 2023.acl-short.34; 2023.acl-long.699 |
| superbpe-mmlu | follow-up | history + follow-up | 5 | 1/1 | 3 | 0 | 0 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2025.babylm-main.16; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 1 | 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1; 2503.13423v3 + 2503.13423v1 |
| superbpe-mmlu | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2410.18836v1; 2509.05486v1; 2607.15232v1; 2506.14761v1; 2507.04886v4 + 2507.04886v1 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | ungrouped | ungrouped | 0 | 2602.07698v2 + 2602.07698v1; 2105.13626v3 + 2105.13626v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2024.emnlp-main.230 + 2408.08541v1 + 2408.08541v2; 2024.emnlp-main.925 + 2409.04599v1 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 | 2305.13707v1; 2305.13707v1; 2305.13707v1; 2305.15425v2 + 2305.15425v1; 2305.13707v1 |
| tokenization-latency | follow-up | reference rewrite | 2 | 1/1 | ungrouped | ungrouped | 0 | 2305.15425v2 + 2305.15425v1; 2305.15425v2 + 2305.15425v1; 2402.10712v3; 2305.15425v2; 2305.15425v2 |
| tokenization-latency | follow-up | rewriter | none | 0/1 | ungrouped | ungrouped | 0 | 2602.07698v2 + 2602.07698v1; 2105.13626v3 + 2105.13626v1; 2020.acl-main.170 + 1910.13267v1 + 1910.13267v2; 2024.emnlp-main.230 + 2408.08541v2 + 2408.08541v1; 2024.emnlp-main.925 + 2409.04599v1 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — | 2020.wmt-1.9; 2020.wmt-1.9; 1711.04457v1; C18-1052; P16-1162 + 1508.07909v5 |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2412.09871v1; 2412.09871v1; 2412.09871v1; 2609.00463v1 |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — | 2412.09871v1; 2023.acl-long.402; 2610.01984v2 + 2610.01984v1; 2310.08754v4; 2412.09871v1 |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — | 2021.emnlp-main.160 + 2012.15524v3 + 2012.15524v1; 2610.04951v1; 2606.17358v3; 2202.12142v1; 2610.19801v1 |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — | 2502.12560v2 + 2502.12560v1; 1812.08621v4 + 1812.08621v1; 2601.06142v1; 2021.naacl-industry.13; 2021.naacl-industry.13 |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — | 2302.14220v1; 2022.tacl-1.17 + 2105.13626v3; 2410.03730v3; 2308.09440v3; 2024.tacl-1.22 + 2302.14220v3 |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — | 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2510.15346v1; 2510.15346v2 + 2510.15346v1; 2510.15346v2 + 2510.15346v1 |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — | 2205.05093v1; 2405.17067v2; 2607.17689v1; 2205.05093v1; 2021.americasnlp-1.22 |

## Cost

Each retriever's model and index, with how long the index took to build and each query took. A hybrid's parameters, dimension and index are its members' summed (BM25 has no model and no vectors), and its build time is theirs; a `+collapsed` twin uses its retriever's index. The times depend on the machine and change from run to run.

| Retriever | Parameters | Dimension | Index on disk | Built on | Build time | Queries | Queried on | Latency p50 | Latency p95 |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|
| bm25 | — | — | 140.3 MB | cpu | 9.35 s | 60 | cpu | 217.51 ms | 346.47 ms |
| bm25+collapsed | — | — | 140.3 MB | cpu | 9.35 s | 60 | cpu | 251.42 ms | 371.19 ms |
| dense.bge-small | 33.4M | 384 | 220.6 MB | mps | 1318.64 s | 60 | mps | 29.47 ms | 35.69 ms |
| dense.bge-small+collapsed | 33.4M | 384 | 220.6 MB | mps | 1318.64 s | 60 | mps | 43.21 ms | 70.21 ms |
| dense.bge-base | 109.5M | 768 | 437.8 MB | mps | 2878.28 s | 60 | mps | 41.65 ms | 47.83 ms |
| dense.bge-base+collapsed | 109.5M | 768 | 437.8 MB | mps | 2878.28 s | 60 | mps | 64.04 ms | 114.01 ms |
| dense.openscholar | 109.5M | 768 | 437.8 MB | mps | 5081.47 s | 60 | mps | 47.28 ms | 80.18 ms |
| dense.openscholar+collapsed | 109.5M | 768 | 437.8 MB | mps | 5081.47 s | 60 | mps | 54.92 ms | 90.49 ms |
| hybrid.bm25+bge-small | 33.4M | 384 | 361.0 MB | cpu+mps | 1327.99 s | 60 | cpu+mps | 260.89 ms | 431.13 ms |
| hybrid.bm25+bge-small+collapsed | 33.4M | 384 | 361.0 MB | cpu+mps | 1327.99 s | 60 | cpu+mps | 301.03 ms | 463.56 ms |
| hybrid.bm25+bge-base | 109.5M | 768 | 578.1 MB | cpu+mps | 2887.63 s | 60 | cpu+mps | 279.23 ms | 471.17 ms |
| hybrid.bm25+bge-base+collapsed | 109.5M | 768 | 578.1 MB | cpu+mps | 2887.63 s | 60 | cpu+mps | 310.08 ms | 456.40 ms |
| hybrid.bm25+openscholar | 109.5M | 768 | 578.1 MB | cpu+mps | 5090.82 s | 60 | cpu+mps | 278.26 ms | 438.98 ms |
| hybrid.bm25+openscholar+collapsed | 109.5M | 768 | 578.1 MB | cpu+mps | 5090.82 s | 60 | cpu+mps | 317.98 ms | 446.34 ms |
