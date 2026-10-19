# 0065. The embedding comparison on the raw ranking: bge-small stays

- **Date:** 2026-10-20
- **Status:** Proposed. It is accepted, or changed, when #61 scores the comparison again on the Collapsed ranking, which the chatbot retrieves with.

## Context
The assignment asks for an embedding model picked with evidence: at least two models, one suited to scientific text, whether keyword search should sit beside vector search, Recall@5 and MRR, cost and latency, and a recommendation. Spec #55 set up the comparison and fixed its decision rule before any run:

> Recommend the retriever with the best *all answerable* Recall@5. When its lead over a cheaper retriever is within noise (the bootstrap interval of the difference crosses 0), recommend the cheaper one, judged on index build time, then p50 query latency. If nothing beats `dense.bge-small` beyond noise, it stays the recommendation, and the report says so.

Everything the rule needs is in place: the two candidate models pinned and checked ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)), the BM25 hybrids ([0058](0058-bm25-dense-hybrids-by-reciprocal-rank-fusion.md)) and the Comparison with paired bootstrap intervals ([0061](0061-the-comparison-paired-bootstrap-against-a-baseline.md)). This record is the full run (#60): all seven retrievers built over the full corpus (2,689 files, 141,348 Chunks) and scored on the 36-question Evaluation set, with the rule applied to the raw ranking.

## Decision
**The candidates.**

| Retriever | What it is there to test |
|---|---|
| `bm25` | keyword search alone ([0039](0039-retrieval-tracer-bm25-index-and-evaluate.md)) |
| `dense.bge-small` | the baseline, `BAAI/bge-small-en-v1.5`, 33M parameters ([0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md)) |
| `dense.bge-base` | the size control: `BAAI/bge-base-en-v1.5`, the same family at 110M parameters. A gain over bge-small is what size alone buys, so a scientific model's gain can be put down to its training rather than its size |
| `dense.openscholar` | the scientific candidate: `OpenScholar/OpenScholar_Retriever`, Contriever-base (110M) trained further on peS2o's scientific papers and built to retrieve passages, which is what our index holds |
| `hybrid.bm25+<model>`, one per dense model | keyword search beside vector search, fused by RRF with k = 60 and no tuned weights |

All three dense models embed the same Chunks (context header, newline, text), share the chunker's uncased BERT WordPiece vocabulary and have a 512-token limit. Each is used as its model card or reference code says ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)).

**The headline numbers**, quoted from the committed eval report (`data/eval/eval-report.md`, section Comparison and the Cost table). They cover the 28 answerable questions as a user asks them (the *all answerable* row), each retriever is set against `dense.bge-small`, and the intervals are 95% paired bootstrap intervals (10,000 resamples, seed 55).

| Retriever | Recall@5 [95%] | Difference [95%] | W/T/L | MRR@10 [95%] | Difference [95%] | W/T/L |
|---|---|---|---|---|---|---|
| bm25 | 0.16 [0.04, 0.30] | -0.14 [-0.32, +0.02], within noise | 2/20/6 | 0.118 [0.033, 0.228] | -0.126 [-0.284, +0.025], within noise | 4/13/11 |
| dense.bge-small | 0.30 [0.14, 0.48] | — | — | 0.244 [0.114, 0.393] | — | — |
| dense.bge-base | 0.29 [0.14, 0.46] | -0.02 [-0.12, +0.09], within noise | 1/25/2 | 0.211 [0.083, 0.358] | -0.033 [-0.125, +0.041], within noise | 4/18/6 |
| dense.openscholar | 0.07 [0.00, 0.18] | **-0.23 [-0.41, -0.05], beyond noise** | 1/19/8 | 0.046 [0.010, 0.093] | **-0.199 [-0.343, -0.074], beyond noise** | 3/14/11 |
| hybrid.bm25+bge-small | 0.34 [0.18, 0.52] | +0.04 [-0.09, +0.16], within noise | 3/23/2 | 0.257 [0.127, 0.400] | +0.013 [-0.091, +0.111], within noise | 6/17/5 |
| hybrid.bm25+bge-base | 0.34 [0.18, 0.52] | +0.04 [-0.09, +0.16], within noise | 3/23/2 | 0.237 [0.119, 0.372] | -0.008 [-0.122, +0.114], within noise | 5/14/9 |
| hybrid.bm25+openscholar | 0.28 [0.13, 0.44] | -0.02 [-0.20, +0.14], within noise | 4/20/4 | 0.190 [0.080, 0.315] | -0.054 [-0.208, +0.091], within noise | 6/14/8 |

| Retriever | Parameters | Dimension | Index on disk | Build time (device) | Query p50 (device) |
|---|---:|---:|---:|---|---:|
| bm25 | — | — | 140.3 MB | 9.35 s (cpu) | about 190 ms (cpu) |
| dense.bge-small | 33.4M | 384 | 220.6 MB | 1318.64 s (mps) | about 27 ms (mps) |
| dense.bge-base | 109.5M | 768 | 437.8 MB | 2878.28 s (mps) | about 37 ms (mps) |
| dense.openscholar | 109.5M | 768 | 437.8 MB | 5081.47 s (mps) | about 37 ms (mps) |
| hybrid.bm25+bge-small | 33.4M | 384 | 361.0 MB | 1327.99 s (cpu+mps) | about 220 ms (cpu+mps) |
| hybrid.bm25+bge-base | 109.5M | 768 | 578.1 MB | 2887.63 s (cpu+mps) | about 235 ms (cpu+mps) |
| hybrid.bm25+openscholar | 109.5M | 768 | 578.1 MB | 5090.82 s (cpu+mps) | about 235 ms (cpu+mps) |

Latencies are given to the nearest few milliseconds, as they change from run to run. The build times are those in the report's index records.

**The rule, applied to the raw numbers.**
1. The best *all answerable* Recall@5 is 0.34, shared by `hybrid.bm25+bge-small` and `hybrid.bm25+bge-base`. Both have the same wins, ties and losses against bge-small (3/23/2).
2. Their lead over the cheaper `dense.bge-small` is +0.04, with an interval of [-0.09, +0.16]. That holds 0, so it is within noise, and the rule recommends the cheaper retriever. `dense.bge-small` builds faster than either hybrid (1318.64 s, against 1327.99 s and 2887.63 s, because a hybrid's build includes its dense member's), and it answers a query in about 27 ms against about 220 ms.
3. Nothing beats `dense.bge-small` beyond noise. The only difference beyond noise is OpenScholar's, and it is a loss.

**On the raw ranking, the rule recommends `dense.bge-small`.** The scientific model doesn't help, bge-base's extra size doesn't help, and the hybrids' +0.04 is one answerable question (each moves Recall@5 by about 0.036) that the intervals can't tell from noise. The answer to "should keyword search sit beside vector search?" is "not on this evidence". The hybrids never lose much: `hybrid.bm25+bge-small` wins 3 questions and loses 2. They do help the follow-ups put as their reference rewrite (`hybrid.bm25+bge-small` Recall@5 0.62 against bge-small's 0.50), but the rule is applied to the *all answerable* row, as #55 set.

