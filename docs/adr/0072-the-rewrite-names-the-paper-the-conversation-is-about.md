# 0072. The Rewrite names the paper the Conversation is about

- **Date:** 2026-10-21
- **Status:** Accepted; amends [0056](0056-follow-ups-the-conversation-and-the-rewrite.md) (the rewrite prompt).

## Context
The diagnosis of #77 ([report](../reports/2026-10-21-chat-failure-diagnosis.md), kind 1) found that the rewriter loses the paper or method a Conversation is about. The rewrite prompt of 0056 asks only for words like "it", "that" and "they" to be replaced. Descriptions that point back, such as "that optimum", "the code study" or "the left-to-right version", are kept, and in wechsel-neighbours "it" became "the process". A sharper prompt fixed WECHSEL but broke two other Turns. Issue #82 asks for a prompt change measured on every follow-up of the Evaluation set: each Rewrite before and after, Recall@5 on follow-ups, and no Rewrite made worse by an invented referent.

## Decision
**The rewrite prompt also names the paper, method or model.** The new `rewrite_prompt` in `[chat]` adds "the study" to the examples of words that point back, and asks that each be replaced "naming the paper, method or model as the conversation names it". It adds "Add nothing the conversation doesn't say". It asks for "the rewritten last question only: one question", and says "Don't repeat the earlier questions, and don't refer to "the conversation" or "the previous answer"". Everything else is as in 0056. No code changes, and the rewriter's messages are unchanged.

**Measured two ways on the 8 follow-ups.** [`rewrites.py`](../reports/2026-10-21-rewrite-prompt/rewrites.py) rewrites each follow-up with each prompt in [`candidates.py`](../reports/2026-10-21-rewrite-prompt/candidates.py). It shows the history two ways: as its stored questions only, as `evaluate`'s rewriter row does (0067), and as those questions with the committed chat run's answers, as `chat-eval` does. Each Rewrite is scored by Recall@5 on the chat retriever, `dense.bge-small+collapsed`. The old prompt reproduces the committed numbers: 0.25 from questions, 0.50 from answers.

| Follow-up | Before, questions only | After, questions only | Before, with answers | After, with answers |
|---|---|---|---|---|
| wechsel-neighbours | pastes the history question in front ✗ (0/1) | the same paste, with WECHSEL ✗ (0/1) | "When **the process** builds…" ✗ (0/1) | "When **the WECHSEL method** builds…" ✓ (1/1) |
| canine-hashing | "How does **the model** give…" ✗ (0/1) | "How does **CANINE** give…" ✓ (1/1) | "How does CANINE give…" ✓ (1/1) | same ✓ (1/1) |
| digits-fourth-digit | "…where does the left-to-right version go wrong?" ✗ (0/1) | pastes the history question in front, "…in **the GPT arithmetic study**?" ✓ (0/1) | as before, questions only ✗ (0/1) | "…the left-to-right version **of the GPT arithmetic model**…" ✓ (0/1) |
| vocabulary-with-scarce-data | "What happens to the optimum…" ✗ (0/1) | "…for **the work on scaling laws for vocabulary size**?" ✓ (1/1) | "…the predicted optimal vocabulary size…" (1/1) | same (1/1) |
| code-tokenizer-initialisation | "…in the code study?" ✗ (0/1) | "…according to **Dagan et al.'s code study**?" ✓ (0/1) | "…in the code study?" ✗ (0/1) | "…described in **Dagan et al.'s code study**?" ✓ (0/1) |
| magikarp-norm-indicator | "…spots the under-trained tokens…" (1/1) | "…spots the under-trained tokens…, **according to Fishing for Magikarp**?" ✓ (0/1) | "…spots severely under-trained tokens…" (1/1) | "…spots the severely under-trained tokens…" (1/1) |
| superbpe-mmlu | "How much did the improvement on MMLU look like?" ✗ (0/1) | "How much did **SuperBPE** help on MMLU?" ✓ (0/1) | "How much did the two-pass tokenization strategy help…" (0/1) | "How much did **SuperBPE** help on MMLU?" ✓ (0/1) |
| tokenization-latency | "Do longer token sequences slow processing down…" (1/1) | "How does the time grow with length for the longer token sequences discussed in the paper on tokenization?" (1/1) | "Do longer token sequences also slow…" (1/1) | "…for the commercial language model API usage discussed in the answer?" (1/1) |
| **Recall@5** | **0.25** | **0.38** | **0.50** | **0.62** |

