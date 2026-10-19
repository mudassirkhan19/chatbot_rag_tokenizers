# Chat report

Written by `chat-eval`. Every question of the Evaluation set is asked of the chatbot through the same Conversation code as the chat page, and each answer is checked for grounding, Abstention and the Passages in the Chunks its Turn retrieved.

## Evaluation set

- File: `data/eval/evaluation-set.jsonl`
- sha256: `19bd5da54270b0c4998294ca275394ea9bc2f70ffd2443f3fda489057d44c5b7`
- Questions: 36 (12 single-paper, 8 multi-paper, 8 follow-up, 8 unanswerable; of the unanswerable, 6 near-miss, 2 out-of-topic)

## Chunks

- Parser: `grobid-0.9.1-crf-223957791ac2`
- Chunking config: `chunking-215005ae4889`
- Files: 2689
- Chunks: 141348

## Chatbot

- Retriever: dense.bge-small (`dense-784e5a0da1b5`), 5 Chunks per Turn
- Answer model: gemma4:e2b-mlx@e98b54fe1913 on Ollama 0.40.5, thinking off, temperature 0.0
- System prompt sha256: `1597fe607c1e22bb9b25a827ee6fd0067c4b635628c5bff5c74b3a79710b23eb` (with the Abstention sentence filled in)
- Rewrite prompt sha256: `667083844bf2a3deeb25ed76510b41f884d360d9767a39e098829b30c6c1dfab`
- Abstention sentence: "The papers in this corpus do not answer this question."
- Earlier Turns shown on a follow-up: 3

## Measures

- Each single-paper, multi-paper and unanswerable question is a Conversation of one Turn. A follow-up is a Conversation that first asks its stored history, the bot answering each, then the follow-up. Only the question's own Turn is scored.
- An answer is an Abstention when it holds the Abstention sentence, compared after the Passage matcher's normalisation. The abstention rate is the share of the questions answered with one: on the unanswerable questions it is the rate of correct Abstentions, on the answerable ones the false-abstention rate.
- An answer that is not an Abstention is grounded when it cites at least one retrieved Chunk, every marker in it names a Chunk retrieved for its Turn, and every number in it, cut into words as the Passage matcher cuts them (a word that starts with a digit, such as 50k or 0.1, but not ByT5), appears in a cited Chunk's context header or text. An uncited answer is not grounded. Abstentions are left out of the grounded rate.
- Recall@5: the share of a question's Passages held by one of the 5 Chunks its Turn retrieved, averaged over the answerable questions, with the Passage matcher of `evaluate` (ADR 0041).
- Every rate has its 95% Wilson interval, in the column beside it and in brackets in the lines below the table. It covers the sampling of the questions, not the answer model's run-to-run variation, which the Variation section measures. Recall@5 is a mean of per-question shares, not a proportion, and has no interval here: it is the retriever's measure, and the eval report gives its bootstrap interval (ADR 0061).

## Results

| Question type | Questions | Abstained | Abstention rate | 95% interval | Answers | Grounded | Grounded rate | 95% interval | Recall@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single-paper | 12 | 0 | 0.00 | [0.00, 0.24] | 12 | 11 | 0.92 | [0.65, 0.99] | 0.58 |
| multi-paper | 8 | 0 | 0.00 | [0.00, 0.32] | 8 | 8 | 1.00 | [0.68, 1.00] | 0.06 |
| follow-up | 8 | 0 | 0.00 | [0.00, 0.32] | 8 | 7 | 0.88 | [0.53, 0.98] | 0.50 |
| all answerable | 28 | 0 | 0.00 | [0.00, 0.12] | 28 | 26 | 0.93 | [0.77, 0.98] | 0.41 |
| unanswerable: near-miss | 6 | 0 | 0.00 | [0.00, 0.39] | 6 | 2 | 0.33 | [0.10, 0.70] | — |
| unanswerable: out-of-topic | 2 | 2 | 1.00 | [0.34, 1.00] | 0 | 0 | — | — | — |
| all unanswerable | 8 | 2 | 0.25 | [0.07, 0.59] | 6 | 2 | 0.33 | [0.10, 0.70] | — |
| all | 36 | 2 | 0.06 | [0.02, 0.18] | 34 | 28 | 0.82 | [0.66, 0.92] | 0.41 |

- Abstention rate on the unanswerable questions: 2/8 (0.25 [0.07, 0.59]); near-miss 0/6 (0.00 [0.00, 0.39]), out-of-topic 2/2 (1.00 [0.34, 1.00])
- False-abstention rate on the answerable questions: 0/28 (0.00 [0.00, 0.12])
- Grounded rate over every answer that is not an Abstention: 28/34 (0.82 [0.66, 0.92])
- Not grounded: 6 uncited, 0 with an invalid Citation, 3 with a number in no cited Chunk (an answer may be counted under more than one)

## Questions

Grounded is yes, no, or — for an Abstention. Passages in its Chunks counts the question's Passages held by one of its Turn's 5 Chunks, then names them by their place in the question (`1/2: 1` found the first of two); a follow-up's line is its own Turn, after its history.

