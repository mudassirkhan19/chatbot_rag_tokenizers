# Where the chatbot's failures first go wrong, 2026-10-21

The diagnosis #77 asks for: for each failure kind the developer's grounding labels found (#69, `data/eval/grounding-check.csv`), the point in the pipeline where it first goes wrong. It was a time-boxed pass of about an hour. Kinds 1, 2, 3, 4 and 8 were tested with experiments. Kinds 5, 6, 7 and 9 were classified from the labels and replies without new experiments, and say so. Nothing in the committed chat run is changed: every experiment ran from the scripts in [`2026-10-21-chat-failure-diagnosis/`](2026-10-21-chat-failure-diagnosis/), and its output stayed outside the repo.

## Which run

The labels judge the replies of the run before #72, and that run retrieved without a **Collapsed ranking**. #72 then switched `[chat]` to `dense.bge-small+collapsed` and re-ran `chat-eval`. So each kind is checked on both runs: the labelled reply, and the same Turn in the committed run (`data/eval/chat-answers.jsonl`: gemma4:e2b-mlx, temperature 0, k 5, history 3). `compare.py` prints both, side by side, for the 20 sampled Turns.

At temperature 0, replaying a Turn's prompt reproduces the stored Rewrites exactly, and most stored replies. Two replies varied in their wording, not their content (sentencepiece-korean-speed, code-tokenizer-initialisation).

## Summary

| # | Failure kind | First goes wrong at | Cause | Fixed by #72? | Evidence |
|---|---|---|---|---|---|
| 8 | Duplicate Chunks | the Collapsed ranking | the collapse | no: 15 of 44 committed Turns hold a near-duplicate pair | tested |
| 2 | Named paper not retrieved | retrieval | the query (a comparison read as one embedding) and the embedder | partly: MEGABYTE now at rank 5 by another Chunk | tested |
| 1 | Rewrite loses the referent | the Rewrite | the rewrite prompt and the model | no: same Rewrites | tested |
| 4 | Misattribution | the answer | the answer prompt (no rule tying a claim to its paper) | no: worse | tested |
| 3 | Unanswerable answered anyway | the answer | the model; a prompt rule doesn't fix it | no | tested |
| 5 | Incomplete answers | the answer, and retrieval for one side | the model; the retrieval of kind 2 | partly | classified |
| 6 | Dropped qualifiers | the answer | the model | not measured | classified |
| 7 | Retrieved specifics not used | the answer | the model | not measured | classified |
| 9 | The check passes all of it | the check | the check, by design | no | from the labels |

## 8. Duplicate Chunks: the Collapsed ranking misses reworded and renumbered copies

**Failure point: the Collapsed ranking (ADR 0057).** On the labelled run, no Collapsed ranking was applied. In magikarp-norm-indicator, all five Chunks came from three files of one Work, `land-2024-fishing-magikarp-automatically`: the EMNLP Edition (`b3ef…`), arXiv v2 (`7c88…`) and v1 (`d439…`). The manifest groups them correctly.

On the committed run the Collapsed ranking is applied and duplicates remain. `dups.py` counts, for each Turn, the pairs of retrieved Chunks that come from different files of one Work and share at least half their word 5-grams (measured on the smaller Chunk). **15 of the 44 Turns hold such a pair**, some 96–100% identical:

| Turn | Copies | Overlap | Why the place key misses them |
|---|---|---|---|
| canine-amharic, canine-hashing | `d6f1…-0048` (2022.tacl-1.5) / `33a9…-0043` (2103.06874v4) | 0.96 | Section path `4.4 NER Results` vs `4 Experiments › 4.4 NER Results`: GROBID nests the Section in one Edition only |
| digits-right-to-left, digits-fourth-digit | `0139…-0013` (2512.20757v1) / `fbb5…-0011` (v2) | 0.96 | `2 BACKGROUND` vs `2. Background` |
| tokenizer-swap-budget, code-tokenizer-initialisation | `235f…-0033` / `4581…-0029` (2405.07883v1/v2, a table) | 1.00 | nesting, as for CANINE |
| wechsel-freezing, wechsel-neighbours | `62b2…-0033` (2112.06598v1) / `0580…-0033` (NAACL) | 0.63 | `5.4.2 Is freezing necessary?` vs `5.3 …`: renumbered |
| tokenization-latency | `2a86…-0028` (2305.15425v2) / `9102…-0055`, `-0056` (v1) | 0.61, 0.51 | `5 Fairness… › 5.2 Latency` vs `6 … › 6.2 Latency`, and v2 rewords the paragraph |
| bpe-dropout-rate, magikarp-norm-indicator, byt5-learning-rate | e.g. `1170…-0011` / `2bb2…-0015` | 0.66–0.70 | same Section path, but a different count of Chunks before it |