✓ marks a Rewrite that names its referent, ✗ one that doesn't, and the counts are Passages found in the top 5. The questions-only columns are the Rewrites of the committed eval report, before and after. Every referent the new prompt adds is named in the Conversation. None of them is the over-specified "for the Llama2-70B model" of #77's sharper prompt, or a second paper the follow-up isn't about.

**Repeat runs gave the same Recall, unless another process was using the model.** Five runs of `rewrites.py` with each prompt gave the same Recall@5 in both settings. Two of the new prompt's 16 Rewrites varied in wording between runs, both in the questions-only setting (digits-fourth-digit: with or without the pasted history question; tokenization-latency). Neither changed its count. One `evaluate` run overlapped with another worktree's `evaluate` on the same Ollama server. In it, tokenization-latency pasted its history question in front and lost its Passage, and the chat retriever's rewriter row stayed at 0.25. The committed report is from a run with no other process using the model, and it agrees with `rewrites.py`. Eight follow-ups are a small sample: one Passage is 0.12 of Recall@5.

## Alternatives considered
The other prompts are in `candidates.py`, and each scored at or below the adopted one in both settings:
- **#77's sharper prompt and variations of it** ("describe", "name-first": a longer instruction to add the paper's name). These scored 0.12 from questions and 0.50 from answers. The 2B model copies the history question into the Rewrite more often under a longer instruction, and name-first adds "for the Llama2-70B model" to vocabulary-with-scarce-data.
- **Worked examples in the prompt** ("base+ex", "base+ex3", "short+ex"), with two Conversations not in the Evaluation set. They scored 0.25, 0.12 and 0.00 from questions. The model began its reply with "Rewrite:" or kept "it" unchanged. Examples as separate user and assistant messages weren't tried: the prompt in the config alone fixed the referent, and a message format would be a code change to the rewriter for no measured gain.
- **Dropping the "don't refer to the conversation" sentence, or wording it another way** ("D", "E"). Both scored 0.25 from questions, because the history paste came back in two more Turns. Neither removed "discussed in the answer" from tokenization-latency.

## Consequences
- On the committed eval report, the rewriter row's Recall@5 changes as follows. The reference rewrite is unchanged.

  | Retriever | Before | After | Reference rewrite |
  |---|---|---|---|
  | bm25 | 0.00 | 0.00 | 0.62 |
  | bm25+collapsed | 0.00 | 0.12 | 0.75 |
  | dense.bge-small | 0.25 | 0.38 | 0.50 |
  | **dense.bge-small+collapsed** (the chat retriever) | **0.25** | **0.38** | 0.50 |
  | dense.bge-base | 0.12 | 0.12 | 0.38 |
  | dense.bge-base+collapsed | 0.38 | 0.25 | 0.50 |
  | dense.openscholar, and +collapsed | 0.00 | 0.12 | 0.12 |
  | hybrid.bm25+bge-small | 0.12 | 0.25 | 0.62 |
  | hybrid.bm25+bge-small+collapsed | 0.12 | 0.50 | 0.88 |
  | hybrid.bm25+bge-base | 0.12 | 0.12 | 0.50 |
  | hybrid.bm25+bge-base+collapsed | 0.12 | 0.38 | 0.62 |
  | hybrid.bm25+openscholar, and +collapsed | 0.00 | 0.12 | 0.50 |

  The hybrids gain most, as expected when a Rewrite now carries the paper's name for BM25 to match. Only dense.bge-base+collapsed loses: its MRR@10 on the row also drops (0.197 to 0.109). MRR@10 falls on both bge-small rows too (0.250 to 0.222, 0.266 to 0.182), while Recall@5 rises: more Passages are found, but the first one found ranks lower on average.
- Naming the paper doesn't always find its Passage. code-tokenizer-initialisation, superbpe-mmlu and digits-fourth-digit now name their referent but still score 0. magikarp-norm-indicator, shown questions only, names Fishing for Magikarp and loses the Passage it found before. The embedder's weak hold on short names (#77, kind 2) is the next limit, which #81 takes up.
- Two faults remain. Shown questions only, wechsel-neighbours still pastes its history question in front (the old prompt did too), and digits-fourth-digit does in some runs. tokenization-latency ends "…discussed in the answer" when shown answers: it points at the Conversation, though it doesn't invent a referent, and no wording tried removed it.
- The chat run isn't regenerated here (#82's coordination note). #86 re-runs `chat-eval` once #80, #81 and #82 have landed, and its follow-up Recall@5 is the measure in use.
