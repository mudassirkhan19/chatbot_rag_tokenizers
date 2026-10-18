# Eval report

Written by `evaluate`. Each retriever ranks the Chunks for every question of the Evaluation set, and the raw ranking is scored against the question's Passages.

## Evaluation set

- File: `data/eval/evaluation-set.jsonl`
- sha256: `6e6babfb08fe4c17bb6674bf7200810b50082b70f3d5971748334251774220a5`
- Questions: 3 (1 single-paper, 1 multi-paper, 1 follow-up, 0 unanswerable)

## Chunks

- Chunking config: `chunking-215005ae4889`
  - token_budget: `350`
  - tokenizer: `google-bert/bert-base-uncased`
  - tokenizer_revision: `86b5e0934494bd15c9632b12f734a8a67f723594`
  - tokenizer_sha256: `ce64fce797c24f68df90b40a3f74f579b336a493db14bd583fd520ea0d8c9a98`
  - min_sections: `2`
  - min_body_characters: `2000`
- Files: 34
- Chunks: 2055

## Retrievers

- bm25: `bm25-4e42ab0ca936`
  - k1: `1.2`
  - b: `0.75`
  - tokens: `lower-cased letter and digit runs, no stemming, no stop words`

## Metrics

- Recall@5: the share of a question's Passages held by a Chunk in the top 5, averaged over questions.
- MRR@10: 1 / the rank of the first Chunk holding any Passage, 0 when none is in the top 10.
- Hit@5: the share of questions with a Passage held by a Chunk in the top 5.
- A Chunk holds a Passage when the quote is in its text, after unicode (NFKC), case and whitespace are normalised; this is a stand-in for the real Passage matcher. The Chunk may come from any Edition.
- The ranking is scored raw: duplicates of one Work all take their slots.
- Unanswerable questions are run but left out of the metrics.
- A follow-up is run three ways: follow-up alone, history + follow-up (its prior turns, then the follow-up, joined by spaces) and reference rewrite. The *all answerable* row takes each follow-up alone, as a user would ask it.

## Results

### Results: bm25

| Question type | Query | Questions | Recall@5 | MRR@10 | Hit@5 |
|---|---|---:|---:|---:|---:|
| single-paper | as asked | 1 | 0.00 | 0.125 | 0.00 |
| multi-paper | as asked | 1 | 0.50 | 1.000 | 1.00 |
| follow-up | follow-up alone | 1 | 0.00 | 0.000 | 0.00 |
| follow-up | history + follow-up | 1 | 0.00 | 0.000 | 0.00 |
| follow-up | reference rewrite | 1 | 0.00 | 0.100 | 0.00 |
| all answerable | as asked, follow-ups alone | 3 | 0.17 | 0.375 | 0.33 |
| unanswerable | left out | 0 | — | — | — |

## Questions

First hit is the rank of the first Chunk holding a Passage, within the top 10; Passages found counts those held in the top 5.

### Questions: bm25

| Question | Type | Query | First hit | Passages found |
|---|---|---|---:|---:|
| wechsel-freezing | single-paper | as asked | 8 | 0/1 |
| bpe-and-wechsel-vocabularies | multi-paper | as asked | 1 | 1/2 |
| wechsel-neighbours | follow-up | follow-up alone | none | 0/1 |
| wechsel-neighbours | follow-up | history + follow-up | none | 0/1 |
| wechsel-neighbours | follow-up | reference rewrite | 10 | 0/1 |

## Timings

These depend on the machine and change from run to run.

- bm25: index built in 0.12 s; 5 queries, latency p50 2.59 ms, p95 3.66 ms
