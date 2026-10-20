# Write-up: a grounded chatbot over tokenizer research

This is the short write-up `docs/ASSIGNMENT.md` asks for. It covers the design decisions, a results table, and why the chatbot uses bge-small and its duplicate strategy. Every number in it is copied from a committed report, which is linked beside it. The ADRs in [`docs/adr/`](adr/README.md) hold the detail and the alternatives. The README says how to run each step.

The other deliverables are the manifest ([`data/manifest.csv`](../data/manifest.csv)), the transcript ([`docs/reports/2026-10-21-chat-transcript.md`](reports/2026-10-21-chat-transcript.md)) and the failure analysis ([`docs/reports/2026-10-21-failure-analysis.md`](reports/2026-10-21-failure-analysis.md)).

## Design decisions

**The topic boundary** (ADR [0009](adr/0009-seeds-and-citation-expansion.md)). Five topics are in scope: subword algorithms for text LMs, byte-level and tokenizer-free models, the NMT-era subword papers, the effects of tokenization (fertility and fairness across languages, arithmetic, code, reasoning, vocabulary size), and vocabulary adaptation and transfer. Tokenizers for other modalities are out, and so are uses of "token" that aren't about tokenization: token pruning, KV caches, crypto tokens. A paper that mixes modalities is in only when text tokenization is central, and the judge decides that. There is no date floor.

**Collection** (ADRs [0003](adr/0003-commit-the-snapshot.md), [0005](adr/0005-rule-pre-filter.md), [0007](adr/0007-local-llm-judge.md), [0021](adr/0021-tev1-decision-model-judge.md)). Keyword queries run against arXiv, Semantic Scholar and OpenAlex. 21 hand-picked Seeds add one citation hop in each direction. ACL Anthology pages give the venue Editions. Each Candidate then passes two stages. Regex rules come first: a required tokenization term, and patterns for the off-topic uses above. A local judge comes second: Tev1 4B on Ollama, which gives P(yes) for a fixed relevance question, kept at a threshold of 0.8. The threshold was chosen on a hand-checked Audit set of 180 Candidates (ADRs [0011](adr/0011-audit-set-and-relevance-metrics.md), [0020](adr/0020-blind-agent-labels-checked-by-the-developer.md)). Every source response and verdict is stored in the committed Snapshot, so `just collect` rebuilds the manifest offline, byte for byte. Withdrawn preprints and documents that aren't papers are excluded (ADRs [0037](adr/0037-withdrawn-preprints-are-excluded.md), [0040](adr/0040-the-corpus-keeps-only-papers.md)).

**Parsing and chunking** (ADRs [0024](adr/0024-grobid-stays-the-parser-after-the-docling-spike.md), [0027](adr/0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md), [0028](adr/0028-element-rules-and-chunk-kinds.md), [0035](adr/0035-missed-table-cells-stay-in-text-chunks.md)). GROBID, pinned by digest, turns each PDF into Sections. It beat Docling on speed and gives the structured bibliography, though Docling was better on Sections and tables. Chunks pack whole paragraphs up to 350 BERT WordPiece tokens, never cross a Section and don't overlap. Each carries a context header (title › Section path) and a citation anchor (Edition, file, Section, pages). Tables become their own Chunks, row by row under their caption. Each figure caption is a small Chunk. Equations stay inline as GROBID renders them. Reference lists are kept as structured data, not Chunks. Acknowledgements are dropped. A file with fewer than 2 Sections or 2,000 characters of text fails the quality gate.

**Versions and near-duplicates** (ADRs [0051](adr/0051-work-grouping-in-collect.md), [0063](adr/0063-versions-and-near-duplicates-measured-before-and-after.md), [0057](adr/0057-the-collapse-merges-copies-not-works.md), [0074](adr/0074-the-collapse-matches-copies-by-their-text.md)). The manifest keeps one row per Edition: each arXiv Version is pinned, and a preprint and its venue Edition are separate rows. `collect` groups Editions into Works and names a Canonical Edition. At query time the Collapsed ranking merges copies of a passage across a Work's files. The section on the duplicate strategy below says why.

