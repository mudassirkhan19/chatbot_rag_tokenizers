# 0072. The hand check scores each sampled reply

- **Date:** 2026-10-21
- **Status:** Accepted

## Context
The chat report's *Grounding checked by hand* section compared a developer's label with the reported run's verdict, and only when the run gave the same reply over the same Chunks ([0071](0071-the-developers-check-of-the-grounding-verdict.md)). #72 re-ran `chat-eval` on the Collapsed ranking, so 3 of the 19 labels were still compared. But a label and the automatic check both judge one reply over its Chunks, and the sample stores both. The diagnosis of the labels (#77) filed #84 to score the check on the sampled reply itself.

## Decision
- **The check is scored on each labelled row as stored in the sample.** The row's reply is read again with the current Abstention sentence, and grounded over the row's retrieved Chunk ids looked up in the corpus, as `--from-answers` re-scores a stored Turn. The run's reply for that question plays no part, so a later run no longer removes labels from the comparison.
- **Only a row whose Chunks the corpus no longer has is left out.** The check reads the Chunks' header and text, which the corpus holds, so a row naming a Chunk it lacks can't be scored. The report names those rows.
- **A disagreement row gives the verdict on the sampled reply.** It is the check's verdict on what the developer read, not the run's.
- **A sampled reply that now reads as an Abstention stays compared.** Read again with a changed Abstention sentence, a labelled reply can decline. The check gives it no grounding verdict, so it counts as a disagreement. The report counts it on its own line, not as grounded or not grounded by the check.

## Alternatives considered
- **Use the stored draft label as the automatic verdict.** It is the verdict of the code that drew the sample. Scoring again uses the current check, as every re-scored measure in the report does, so a change to the check shows up in the agreement.
- **Ground over the cited Chunks' text stored in the row.** That needs no corpus, but the row stores only the cited Chunks. A marker naming no retrieved Chunk needs the count of retrieved ones, which the ids give, and the corpus keeps the check reading Chunks as the answer model was shown them.

## Consequences
- The committed report compares all 19 labels: 16 agree (0.84 [0.62, 0.94]), and all three disagreements are automatically grounded but not grounded by hand. These are the numbers [0071](0071-the-developers-check-of-the-grounding-verdict.md) recorded for the run they were drawn from.
- The agreement now measures the check, not the run. How grounded the reported run's own answers are by hand needs a sample drawn from it.
- The committed report's section was spliced in as 0071's was: a `--from-answers` report of copies of the committed answers came out the same above the section, and the answers files are unchanged.
