# Chat transcript, 2026-10-20

Saved from the chat page (`just chat`). Each question retrieved the top 5 Chunks from dense.bge-small+collapsed, and gemma4:e2b-mlx@e98b54fe1913 on Ollama 0.40.5 answered from them.

## Turn 1

**Question:** What score does CANINE reach on Amharic named entities, a language it never saw in pre-training?

**Answer:**

CANINE is able to achieve 50 F1 on Amharic named entities even though it had never seen Amharic text during pre-training [1][2]. This is because CANINE always supports the full Unicode space [1].

**References:**

- [1] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation. 2022.tacl-1.5, 4.4 NER Results, p. 11.
- [2] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation. 2103.06874v4, 4.4 NER Results, p. 10.

**Retrieved, not cited:**

- [3] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2103.06874v4 · 6 Conclusion · p. 18
- [4] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 · 6 Conclusion · pp. 18–19
- [5] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2103.06874v1 · 6 Future Work · p. 11

*retrieval 0.05 s · answer 1.8 s*

## Turn 2

**Question:** How does it give every possible character an embedding without an enormous table?

**Searched as:** How does CANINE give every possible character an embedding without an enormous table?

**Answer:**

CANINE uses multiple hash functions applied to each codepoint and concatenates the representations from these hash values to create a single representation. This results in character embeddings of size $d$, where $d = d/K$, by looking up each hashing result in its own embedding matrix $E_k$, and then concatenating them [1]. Because the model supports all codepoints, it can learn representations for characters never seen during pre-training [1].

**References:**

- [1] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation. 2022.tacl-1.5, also 2103.06874v4 and v1, 3.1 Model, pp. 4–5.

**Retrieved, not cited:**

- [2] Why don't people use character-level machine translation? · 2110.08191v2, also v1 · CANINE. · p. 4
- [3] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v1 and v4 · 3.1 Model · p. 4
- [4] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 · 3 CANINE · p. 3
- [5] CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation · 2022.tacl-1.5, also 2103.06874v4 · 3.2.1 Autoregressive Character Loss · p. 6

*rewrite 0.3 s · retrieval 0.06 s · answer 3.6 s*

## Turn 3

**Question:** How does that compare with how ByT5 handles characters?

**Searched as:** How does the method described in the previous answer compare with how ByT5 handles characters?

**Answer (Abstention):**

The provided chunks do not contain information comparing the character handling method of CANINE with how ByT5 handles characters.

**Retrieved, not cited:**

- [1] ByT5: Towards a token-free future with pre-trained byte-to-byte models · 2105.13626v1 · A Per-Language Results · p. 16
- [2] ByT5: Towards a token-free future with pre-trained byte-to-byte models · 2105.13626v1 · A Per-Language Results · p. 16
- [3] ByT5: Towards a token-free future with pre-trained byte-to-byte models · 2105.13626v1 · A Per-Language Results · p. 16
- [4] ByT5: Towards a token-free future with pre-trained byte-to-byte models · 2105.13626v1 · A Per-Language Results · p. 16
- [5] Dialect-to-Standard Normalization: A Large-Scale Multilingual Evaluation · 2023.findings-emnlp.923 · 5 Methods and Tools · p. 6

*rewrite 0.5 s · retrieval 0.07 s · answer 2.4 s*

## Turn 4

**Question:** Which learning rate schedule did ByT5 use for pre-training?

**Searched as:** What learning rate schedule did ByT5 use for pre-training?

**Answer (Abstention):**

The provided chunks do not contain information about the learning rate schedule used by ByT5 for pre-training.

**Retrieved, not cited:**

- [1] EUROLLM-9B: TECHNICAL REPORT · 2506.04079v2, also v1 · 2.3 PRE-TRAINING PHASES · p. 4
- [2] EUROLLM-22B: TECHNICAL REPORT · 2602.05879v1 · 2.2 TRAINING PHASES · p. 3
- [3] ByT5: Towards a Token-Free Future with Pre-trained Byte-to-Byte Models · 2022.tacl-1.17, also 2105.13626v1 · 6.4 Character Vocabulary · p. 10
- [4] Dialect-to-Standard Normalization: A Large-Scale Multilingual Evaluation · 2023.findings-emnlp.923 · 5 Methods and Tools · p. 6
- [5] ByT5: Towards a Token-Free Future with Pre-trained Byte-to-Byte Models · 2105.13626v3, also v1 · 6.4 Character Vocabulary · p. 10

*rewrite 0.2 s · retrieval 0.06 s · answer 1.7 s*

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

*rewrite 0.4 s · retrieval 0.06 s · answer 1.4 s*

## Turn 6

**Question:** How does SuperBPE change BPE training so that it ends up with tokens that span several words?

**Searched as:** How does SuperBPE change BPE training so that it ends up with tokens that span several words?

**Answer:**

SuperBPE employs a two-pass tokenization strategy to obtain multi-word tokens, also called superwords [3][4]. The first phase involves an initial BPE training phase with pre-tokenization up to a vocabulary size $t < T$, where $T$ is the transition point [3][4]. This phase is followed by a second BPE training pass that resumes from the first but omits pre-tokenization, which enables the formation of superwords to populate the remainder of the vocabulary [3][4].

**References:**

- [3] Boundless Byte Pair Encoding: Breaking the Pre-tokenization Barrier. 2504.00178v2, Multi-word tokens, p. 10.
- [4] Boundless Byte Pair Encoding: Breaking the Pre-tokenization Barrier. 2504.00178v1, 5 Related work, p. 9.

**Retrieved, not cited:**

- [1] SuperBPE: Space Travel for Language Models · 2503.13423v3, also v1 · 2.1 Background on BPE · p. 3
- [2] Explaining and Mitigating Crosslingual Tokenizer Inequities · 2510.21909v1 · K SuperBPE Training · p. 28
- [5] Faster Superword Tokenization · 2604.05192v2, also v1 · 1 Introduction · pp. 1–2

*rewrite 0.4 s · retrieval 0.06 s · answer 3.0 s*