The recommendation is not final. #61 scores every retriever again through its `+collapsed` twin and applies the rule to those numbers, and the chatbot's retriever is named only then.

**What OpenScholar's checks found** ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)). Its mean pooling matches Contriever's reference code to 6.1e-8 per dimension. Normalising its vectors, which turns Contriever's raw inner product into a cosine, changed the top 10 of every fixture question.

**Why OpenScholar scores so low.** At 0.07 against 0.30 it is the run's surprise, and it is not a wrongly used model:
- *Not the normalisation.* The vectors' norms before normalising sit in a narrow band: from 1.27 to 2.04, median 1.61, over the 6,050 Chunks we measured (each question's cosine top 300 plus its gold Chunks). Re-ranking that pool by raw inner product puts a gold Chunk in the top 5 for 4 of the 28 questions, against 2 by cosine. That is two more questions, still far below bge-small, so the cosine is not why OpenScholar falls short.
- *Not the token limit.* Every model cut the same 5 of 141,348 texts at 512 tokens: Chunks whose headers are unusually long.
- *It finds the paper but not the passage.* 52 of OpenScholar's 140 top-5 slots come from a Passage's paper, about as many as bge-small (55) and bge-base (58). But 44% of its top-5 Chunks have fewer than 40 words, against 5% for bge-small and 9% for bge-base. Across the corpus the share is 12%. These short Chunks are mostly figure captions and short lists from the right paper ("Figure 1: Commandline usage of SentencePiece" is its first hit for the SentencePiece whitespace question, whose gold Chunk ranks 133rd). Every Chunk carries its paper's title and Section in the header. With mean pooling, a short Chunk's vector is mostly that header, so it lies close to any question about the paper. bge's `[CLS]` vector and its query instruction are trained for asymmetric passage search, and don't show this pull. OpenScholar's own datastore embeds passages of 256 words with no header like ours ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)), so our headed, variable-length Chunks are further from its training than from bge's. That last point is an explanation we haven't tested: testing it means changing the indexed text, which #55 holds fixed for every model.
- *Its build time is not the model's.* OpenScholar took 5081 s to embed against bge-base's 2878 s, though the two share an architecture and a tokenizer. Timed again on the same 640 texts, the two tokenise in 0.12 s and run their forward passes in 5.30 s each, and their query latencies in the report match (about 37 ms). The slower build ran overnight straight after bge-base's, and was slow from its first texts; the machine, not the model, made the difference. The report's figure stands as recorded, and the rule never reaches OpenScholar's cost anyway.

