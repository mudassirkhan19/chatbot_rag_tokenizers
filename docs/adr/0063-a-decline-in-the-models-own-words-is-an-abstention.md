# 0063. A decline in the model's own words is an Abstention

- **Date:** 2026-10-20
- **Status:** Accepted; amends [0054](0054-pinned-local-answer-model-and-the-chat-page.md)'s and [0059](0059-abstention-by-instruction-and-the-chat-report.md)'s rule for what an Abstention is

## Context
ADR 0054 counts a reply as an Abstention only when it holds the fixed sentence, "The papers in this corpus do not answer this question." ADR 0059's run found that the pinned model (gemma4:e2b-mlx) mostly declines in its own words instead: "The provided chunks do not contain the specific BLEU score …". The committed #67 run has seven such declines, the same in all three of #75's runs:

- five near misses: bpe-english-french, blt-70b-mmlu, blt-8b-gpu-hours, fast-wordpiece-gpu and byt5-learning-rate (counted as grounded, because its decline starts with two stray markers, `[3][5]`, on a line of their own);
- two answerable questions whose retrieval missed: llama2-70b-vocabulary and superbpe-mmlu.

Each was counted as an uncited, ungrounded answer. So the near-miss abstention rate (0/6), the false-abstention rate (0/28) and the grounded rate (28/34) measured the fixed phrase as much as the bot's decision. The glossary already defines an Abstention by what it says: it "says plainly the corpus does not support an answer". Issue #73 offered two levers, to be chosen by measurement: hold the model to the sentence through the prompt, or widen what counts as an Abstention.

## Decision
**Widen the match; leave the prompt as 0054 left it.** A reply is an Abstention when it holds the fixed sentence, as before, or when its text, with its markers taken out, is **one sentence that opens with a decline of the Chunks**. A decline is, on the Passage matcher's normalised words: optionally "the", then optionally "provided", "given" or "retrieved", then "chunks" or "excerpts", then "do not", "does not", "don't" or "doesn't", then optionally "explicitly", "specifically", "directly" or "clearly", then one of "contain", "state", "mention", "include", "provide", "specify" or "say". The phrases are the model's own, from the committed answers, with a few near synonyms.

**A decline followed by an answer is an answer.** The one-sentence condition is the guard against false positives. "The provided chunks do not contain TransInner's results. WECHSEL does not need freezing [1]." has two sentences, so it is an answer and is checked for grounding. An answer that only mentions abstaining, as 0054's test requires, stays an answer too. A sentence ends at ".", "!" or "?" followed by a space, so a decline that an abbreviation splits ("e.g. the …") stays an answer. The rule errs towards counting a reply as an answer, which is what the old rule did with every decline.

**A decline that carries markers is an Abstention, and its markers are kept.** byt5-learning-rate's reply is `[3][5]`, a blank line, then the decline. Rule 2 has the model cite a sentence after it, and these markers come before any sentence, so they cite nothing the reply says. The reply is counted as an Abstention, with no grounding, like any other. Its markers stay in the answer as written, as 0054 requires: never dropped. On the page they show as markers with their references, and the answers file lists them under `cited`. A marker after the decline doesn't change the verdict either: the sentence still claims only that the Chunks lack the answer.

**One rule for the page and `chat-eval`.** `read_answer` decides it, and the page's Conversation, `chat-eval` and `chat-eval --from-answers` all call it. The rule lives in code beside the fixed sentence's match, not in `[chat]`: it decides how a reply is scored, and the answers file's first line names only what the replies were asked over.

## Alternatives considered
- **Holding the model to the sentence (lever 1).** Rule 4 was given one more sentence: "Do not say in your own words what the Chunks lack or do not contain." A 3-run `chat-eval` with that prompt, compared with the committed run:
  - Only one of the seven declines became the fixed sentence (bpe-english-french). The other five kept their own words, with "Chunks" now capitalised as the prompt writes it.
  - llama2-70b-vocabulary stopped declining and answered from an unrelated Chunk: it gave Llama2 7B's 32K vocabulary, cited it, and was counted as grounded with none of its Passages retrieved. A wrong answer counted as grounded is worse than a decline.
  - Across its three runs, 13 of the 44 replies changed wording from run 1, against the committed run's 14, and no verdict changed. But three follow-up Turns retrieved other Chunks between runs (their history's replies changed the Rewrite), against none in the committed run. So the prompt didn't make the verdicts vary (0056's concern), and it barely moved the decision either.
  - The rates on the old rule: near miss 1/6, out of topic 2/2, false abstention 0/28, grounded 29/33. Scored with the widened rule as well, they were near miss 5/6 and false abstention 1/28. That is the same near-miss rate as widening alone; the false-abstention rate is lower only because llama2-70b-vocabulary's decline became the wrong answer above.

  ADR 0054 had already found one rewording that didn't move a near miss. This is a second. The prompt stays unchanged, so the committed replies stay comparable with #67's.