The collapse merges copies only at "the same Section path, and the same count of Chunks before it". Editions and Versions of one paper break that key in four ways: GROBID nests a Section differently, headings change case or punctuation, Sections are renumbered, and a revision adds or splits paragraphs. Each duplicate takes a slot one of the five could have used for the other side of a comparison (megabyte-and-blt-patches, kind 2).

**Cause: the collapse.** Its key is too strict for real Editions. A fix should match copies within a Work by their text, not their place.

## 2. Retrieval misses the paper the question names

**Failure point: retrieval, at the query.** On megabyte-and-blt-patches, the MEGABYTE Passage (`94e3…-0001`, its Introduction) ranks as follows (`probe.py`, k=50):

| Query | Raw rank | Collapsed rank |
|---|---|---|
| the question, as asked (a comparison) | 11 | 8 |
| "How does MEGABYTE group bytes into patches?" | 13 | 9 |
| MEGABYTE's title + "How are byte sequences segmented into patches?" | 2 | **1** |

The BLT Passage (`23e0…-0000`, the Abstract) isn't in the top 50 for the comparison, and ranks 18 even for "How does the Byte Latent Transformer group bytes into patches?". BLT's body Chunks (0008, 0012) outrank its Abstract.

The Chunk text and the Context header are not the problem: once the query names the paper's title, the Introduction ranks first. The cause is how the question reaches the embedder. A short name like "MEGABYTE" carries little weight in bge-small's embedding, against a body of BLT and SpaceByte Chunks that discuss MEGABYTE in the same words. In a comparison, the whole question becomes one embedding, and it lands near whichever paper restates both sides. On the committed run, the collapse frees a slot and MEGABYTE's "2.1 Overview" Chunk (`-0006`, "chunks it into patches of length P") enters at rank 5. That is a usable Chunk but not the labelled Passage, so `passages_found` is `[]`.

The same pattern shows on compression-and-accuracy. "Tokenization Is More Than Compression" is in the corpus (`schmidt-2024-tokenization-more-than`, both Editions indexed), but the comparison question retrieves only Goldman et al. (4 slots) and Arnett. Put the title first and it ranks 2nd.

**Cause: the query and the embedder.** It isn't restatement crowding alone, or the Chunk text. Fix candidates: retrieve once for each paper a comparison names and merge the results, or give the lexical match of a name more weight (BM25 or hybrid).

## 1. Rewrite and coreference failures

**Failure point: the Rewrite.** `rewrites.py` replays the rewriter with the production prompt and history (the earlier question and its answer without markers, as `Chatbot.ask` builds it), with the questions alone, and with a sharper prompt that also asks it to "always name the method, model or paper the question is about":

| Turn | Production (reproduces the stored Rewrite) | Questions only | Sharper prompt |
|---|---|---|---|
| wechsel-neighbours | "When **the process** builds…" | pastes Turn 1 in front of the follow-up | "…for WECHSEL?" ✓ |
| vocabulary-with-scarce-data | "What happens to the predicted optimal vocabulary size…" (no paper) | "the optimum" | adds "for the Llama2-70B model", over-specified ✗ |
| code-tokenizer-initialisation | "…before that training in the code study?" | same | names both papers, duplicated ✗ |
| canine-hashing | "How does CANINE…" ✓ | "the model" | ✓ |
| digits-fourth-digit | "…the left-to-right version…" (no study) | same | names the study, appends "Tokenization method." ✗ |

The history isn't the cause. Showing questions only (no answers) is worse, and in production the referent (WECHSEL, the vocabulary scaling-law paper, Dagan et al.) is always in Turn 1's question. The prompt only asks the model to replace pronouns ("it", "that", "they"). Definite descriptions that point back, such as "that optimum", "the code study" or "the left-to-right version", are left alone, and the paper that frames the Conversation is dropped. The sharper prompt fixes wechsel-neighbours but breaks two others. The 2B model follows a longer instruction unevenly.

**Cause: the rewrite prompt first, then the model.** A fix needs a prompt change measured on every follow-up of the Evaluation set, not on these five.

## 4. Misattribution

**Failure point: the answer.** digits-fourth-digit retrieves Chunks from three Works: Baeumel et al. 2025 (`[1]`, the look-ahead paper), Singh & Strouse 2024 (`[2][3]`, the source) and Bie et al. 2026. The answer takes `[1]`'s explanation (left-to-right generation vs right-to-left arithmetic) as the reason for Singh's 8.25% result, though `[3]` says the cause is likely "misalignment between input and output tokenizations". The committed run makes it worse: it adds "due to a final carry" and cites `[1][3]`.

