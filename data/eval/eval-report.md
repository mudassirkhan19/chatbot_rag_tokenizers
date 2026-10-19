# Eval report

Written by `evaluate`. Each retriever ranks the Chunks for every question of the Evaluation set, and the raw ranking is scored against the question's Passages.

## Evaluation set

- File: `data/eval/evaluation-set.jsonl`
- sha256: `091b160499444e92c384d4ff741242032a75ef25f76c02d8524a9f6b25ac7f59`
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
- Files: 2690
- Chunks: 141512

## Retrievers

- bm25: `bm25-abfdc4a74910`
  - k1: `1.2`
  - b: `0.75`
  - tokens: `lower-cased letter and digit runs, decimals whole, no stemming, no stop words`
- dense: `dense-784e5a0da1b5`
  - model: `BAAI/bge-small-en-v1.5`
  - revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
  - model_sha256: `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`
  - query_instruction: `Represent this sentence for searching relevant passages: `
  - pooling: `[CLS] vector of the last layer, L2-normalised`
  - max_tokens: `512`
  - search: `exact dot product over every Chunk's float32 vector`

## Metrics

- Recall@5: the share of a question's Passages held by a Chunk in the top 5, averaged over questions.
- MRR@10: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top 10.
- Hit@5: the share of questions with a Passage held by a Chunk in the top 5.
- A Chunk holds a Passage when, after unicode, case, whitespace and hyphenation are normalised and citations dropped, at least 65% of the quote's words match the Chunk's in order, in blocks of at least 2 words (a number may match alone) within twice the quote's length, and every number in the quote matches (ADR 0041). A match running into the Chunk's first or last word counts only the quote's words on the Chunk's side, and must cover at least 6 words. The Chunk may come from any Edition.
- The ranking is scored raw: duplicates of one Work all take their slots.
- Unanswerable questions are run but left out of the metrics.
- A follow-up is run three ways: follow-up alone, history + follow-up (its prior turns, then the follow-up, joined by spaces) and reference rewrite. The *all answerable* row takes each follow-up alone, as a user would ask it.

## Results

### Results: bm25

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.33 | 0.173 | 0.33 |
| multi-paper | as asked | 8 | 0.06 | 0.153 | 0.12 |
| follow-up | follow-up alone | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 8 | 0.00 | 0.000 | 0.00 |
| follow-up | reference rewrite | 8 | 0.62 | 0.583 | 0.62 |
| all answerable | as asked, follow-ups alone | 28 | 0.16 | 0.118 | 0.18 |
| unanswerable | left out | 8 | — | — | — |

### Results: dense

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 12 | 0.58 | 0.462 | 0.58 |
| multi-paper | as asked | 8 | 0.06 | 0.038 | 0.12 |
| follow-up | follow-up alone | 8 | 0.12 | 0.125 | 0.12 |
| follow-up | history + follow-up | 8 | 0.12 | 0.031 | 0.12 |
| follow-up | reference rewrite | 8 | 0.50 | 0.400 | 0.50 |
| all answerable | as asked, follow-ups alone | 28 | 0.30 | 0.244 | 0.32 |
| unanswerable | left out | 8 | — | — | — |

## Crowding

