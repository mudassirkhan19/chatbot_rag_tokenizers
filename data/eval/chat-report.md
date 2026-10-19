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
- An answer is an Abstention when it holds the Abstention sentence, or when its text, without its markers, is one sentence declining in the model's own words, such as "The provided chunks do not contain …". Both are compared after the Passage matcher's normalisation. A decline that goes on to answer (another sentence, or a clause after ";", "but" or "however") or cites a Chunk after it is an answer. The abstention rate is the share of the questions answered with one: on the unanswerable questions it is the rate of correct Abstentions, on the answerable ones the false-abstention rate.
- An answer that is not an Abstention is grounded when it cites at least one retrieved Chunk, every marker in it names a Chunk retrieved for its Turn, and every number in it, cut into words as the Passage matcher cuts them (a word that starts with a digit, such as 50k or 0.1, but not ByT5), appears in a cited Chunk's context header or text. An uncited answer is not grounded. Abstentions are left out of the grounded rate.
- Recall@5: the share of a question's Passages held by one of the 5 Chunks its Turn retrieved, averaged over the answerable questions, with the Passage matcher of `evaluate` (ADR 0041).
- Every rate has its 95% Wilson interval, in the column beside it and in brackets in the lines below the table. It covers the sampling of the questions, not the answer model's run-to-run variation, which the Variation section measures. Recall@5 is a mean of per-question shares, not a proportion, and has no interval here: it is the retriever's measure, and the eval report gives its bootstrap interval (ADR 0061).

## Results

| Question type | Questions | Abstained | Abstention rate | 95% interval | Answers | Grounded | Grounded rate | 95% interval | Recall@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single-paper | 12 | 1 | 0.08 | [0.01, 0.35] | 11 | 11 | 1.00 | [0.74, 1.00] | 0.58 |
| multi-paper | 8 | 0 | 0.00 | [0.00, 0.32] | 8 | 8 | 1.00 | [0.68, 1.00] | 0.06 |
| follow-up | 8 | 1 | 0.12 | [0.02, 0.47] | 7 | 7 | 1.00 | [0.65, 1.00] | 0.50 |
| all answerable | 28 | 2 | 0.07 | [0.02, 0.23] | 26 | 26 | 1.00 | [0.87, 1.00] | 0.41 |
| unanswerable: near-miss | 6 | 5 | 0.83 | [0.44, 0.97] | 1 | 1 | 1.00 | [0.21, 1.00] | — |
| unanswerable: out-of-topic | 2 | 2 | 1.00 | [0.34, 1.00] | 0 | 0 | — | — | — |
| all unanswerable | 8 | 7 | 0.88 | [0.53, 0.98] | 1 | 1 | 1.00 | [0.21, 1.00] | — |
| all | 36 | 9 | 0.25 | [0.14, 0.41] | 27 | 27 | 1.00 | [0.88, 1.00] | 0.41 |

- Abstention rate on the unanswerable questions: 7/8 (0.88 [0.53, 0.98]); near-miss 5/6 (0.83 [0.44, 0.97]), out-of-topic 2/2 (1.00 [0.34, 1.00])
- False-abstention rate on the answerable questions: 2/28 (0.07 [0.02, 0.23])
- Grounded rate over every answer that is not an Abstention: 27/27 (1.00 [0.88, 1.00])
- Not grounded: 0 uncited, 0 with an invalid Citation, 0 with a number in no cited Chunk (an answer may be counted under more than one)

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
| llama2-70b-vocabulary | single-paper | yes | — | — | — | 0/1 |
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
| superbpe-mmlu | follow-up | yes | — | — | — | 0/1 |
| tokenization-latency | follow-up | no | yes | — | — | 1/1: 1 |
| bpe-english-french | unanswerable | yes | — | — | — | — |
| blt-70b-mmlu | unanswerable | yes | — | — | — | — |
| blt-8b-gpu-hours | unanswerable | yes | — | — | — | — |
| fast-wordpiece-gpu | unanswerable | yes | — | — | — | — |
| sentencepiece-korean-speed | unanswerable | no | yes | — | — | — |
| byt5-learning-rate | unanswerable | yes | — | — | — | — |
| vitamin-d | unanswerable | yes | — | — | — | — |
| world-cup-2018 | unanswerable | yes | — | — | — | — |

## Variation

3 runs of the whole set, one after another in one process; the report above is run 1's, and the answers file's runs file holds the others. A range is the lowest and highest rate over the runs.

| Measure | Run 1 | Run 2 | Run 3 | Range |
|---|---:|---:|---:|---:|
| Abstention rate, unanswerable | 7/8 | 7/8 | 7/8 | 0.88–0.88 |
| Abstention rate, near-miss | 5/6 | 5/6 | 5/6 | 0.83–0.83 |
| Abstention rate, out-of-topic | 2/2 | 2/2 | 2/2 | 1.00–1.00 |
| False-abstention rate, answerable | 2/28 | 2/28 | 2/28 | 0.07–0.07 |
| Grounded rate | 27/27 | 26/27 | 26/27 | 0.96–1.00 |
| Recall@5, answerable | 0.41 | 0.41 | 0.41 | 0.41–0.41 |

### Questions whose verdict changed

1 of 36 questions; each count is out of the 3 runs, and the verdicts are in run order.

| Question | Type | Abstained | Grounded | Verdicts |
|---|---|---:|---:|---|
| gpt-4-number-tokens | multi-paper | 0/3 | 1/3 | grounded, not grounded, not grounded |

- Turns whose reply changed wording from run 1: 11 of 44 (bpe-dropout-rate, xlm-r-tokens-per-language, megabyte-and-blt-patches, api-cost-by-language, gpt-4-number-tokens, wechsel-neighbours Turn 2, digits-fourth-digit Turn 2, vocabulary-with-scarce-data Turn 2, magikarp-norm-indicator Turn 2, tokenization-latency Turn 1, tokenization-latency Turn 2)
- Turns whose retrieved Chunks changed from run 1: 1 of 44 (tokenization-latency Turn 2) (a follow-up's can move, as its history's replies feed the rewriter)

## Against the baseline

Baseline: `data/eval/chat-answers.jsonl`, 3 runs, its verdicts as stored. Each question whose verdict here differs from the baseline's run 1 is listed, marked flaky in the baseline when its runs disagreed on it, so a change the baseline already varied on is not read as an effect.

| Question | Type | Baseline | Now | Note |
|---|---|---|---|---|
| llama2-70b-vocabulary | single-paper | not grounded | abstained | — |
| superbpe-mmlu | follow-up | not grounded | abstained | — |
| bpe-english-french | unanswerable | not grounded | abstained | — |
| blt-70b-mmlu | unanswerable | not grounded | abstained | — |
| blt-8b-gpu-hours | unanswerable | not grounded | abstained | — |
| fast-wordpiece-gpu | unanswerable | not grounded | abstained | — |
| byt5-learning-rate | unanswerable | grounded | abstained | — |

## Timings

These depend on the machine and change from run to run. They count every Turn of the reported run, a follow-up's history included; rewriting counts only the Turns that were rewritten, as a Conversation's first Turn is not.

| Step | Turns | p50 | p95 |
|---|---:|---:|---:|
| retrieval | 44 | 0.09 s | 0.21 s |
| rewriting | 8 | 0.57 s | 0.78 s |
| answering | 44 | 4.77 s | 7.06 s |
| whole Turn | 44 | 4.87 s | 7.34 s |