| Question | Type | Abstained | Grounded | Invalid Citations | Numbers not in cited Chunks | Passages in its Chunks |
|---|---|---|---|---|---|---:|
| wechsel-freezing | single-paper | no | yes | — | — | 1/1: 1 |
| sentencepiece-whitespace | single-paper | no | yes | — | — | 1/1: 1 |
| bpe-dropout-rate | single-paper | no | yes | — | — | 2/2: 1, 2 |
| bpe-cyrillic | single-paper | no | yes | — | — | 1/1: 1 |
| canine-amharic | single-paper | no | yes | — | — | 1/1: 1 |
| byt5-span-length | single-paper | no | yes | — | — | 0/1 |
| digits-right-to-left | single-paper | no | yes | — | — | 0/1 |
| llama2-70b-vocabulary | single-paper | no | no | — | 70b | 0/1 |
| xlm-r-tokens-per-language | single-paper | no | yes | — | — | 1/1: 1 |
| magikarp-verified-share | single-paper | no | yes | — | — | 0/1 |
| superbpe-curriculum | single-paper | no | yes | — | — | 0/1 |
| fast-wordpiece-speed | single-paper | no | yes | — | — | 1/1: 1 |
| bpe-and-wechsel-vocabularies | multi-paper | no | yes | — | — | 0/2 |
| compression-and-accuracy | multi-paper | no | yes | — | — | 0/3 |
| one-sided-regularization | multi-paper | no | yes | — | — | 0/3 |
| tokenizer-swap-budget | multi-paper | no | yes | — | — | 0/2 |
| megabyte-and-blt-patches | multi-paper | no | yes | — | — | 0/2 |
| api-cost-by-language | multi-paper | no | yes | — | — | 1/2: 2 |
| renyi-efficiency | multi-paper | no | yes | — | — | 0/2 |
| gpt-4-number-tokens | multi-paper | no | yes | — | — | 0/2 |
| wechsel-neighbours | follow-up | no | yes | — | — | 0/1 |
| canine-hashing | follow-up | no | yes | — | — | 1/1: 1 |
| digits-fourth-digit | follow-up | no | yes | — | — | 0/1 |
| vocabulary-with-scarce-data | follow-up | no | yes | — | — | 1/1: 1 |
| code-tokenizer-initialisation | follow-up | no | yes | — | — | 0/1 |
| magikarp-norm-indicator | follow-up | no | yes | — | — | 1/1: 1 |
| superbpe-mmlu | follow-up | no | no | — | — | 0/1 |
| tokenization-latency | follow-up | no | yes | — | — | 1/1: 1 |
| bpe-english-french | unanswerable | no | no | — | — | — |
| blt-70b-mmlu | unanswerable | no | no | — | 70b | — |
| blt-8b-gpu-hours | unanswerable | no | no | — | 8bparameter | — |
| fast-wordpiece-gpu | unanswerable | no | no | — | — | — |
| sentencepiece-korean-speed | unanswerable | no | yes | — | — | — |
| byt5-learning-rate | unanswerable | no | yes | — | — | — |
| vitamin-d | unanswerable | yes | — | — | — | — |
| world-cup-2018 | unanswerable | yes | — | — | — | — |

## Variation

3 runs of the whole set, one after another in one process; the report above is run 1's, and the answers file's runs file holds the others. A range is the lowest and highest rate over the runs.

| Measure | Run 1 | Run 2 | Run 3 | Range |
|---|---:|---:|---:|---:|
| Abstention rate, unanswerable | 2/8 | 2/8 | 2/8 | 0.25–0.25 |
| Abstention rate, near-miss | 0/6 | 0/6 | 0/6 | 0.00–0.00 |
| Abstention rate, out-of-topic | 2/2 | 2/2 | 2/2 | 1.00–1.00 |
| False-abstention rate, answerable | 0/28 | 0/28 | 0/28 | 0.00–0.00 |
| Grounded rate | 28/34 | 27/34 | 27/34 | 0.79–0.82 |
| Recall@5, answerable | 0.41 | 0.41 | 0.41 | 0.41–0.41 |

### Questions whose verdict changed

1 of 36 questions; each count is out of the 3 runs, and the verdicts are in run order.

| Question | Type | Abstained | Grounded | Verdicts |
|---|---|---:|---:|---|
| gpt-4-number-tokens | multi-paper | 0/3 | 1/3 | grounded, not grounded, not grounded |

- Turns whose reply changed wording from run 1: 14 of 44 (byt5-span-length, xlm-r-tokens-per-language, superbpe-curriculum, megabyte-and-blt-patches, gpt-4-number-tokens, wechsel-neighbours Turn 1, wechsel-neighbours Turn 2, digits-fourth-digit Turn 2, vocabulary-with-scarce-data Turn 1, vocabulary-with-scarce-data Turn 2, magikarp-norm-indicator Turn 2, tokenization-latency Turn 1, tokenization-latency Turn 2, byt5-learning-rate)
- Turns whose retrieved Chunks changed from run 1: 0 of 44 (a follow-up's can move, as its history's replies feed the rewriter)

## Timings

These depend on the machine and change from run to run. They count every Turn of the reported run, a follow-up's history included; rewriting counts only the Turns that were rewritten, as a Conversation's first Turn is not.

| Step | Turns | p50 | p95 |
|---|---:|---:|---:|
| retrieval | 44 | 0.15 s | 0.30 s |
| rewriting | 8 | 1.84 s | 2.20 s |
| answering | 44 | 9.17 s | 14.98 s |
| whole Turn | 44 | 9.80 s | 16.31 s |