**Retrieval** (ADRs [0042](adr/0042-dense-baseline-bge-small-behind-the-embedder-boundary.md), [0065](adr/0065-the-embedding-comparison-on-the-raw-ranking.md), [0076](adr/0076-retrieve-once-for-each-paper-a-question-names.md)). `BAAI/bge-small-en-v1.5` embeds each Chunk's header and text, searched by exact dot product. The chatbot retrieves 5 Chunks with `dense.bge-small+per-paper+collapsed`. When a question names two or more papers, the answer model lists the names, each name is looked up among the Works by title or first author, and the named papers fill the slots in turn. Then copies are merged.

**The chatbot** (ADRs [0054](adr/0054-pinned-local-answer-model-and-the-chat-page.md), [0056](adr/0056-follow-ups-the-conversation-and-the-rewrite.md), [0059](adr/0059-abstention-by-instruction-and-the-chat-report.md), [0064](adr/0064-a-decline-in-the-models-own-words-is-an-abstention.md), [0069](adr/0069-citations-name-the-merged-editions-after-the-collapse.md), [0073](adr/0073-the-rewrite-names-the-paper-the-conversation-is-about.md)). The answer model is `gemma4:e2b-mlx` on Ollama, pinned, at temperature 0. It runs locally, so no API key is needed.
- *Rewriter.* A follow-up is rewritten by the same model, from the last three Turns, into a question that stands alone and names the paper it points back to. The page shows it as "Searched as:".
- *Citations.* The system prompt asks for a marker on every sentence. Each reference names the paper, the Edition shown, the Editions merged into it ("2022.tacl-1.5, also 2103.06874v4"), the Section and the pages. A Survey is marked.
- *Abstention.* The bot always sees its 5 Chunks. When they don't answer, the prompt asks for a fixed sentence. A one-sentence decline in the model's own words counts too. No retrieval score decides it.
- *Grounding check.* An answer is grounded when it cites a retrieved Chunk, every marker is valid, and every number in it appears in a cited Chunk. It checks citations and numbers, not claims. The developer's hand check measures how far that falls short (ADRs [0071](adr/0071-the-developers-check-of-the-grounding-verdict.md), [0072](adr/0072-the-hand-check-scores-each-sampled-reply.md)).

**The Evaluation set** (ADRs [0041](adr/0041-passage-matcher-eval-check-and-calibration.md), [0046](adr/0046-evaluation-set-quotes-checked-by-and-absence-evidence.md)) has 36 questions: 12 single-paper, 8 multi-paper, 8 follow-up and 8 unanswerable, of which 6 are near misses and 2 are off the topic ([eval report](../data/eval/eval-report.md), [chat report](../data/eval/chat-report.md)). Each answerable question has short quoted Passages. A Chunk holds a Passage when the Passage matcher finds the quote in it, in any Edition. So a hit doesn't depend on which copy is ranked.

## Results

**Corpus**, from the [funnel report](../data/report.md), the [parse report](../data/parse-report.md) and the [audit report](../data/audit/report.md):

| | |
|---|---:|
| Editions discovered | 26,386 |
| Rejected: by the rules / by the judge / withdrawn / not a paper | 19,185 / 4,329 / 15 / 152 |
| Included Editions / Works | 2,705 / 2,393 |
| With full text / indexed / no open PDF | 2,067 / 2,066 / 636 |
| Files parsed / failed the quality gate | 2,689 / 1 |
| Chunks (of them tables / captions) | 141,348 (18,034 / 13,712) |
| Rules and judge at 0.8 on the Audit set: precision / recall / F1 | 0.810 / 0.872 / 0.840 |

The threshold was picked on the same Audit set, so the F1 is an optimistic estimate, as the audit report says.