- **Both levers.** As measured above, the prompt adds nothing to the widened match on the near misses, and it costs llama2-70b-vocabulary's decline.
- **A decline anywhere in the reply**, as the fixed sentence is matched anywhere. "WECHSEL does not need freezing [1]. The provided chunks do not state whether it helps." answers and only mentions a gap. Matching it would hide an answer from the grounded rate, which is the false positive the issue rules out.
- **A decline with any marker counted as an answer.** This would keep byt5-learning-rate counted as grounded for two markers that cite no sentence of its reply, and that sentence answers nothing.
- **Dropping a decline's stray markers.** 0054 never drops a marker, so that a reader sees exactly what the model wrote. An Abstention already has no grounding, so its markers change no rate.
- **A judge model deciding whether a reply declines.** As in 0059, that is a second model call per Turn and a second pin. The model's declines are few and formulaic: every one in the committed answers opens "The provided chunks do not contain" or "… do not explicitly state". A pattern catches them exactly, and the re-score shows it catches nothing else.

## Consequences
- **Re-scoring the committed #67 replies** (`chat-eval --from-answers`, with no model noise) moves exactly the seven declines above to Abstentions, in all three runs, and changes no other verdict:

  | Rate | #67 run | Re-scored |
  |---|---|---|
  | Near miss | 0/6 (0.00 [0.00, 0.39]) | 5/6 (0.83 [0.44, 0.97]) |
  | Out of topic | 2/2 | 2/2 |
  | False abstention | 0/28 (0.00 [0.00, 0.12]) | 2/28 (0.07 [0.02, 0.23]) |
  | Grounded | 28/34 (0.82 [0.66, 0.92]) | 27/27 (1.00 [0.88, 1.00]) |

  (The issue quotes 27/34 grounded, from #67's single run. #75's committed run 1 has 28/34, gpt-4-number-tokens being flaky.)
- **The committed run is a fresh `chat-eval --runs 3`** with this rule and the prompt unchanged, compared with #75's committed run through `--baseline`. It gives the re-score's numbers in run 1: near miss 5/6, out of topic 2/2, false abstention 2/28, grounded 27/27, Recall@5 0.41. Its *Against the baseline* section lists the same seven questions, and no other. Across the three runs the Abstentions were the same, and the grounded rate was 27, 26 and 26 of 27: gpt-4-number-tokens flipped as it did in #75's runs. 11 of the 44 replies changed wording from run 1, and one follow-up Turn (tokenization-latency) retrieved other Chunks. Every one of the 27 abstaining Turns over the three runs is the fixed sentence or a one-sentence decline. None cites a Chunk to answer the question.
- **The near miss still answered** is sentencepiece-korean-speed. It gives SentencePiece's English and Japanese speeds, with citations, in answer to a question about Korean, so it is an answer under any rule, and a wrong one that the grounding check passes. The grounding check sees citations and numbers, not whether the answer fits the question. #70's judge is where that belongs.
- **The two false Abstentions are real.** llama2-70b-vocabulary and superbpe-mmlu decline because retrieval missed their Passages: none of their Passages is in their five Chunks. That is the right reply to the Chunks the bot saw, and it shows the retriever's misses in the chat report instead of hiding them as ungrounded answers.
- **The grounded rate is now over answers only.** Before, it held six declines as not grounded and one as grounded. 27/27 says every reply that answers cites its Chunks and copies their numbers. It does not say that every answer is right.
- A reply that declines in words the pattern lacks ("The excerpts provided lack …", "There is no information in the chunks …") still counts as an answer, as all declines did before. A new decline phrase in a later run shows as an uncited, ungrounded answer in the per-question lines, and one more alternative in `_DECLINE` adds it, re-scored with `--from-answers`.
