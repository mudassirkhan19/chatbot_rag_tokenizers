# Chat transcript, 2026-10-21

Saved from the chat page (`just chat`). Each question retrieved the top 5 Chunks from dense.bge-small+per-paper+collapsed, and gemma4:e2b-mlx@e98b54fe1913 on Ollama 0.40.5 answered from them.

## Turn 1

**Question:** What score does CANINE reach on Amharic named entities, a language it never saw in pre-training?

**Answer:**

CANINE can achieve a score of 50 F1 on Amharic named entities, even though it had never seen Amharic text during pre-training [1]. This is noted as validation of CANINE's vocabulary-free approach [1].

**References:**

- [1] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation. 2022.tacl-1.5, also 2103.06874v4, 4.4 NER Results, p. 11.

**Retrieved, not cited:**

- [2] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2103.06874v4 · 6 Conclusion · p. 18
- [3] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 · 6 Conclusion · pp. 18–19
- [4] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2103.06874v1 · 6 Future Work · p. 11
- [5] Vocabulary Expansion for Low-Resource African Languages: A Case Study in Amharic and Tigrinya · 2607.15209v3 · Named Entity Recognition (NER). · p. 6

*retrieval 0.55 s · answer 1.7 s*

## Turn 2

**Question:** How does it give every possible character an embedding without an enormous table?

**Searched as:** How does CANINE give every possible character an embedding without an enormous table?

**Answer:**

CANINE supports the full space of Unicode codepoints by applying multiple hash functions to each codepoint and concatenating the representations associated with the various hash values [1]. This process yields multiple embeddings for each codepoint, which are then concatenated into a single representation [1].

**References:**

- [1] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation. 2022.tacl-1.5, also 2103.06874v4, 3.1 Model, pp. 4–5.

**Retrieved, not cited:**

- [2] Why don't people use character-level machine translation? · 2110.08191v2, also v1 · CANINE. · p. 4
- [3] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v1 and v4 · 3.1 Model · p. 4
- [4] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 and v1 · 3 CANINE · p. 3
- [5] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 · 3.2.1 Autoregressive Character Loss · p. 6

*rewrite 0.2 s · retrieval 0.20 s · answer 2.5 s*

## Turn 3

**Question:** How does that compare with how ByT5 handles characters?

**Searched as:** How does the comparison between CANINE's character handling and ByT5's character handling compare?

**Answer:**

CANINE operates on raw characters and is pretrained using the masked language modeling objective [2]. ByT5 operates on the raw UTF-8 bytes of the input without any downsampling [2].

**References:**

- [2] A Multi-dimensional Evaluation of Tokenizer-free Multilingual Pretrained Models. 2023.findings-eacl.128, 2 Tokenizer-free Multilingual Models, pp. 1–2.

**Retrieved, not cited:**

- [1] Where are we Still Split on Tokenization? · 2024.findings-eacl.9 · C Results Character-level Models · p. 11
- [3] Are Character-level Translations Worth the Wait? Comparing ByT5 and mT5 for Machine Translation · 2024.tacl-1.22, also 2302.14220v3 · 2 Related Work · p. 2
- [4] Are Character-level Translations Worth the Wait? Comparing ByT5 and mT5 for Machine Translation · 2024.tacl-1.22, also 2302.14220v3 · 3 Method · p. 3
- [5] Why don't people use character-level machine translation? · 2110.08191v2, also v1 · 3 WMT submissions · p. 3

*rewrite 0.6 s · retrieval 0.30 s · answer 1.6 s*

## Turn 4

**Question:** Which learning rate schedule did ByT5 use for pre-training?

**Searched as:** Which learning rate schedule did ByT5 use for pre-training?

**Answer (Abstention):**

The provided chunks do not contain information about the specific learning rate schedule used by ByT5 for pre-training.

**Retrieved, not cited:**

- [1] EUROLLM-9B: TECHNICAL REPORT · 2506.04079v2, also v1 · 2.3 PRE-TRAINING PHASES · p. 4
- [2] ByT5: Towards a Token-Free Future with Pre-trained Byte-to-Byte Models · 2022.tacl-1.17 · 6.4 Character Vocabulary · p. 10
- [3] EUROLLM-22B: TECHNICAL REPORT · 2602.05879v1 · 2.2 TRAINING PHASES · p. 3
- [4] ByT5: Towards a Token-Free Future with Pre-trained Byte-to-Byte Models · 2105.13626v3, also v1 · 6.4 Character Vocabulary · p. 10
- [5] Dialect-to-Standard Normalization: A Large-Scale Multilingual Evaluation · 2023.findings-emnlp.923 · 5 Methods and Tools · p. 6

*rewrite 0.2 s · retrieval 0.19 s · answer 1.6 s*

## Turn 5

**Question:** How much vitamin D should an adult take each day?

**Searched as:** How much vitamin D should an adult take each day?

**Answer (Abstention):**

The provided chunks do not contain information about how much vitamin D an adult should take each day.

**Retrieved, not cited:**

- [1] Token Assorted: Mixing Latent and Text Tokens for Improved Language Model Reasoning · 2502.03275v2 · Example Generation of Our Latent Approach · p. 19
- [2] TOKENIZATION TRADEOFFS IN STRUCTURED EHR FOUNDATION MODELS · 2603.15644v1 · 4 Discussion · pp. 21–22
- [3] TOKENIZATION TRADEOFFS IN STRUCTURED EHR FOUNDATION MODELS · 2603.15644v1 · 4 Discussion · p. 21
- [4] Towards Cross-Tokenizer Distillation: the Universal Logit Distillation Loss for LLMs · 2402.12030v1 · Does the leukocyte count correlate with the severity of injury · p. 17
- [5] MEDVOC: Vocabulary Adaptation for Fine-tuning Pre-trained Language Models on Medical Text Summarization · 2405.04163v2, also v1 · B.2 Human Evaluation · pp. 12–13

*rewrite 0.3 s · retrieval 0.12 s · answer 1.3 s*

## Turn 6

**Question:** How does SuperBPE change BPE training so that it ends up with tokens that span several words?

**Searched as:** How does SuperBPE change BPE training so that it ends up with tokens that span several words?

**Answer:**

SuperBPE employs a two-pass tokenization strategy to obtain multi-word tokens, which are called superwords [3]. This method involves an initial BPE training phase with pre-tokenization, conducted up to a vocabulary size $t < T$, where $T$ is the transition point [3]. This phase is followed by a second BPE training pass that resumes from the first but omits pre-tokenization, which enables the formation of superwords to populate the remainder of the vocabulary [3].

**References:**

- [3] Boundless Byte Pair Encoding: Breaking the Pre-tokenization Barrier. 2504.00178v2, also v1, Multi-word tokens, p. 10.

**Retrieved, not cited:**

- [1] SuperBPE: Space Travel for Language Models · 2503.13423v3, also v1 · 2.1 Background on BPE · p. 3
- [2] Explaining and Mitigating Crosslingual Tokenizer Inequities · 2510.21909v1 · K SuperBPE Training · p. 28
- [4] Faster Superword Tokenization · 2604.05192v2 · 1 Introduction · pp. 1–2
- [5] SuperBPE: Space Travel for Language Models · 2503.13423v3, also v1 · 2.2 SuperBPE tokenization · p. 3

*rewrite 0.4 s · retrieval 0.19 s · answer 3.1 s*