**Retrieval for the chatbot's retriever, before and after.** From the [eval report](../data/eval/eval-report.md)'s *Comparison* and *Before and after* sections. These are the 28 answerable questions as a user asks them (a follow-up alone). Brackets are 95% paired bootstrap intervals (10,000 resamples). Duplicate slots are counted against hand-checked Work groups, over the questions whose top 5 is fully grouped.

| dense.bge-small | Recall@5 | MRR@10 | Hit@5 | Duplicate slots in the top 5 | of them another Edition or Version |
|---|---|---|---:|---:|---:|
| raw | 0.30 [0.14, 0.48] | 0.244 [0.114, 0.393] | 0.32 | 70/140 | 33/140 |
| Collapsed | 0.38 [0.20, 0.55] | 0.276 [0.147, 0.421] | 0.39 | 52/130 | 5/130 |
| per paper, Collapsed (the chatbot's) | 0.43 [0.27, 0.61] | 0.329 [0.191, 0.477] | 0.50 | 52/125 | 5/125 |

**Chat**, from the [chat report](../data/eval/chat-report.md): three runs of the whole set, which agree on every verdict and rate. Brackets are 95% Wilson intervals.

| Measure | Result |
|---|---|
| Abstention on the unanswerable questions | 7/8 (0.88 [0.53, 0.98]): near miss 5/6, off-topic 2/2 |
| False abstention on the answerable questions | 2/28 (0.07 [0.02, 0.23]) |
| Grounded rate, every answer that is not an Abstention | 25/27 (0.93 [0.77, 0.98]) |
| Recall@5 of the Chunks each Turn retrieved: answerable / single / multi / follow-up | 0.54 / 0.75 / 0.25 / 0.50 |
| Hand check agrees with the grounding check | 16/19 (0.84 [0.62, 0.94]); 3 passed by the check, not by hand |
| Whole Turn, p50 / p95 | 0.75 s / 1.43 s |

Chat Recall@5 (0.54) is higher than the eval's 0.43 because a chat follow-up retrieves with its Rewrite, while the eval's *all answerable* row takes the follow-up alone. The single-paper and multi-paper figures are the same in both.

## Why bge-small

The decision rule was fixed in spec #55 before any run. Recommend the best *all answerable* Recall@5. If its lead over a cheaper retriever is within noise (the paired interval of the difference holds 0), recommend the cheaper one. If nothing beats `dense.bge-small` beyond noise, it stays. #60 applied the rule to the raw ranking and #61 to the Collapsed ranking, which the chatbot uses (ADR [0065](adr/0065-the-embedding-comparison-on-the-raw-ranking.md)). The candidates test three things: model size (bge-base, the same family at three times the parameters), a scientific model (OpenScholar_Retriever, Contriever trained further on scientific papers to retrieve passages), and keyword search beside vectors (BM25, and BM25 fused with each dense model by reciprocal rank fusion). The numbers are from the [eval report](../data/eval/eval-report.md)'s *Comparison* and *Cost* sections. Latencies change from run to run.

| Retriever | Recall@5 raw | Recall@5 Collapsed | Difference from bge-small, Collapsed [95%] | Parameters | Index | Build | Query p50 |
|---|---:|---:|---|---:|---:|---:|---:|
| bm25 | 0.16 | 0.21 | -0.17 [-0.36, +0.01], within noise | — | 140.3 MB | 9.35 s | 222.96 ms |
| **dense.bge-small** | 0.30 | **0.38** | — | 33.4M | 220.6 MB | 1318.64 s | 28.89 ms |
| dense.bge-base | 0.29 | 0.32 | -0.05 [-0.18, +0.07], within noise | 109.5M | 437.8 MB | 2878.28 s | 38.67 ms |
| dense.openscholar | 0.07 | 0.12 | -0.26 [-0.45, -0.07], **beyond noise** | 109.5M | 437.8 MB | 5081.47 s | 39.13 ms |
| hybrid.bm25+bge-small | 0.34 | 0.39 | +0.01 [-0.14, +0.16], within noise | 33.4M | 361.0 MB | 1327.99 s | 245.51 ms |
| hybrid.bm25+bge-base | 0.34 | 0.35 | -0.02 [-0.20, +0.14], within noise | 109.5M | 578.1 MB | 2887.63 s | 282.02 ms |
| hybrid.bm25+openscholar | 0.28 | 0.32 | -0.06 [-0.25, +0.12], within noise | 109.5M | 578.1 MB | 5090.82 s | 259.59 ms |

- **The hybrid's lead is noise.** `hybrid.bm25+bge-small` has the best Collapsed Recall@5, 0.39, but its lead of +0.01 holds 0, and bge-small answers a query in 28.89 ms against 245.51 ms. With per-paper retrieval on both, the hybrid reaches 0.44 and bge-small 0.43. Against bge-small Collapsed, the hybrid's lead is then +0.07 [-0.10, +0.23], still within noise. So keyword search doesn't earn its place on this evidence. It does help the follow-ups when they are put as their hand-written reference rewrite (ADR 0065).
- **Size doesn't help.** bge-base scores lower and takes twice as long to build.
- **The scientific model is the only difference beyond noise, and it is a loss.** By ADR [0065](adr/0065-the-embedding-comparison-on-the-raw-ranking.md)'s measurements, OpenScholar finds the right paper about as often as bge-small. But 44% of its top-5 Chunks have fewer than 40 words, against 5% for bge-small: mostly captions from the right paper, ranked above the Chunk that holds the answer. The ADR checks that the model is used correctly and gives a likely, untested reason: mean pooling over a short Chunk is mostly its title header.
- Paper-level scientific models (SPECTER2, SciNCL) were left out before the run. They embed a title and abstract, and we retrieve and cite passages.

## Why this duplicate strategy

Each Version is kept on purpose: v1 and the latest Version of a preprint, and a preprint and its venue Edition. A citation should name the Edition it quotes, and a revision can add the sentence that answers a question. So duplicates are handled in two places, and nothing is deleted from the index.

**Work grouping**, in `collect` (ADRs [0051](adr/0051-work-grouping-in-collect.md), [0063](adr/0063-versions-and-near-duplicates-measured-before-and-after.md)). Two Editions are one Work when they share an arXiv id, a DOI or an ACL ID, a file's bytes, or a title and a first-author surname. Titles are compared without case, punctuation, hyphens or word order. The venue Edition is canonical, else the latest Version. Scored pair by pair against 209 hand-checked Editions in 179 Works, the rule joins 30 pairs and the Work groups 30, the same 30: precision and recall 1.00 ([eval report](../data/eval/eval-report.md), *Grouping*). On the whole manifest it makes 2,393 Works of 2,705 Editions. 260 of the joined Works share an identifier and 50 needed the title and first author ([funnel report](../data/report.md)).

**The Collapsed ranking**, at query time (ADRs [0053](adr/0053-collapsed-ranking-and-collapsed-twins.md), [0057](adr/0057-the-collapse-merges-copies-not-works.md), [0074](adr/0074-the-collapse-matches-copies-by-their-text.md)). From the raw top 50, two Chunks of one Work from different files are copies when they share at least 40% of their word 5-grams and one is the other's closest Chunk in its file. Copies take one slot, shown from the Canonical Edition when the pool holds it, and the citation lists the merged Editions. It merges copies of a passage, not whole Works. A paper's other passages keep their slots, so a question about a paper can still get several of its Sections. Surveys are marked, not demoted. They take 1 of 140 top-5 slots on bge-small's raw ranking ([eval report](../data/eval/eval-report.md), *Crowding*), so a demotion would have had nothing to move.

**Measured impact.** On bge-small, copies from another Edition or Version fall from 33 of 140 top-5 slots to 5 of 130. Recall@5 rises from 0.30 to 0.38, and MRR@10 from 0.244 to 0.276 (table above). Duplicates from the same file rise from 37/140 to 47/130: the freed slots go to the next Chunks, often other passages of a paper already ranked. In the chat run, Turns holding a near-duplicate pair fell from 15 of 44 ([diagnosis](reports/2026-10-21-chat-failure-diagnosis.md)) to 2 of 44 after the text match (ADR [0077](adr/0077-the-final-chat-run-after-the-text-collapse-the-rewrite-and-per-paper-retrieval.md)).

**What it might wrongly merge.**
- *Grouping.* Two different papers with the same title words and the same first author would be joined. There is no such case in the corpus. A title match with a different first author is never joined: the funnel report lists 5 such Suspected pairs. The rule misses title variants such as MEGABYTE's "Predicting" against "Modeling", which stay two Works (ADR 0063).
- *The collapse.* Near the 0.4 threshold, a sample found one wrong merge in eight pairs at 0.4–0.5: two appendix Sections of one paper that share table rows (ADR 0074). A wrong merge can hide a passage behind another passage of the same paper. It can never hide another paper.
- *Coverage.* The Collapsed duplicate rates count 26 of the 28 questions. Merging lets Editions without a Work group into the top 5.

## Failure cases

The [failure analysis](reports/2026-10-21-failure-analysis.md) traces six questions the final run still gets wrong, each the same in all three runs:
- **False abstentions from retrieval.** In `llama2-70b-vocabulary` the answer is in the paper's Abstract, which ranks 22nd. In `magikarp-norm-indicator` the Rewrite leaves "them" unresolved, and the Passage is not in the top 50.
- **A grounded but wrong answer.** `superbpe-mmlu` asks about MMLU and gets SuperBPE's CommonsenseQA gain. The check passes it, since the number is in a cited Chunk.
- **Misattribution.** `gpt-4-number-tokens` gives another paper's custom tokenizer as GPT-4's.
- **A near miss answered.** `sentencepiece-korean-speed` gives English and Japanese speeds instead of abstaining.
- **An uncited answer.** `canine-hashing` is right but cites nothing.

Each traces back to [#77's diagnosis](reports/2026-10-21-chat-failure-diagnosis.md). The [transcript](reports/2026-10-21-chat-transcript.md) shows a six-Turn conversation with a follow-up, a near-miss Abstention and an off-topic one.

## Limitations and what's next

- **Small samples.** 28 answerable questions give wide intervals. The chatbot's per-paper gain over the Collapsed ranking (+0.05) sits at the edge of the noise ([eval report](../data/eval/eval-report.md)).
- **The grounding check sees citations and numbers, not claims.** The hand check disagrees on 3 of 19 replies, all passed by the check. Tev1 as a sentence-by-Chunk judge (#70, ADR [0075](adr/0075-tev1-as-a-grounding-judge-measured-against-the-hand-labels.md)) agrees with the hand labels on the same 16 of 19 and misses the same three. So it is measured in the chat report but not adopted.
- **Multi-paper questions stay weak.** Their chat Recall@5 is 0.25.
- **Coverage.** 636 included Editions have no open PDF, so they are in the manifest but not the index ([funnel report](../data/report.md)).
- **A small local answer model.** It explains most of the answer-side failures above.

These are filed as `enhancement` issues and deferred:
- #62: a cross-encoder reranker (OpenScholar_Reranker) over the top 50, where the missed Passages sit.
- #83: the answer prompt keeps each paper's claims to that paper.
- #85: measure a larger answer model on near-miss abstention and complete answers.
- #87: ask again for the markers when an answer cites no Chunk.
- #88: the Rewrite still leaves "them" unresolved once it names the paper.
- #39, #40, #42, #43: parse clean-up (junk Chunks, a junk heading opening the appendix, reference text leaking into body Chunks, headless body text filed under the Abstract).