So the scientific candidate tests "a model trained on scientific text" fairly at the model level, but against our Chunks it loses on ranking within a paper, not on finding the paper.

## Alternatives considered
- **Paper-level scientific models: SPECTER2 and SciNCL.** They embed a whole paper from its title and abstract, for citation recommendation and paper similarity. We retrieve and cite Chunks of up to 350 tokens, so they answer a different question. They also use SciBERT's SciVocab, not the chunker's vocabulary, so a Chunk's token count would mean something else to them, and SPECTER2 needs the `adapters` library for its retrieval adapter. Rejected in #55, before the run.
- **Other models and sizes.** bge-large, e5-large and 7B embedders: base size already costs 48 minutes or more of embedding per model on MPS, and #55 left them out. Hosted embedding APIs were left out too, as was a reranker such as OpenScholar's cross-encoder, which gets its own issue.
- **Score OpenScholar by raw inner product.** The pool re-rank above shows it would move two questions, not close the gap to bge-small, so the table setting [0052](0052-bge-base-and-openscholar-pinned-and-verified.md) floated (`normalise = false`) isn't worth its key change.
- **Index OpenScholar without the context header, or with Chunks re-cut to 256 words.** This might suit the model better, but it changes the text one model sees and not the others. #55 holds Chunks and indexed text fixed, so the comparison stays one of models.
- **Recommend a hybrid for its +0.04.** That is what the rule exists to prevent: one question's lead, inside the noise, paid for with an eightfold query latency.

## Consequences
- `index` builds all seven retrievers by default, which takes about 2.5 hours on an M1 Max: BM25 about 10 s, bge-small about 22 min, bge-base about 48 min and OpenScholar 48 to 85 min. `--retriever dense.bge-base` builds one at a time. The README says how.
- The committed eval report scores all seven retrievers and their `+collapsed` twins. #61 reads its collapsed rows, applies the rule to them and accepts or changes this record.
- The duplicate and restatement shares of the new retrievers rest on fewer questions: 77 Editions in their top 5s have no Work group, so, for example, `dense.bge-base`'s are over 20 of the 28 questions and `dense.openscholar`'s over 15. The report says so per retriever. The rule reads only Recall@5, so this doesn't touch the recommendation, but grouping those Editions (by hand, [0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md)) would complete the crowding numbers.
- `[chat]` keeps `dense.bge-small` until #61.
