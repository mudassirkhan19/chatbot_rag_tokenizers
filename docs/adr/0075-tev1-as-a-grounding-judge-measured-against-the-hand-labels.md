# 0075. Tev1 as a grounding judge, measured against the hand labels

- **Date:** 2026-10-21
- **Status:** Accepted

## Context
The automatic grounding check reads markers and numbers only ([0059](0059-abstention-by-instruction-and-the-chat-report.md)). The developer's hand check measures it on a sample of 19 labelled replies: it agrees on 16 ([0071](0071-the-developers-check-of-the-grounding-verdict.md), [0072](0072-the-hand-check-scores-each-sampled-reply.md)). Spec #63 (story 52) asks, last and droppable, for the decision model already pinned as the judge to score grounding too. It is to be reported with its own agreement against the hand labels, not trusted. That model is Tev1 4B on Ollama 0.40.5 ([0021](0021-tev1-decision-model-judge.md)).

## Decision
- **`chat-eval --judge` scores the labelled rows of the sample.** It scores the rows the hand check compares, using the same reply and Chunks. That is where its verdict can be measured. It works with `--from-answers` as well as a run that asks, since it needs Ollama but not the answer model. The judge is checked against its pin before anything is asked. Without the flag the report is unchanged.
- **A claim is a sentence that cites a Chunk.** `Answer.claims` cuts the reply into sentences where the Abstention reading cuts them. It keeps each sentence that holds a valid marker, without its markers, together with the Chunks it cites. A marker that opens a sentence ("… for BPE. [2] It …") cites the sentence before it. A sentence with no marker is no claim: it is the automatic check's job to fail an uncited answer.
- **One question per claim and cited Chunk, averaged per Turn.** The model is asked whether the Chunk supports the claim, and gives P(yes) for each pair. The state is the Chunk's context header and text, as the answer model was shown it, then the claim. A Turn's score is the mean over its pairs. It is grounded by the judge when the score is at least the threshold. A Turn with no claim has no score and is not grounded.
- **The question, threshold and pin are in `[chat.judge]`.** They sit in the retrieval config, beside the prompts of `[chat]`. A test keeps the pin equal to the scope config's `[judge]`. The report gives the pin, the threshold, and the sha256 of the state, instructions, criteria and threshold.
- **The threshold is 0.5, set before looking at the scores.** The only labels to tune it on are the 19 it is measured against, and a threshold tuned on them would overstate the agreement. One half is where the model leans to yes.
- **The section beside the hand check.** *The decision model* subsection gives the agreement with its Wilson interval and the split by direction. It has a table of every labelled row: the pairs judged, the score, and the judge's, the automatic check's and the developer's verdicts. A second table lists each disagreement with the developer's note.
- **One request shape for decision models.** `Ollama.decide` in the shared module ([0054](0054-pinned-local-answer-model-and-the-chat-page.md)) sends the `/v1/systemone` request and raises `InputTooLong` when the model refuses an input. The scope judge now goes through it, and still cuts and resends a refused abstract ([0025](0025-judge-cuts-only-refused-inputs.md)). Its request is the same as before, so its cached verdicts stand.

## Alternatives considered
- **Judge every Turn of the run.** That gives a judged grounded rate for the whole run, but nothing to measure it against. The sample is where a hand label exists.
- **Each claim against all its cited Chunks at once.** A claim spread over two Chunks would then not be failed by each one alone. But five Chunks of 350 tokens come near Tev1's 2,048-token input. The spec also asks for one question per claim and Chunk.
- **The lowest score per Turn instead of the mean.** That is closer to the developer's question, which asks whether every claim is supported. It isn't what the spec set, and with 19 labels the choice can't be measured. The table gives each Turn's mean, so a reader can see how near each one is to the threshold.
- **Tune the threshold on the labels.** See the decision above: the agreement would be measured on the labels the threshold was fitted to.

## Consequences
- **The first run.** The committed sample took under two minutes on the author's laptop for 55 pairs. The judge agrees with the hand labels on 16 of 19 (0.84 [0.62, 0.94]), the same as the automatic check. Its three disagreements are the automatic check's three: it grounds all three replies the developer failed, with scores of 0.89 to 0.99. No threshold separates them, since grounded rows score as low as 0.52. The failures the developer's notes describe are a borrowed explanation, a missing comparison, and an answer to an unanswerable question. Tev1 asked one sentence and one Chunk at a time does not see them. So on this sample the judge adds no signal beyond the automatic check.
- The committed report's section was spliced in as 0071's and 0072's were. A `--from-answers --judge` report of copies of the committed answers came out the same as the committed one everywhere else, and the answers files are unchanged.
- A change to the question, its criteria or the threshold changes the report, and is measured by rerunning `chat-eval --from-answers --judge`.