`answers.py` re-answers over the committed Chunks with two rules added to the system prompt: use only Chunks about a language, model or setting the question names; and "Each Chunk comes from the paper named in its header. Never give one paper's explanation as the reason for another paper's result." With them, the borrowed explanation is gone ("…dropping to 8.25% accuracy, which is referred to as the 'length mismatch' condition [2][3]"). The control Turns are unchanged: canine-amharic and magikarp-verified-share give the same content, and bpe-and-wechsel-vocabularies is word for word.

**Cause: the answer prompt.** It says nothing about keeping each paper's claims apart, though every Chunk's header names its paper. One Turn is evidence for a fix to try, not a measured fix.

## 3. Unanswerable questions answered anyway

**Failure point: the answer.** sentencepiece-korean-speed retrieves SentencePiece's speed Chunk, which gives English and Japanese speeds only, and the answer reports those. code-tokenizer-initialisation retrieves only Dobler et al. (`dobler-2025-token-distillation-attention`, 5 slots), not Dagan et al.'s code study. It answers with Dobler's subtoken-mean initialisation as if it were the code study's. Both are "nearby facts in place of a missing detail".

The strict prompt above doesn't fix either. Korean still gets the English and Japanese speeds, plus a new, misleading "For Korean, SentencePiece is used for BPE tokenization [3]". The code study still gets Dobler's method, now called "in the code study". The model saw rule 4 (abstain if the Chunks do not answer) and an explicit rule about named languages, and answered anyway.

**Cause: the model, with retrieval as a contributor on code-tokenizer-initialisation.** That Turn's Rewrite loses "Dagan et al." (kind 1), so the paper it should have checked isn't retrieved. A prompt rule doesn't change gemma4:e2b's behaviour on near-misses. What's left is a bigger answer model, or a check after the answer.

## 5–7. Incomplete answers, dropped qualifiers, unused specifics (classified, not tested)

- **5, incomplete:** megabyte-and-blt-patches never says how BLT patches. On the labelled run the Chunks held it (`[1]` = BLT `-0012`) and the model described only MEGABYTE. On the committed run it still gives only MEGABYTE's side. compression-and-accuracy answers from Goldman et al. alone, because the other paper isn't retrieved (kind 2), and the committed reply starts by echoing the question. **Cause: the model, plus retrieval for one-sided comparisons.**
- **6, dropped qualifiers, and 7, "some studies":** the labels name them, but no Turn was tested. Both happen when the Chunks hold the qualifier or the name and the reply doesn't. **Cause: the model, by elimination.** Neither retrieval nor the prompt removes the information. The digits experiment suggests a prompt rule about the papers in the headers is worth trying on these too.

## 9. What the automatic check misses

The check marked all 20 sampled Turns grounded. The developer labelled 16 grounded, 3 not grounded (bpe-and-wechsel-vocabularies, digits-fourth-digit, sentencepiece-korean-speed) and left 1 unlabelled with the note "unanswerable from context, answered anyway" (code-tokenizer-initialisation). Among the 16 grounded, the notes find a further failure in 6: compression-and-accuracy, megabyte-and-blt-patches and wechsel-neighbours (kinds 5 and 1), vocabulary-with-scarce-data (kind 1), and magikarp-norm-indicator and tokenization-latency (kind 8).

So **10 of 20 sampled answers have a problem the developer saw and the check couldn't**: 4 not grounded or not answerable, and 6 grounded but flawed. The check only looks at markers and numbers, so it is blind to kinds 1–7 by design. This is the cause, not a bug in it. It can't serve as the quality measure for the fixes above. A fix to kinds 3–7 needs its own measure (labels, or a judge that reads claims).

## The agreement on the sampled reply

The issue also asks for the chat report to score the check on each sampled reply directly, rather than only where the committed run gave the same reply. That is a code change, not diagnosis, so it is filed as its own issue.

## Reproducing

From a checkout with the parse cache and the index cache, `uv run python docs/reports/2026-10-21-chat-failure-diagnosis/chunks.py <out.pkl>` dumps the Chunks. `compare.py`, `dups.py <pkl> data/eval/chat-answers.jsonl`, `probe.py <chunk ids> <queries…>`, `rewrites.py` and `answers.py <pkl> <question ids…>` print the tables above. `rewrites.py` and `answers.py` need Ollama 0.40.5 with the pinned model.

## Fixes filed

Under #63: #80 (the collapse merges by text), #81 (retrieve for each named paper), #82 (the rewrite keeps the referent), #83 (the answer prompt's attribution rule), #84 (score the check on each sampled reply), #85 (a larger answer model, a defer candidate).
