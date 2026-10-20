# 0065. The embedding comparison, raw and collapsed: bge-small stays

- **Date:** 2026-10-20
- **Status:** Accepted. Proposed by #60 on the raw ranking; accepted by #61, which applied the rule again to the Collapsed ranking and found the same retriever.

## Context
The assignment asks for an embedding model picked with evidence: at least two models, one suited to scientific text, whether keyword search should sit beside vector search, Recall@5 and MRR, cost and latency, and a recommendation. Spec #55 set up the comparison and fixed its decision rule before any run:

> Recommend the retriever with the best *all answerable* Recall@5. When its lead over a cheaper retriever is within noise (the bootstrap interval of the difference crosses 0), recommend the cheaper one, judged on index build time, then p50 query latency. If nothing beats `dense.bge-small` beyond noise, it stays the recommendation, and the report says so.

Everything the rule needs is in place: the two candidate models pinned and checked ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)), the BM25 hybrids ([0058](0058-bm25-dense-hybrids-by-reciprocal-rank-fusion.md)) and the Comparison with paired bootstrap intervals ([0061](0061-the-comparison-paired-bootstrap-against-a-baseline.md)). This record is the full run (#60): all seven retrievers built over the full corpus (2,689 files, 141,348 Chunks) and scored on the 36-question Evaluation set, with the rule applied to the raw ranking. #61 applied it again to every retriever's `+collapsed` twin, since the Collapsed ranking ([0053](0053-collapsed-ranking-and-collapsed-twins.md), [0057](0057-the-collapse-merges-copies-not-works.md)) is what the chatbot will retrieve with, and made the final choice on those numbers.

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
2. Their lead over the cheaper `dense.bge-small` is +0.04, with an interval of [-0.09, +0.16]. That holds 0, so it is within noise, and the rule recommends the cheaper retriever. `dense.bge-small` builds faster than either hybrid (1318.64 s, against 1327.99 s and 2887.63 s, because a hybrid's build includes its dense member's), and it answers a query in about 27 ms against about 220 ms. BM25 is cheaper still, but the report has no interval between a hybrid and BM25. The step that settles it is the next one.
3. Nothing beats `dense.bge-small` beyond noise, so by the rule's last clause it stays. BM25 trails it by -0.14 (within noise too, so not shown to be worse), but it doesn't beat it. The only difference beyond noise is OpenScholar's, and it is a loss.

**On the raw ranking, the rule recommends `dense.bge-small`.** The scientific model doesn't help, bge-base's extra size doesn't help, and the hybrids' +0.04 is one answerable question (each moves Recall@5 by about 0.036) that the intervals can't tell from noise. The answer to "should keyword search sit beside vector search?" is "not on this evidence". The hybrids never lose much: `hybrid.bm25+bge-small` wins 3 questions and loses 2. They do help the follow-ups put as their reference rewrite (`hybrid.bm25+bge-small` Recall@5 0.62 against bge-small's 0.50), but the rule is applied to the *all answerable* row, as #55 set.

**The collapsed numbers**, from the same report's Comparison, where each `+collapsed` twin is set against `dense.bge-small+collapsed`. The raw numbers are repeated beside them. A twin uses its retriever's index, so its cost is its retriever's (the Cost table gives the same build times, and latencies within a few milliseconds).

| Retriever | Recall@5 raw | Recall@5 collapsed [95%] | Difference collapsed [95%] | W/T/L | MRR@10 raw | MRR@10 collapsed [95%] | Difference collapsed [95%] | W/T/L |
|---|---|---|---|---|---|---|---|---|
| bm25 | 0.16 | 0.20 [0.07, 0.34] | -0.18 [-0.36, +0.00], within noise | 2/19/7 | 0.118 | 0.138 [0.048, 0.250] | -0.133 [-0.286, +0.015], within noise | 4/11/13 |
| dense.bge-small | 0.30 | 0.38 [0.20, 0.55] | — | — | 0.244 | 0.271 [0.142, 0.418] | — | — |
| dense.bge-base | 0.29 | 0.32 [0.14, 0.50] | -0.05 [-0.18, +0.07], within noise | 1/24/3 | 0.211 | 0.258 [0.127, 0.402] | -0.013 [-0.100, +0.060], within noise | 6/16/6 |
| dense.openscholar | 0.07 | 0.08 [0.00, 0.19] | **-0.29 [-0.49, -0.10], beyond noise** | 2/16/10 | 0.046 | 0.061 [0.020, 0.113] | **-0.210 [-0.350, -0.084], beyond noise** | 2/13/13 |
| hybrid.bm25+bge-small | 0.34 | 0.39 [0.21, 0.57] | +0.01 [-0.14, +0.16], within noise | 4/21/3 | 0.257 | 0.277 [0.146, 0.421] | +0.006 [-0.098, +0.106], within noise | 7/14/7 |
| hybrid.bm25+bge-base | 0.34 | 0.35 [0.19, 0.52] | -0.02 [-0.20, +0.14], within noise | 4/20/4 | 0.237 | 0.270 [0.150, 0.403] | -0.001 [-0.115, +0.121], within noise | 6/12/10 |
| hybrid.bm25+openscholar | 0.28 | 0.32 [0.15, 0.48] | -0.06 [-0.25, +0.12], within noise | 4/19/5 | 0.190 | 0.227 [0.115, 0.354] | -0.044 [-0.191, +0.099], within noise | 6/13/9 |