What takes the top 5 slots of each answerable question, as a user would ask it (the *all answerable* row's queries), on the raw ranking (ADR 0044).

- Work groups: `data/eval/work-groups.csv` (sha256 `7c42da873e6fea33af1a712bdf97b9a8f1423de68f55864c40d5069b78938307`), 154 Editions in 130 Works, 0 of the Editions checked by hand (checked_by), never computed by the system being measured.
- A duplicate slot holds a Chunk from a Work already ranked higher: another Edition or Version of it, or another Chunk of the same file.
- A restatement slot holds a Chunk from a Survey. A Survey is always its own Work, and its Chunks are never duplicates.
- Duplicates and restatement count only the questions whose top 5 Editions all have a Work group.
- A mostly-numeric slot holds a text Chunk with more than 35% of its words numbers, as the parse report counts them (ADR 0035). It counts every question.

### Crowding: bm25

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 59/140 | 0.42 | 27/28 | 0.96 |
| restatement | 0/140 | 0.00 | 0/28 | 0.00 |
| mostly numeric | 1/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 28 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 1

### Crowding: dense

| Measure | Top-5 slots | Share of slots | Questions | Share of questions |
|---|---:|---:|---:|---:|
| duplicate | 70/140 | 0.50 | 27/28 | 0.96 |
| restatement | 1/140 | 0.01 | 1/28 | 0.04 |
| mostly numeric | 2/140 | 0.01 | 1/28 | 0.04 |

- Grouped: 28 of 28 questions have a Work group for every Edition in their top 5.
- Mostly-numeric slots holding a Passage: 0 of 2

## Editions without a Work group

Editions in any retriever's top 5 for an answerable question, in any query, with no Work group. `evaluate --export-ungrouped` writes them, with their titles, for grouping.

None.

## Questions

First hit is the rank of the first Chunk holding a Passage, within the top 10; Passages found counts those held in the top 5. The slot counts are within the top 5; a question with an Edition there that has no Work group has its duplicates and restatements marked ungrouped.

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
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 1 |
| canine-hashing | follow-up | reference rewrite | 2 | 1/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 0 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | 1 | 1/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | 6 | 0/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 2 | 0 | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

### Questions: dense

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
| canine-hashing | follow-up | follow-up alone | none | 0/1 | 1 | 0 | 0 |
| canine-hashing | follow-up | history + follow-up | none | 0/1 | 3 | 1 | 2 |
| canine-hashing | follow-up | reference rewrite | 1 | 1/1 | 3 | 1 | 0 |
| digits-fourth-digit | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| digits-fourth-digit | follow-up | history + follow-up | none | 0/1 | 3 | 0 | 0 |
| digits-fourth-digit | follow-up | reference rewrite | none | 0/1 | 2 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | history + follow-up | 4 | 1/1 | 4 | 0 | 0 |
| vocabulary-with-scarce-data | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | follow-up alone | none | 0/1 | 3 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | history + follow-up | none | 0/1 | 2 | 0 | 0 |
| code-tokenizer-initialisation | follow-up | reference rewrite | none | 0/1 | 3 | 0 | 0 |
| magikarp-norm-indicator | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| magikarp-norm-indicator | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| magikarp-norm-indicator | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| superbpe-mmlu | follow-up | follow-up alone | none | 0/1 | 2 | 0 | 0 |
| superbpe-mmlu | follow-up | history + follow-up | none | 0/1 | 1 | 0 | 0 |
| superbpe-mmlu | follow-up | reference rewrite | none | 0/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | follow-up alone | 1 | 1/1 | 2 | 0 | 0 |
| tokenization-latency | follow-up | history + follow-up | none | 0/1 | 4 | 0 | 0 |
| tokenization-latency | follow-up | reference rewrite | 1 | 1/1 | 4 | 0 | 0 |
| bpe-english-french | unanswerable | as asked | left out | — | — | — | — |
| blt-70b-mmlu | unanswerable | as asked | left out | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | as asked | left out | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | as asked | left out | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | as asked | left out | — | — | — | — |
| byt5-learning-rate | unanswerable | as asked | left out | — | — | — | — |
| vitamin-d | unanswerable | as asked | left out | — | — | — | — |
| world-cup-2018 | unanswerable | as asked | left out | — | — | — | — |

## Timings

These depend on the machine and change from run to run.

- bm25: index built on cpu in 9.63 s; 52 queries on cpu, latency p50 200.26 ms, p95 320.52 ms
- dense: index built on mps in 817.53 s; 52 queries on mps, latency p50 28.51 ms, p95 30.91 ms
