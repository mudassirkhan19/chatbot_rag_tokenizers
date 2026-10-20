# Failure analysis: six questions the chatbot still gets wrong, 2026-10-21

The failure analysis `docs/ASSIGNMENT.md` asks for (#78): questions the system still gets wrong, and why. It works from the committed chat run (`data/eval/chat-answers.jsonl`, ADR 0077: `dense.bge-small+per-paper+collapsed`, gemma4:e2b-mlx at temperature 0, k 5, history 3), and the system was not re-run. Each failure below is the same in all three runs of `data/eval/chat-answers-runs.jsonl`: the same Chunks, the same Rewrite and the same verdict.

The causes come from #77's diagnosis ([`2026-10-21-chat-failure-diagnosis.md`](2026-10-21-chat-failure-diagnosis.md)). #80, #81 and #82 fixed part of what it found, so each failure here is the part still left. The only new evidence is read-only: the Chunks' text, and the ranks of the Chunks that hold the answer. [`probe.py`](2026-10-21-failure-analysis/probe.py) ranks them under the committed retriever without its per-paper split, which changes only a question naming two or more papers. For the four Turns probed, its top 5 matches the committed `retrieved` exactly.

## Summary

| # | Question | Type | What the reply does | First goes wrong at | Kind (#77) | Fix |
|---|---|---|---|---|---|---|
| 1 | magikarp-norm-indicator | follow-up | abstains, though the paper answers | the Rewrite, then retrieval | 1, 2 | #88, #62 |
| 2 | llama2-70b-vocabulary | single-paper | abstains, though the paper's Abstract answers | retrieval | 2 | #62 |
| 3 | superbpe-mmlu | follow-up | gives a CommonsenseQA gain, from another paper, for MMLU | retrieval, then the answer | 2, 4, 3 | #62, #83, #85 |
| 4 | gpt-4-number-tokens | multi-paper | says GPT-4 groups digits from the right; it groups from the left | the answer | 4 | #83 |
| 5 | sentencepiece-korean-speed | unanswerable | gives English and Japanese speeds instead of abstaining | the answer | 3 | #85 |
| 6 | canine-hashing | follow-up | right, but cites nothing | the answer | new | #87 |

Two of them the automatic check passes as grounded (3 and 5). One it fails for the wrong reason (4).

## 1. magikarp-norm-indicator: the Rewrite drops the referent, and retrieval misses the Passage

**Conversation.**
Turn 1: "In Fishing for Magikarp, what share of the flagged candidate tokens were confirmed as under-trained, and how much of a vocabulary is that?" It is answered correctly: "5-50% of tested candidate tokens, which corresponds to 0.1-1% of the total vocabulary size [3]".
Turn 2: "Is there a signal in the weights that spots them without already knowing some?"

**Rewrite:** "Is there a signal in the weights that spots them without already knowing some in Fishing for Magikarp?"

**Answer given:** "The papers do not answer this question." It is a false abstention.

**Correct answer:** yes, the norm of the input embeddings, which "conveniently does not require a set of previously known untrained tokens". The Chunk is `b3ef5544a0943f38-0011` (EMNLP Edition, § 2.2 Under-trained token indicators). `7c88df71d4c601fc-0011` in arXiv v2 holds the same text, and the collapse merges it into the EMNLP Chunk.

**Where it goes wrong: the Rewrite first.** #82's prompt (ADR 0073) added the paper's name, as it should. But it left "them", where 0070's Rewrite had said "the under-trained tokens". The five Chunks retrieved are other parts of the paper (closed models, a results table, the v1 indicators section), plus another paper's use of Magikarp. None of them says what the norm indicator does without known tokens, so the model's decline is correct for its Chunks.

**Then retrieval.** A better Rewrite alone doesn't find the Passage:

| Query | Rank of `b3ef…-0011` (of 50) |
|---|---|
| the committed Rewrite ("…spots them…") | not in the top 50 |
| "them" → "under-trained tokens" | 14 |
| the Evaluation set's reference Rewrite ("which embedding-based indicator flags under-trained tokens without needing a set of known untrained tokens?") | 8 |

This is #77's kind 1, and then kind 2's weak hold of the embedder on the question's terms. The paper has many Chunks about indicators, and § 2.2 isn't the closest to any of these wordings.

**Fix:** #88 (new: the rewrite prompt also replaces "them"), then a reranker over the top 50 (#62), where the Passage is.

## 2. llama2-70b-vocabulary: retrieval returns the Llama3 appendix, not the Abstract

**Question:** "According to the work on scaling laws for vocabulary size, how many tokens did Llama2-70B really need in its vocabulary?"

**Answer given:** "The provided chunks do not contain the specific number of tokens Llama2-70B needed in its vocabulary." It is a false abstention.

**Correct answer:** at least 216K, "7 times larger than its vocabulary of 32K". The Chunk is the Abstract of Scaling Laws with Vocabulary (`f6ab4b65efb387f6-0000`, 2407.13623v3).

**Where it goes wrong: retrieval.** Two of the five Chunks are from the right paper, but from its Appendix A.11, Prediction for Llama3 (`-0060`, `-0061`). They mention Llama2's vocabulary and 70B models, and give the Llama3-400B figure (487K), not Llama2-70B's. The other three are from other papers. The decline is correct for these Chunks.

| Query | Rank of the Abstract (of 50) |
|---|---|
| the question, as asked | 22 |
| "Scaling Laws with Vocabulary: what optimal vocabulary size does it predict for Llama2-70B?" | 5 |

This is #77's kind 2. The question describes the paper ("the work on scaling laws for vocabulary size") rather than naming its title. Body Chunks that repeat its terms outrank the Abstract, as BLT's body Chunks did. #81's per-paper retrieval doesn't apply, since it splits only a question naming two or more papers.

**Fix:** a reranker over the top 50 (#62), where the Abstract is at rank 22. No filed fix changes the first-stage ranking for a paper that is described rather than named.

## 3. superbpe-mmlu: the wrong benchmark, from another paper, passed as grounded

**Conversation.**
Turn 1: "How does SuperBPE change BPE training so that it ends up with tokens that span several words?" It is answered correctly, from SuperBPE § 2 (two phases, whitespace pretokenization skipped in the second).
Turn 2: "How much did that help on MMLU?"

**Rewrite:** "How much did SuperBPE help on MMLU?" This is correct.

**Answer given:** "SuperBPE yields a 20.3 percentage point improvement on the CommonsenseQA benchmark compared to a model that used BPE [5]."

**Correct answer:** +8.2% on MMLU (36.5 to 44.7), within a +4.0% average over 30 tasks. Three of SuperBPE's Chunks hold it: the Introduction (`6b625407f4717f4a-0005`, the Passage), Table 1 (`-0010`) and the Abstract (`-0000`).

**Where it goes wrong: retrieval first.** The five Chunks are SuperBPE's results text (`-0019`: the 4.0% average and +9.7% on multiple choice, but not MMLU), its setup (`-0018`), its loss analysis (`-0024`), and two Chunks of another paper, Benchmarking BPE Tokenizers … with Bits per Byte (`ab54dfb946207c7e-0026`, `-0007`). None of them says "MMLU". The Introduction ranks 6th, one place outside k = 5. Table 1 ranks 29th, and the Abstract is not in the top 50. The reference Rewrite ("How much does the SuperBPE model improve over the BPE baseline on MMLU?") ranks the Introduction 13th, so the wording isn't the cause.

**Then the answer.** Without an MMLU figure, the model should abstain. It takes the one benchmark number in its Chunks instead: `[5]`'s report of another paper's result ("Liu et al. (2025) found that SuperBPE yields a 20.3 percentage point improvement on the CommonsenseQA benchmark"). It answers a different benchmark and drops whose claim it was. This is #77's kind 3 (a nearby fact in place of a missing one) and kind 4 (another paper's account). The check passes it, since 20.3 is in the cited Chunk (#77's kind 9).

**Fix:** a reranker (#62) for the Introduction at rank 6. The attribution rule (#83) and a larger model (#85) would be needed for the answer step, as #77 found a prompt rule alone doesn't stop near-miss answers.

## 4. gpt-4-number-tokens: one paper's custom tokenizer given as GPT-4's

**Question:** "What in GPT-4's tokenizer caps numeral tokens at three characters, and does it chunk lengthy figures starting from the left or the right?"

**Answer given:** "GPT-4's tokenizer splits digit spans into groups of three according to place values, and it chunks lengthy figures starting from the right. This is indicated by the regex used for digit grouping, which ensures that "123456" tokenizes as ["123", "456"] (thousands-aligned) rather than left-aligned ["12", "345", "6"] [1]."

**Correct answer:** the pre-tokenization regular expression, which limits a token to three digits, and it chunks from the left. Two of the five retrieved Chunks hold it:

- `762b049e1ca2dbb3-0013` (Singh & Strouse, Tokenization counts, Figure 3, rank 2): "cl100k base, the tokenizer for GPT-3.5 and GPT-4 … standardized number tokenization to chunks of 3 digits, left-to-right".
- `fbb556e5d06ae238-0061` (TokSuite, rank 4): "GPT-4 pre-tokenization follows GPT-2's approach, but it also creates a new token after 3 contiguous digits".

The Evaluation set's Passages are in other Chunks of these papers (`3ea111d46ca777bf-0015` in Dagan et al., `762b049e1ca2dbb3-0009`), so `passages_found` is `[]`. The answer is in the Chunks all the same.

**Where it goes wrong: the answer.** `[1]` is `dedfb2f3754f10c7-0071`, TokEval's appendix on its own pretokenizer variants. Its paragraph, "Right-aligned digits", describes a variant "identical to GPT-4o except the digit group regex uses a lookahead for place-value alignment". The model takes that variant as GPT-4's tokenizer, and the answer is the opposite of what the two Chunks about GPT-4 say. Neither of them is cited. This is #77's kind 4, misattribution: the header names TokEval, and the paragraph names the variant. The answer prompt has no rule tying a claim to its source.

The check calls the answer not grounded, but for the "4" of "GPT-4", which no cited Chunk holds (`dedf…-0071` says "GPT-4o"). It would call it grounded if the model had written "GPT-4o".

**Fix:** #83, the attribution rule. On digits-fourth-digit, #77 found that the rule removed a borrowed explanation and left the control Turns unchanged.

## 5. sentencepiece-korean-speed: a near miss answered with other languages

**Question:** "How quickly does SentencePiece segment Korean text?" The corpus doesn't say. It is an unanswerable near miss.

**Answer given:** "SentencePiece has a segmentation speed of around 21k and 74k sentences/sec for English and Japanese, respectively [1]. While there is specific mention of SentencePiece being used for BPE tokenization in Korean, the exact segmentation speed for Korean text is not explicitly stated in the provided chunks."

**Correct answer:** the Abstention sentence. A reply that adds the English and Japanese figures as context, clearly labelled, would be acceptable to a reader. But rule 4 asks for the sentence alone, and the reply leads with the wrong languages.

**Where it goes wrong: the answer.** Retrieval does what it can: three SentencePiece Chunks (§ 3.2 and § 4.2, the speed results), plus two Korean papers. The model reports the speeds the Chunks hold, then declines. Its "specific mention of SentencePiece being used for BPE tokenization in Korean" comes from `0d8e2a997e4cb2d3-0038`, the Jamo-level Korean MT paper, which uses SentencePiece and says nothing of its speed. The Abstention rule (ADR 0064) counts a decline after an answer as an answer, and the developer labelled the labelled run's reply "not grounded (should have abstained)".

This is #77's kind 3. #77 re-answered this Turn with a stricter prompt, and Korean still got the English and Japanese speeds, plus a new misleading sentence. A prompt rule doesn't change gemma4:e2b's behaviour on near misses.

**Fix:** #85, a larger answer model measured on near-miss abstention.

## 6. canine-hashing: right, and uncited

**Conversation.**
Turn 1: "What score does CANINE reach on Amharic named entities, a language it never saw in pre-training, and why can it read that script at all?" It is answered and cited ("50 F1 … [1]").
Turn 2: "How does it give every possible character an embedding without an enormous table?"

**Rewrite:** "How does CANINE give every possible character an embedding without an enormous table?" This is correct.

**Answer given:** "CANINE uses a generalization of the standard hashing approach where multiple hash functions are applied to each codepoint, and the representations associated with these hash values are concatenated. This yields multiple embeddings for each codepoint, which are then concatenated into a single representation. Because the model supports all codepoints, it can learn representations for characters it has never seen during pre-training."

**Correct answer:** what the reply says, with a citation. CANINE hashes each codepoint with K hash functions into K small embedding tables and concatenates the results. The Chunk is `d6f1920d5d5d32be-0013` (§ 3.1 Model, retrieved first), and the Passage, "CANINE uses hashing … with a relatively small number of parameters", is in its Chunks (1/1).

**Where it goes wrong: the answer.** Retrieval and the Rewrite are right, and the content is right. The reply has no marker, though rule 2 asks for one on every sentence. So the check counts it not grounded, and the page shows no reference. 0070's run cited it. ADR 0077 notes that the history Turn's reply changed when the text collapse (#80) left one copy of the NER result instead of two. The model is shown earlier answers without their markers, which may be what it copies here. That isn't tested.

#77 has no kind for this: its labels came from a run where this Turn cited. No filed issue covers it.

**Fix:** #87 (new): when a reply that isn't an Abstention cites nothing, ask once more for the markers, and measure.

## Also wrong, not traced here

- **digits-fourth-digit** (follow-up) no longer borrows Baeumel et al.'s explanation, #77's main example of kind 4. But it doesn't answer the question either. It says left-to-right "is significantly worse" in the "length mismatch" condition, and not that the model "always gets the fourth digit wrong" (`762b049e1ca2dbb3-0029`). That Chunk is not in the top 50 for the Rewrite, which drops the study's name ("the left-to-right tokenization version").
- **bpe-and-wechsel-vocabularies** (multi-paper) retrieves neither paper. It says the subword NMT paper "did not specify" its merges, though it used 59,500 and 89,500 (`f4e5a6bbbe0d8745-0017`). Its 10k, 32k and 64k come from another paper (`0aa9ed33e506a59f-0016`, 2020.lrec-1.450), and WECHSEL's 50k (`60e34b5be09609b8-0018`) is not given. Per-paper retrieval (#81) looks a name up by the words of a title. "The original subword NMT paper" doesn't match its title, Neural Machine Translation of Rare Words with Subword Units, so the question may be ranked as one query. The Names the model gave aren't stored, so that is not confirmed.

## Reproducing

From a checkout with the parse cache and the index cache: `uv run python docs/reports/2026-10-21-failure-analysis/probe.py <chunk ids, comma-separated> <query>…` prints the ranks above. The Chunks' text comes from #77's `chunks.py` and `show.py` ([`2026-10-21-chat-failure-diagnosis/`](2026-10-21-chat-failure-diagnosis/)). Neither needs Ollama.