**The rule, applied to the collapsed numbers.**
1. The best *all answerable* Recall@5 is 0.39, `hybrid.bm25+bge-small+collapsed`'s alone. It wins 4 questions against `dense.bge-small+collapsed` and loses 3.
2. Its lead over the cheaper `dense.bge-small+collapsed` is +0.01, with an interval of [-0.14, +0.16]. That holds 0, so the rule recommends the cheaper retriever: bge-small builds in 1318.64 s against the hybrid's 1327.99 s, and answers a query in about 28 ms against about 220 ms.
3. Nothing beats `dense.bge-small+collapsed` beyond noise, so it stays. The only difference beyond noise is again OpenScholar's, a loss. BM25's upper bound reaches +0.00 but holds 0, so it is within noise, as the report labels it.

**Collapsing doesn't change the choice: the rule recommends `dense.bge-small` on both rankings.** It narrows the race. Collapsing lifts bge-small's Recall@5 by 0.08 (0.30 to 0.38), more than any other retriever's. In its top 5s, another Edition's or Version's copy fills 33 of 140 slots raw and 13 collapsed (*Before and after*). The hybrids' lead shrinks from +0.04 to +0.01 for BM25 + bge-small, and BM25 + bge-base's turns to -0.02. The per-question first-hit tables show where: `magikarp-verified-share` has no hit in bge-small's raw top 10, where 4 of its top 5 slots are duplicates (the report's *Questions* table), and the Collapsed ranking, which merges them, puts a hit at rank 3. Both BM25 + bge-small rankings miss it.

**The chatbot's retriever is `dense.bge-small`.** `[chat]` in `config/retrieval.toml` names it, and config loading refuses a name the file doesn't configure ([0054](0054-pinned-local-answer-model-and-the-chat-page.md)). The chatbot takes its `+collapsed` twin when its Citations can name the merged Editions (#71, #72). The choice was made on that twin's numbers.

**What OpenScholar's checks found** ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)). Its mean pooling matches Contriever's reference code to 6.1e-8 per dimension. Normalising its vectors, which turns Contriever's raw inner product into a cosine, changed the top 10 of every fixture question.

**Why OpenScholar scores so low.** At 0.07 against 0.30 it is the run's surprise, and it is not a wrongly used model:
- *Not the normalisation.* The vectors' norms before normalising sit in a narrow band: from 1.27 to 2.04, median 1.61, over the 6,050 Chunks we measured (each question's cosine top 300 plus its gold Chunks). Re-ranking that pool by raw inner product puts a gold Chunk in the top 5 for 4 of the 28 questions, against 2 by cosine. The pool always holds the gold Chunks, so 4 is an upper bound on what raw inner product over the whole index would do. Even that is two more questions, still far below bge-small, so the cosine is not why OpenScholar falls short.
- *Not the token limit.* `index` printed, for each of the three builds, that 5 of 141,348 texts were cut at 512 tokens: Chunks whose headers are unusually long. The eval report doesn't carry that count; the build's output does.
- *It finds the paper but not the Chunk that holds the Passage.* 52 of OpenScholar's 140 top-5 slots come from a Passage's paper, about as many as bge-small (55) and bge-base (58). But 44% of its top-5 Chunks have fewer than 40 words, against 5% for bge-small and 9% for bge-base. Across the corpus the share is 12%. These short Chunks are mostly figure captions and short lists from the right paper ("Figure 1: Commandline usage of SentencePiece" is its first hit for the SentencePiece whitespace question, whose gold Chunk ranks 133rd). The shares are measured; why they differ is not. Our likely explanation: every Chunk carries its paper's title and Section in the header, and with mean pooling a short Chunk's vector is mostly that header, so it lies close to any question about the paper. bge's `[CLS]` vector and query instruction, trained for asymmetric passage search, would feel that pull less, as the shares suggest. OpenScholar's own datastore embeds passages of 256 words with no header like ours ([0052](0052-bge-base-and-openscholar-pinned-and-verified.md)), so our headed, variable-length Chunks are further from its training. None of this is tested: testing it means changing the indexed text, which #55 holds fixed for every model.
- *Its build time is not the model's.* OpenScholar took 5081 s to embed against bge-base's 2878 s, though the two share an architecture and a tokenizer. Timed again on the same 640 texts, the two tokenise in 0.12 s and run their forward passes in 5.30 s each, and their query latencies in the report match (about 37 ms). The slower build ran overnight straight after bge-base's, and was slow from its first texts. Build times on this laptop swing that much for one model too: bge-small's index, the same key over the same Chunks, took 1318.64 s in the build this report reads and 2917.55 s in the one the previous report read. So we put the difference down to the machine during that run, not to the model. The report's figure stands as recorded, and the rule never reaches OpenScholar's cost anyway.

So the scientific candidate tests "a model trained on scientific text" fairly at the model level, but against our Chunks it loses on ranking within a paper, not on finding the paper.

## Alternatives considered
- **Paper-level scientific models: SPECTER2 and SciNCL.** They embed a whole paper from its title and abstract, for citation recommendation and paper similarity. We retrieve and cite Chunks of up to 350 tokens, so they answer a different question. They also use SciBERT's SciVocab, not the chunker's vocabulary, so a Chunk's token count would mean something else to them, and SPECTER2 needs the `adapters` library for its retrieval adapter. Rejected in #55, before the run.
- **Other models and sizes.** bge-large, e5-large and 7B embedders: base size already costs 48 minutes or more of embedding per model on MPS, and #55 left them out. Hosted embedding APIs were left out too, as was a reranker such as OpenScholar's cross-encoder, which gets its own issue.
- **Score OpenScholar by raw inner product.** The pool re-rank above shows it would move two questions, not close the gap to bge-small, so the table setting [0052](0052-bge-base-and-openscholar-pinned-and-verified.md) floated (`normalise = false`) isn't worth its key change.
- **Index OpenScholar without the context header, or with Chunks re-cut to 256 words.** This might suit the model better, but it changes the text one model sees and not the others. #55 holds Chunks and indexed text fixed, so the comparison stays one of models.
- **Recommend a hybrid for its +0.04.** That is what the rule exists to prevent: one question's lead, inside the noise, paid for with an eightfold query latency.

## Consequences
- `index` builds all seven retrievers by default, which takes 2.5 to 3 hours on an M1 Max: BM25 about 10 s, bge-small 22 to 49 min, bge-base about 48 min and OpenScholar 48 to 85 min. `--retriever dense.bge-base` builds one at a time. The README says how.
- The committed eval report scores all seven retrievers and their `+collapsed` twins. #61 ran `evaluate` again on the same index before applying the rule: the report came back the same apart from the latencies in the Cost table, so the numbers above are the committed report's.
- **The follow-ups as their reference rewrite favour the hybrid.** `hybrid.bm25+bge-small+collapsed` reaches Recall@5 0.88 on them against `dense.bge-small+collapsed`'s 0.50 (8 questions). The chatbot sends a follow-up's Rewrite, not the follow-up alone, so its follow-ups may get more from the hybrid than the *all answerable* row shows. The rule reads the *all answerable* row, as #55 set before the run, and a reference rewrite is written by hand, not by the rewriter. The rewriter row (#66) measures what the chatbot actually sends. If that row shows a lead beyond noise, it is a case for a new record. It does not reopen this one.
- The duplicate and restatement shares of the new retrievers rest on fewer questions: 77 Editions in their top 5s have no Work group, so, for example, `dense.bge-base`'s are over 20 of the 28 questions and `dense.openscholar`'s over 15. The report says so per retriever. The rule reads only Recall@5, so this doesn't touch the recommendation, but grouping those Editions (by hand, [0047](0047-hand-checked-work-groups-are-the-duplicate-ground-truth.md)) would complete the crowding numbers.
- One of those 77 is an alias, not a new paper. The file of `2607.05691v1` is also pinned as `arXiv:2607.05691v1` (same sha256, both in the committed full-text record). Its Chunks in the parse cache carry the id that first parsed them, and this run's cache says `arXiv:2607.05691v1`. That Edition has no Work group, so `bm25+collapsed` shows 27 of 28 questions grouped here, against 28 in the report #54 committed, though nothing about BM25 changed. No metric moves. The Chunks should carry the parse report's pinned id rather than the cache's. That fix is #76. #61's rerun didn't wait for it, because it moves no metric and the rule reads only Recall@5. Fixed by [0066](0066-chunks-cite-the-parse-reports-ids-whatever-filled-the-cache.md): the rerun after it shows 28 of 28 grouped and 76 Editions without a Work group.
- `[chat]` keeps `dense.bge-small`, now as this record's choice rather than as a placeholder.
