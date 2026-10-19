# Absence evidence for the unanswerable questions

Written by `hack/absence_search.py` (ADR 0045) over 141512 Chunks from 2690 files.
For each unanswerable question, the top 10 Chunks from each retriever for the question and for each probe query.
A question stays unanswerable only if none of these Chunks answers it; the developer confirms each one.

## bpe-english-french

> What BLEU score did Sennrich et al.'s subword NMT paper report for English→French translation?

Drafter's reading: The paper's own results are English→German and English→Russian only. Other papers' English–French BLEU is for their own systems, not Sennrich et al.'s.

### bm25: What BLEU score did Sennrich et al.'s subword NMT paper report for English→French translation?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 33.729 | 1508.07909v5 | 4 Evaluation › 4.2 Translation experiments | For English→German, we observe the best BLEU score of 25.3 with C2-50k, but the best CHRF3 score of 54.1 with BPE-J90k. For comparison to the (to our knowledge) |
| 2 | 33.729 | P16-1162 | 4 Evaluation › 4.2 Translation experiments | For English→German, we observe the best BLEU score of 25.3 with C2-50k, but the best CHRF3 score of 54.1 with BPE-J90k. For comparison to the (to our knowledge) |
| 3 | 30.498 | 2020.wmt-1.9 | 3 Previous Work | To the best of our knowledge, there have only been a handful of NMT systems trained on EN→TA. For the Indic languages multilingual tasks of WAT-2018, Sen et al. |
| 4 | 30.146 | 2020.wmt-1.9 | 5 Methods › 5.4 Word Dropout | First introduced in Gal and Ghahramani (2016), the word dropout technique was modified by Sennrich et al. (2016a) to randomly drop tokens in-stead of types duri |
| 5 | 29.648 | 2402.00786v5 | 4 Evaluation Benchmarks › 4.3 Other Tasks | MT-Bench French. Mt-Bench Frenchfoot_13 is a translated and adapted version of MT-Bench in French with all questions having undergone rigorous human review and  |
| 6 | 28.214 | 2402.00786v1 | 4 Evaluation Benchmarks › 4.2 French › 4.2.2 FrenchBench Multiple Choice › WMT14. | Translation capabilities are evaluated through the test set of the 2014 WMT French-English and English-French tasks (Alves et al., 2023). We measure performance |
| 7 | 28.090 | 2020.wmt-1.9 | 5 Methods › 5.2 Back-translation | In order to artificially increase the training data, we employ back-translation (BT) (Sennrich et al., 2016b). We consider two variations of this approach: Tagg |
| 8 | 28.003 | 2021.wat-1.21 | 2 Previous Work › 2.1 Translation Systems › Neural Machine Translation | On the neural machine translation (NMT) side, there have been a handful of NMT systems trained on English→Tamil. On the aforementioned Indic languages multiling |
| 9 | 27.545 | 2022.aacl-short.12 | 3 Experimental Settings › NMT Settings | We used the transformer base architecture (Vaswani et al., 2017) and the fairseq framework (Ott et al., 2019). We trained the model until no BLEU score improvem |
| 10 | 27.538 | 1511.04586v1 | 3 EXPERIMENTS › 3.2 RESULTS | For the BTEC dataset, the word-based neural model achieves a BLEU score of 15.38 in the French to English translation direction, while the character-based model |

### dense: What BLEU score did Sennrich et al.'s subword NMT paper report for English→French translation?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.768 | 2023.icon-1.19 | 3 Experimentation › 3.4 Model Evaluation | The performance of the models was tested using the 1000 parallel test data from the LRILT task, WMT 23. The performance evaluation is done using the popular met |
| 2 | 0.749 | W7218093374 | Abstract | In NMT, the Bilingual Evaluation Understudy (BLEU) scores and other parameters have shown that the efficiency in translating the source sentences is higher for  |
| 3 | 0.739 | 2505.16868v1 | 5. Results and Discussion › 5.2 Analysis of Result | Bilingual Evaluation Understudy (BLEU) is one of the famous measures for MT evaluation, and it evaluates the overlap of n-grams (word sequences) among the machi |
| 4 | 0.739 | 2020.wmt-1.92 | 4 Experiments and Results › 4.2 BERT-fused NMT | R2 showed improvements in scores as fine tuned on in-domain corpus (Medline abstracts and titles). It gave highest BLEU score points of 38.4 for medline 19 test |
| 5 | 0.738 | 2505.16868v1 | 5. Results and Discussion › 5.2 Analysis of Result | Using BPE tokenization, MNMT's BLEU score falls between 5.14 and 32.19 whereas the TER score falls between 56.84 and 102.9. The CHRF ranges from 35.81 to 62.35  |
| 6 | 0.736 | 1709.02184v1 | 5 Evaluation › 5.1 WMT15 Dataset Evaluation | We translate the WMT15 evaluation set to evaluate the generic performance of the trained SMT and NMT models, considering the translation generation from English |
| 7 | 0.733 | 1612.04629v1 | 3 Evaluation › 3.1 Data and Methods | Table 3: Case-sensitive BLEU scores (EN-DE) on WMT newstest. We report scores with detokenized NIST BLEU (mteval-v13a.pl), and in brackets, tokenized BLEU with  |
| 8 | 0.732 | 2305.12371v1 | 6 Results and Analysis | We compare the proposed approach with the Mosesbased SMT and the Transformer-based NMT model [3], where the latter is used as the baseline for NMT. We use six e |
| 9 | 0.731 | 1704.04520v1 | 5 Evaluation › 5.4 Evaluation Results | In this work, we calculated automatic evaluation scores for the translation results using a popular metrics called BLEU (Papineni et al., 2002). As shown in Tab |
| 10 | 0.731 | W18-1207 | 6 Results and discussion | Figure 1: Translation accuracies of NMT systems for various translation units (BLEU scores reported). |

### bm25: Sennrich BPE subword units English French BLEU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 21.405 | 10.1109/ACCESS.2019.2941161 | C. UNK PROBLEM | Different techniques have been presented to mitigate the UNK word problem. Luong et al. [17] handled the OOV problem in a post-processing step by translating ea |
| 2 | 19.907 | 2005.06606v1 | Abstract | This paper introduces Dynamic Programming Encoding (DPE), a new segmentation algorithm for tokenizing sentences into subword units. We view the subword segmenta |
| 3 | 19.907 | 2005.06606v2 | Abstract | This paper introduces Dynamic Programming Encoding (DPE), a new segmentation algorithm for tokenizing sentences into subword units. We view the subword segmenta |
| 4 | 19.907 | 2020.acl-main.275 | Abstract | This paper introduces Dynamic Programming Encoding (DPE), a new segmentation algorithm for tokenizing sentences into subword units. We view the subword segmenta |
| 5 | 19.798 | 2024.emnlp-main.600 | C Full Experiments | 0.4194 40.80 64.50 86.38 Unigram (α=1) 0.3801 40.59 64.43 86.27 Unigram (α=0.3) 0.3773 40.71 64.53 86.36 (c) French→English (source only dropout) Tokenizer Effi |
| 6 | 19.798 | 2408.11443v1 | D Full Experiments | 0.4194 40.80 64.50 86.38 Unigram (α=1) 0.3801 40.59 64.43 86.27 Unigram (α=0.3) 0.3773 40.71 64.53 86.36 (c) French→English (source only dropout) Tokenizer Effi |
| 7 | 19.704 | 2005.06606v1 | 1 Introduction | We present a new family of mixed charactersubword transformers, for which simple dynamic programming algorithms exist for exact marginalization and MAP inferenc |
| 8 | 19.704 | 2005.06606v2 | 1 Introduction | We present a new family of mixed charactersubword transformers, for which simple dynamic programming algorithms exist for exact marginalization and MAP inferenc |
| 9 | 19.704 | 2020.acl-main.275 | 1 Introduction | We present a new family of mixed charactersubword transformers, for which simple dynamic programming algorithms exist for exact marginalization and MAP inferenc |
| 10 | 19.650 | 1905.10453v2 | 3 Analysis Setup › 3.1 Dataset | Our experiments are conducted with the all the data from IWSLT 2016 shared task, covering translation of English (en) from and into Arabic (ar), Czech (cs), Fre |

### dense: Sennrich BPE subword units English French BLEU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.774 | 1610.06510v3 | 5 Results and Analysis › 5.1 Comparison of BPE with other units | Table 3: Translation accuracies for various translation units (BLEU and LeBLEU scores reported). The reported scores are:-W: word-level, M: morpheme, O: orthogr |
| 2 | 0.774 | W17-4102 | 5 Results and Analysis › 5.1 Comparison of BPE with other units | Table 3: Translation accuracies for various translation units (BLEU and LeBLEU scores reported). The reported scores are:-W: word-level, M: morpheme, O: orthogr |
| 3 | 0.759 | 2022.aacl-short.12 | 4 Results and Analysis › Subword Frequency Distribution | Table 6 (Subword Frequency Distribution): High-resource MT BLEU score results. Statistical significance p < 0.001 is indicated by * against BPE and by • against |
| 4 | 0.759 | 1610.06510v3 | 5 Results and Analysis › 5.6 Joint bilingual learning of BPE units | Table 6 (5.6 Joint bilingual learning of BPE units): Translation accuracies for Joint BPE models trained with different number of merge operations (BLEU). The B |
| 5 | 0.759 | W17-4102 | 5 Results and Analysis › 5.6 Joint bilingual learning of BPE units | Table 6 (5.6 Joint bilingual learning of BPE units): Translation accuracies for Joint BPE models trained with different number of merge operations (BLEU). The B |
| 6 | 0.759 | C18-1052 | 2 Neural Machine Translation with Subword Units › 2.2 Subword Units Based on Byte-Pair Encoding | Several approaches have been proposed to obtain a set of subword units based on statistics, e.g., (Schuster and Nakajima, 2012;Sennrich et al., 2016). The schem |
| 7 | 0.755 | 1702.07203v2 | 2 Proposed Solution | Both OS and BPE units are variable length units which provide appropriate context for translation between related languages. Since their vocabularies are much s |
| 8 | 0.749 | 1610.06510v3 | 4 Experimental Setup › 4.4 Evaluation | The primary evaluation metric is word-level BLEU (Papineni et al., 2002). We also report LeBLEU (Virpioja and Grönroos, 2015) scores as an alternative evaluatio |
| 9 | 0.749 | W17-4102 | 4 Experimental Setup › 4.4 Evaluation | The primary evaluation metric is word-level BLEU (Papineni et al., 2002). We also report LeBLEU (Virpioja and Grönroos, 2015) scores as an alternative evaluatio |
| 10 | 0.748 | 2022.aacl-short.12 | 3 Experimental Settings › Dataset Train Valid Test | Table 3 (Dataset Train Valid Test): Low-resource Asian languages→English MT BLEU score results. BERTSeg-Regularization consistently improves over all baselines. |

### bm25: English→French translation results subword units newstest

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 22.631 | 1808.09943v1 | 4 Experimental Design › 4.1 Corpora | We adopt the corpora used by Lee et al (2017), with the exception of WMT15 Russian-English. 4To measure performance on an "easy" language pair, and to calibrate |
| 2 | 22.631 | D18-1461 | 4 Experimental Design › 4.1 Corpora | We adopt the corpora used by Lee et al (2017), with the exception of WMT15 Russian-English. 4To measure performance on an "easy" language pair, and to calibrate |
| 3 | 20.861 | 1808.07364v1 | 3 Experiments › 3.2 Results › Subwords only models. | Table 3 shows the performance of models that rely solely on subword units. When used individually, different subword units yield the best results for different  |
| 4 | 20.602 | 1808.07364v3 | 3. Experiments › 3.2. Results › Subwords only models. | Table 3 shows the performance of models that rely solely on subword units. When used individually, different subword units yield the best results for different  |
| 5 | 19.602 | 1603.06147v1 | 5 Experiment Settings › Corpora and Preprocessing | We use all available parallel corpora for four language pairs from WMT'15: En-Cs, En-De, En-Ru and En-Fi. They consist of 12.1M, 4.5M, 2.3M and 2M sentence pair |
| 6 | 19.241 | 2005.11239v1 | 5 Experimental Settings › 5.1 Datasets and Preprocessing | We applied the NMT models to the four language pairs from WMT'15: DE-EN, CS-EN, FI-EN and RU-EN. We obtained the datasets 1 already preprocessed by Lee et al. ( |
| 7 | 18.576 | 1603.06147v4 | 5 Experiment Settings › Corpora and Preprocessing | We use all available parallel corpora for four language pairs from WMT'15: En-Cs, En-De, En-Ru and En-Fi. They consist of 12.1M, 4.5M, 2.3M and 2M sentence pair |
| 8 | 18.418 | P16-1160 | 5 Experiment Settings › Corpora and Preprocessing | We use all available parallel corpora for four language pairs from WMT'15: En-Cs, En-De, En-Ru and En-Fi. They consist of 12.1M, 4.5M, 2.3M and 2M sentence pair |
| 9 | 17.751 | 2016.amta-researchers.11 | 4 Evaluation › 4.3 Results and analysis | For the English-Finnish models the auxiliary data helped only for the bigger dataset because the smaller dataset overfitted for Finnish before it could use any  |
| 10 | 17.642 | 1610.03017v1 | 5 Experiment Settings › 5.2 Datasets and Preprocessing | We use all available parallel data on the four language pairs from WMT'15: DE-EN, CS-EN, FI-EN and RU-EN. For the bpe2char baselines, we only use sentence pairs |

### dense: English→French translation results subword units newstest

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.785 | 1902.01313v1 | 5 Experiments and results | We use newstest2014 as our test set for French-English, and both newstest2014 and new-stest2016 (from WMT 2016 10 ) for German-8 http://www.statmt.org/moses/ 9  |
| 2 | 0.784 | 1508.07909v5 | 4 Evaluation | We aim to answer the following empirical questions: • Can we improve the translation of rare and unseen words in neural machine translation by representing them |
| 3 | 0.784 | P16-1162 | 4 Evaluation | We aim to answer the following empirical questions: • Can we improve the translation of rare and unseen words in neural machine translation by representing them |
| 4 | 0.779 | C18-1052 | 4 Experiments › 4.1 Setup | In this paper, we focused on from/to English (EN) to/from French (FR), German (DE) translations. We carried out our experiments on the IWSLT evaluation campaign |
| 5 | 0.778 | 1907.05854v1 | 4 German → English › 4.4 Data Filtering | The CommonCrawl and ParaCrawl datasets consist of parallel data automatically extracted from web pages from systematic internet crawls. These datasets contain c |
| 6 | 0.778 | C16-1301 | 5 Experimental Setup › 5.1 Dataset & Preprocessing | Our models were trained on the data provided by the 2014 Workshop on Machine Translation (WMT). Specifically, we used the Europarl v7, Common Crawl, and News Co |
| 7 | 0.775 | 1807.09639v1 | 4 Experiments › 4.1 Setup | Our experiments will be performed on two typical language pairs, German to English and Chinese to English. The translation quality is evaluated by the 4gram cas |
| 8 | 0.771 | 1907.05854v1 | 2.2 Creation of synthetic parallel data › 2.2.2 EN and GU backtranslation › Degree of subword segmentation | Figure 1: The effect of the number of subword operations on BLEU score during training for EN→GU (calculated on the newsdev2019 dataset). |
| 9 | 0.771 | W19-5304 | 2.2 Creation of synthetic parallel data › 2.2.2 EN and GU backtranslation › Degree of subword segmentation | Figure 1: The effect of the number of subword operations on BLEU score during training for EN→GU (calculated on the newsdev2019 dataset). |
| 10 | 0.770 | 1508.07909v1 | 4 Evaluation › 4.2 Translation experiments | 7 We attempted to reproduce the results by Jean et al. (2015a), but our baseline is slightly worse 8 ; We speculate that the difference is caused by differences |

## blt-70b-mmlu

> What does the Byte Latent Transformer score on MMLU when it is scaled to 70B parameters?

Drafter's reading: The Byte Latent Transformer is trained up to 8B parameters; no Chunk gives a 70B BLT.

### bm25: What does the Byte Latent Transformer score on MMLU when it is scaled to 70B parameters?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 22.818 | 2412.09871v1 | 6 Byte Modeling Improves Robustness › 6.2 Training BLT from Llama 3 | We explore a workflow where BLT models can leverage existing pre-trained tokenizer-based models for better and faster training convergence, acheived by initiali |
| 2 | 22.553 | 2410.01930v1 | 5. Don't flatten, tokenize! › 5.1. Additional analyses › More agents | In the DQN setting, SoftMoE-1 does not appear to offer significant improvements over the baseline, potentially due to the limited gains observed 2.8 3.0 3.2 3.4 |
| 3 | 22.429 | 2410.01930v2 | 7 RELATED WORKS | 2.8 3.0 3.2 3.4 SoftMoE-4 SoftMoE-1 (scaled x4) Baseline (scaled x4) Median 3.00 3.25 3.50 IQM 5.4 6.0 6.6 Mean 0.060 0.075 0.090 0.105 Optimality Gap Human Nor |
| 4 | 21.467 | 2305.07185v1 | 3. Efficiency Analysis › 3.1. Training Efficiency › Attention | Feedforward Layers However, attention is not the main cost in large transformers. Instead of increasing the sequence length, transformers are more commonly scal |
| 5 | 21.467 | 2305.07185v2 | 3. Efficiency Analysis › 3.1. Training Efficiency › Attention | Feedforward Layers However, attention is not the main cost in large transformers. Instead of increasing the sequence length, transformers are more commonly scal |
| 6 | 21.001 | 2412.09871v1 | 2 Patching: From Individual Bytes to Groups of Bytes › 2.4 The Byte-Pair Encoding (BPE) Tokenizer and Incremental Patching | When generating, BLT needs to decide whether the current step in the byte sequence is at a patch boundary or not as this determines whether more compute is invo |
| 7 | 20.611 | 2609.00463v1 | 4 Results › Scaling Up | Scaling trends show overall improvement, but architecture still matters. For example, Bot 18 , which most closely resembles Bolmo and Byte Latent Transformer, i |
| 8 | 20.596 | 2412.09871v1 | Abstract | We introduce the Byte Latent Transformer (BLT), a new byte-level LLM architecture that, for the first time, matches tokenization-based LLM performance at scale  |
| 9 | 20.435 | 2405.13929v1 | 4 Experiments › 4.1 Experimental Setup | Benchmarks. The evaluation was performed on MMLU (Hendrycks et al., 2021), Ru-MMLU 5 , CheGeKa, Russian SuperGLUE (Shavrina et al., 2020), and MERA (Fenogenova  |
| 10 | 20.357 | 2412.09871v1 | 5 Scaling Trends › 5.3 Patches Scale Better Than Tokens | The crossover point where BLT improves over token-based models has shifted slightly closer to the computeoptimal point when moving to the larger flop class mode |

### dense: What does the Byte Latent Transformer score on MMLU when it is scaled to 70B parameters?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.766 | 2412.09871v1 | 9 Limitations and Future Work | In this work, for the purposes of architectural choices, we train models for the optimal number of steps as determined for Llama 3 (Dubey et al., 2024). However |
| 2 | 0.762 | 2501.10322v1 | B EXPERIMENT DETAILS B.1 TRAINING SETTINGS › B.4 EVALUATION TASKS | We use a set of established downstream evaluation tasks, implemented in evaluation suites like the Eleuther AI eval harness (Gao et al., 2024). In the following |
| 3 | 0.762 | 2501.10322v2 | B EXPERIMENT DETAILS B.1 TRAINING SETTINGS › B.4 EVALUATION TASKS | We use a set of established downstream evaluation tasks, implemented in evaluation suites like the Eleuther AI eval harness (Gao et al., 2024). In the following |
| 4 | 0.761 | 2412.09871v1 | Local Model Hyperparamaters | ), which can maintain a fixed-size memory state over a very large context length,Wang et al. (2024) train a byte-level Mamba architecture also without using pat |
| 5 | 0.761 | 2502.14553v1 | 2. Related work | The MBLM builds upon the design principles of MegaByte (Yu et al., 2023), a causal byte language model featuring a hierarchical architecture of two Transformer  |
| 6 | 0.757 | 2412.09871v1 | 1 Introduction | We introduce the Byte Latent Transformer (BLT), a tokenizer-free architecture that learns from raw byte data and, for the first time, matches the performance of |
| 7 | 0.756 | 2412.09871v1 | 4 Experimental Setup › 4.7 Transformer Architecture Hyperparameters | For all the transformer blocks in BLT, i.e. both local and global models, we largely follow the architecture of Llama 3 (Dubey et al., 2024); we use the SwiGLU  |
| 8 | 0.754 | 2412.09871v1 | 6 Byte Modeling Improves Robustness › 6.2 Training BLT from Llama 3 | We explore a workflow where BLT models can leverage existing pre-trained tokenizer-based models for better and faster training convergence, acheived by initiali |
| 9 | 0.753 | 2501.16975v1 | 4. Experiments Implementation. › 4.2. Ablation Study › Vocabulary Size Scaling. | Table 2 (Vocabulary Size Scaling.): Ablation study on different input vocabulary designs. The downstream tasks follow the eval settings in OLMoE, where MMLU-V s |
| 10 | 0.753 | 2412.09871v1 | 7 Ablations and Discussion › Entropy Model Hyper-parameters | Our work draws inspiration and is most closely related to MegaByte (Yu et al., 2023), which is a decoder only causal LLM that uses a fixed static patching and c |

### bm25: Byte Latent Transformer 70B MMLU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 17.753 | 2602.01007v1 | 6. Ablation Study 6.1. Necessity of Embedding Alignment › 6.3. Impact of Encoder Architecture › Step 1 (Embedding Alignment) protocol on Qwen-3 4B. | Performance Collapse of Attention. Table 5 shows significant differences in alignment quality. The Mamba2 encoder achieves high fidelity (70.2 MMLU), while the  |
| 2 | 16.402 | 2605.08044v1 | B All 1B Model Results | Table 2 (B All 1B Model Results): Performance comparison of BLT and BLT-D (block sizes 4, 8, 16) at 1B parameters across five benchmarks. Benchmark \| BLT 1B BLT |
| 3 | 16.207 | 2602.01007v2 | 5 Ablation Study › 5.3 Impact of Encoder Architecture | A pivotal design choice is using Mamba2 as the encoder. We ablate by replacing the Mamba2 block with a standard transformer of equivalent size, training both un |
| 4 | 16.160 | 2412.09871v1 | E Entropy Patching Example from MMLU | We illustrate how a few-shot example from a downstream task i.e. MMLU (Hendrycks et al., 2020), is patched using an entropy-model trained for use with BLT model |
| 5 | 15.466 | 2602.05879v1 | C REGEX VERSUS LLM-AS-A-JUDGE › C.1 SETUP › Model Correlation Accuracy | Table 28 (Model Correlation Accuracy): Comparison of regex-based and LLM-based evaluations in terms of correlation with human judgments and accuracy. \| Llama-3. |
| 6 | 15.374 | 2603.15953v1 | 7 Model Performance › 7.3 Evaluation Results › 7.3.4 Llama-3.1-70B-TFree-HAT | Table 24 (7.3.4 Llama-3.1-70B-TFree-HAT): Knowledge: SFT evaluation metrics across tasks and models. Task \| Metric \| HATified-SFT Llama-Instruct MMLU 5-shot \| n |
| 7 | 15.129 | 2412.09871v1 | 1 Introduction | Figure2BLT comprises three modules, a lightweight Local Encoder that encodes input bytes into patch representations, a computationally expensive Latent Transfor |
| 8 | 14.932 | 2412.09871v1 | 6 Byte Modeling Improves Robustness › 6.2 Training BLT from Llama 3 | This setup can also be viewed as transforming tokenizer-based models into tokenizer-free ones, effectively converting a pre-trained LLaMA 3.1 model into a BLT m |
| 9 | 14.848 | 2605.08044v1 | 2 Background and Related Work › 2.1 Byte Latent Transformer › 2.1.1 Architecture overview | BLT's architecture creates latent token representations that mix byte-and patch-level information. It consists of three components: a local encoder E, a global  |
| 10 | 14.747 | 2605.08044v1 | 2 Background and Related Work › 2.1 Byte Latent Transformer › 2.1.2 Local decoder | The local decoder D autoregressively decodes the final latent token representations o into a sequence of output bytes y = [y 1 ; y 2 ; . . . ; y N ] ∈ V N using |

### dense: Byte Latent Transformer 70B MMLU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.816 | 2605.08044v1 | 2 Background and Related Work › 2.1 Byte Latent Transformer › 2.1.1 Architecture overview | BLT's architecture creates latent token representations that mix byte-and patch-level information. It consists of three components: a local encoder E, a global  |
| 2 | 0.811 | 2412.09871v1 | 1 Introduction | We introduce the Byte Latent Transformer (BLT), a tokenizer-free architecture that learns from raw byte data and, for the first time, matches the performance of |
| 3 | 0.801 | 2605.08044v1 | 2 Background and Related Work › 2.1 Byte Latent Transformer | BLT is a byte-level architecture that operates directly on raw byte sequences while matching the performance of subword tokenization-based language models at sc |
| 4 | 0.798 | 2412.09871v1 | 6 Byte Modeling Improves Robustness › 6.2 Training BLT from Llama 3 | We explore a workflow where BLT models can leverage existing pre-trained tokenizer-based models for better and faster training convergence, acheived by initiali |
| 5 | 0.797 | 2605.08044v1 | 2 Background and Related Work › 2.1 Byte Latent Transformer › 2.1.2 Local decoder | The local decoder D autoregressively decodes the final latent token representations o into a sequence of output bytes y = [y 1 ; y 2 ; . . . ; y N ] ∈ V N using |
| 6 | 0.796 | 2603.27859v1 | 3 Background › 3.2 Byte Latent Transformer | Pagnoni et al. ( 2025) introduce the Byte Latent Transformer (BLT), which replaces fixedvocabulary tokenization with a dynamic, learnable byte-to-patch mapping. |
| 7 | 0.794 | 2412.09871v1 | Abstract | We introduce the Byte Latent Transformer (BLT), a new byte-level LLM architecture that, for the first time, matches tokenization-based LLM performance at scale  |
| 8 | 0.793 | 2605.08044v1 | 1 Introduction | Recent architectural innovations have substantially narrowed this efficiency gap. Rather than running a full Transformer over every byte, modern byte-level mode |
| 9 | 0.792 | 2412.09871v1 | 7 Ablations and Discussion › Entropy Model Hyper-parameters | Our work draws inspiration and is most closely related to MegaByte (Yu et al., 2023), which is a decoder only causal LLM that uses a fixed static patching and c |
| 10 | 0.787 | 2602.01007v2 | 6 Conclusion | Table 5 (6 Conclusion): Impact of Encoder Architecture. We compare the performance of Mamba2 against a standard Transformer encoder on Qwen-3 4B after Step 1 (E |

### bm25: BLT byte-level model 70B parameters results

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 21.360 | 2512.15586v1 | 5 Main Results › Bolmo 7B Results. | Table 1 (Bolmo 7B Results.): Pagnoni et al. (2025)o 1B (trained off of OLMo2 1B; OLMo et al., 2024) with existing byte-level models, including H-Net (for which  |
| 2 | 20.866 | 2605.08044v1 | B All 1B Model Results | Table 2 (B All 1B Model Results): Performance comparison of BLT and BLT-D (block sizes 4, 8, 16) at 1B parameters across five benchmarks. Benchmark \| BLT 1B BLT |
| 3 | 19.879 | 2412.09871v1 | Abstract | We introduce the Byte Latent Transformer (BLT), a new byte-level LLM architecture that, for the first time, matches tokenization-based LLM performance at scale  |
| 4 | 19.529 | 2412.09871v1 | 5 Scaling Trends › 5.3 Patches Scale Better Than Tokens | The crossover point where BLT improves over token-based models has shifted slightly closer to the computeoptimal point when moving to the larger flop class mode |
| 5 | 19.091 | 2605.08044v1 | 4 Pre-training and Generation Experiments › 4.1 Models, Pre-training Data, and Optimization | We pre-train four model types: one BLT and three BLT-D variants with block sizes of 4, 8, and 16, referred to as BLT-D-4, BLT-D-8, and BLT-D-16, respectively. F |
| 6 | 18.941 | 2412.09871v1 | 7 Ablations and Discussion | In this section, we discuss ablations justifying architectural choices for BLT and the patching scheme and hyper-parameters for the BLT 8B parameter model train |
| 7 | 18.921 | 2605.08044v1 | 7 Conclusion | In this paper, we introduced BLT Diffusion (BLT-D), a byte-level language model that combines BLT's hierarchical latent tokenization with a block-wise diffusion |
| 8 | 18.678 | 2610.11790v1 | Abstract | Byte-level language models such as the Byte Latent Transformer (BLT) group bytes into patches and run their large global model once per patch. BLT starts a patc |
| 9 | 18.660 | 2412.09871v1 | 5 Scaling Trends › 5.1 Parameter Matched Compute Optimal Scaling Trends | Using the Llama 2 dataset, we train various compute-optimal bpe and BLT models across four different sizes, ranging from 1B to 8B parameters. We then plot the t |
| 10 | 18.471 | 2605.08044v1 | Abstract | Recent byte-level language models (LMs) match the performance of token-level models without relying on subword vocabularies, yet their utility is limited by slo |

### dense: BLT byte-level model 70B parameters results

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.857 | 2605.08044v1 | B All 1B Model Results | BPEFigure 9: Figure9Generation task results of 1B-parameter variants of BLT, BLT-D-4, BLT-D-8, and BLT-D-16. Higher is better for task performance; lower is bet |
| 2 | 0.847 | 2605.08044v1 | 4 Pre-training and Generation Experiments › 4.3 Generation Task Results | Figure6Generation task results of 3B-parameter variants of BLT, BLT-D-4, BLT-D-8, and BLT-D-16. Higher is better for task performance; lower is better for NFEs  |
| 3 | 0.833 | 2605.08044v1 | B All 1B Model Results | Table 3 (B All 1B Model Results): Full French-to-English translation results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \|  |
| 4 | 0.832 | 2605.08044v1 | C All 3B Model Results | Table 7 (C All 3B Model Results): Full French-to-English translation results for 3B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \|  |
| 5 | 0.831 | 2605.08044v1 | B All 1B Model Results | Table 4 (B All 1B Model Results): Full German-to-English translation results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \|  |
| 6 | 0.831 | 2605.08044v1 | B All 1B Model Results | Table 3 (B All 1B Model Results): Full French-to-English translation results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \|  |
| 7 | 0.829 | 2605.08044v1 | B All 1B Model Results | Table 6 (B All 1B Model Results): Full MBPP task results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \| Memory \| \| \| Diffusi |
| 8 | 0.829 | 2412.09871v1 | 4 Experimental Setup › 4.8 BLT-Specific Hyperparameters | To study the effectiveness of BLT models, we conduct experiments along two directions, scaling trends, and downstream task evaluations, and we consider models a |
| 9 | 0.827 | 2605.08044v1 | B All 1B Model Results | Table 4 (B All 1B Model Results): Full German-to-English translation results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \|  |
| 10 | 0.827 | 2605.08044v1 | B All 1B Model Results | Table 6 (B All 1B Model Results): Full MBPP task results for 1B-parameter models across various generation settings. \| \| \| \| \| \| \| Memory \| Memory \| BLT-DV (dif |

## blt-8b-gpu-hours

> How many GPU-hours did it take to pre-train the 8B-parameter Byte Latent Transformer?

Drafter's reading: The BLT paper compares models by training FLOPs and names wall-clock time as a limitation, without giving hours. Papers that report GPU-hours for a BLT train their own small ones, not the 8B model.

### bm25: How many GPU-hours did it take to pre-train the 8B-parameter Byte Latent Transformer?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 23.132 | 2412.09871v1 | 9 Limitations and Future Work | In this work, for the purposes of architectural choices, we train models for the optimal number of steps as determined for Llama 3 (Dubey et al., 2024). However |
| 2 | 23.041 | 2023.acl-long.402 | C Did you run computational experiments? | 3.2 C1. Did you report the number of parameters in the models used, the total computational budget (e.g., GPU hours), and computing infrastructure used? |
| 3 | 22.657 | 2412.09871v1 | 7 Ablations and Discussion | In this section, we discuss ablations justifying architectural choices for BLT and the patching scheme and hyper-parameters for the BLT 8B parameter model train |
| 4 | 22.348 | 2412.09871v1 | 5 Scaling Trends › 5.1 Parameter Matched Compute Optimal Scaling Trends | Using the Llama 2 dataset, we train various compute-optimal bpe and BLT models across four different sizes, ranging from 1B to 8B parameters. We then plot the t |
| 5 | 22.070 | 2203.09963v1 | 4 Methods › 4.3 Training Details | To train the models, we used a GeForce RTX 2080 Ti GPU. Following the best practices with the T5 family of models [15,18,30,31], we used the total batch size (n |
| 6 | 21.964 | 2305.07185v1 | 4. Experimental setup › 4.4. Inference Methods | Table 4 (4.4. Inference Methods): Bits per byte (bpb) on ImageNet 64×64. MEGABYTE matches the current state-of-the-art while only using half the amount of GPU h |
| 7 | 21.964 | 2305.07185v2 | 4. Experimental setup › 4.4. Inference Methods | Table 4 (4.4. Inference Methods): Bits per byte (bpb) on ImageNet 64×64. MEGABYTE matches the current state-of-the-art while only using half the amount of GPU h |
| 8 | 21.751 | 2412.09871v1 | Local Model Hyperparamaters | ), which can maintain a fixed-size memory state over a very large context length,Wang et al. (2024) train a byte-level Mamba architecture also without using pat |
| 9 | 21.684 | 2412.09871v1 | 7 Ablations and Discussion › Entropy Model Hyper-parameters | Character-Level Transformers: The development of transformer models using attention (Vaswani et al., 2017) together with subword tokenization (Sennrich et al.,  |
| 10 | 21.504 | 2023.acl-long.200 | C Did you run computational experiments? | In section 4. C1. Did you report the number of parameters in the models used, the total computational budget (e.g., GPU hours), and computing infrastructure use |

### dense: How many GPU-hours did it take to pre-train the 8B-parameter Byte Latent Transformer?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.779 | 2402.18376v1 | 7 Conclusion › Ethics Statement | We have used the commonly used public dataset The Pile, which has not undergone a formal ethics review (Biderman et al., 2022). Our models may include biases fr |
| 2 | 0.779 | 2402.18376v2 | 7 Conclusion › Ethics Statement | We have used the commonly used public dataset The Pile, which has not undergone a formal ethics review (Biderman et al., 2022). Our models may include biases fr |
| 3 | 0.778 | 2610.01984v1 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 4 | 0.775 | 2610.01984v2 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 5 | 0.774 | 2023.acl-long.353 | 5 Results › Time and Space Complexity | To capture the concrete gains in efficiency of models with higher SFs, we have measured the memory consumption and training time of our PyTorch implementation o |
| 6 | 0.774 | 2211.09761v2 | 5 Results › Time and Space Complexity | To capture the concrete gains in efficiency of models with higher SFs, we have measured the memory consumption and training time of our PyTorch implementation o |
| 7 | 0.774 | 2211.09761v1 | B Shortening benefits | We quantify the reduction in GPU memory and training time that results from different shortening factors (SFs) in Figure 5. We measure these metrics on an NVIDI |
| 8 | 0.772 | 2507.22543v1 | D Experimental Details | Computational Resources. All experiments were conducted using a combination of 8 NVIDIA 2080Ti GPUs and 4 NVIDIA A10 GPUs. In total, our experiments consumed ap |
| 9 | 0.771 | 2610.15373v1 | G Long-context checkpoint evaluation | Table 8 (G Long-context checkpoint evaluation): GPU-hours for CPT, excluding embedding warmup and ablations.Broad training and annealing ran at a median 5.85 s  |
| 10 | 0.771 | 2310.08754v4 | E Infrastructure & Computational Costs | We trained each of our 26 2.6B parameter models on NVIDIA A100 GPUs, and the training of each model took up to 2304 GPU hours. Therefore, the total training cos |

### bm25: Byte Latent Transformer 8B pre-training GPU hours

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 22.024 | 2610.01984v1 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 2 | 22.002 | 2610.01984v2 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 3 | 20.678 | 2601.03034v1 | 3 Model Training › 3.2 Pre-training | Table 1 (3.2 Pre-training): NorwAI LLMs training specifications. Model \| Params Architecture \| Context Length \| Hidden Size \| Vocab Size \| Training Strategy \| G |
| 4 | 20.678 | 2601.03034v2 | 3 Model Training › 3.2 Pre-training | Table 1 (3.2 Pre-training): NorwAI LLMs training specifications. Model \| Params Architecture \| Context Length \| Hidden Size \| Vocab Size \| Training Strategy \| G |
| 5 | 20.058 | 2512.03989v1 | G Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 8. The hyperparamters for continued pre-training are in  |
| 6 | 19.759 | 2026.findings-eacl.341 | C Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 9. The hyperparamters for continued pre-training using H |
| 7 | 19.759 | 2512.03989v2 | C Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 9. The hyperparamters for continued pre-training using H |
| 8 | 19.625 | 2504.15431v1 | 3. Pre-training › 3.6. Training Infrastructure | Table 1 \| (3.6. Training Infrastructure): Training costs of Trillion 7B on 2T tokens, given H100 price as $2.49 per GPU hour. Training Costs \| Pre-Training Post |
| 9 | 19.361 | 2608.12756v1 | B Reproducibility and compute accounting | Other evaluation and plotting jobs range from minutes to roughly two hours each. Including a conservative six GPU-hour allowance for those jobs, the paper pipel |
| 10 | 19.322 | 2603.27859v1 | 1 Introduction | MATT (Haltiuk and Smywinski-Pohl, 2025) is the most recent and strongest entry: it aligns attention patterns between a teacher (original tokenizer) and a studen |

### dense: Byte Latent Transformer 8B pre-training GPU hours

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.787 | 2610.01984v1 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 2 | 0.783 | 2610.01984v2 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 3 | 0.779 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 1 (5.1 Latency and throughput): Latency comparison across tokenizers on WikiText-103 (ms). Seq. Len HF GPT2 tiktoken CPU-BPE GPU-Base GPU-Opt 256 \| 4.21 \| |
| 4 | 0.777 | 2024.findings-naacl.113 | B Ablations Across | Table 5 (B Ablations Across): Average GPU Hours For Full Finetuning Model Size Hours 70M 160M 410M 1.4B \| 0.65 0.74 1.2 1.7 Model Size Training Time Reduction ( |
| 5 | 0.776 | 2512.03989v1 | G Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 8. The hyperparamters for continued pre-training are in  |
| 6 | 0.776 | 2026.findings-eacl.341 | C Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 9. The hyperparamters for continued pre-training using H |
| 7 | 0.776 | 2512.03989v2 | C Continued pre-training details | We provide details for the modified Llama-3 tokenizers in the continued pertaining experiments in Table 9. The hyperparamters for continued pre-training using H |
| 8 | 0.776 | 2602.06394v1 | G Complete Experimental Results › G.3 Computational Costs | Training Time. • Standard BPE: 5-10 minutes (5GB, CPU) • QA-Token Stage 1 (RL): 30-36 GPU-hours (A100) • QA-Token Stage 2 (Adaptive): 20-24 GPU-hours Memory Req |
| 9 | 0.775 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 2 (5.1 Latency and throughput): Speedup ratios of GPU-Optimized relative to CPU and CPU-based tokenizers. Values > 1 indicate GPU advantage. Seq. Len GPU- |
| 10 | 0.774 | 2211.09761v1 | B Shortening benefits | We quantify the reduction in GPU memory and training time that results from different shortening factors (SFs) in Figure 5. We measure these metrics on an NVIDI |

### bm25: BLT training wall-clock time compute cost H100

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 33.901 | 2506.01084v2 | I.5 Compute Resources | We report the compute resources used for training our models in Table 13. All training was conducted on internal servers equipped with NVIDIA H100 GPUs. We esti |
| 2 | 33.519 | 2506.01084v1 | C Additional Results › Compute Resources | We report the compute resources used for training our models in Table 11. All training was conducted on internal servers equipped with NVIDIA H100 GPUs. We esti |
| 3 | 32.790 | 2606.15521v1 | E Experimental Compute Resources | Most experiments were run on single H100 and A100 GPUs. The bulk of compute resources were expended in retokenization, temperature and typo sampling procedures. |
| 4 | 32.556 | 2505.20133v3 | B ADDITIONAL RESULTS › B.2 RESULTS FOR "TOKENS TO WORDS" (KAPLAN ET AL., 2025) | Empirical speedups. We empirically validate that reduced token counts translate into concrete wall-clock speedups. We compare batch processing of documents from |
| 5 | 30.177 | 2610.05597v1 | 4 Experiments › 4.3 Nanochat speedrun | We next evaluate COBPE on the NANOCHAT speedrun benchmark (Karpathy, 2025) which measures wall-clock training time needed to reach GPT-2-level capability, defin |
| 6 | 28.816 | 2610.01984v1 | G Reproducibility and compute disclosure › G.2 Compute disclosure | Multiplying the primary-suite per-run ranges by their run counts gives approximately 14.8K-27.3K A100 80 GB GPU-hours, plus <6 GPU-hours for downstream evaluati |
| 7 | 28.719 | 2610.01984v2 | G Reproducibility and compute disclosure › G.2 Compute disclosure | Multiplying the primary-suite per-run ranges by their run counts gives approximately 14.8K-27.3K A100 80 GB GPU-hours, plus <6 GPU-hours for downstream evaluati |
| 8 | 27.875 | 2610.01984v1 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 9 | 27.844 | 2610.01984v2 | G Reproducibility and compute disclosure › G.2 Compute disclosure | The primary 28-run LM suite and its single-GPU evaluations ran on internal Linux nodes with NVIDIA A100 80 GB GPUs. Tokenizer training used our two-phase CPU pi |
| 10 | 27.823 | 2610.21679v1 | B Model Details › B.3 VISTA Models › B.3.4 Compute Costs | All VISTA models are trained on 4 or 8 NVIDIA H100/A100 GPUs in bfloat16 mixed precision. VISTA 130M. Each 130M model is trained for 10 epochs on the BP-scaled  |

### dense: BLT training wall-clock time compute cost H100

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.755 | 2406.02517v1 | A Implementation Details › A.3 Computational Cost | Total training duration and GPU used in DRDA experiments are listed in Table 11. WMT IWSLT TED GPU 2× 4× 2× RTX 3090 TITAN Xp TITAN X (Pascal) time 12 days 2 da |
| 2 | 0.755 | 2406.02517v2 | A Implementation Details › A.3 Computational Cost | Total training duration and GPU used in DRDA experiments are listed in Table 11. WMT IWSLT TED GPU 2× 4× 2× RTX 3090 TITAN Xp TITAN X (Pascal) time 12 days 2 da |
| 3 | 0.754 | 2605.07711v3 | F Computational Resources | Table 5 (F Computational Resources): Training time comparison.We report wall-clock training time on a single machine with 8 NVIDIA H20 GPUs. All methods use the |
| 4 | 0.740 | 2605.07711v1 | E Computational Resources | Table 5 (E Computational Resources): Training time comparison.We report wall-clock training time on a single machine with 8 NVIDIA H20 GPUs. All methods use the |
| 5 | 0.731 | 2412.09871v1 | 5 Scaling Trends › 5.1 Parameter Matched Compute Optimal Scaling Trends | Using the Llama 2 dataset, we train various compute-optimal bpe and BLT models across four different sizes, ranging from 1B to 8B parameters. We then plot the t |
| 6 | 0.730 | 2605.08044v1 | A.2 Pre-training Optimization and Hyperparameter Settings | All BLT/BLT-D 1B models are trained for 240,000 steps with a batch size of 2 19 tokens per step (approximately 2 million bytes), and our 3B models are trained f |
| 7 | 0.729 | 2412.09871v1 | 5 Scaling Trends › 5.2 Beyond Compute Optimal Task Evaluations | To assess scaling properties further, we train an 8B BLT model beyond the compute optimal ratio on the BLT-1T dataset, a larger higher-quality dataset, and meas |
| 8 | 0.723 | 2504.15431v1 | 3. Pre-training › 3.6. Training Infrastructure | Table 1 \| (3.6. Training Infrastructure): Training costs of Trillion 7B on 2T tokens, given H100 price as $2.49 per GPU hour. Training Costs \| Pre-Training Post |
| 9 | 0.722 | 2412.09871v1 | 4 Experimental Setup › 4.7 Transformer Architecture Hyperparameters | For all the transformer blocks in BLT, i.e. both local and global models, we largely follow the architecture of Llama 3 (Dubey et al., 2024); we use the SwiGLU  |
| 10 | 0.720 | 2412.09871v1 | 5 Scaling Trends › 5.2 Beyond Compute Optimal Task Evaluations | trained with an equivalent flop budget. However, with BLT-Entropy we additionally make an inference time adjustment of the entropy threshold from 0.6 to 0.1 whi |

## fast-wordpiece-gpu

> How fast is Fast WordPiece when it runs on a GPU?

Drafter's reading: Fast WordPiece reports CPU timings only. The GPU tokenizers that come up are other systems.

### bm25: How fast is Fast WordPiece when it runs on a GPU?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 20.866 | 2606.17358v3 | 4 OTRO: Practical Oblivious Tokenization Path with Read-Only ORAM › 4.3 Chunked Tokenization | The compact bound size to whichever stage is the bottleneck. When the GPU is fast, prefill sets the drain, D eff =D (Llama-8B, Qwen-8B). When the tokenizer outp |
| 2 | 20.307 | 2610.19801v1 | 5 Related Work | Fast serial and GPU tokenizers. The Hugging Face tokenizers library is the reference implementation for most open models and encodes one request on one core [12 |
| 3 | 19.314 | 2610.13325v1 | 1 INTRODUCTION | The end-to-end benefit appears when prefix caching exposes the frontend. With a cold cache, replacing vLLM's stock tokenizer improves mean TTFT by only 2-4%, wh |
| 4 | 19.000 | 2607.29678v3 | 7 Limitations | Three measurements place the implementation at that floor. First, measurements across five GPUs spanning three architecture generations follow sustained clock m |
| 5 | 18.267 | 2610.19801v1 | 1 Introduction | For chat requests with 100K-token contexts, the fast encoder in Delta Tokenizer, used without session state, is no quicker than the reference, whereas Delta Tok |
| 6 | 18.207 | 2607.29678v1 | 7 Limitations | Three measurements place the implementation at that floor. First, measurements across five GPUs spanning three architecture generations follow sustained clock m |
| 7 | 18.181 | 2610.13325v1 | 6 EVALUATION › 6.2 Does GRAPHTOK produce the reference token | Across four decades of input length, the figure shows two regimes. Below the crossover, GRAPHTOK serves the input on its CPU route, whose engine is gigatoken (o |
| 8 | 18.063 | 2302.09207v1 | 4. Experiment: Speed › Setup | We use the Multilingual Amazon Reviews (McAuley & Leskovec, 2013) dataset for the tokenization speed evaluations. The corpus is composed of 1.2M tokens -200k to |
| 9 | 17.821 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | When it returns on line 10, = \| 2 \|, is node 12 (since (12) = ∅), and the result tokens are [a, ##b, ##c], which do not cover character d. Actually, the string  |
| 10 | 17.821 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | When it returns on line 10, = \| 2 \|, is node 12 (since (12) = ∅), and the result tokens are [a, ##b, ##c], which do not cover character d. Actually, the string  |

### dense: How fast is Fast WordPiece when it runs on a GPU?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.752 | 2012.15524v3 | 5 Experiments | All experiments are conducted on a Linux desktop with a six-core Intel Xeon @ 3.60GHz CPU and 64GB memory. We iterate each benchmark (after warming up) until it |
| 2 | 0.752 | 2021.emnlp-main.160 | 5 Experiments | All experiments are conducted on a Linux desktop with a six-core Intel Xeon @ 3.60GHz CPU and 64GB memory. We iterate each benchmark (after warming up) until it |
| 3 | 0.742 | 2606.20993v1 | H Experimental setup H.1 Tokenizer training hyper-parameters › H.3 Computational footprint | All experiments were run on a single GPU on the Snellius cluster, using either an NVIDIA H100 GPU (for GPT-2 pre-training runs) or an NVIDIA A100 GPU (for all o |
| 4 | 0.740 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 2 (5.1 Latency and throughput): Speedup ratios of GPU-Optimized relative to CPU and CPU-based tokenizers. Values > 1 indicate GPU advantage. Seq. Len GPU- |
| 5 | 0.732 | 2012.15524v3 | 5 Experiments › Results | Table 3 shows the mean and the 95 percentilefoot_8 running time when tokenizing a single word or general text (end-to-end) for each system. For single-word toke |
| 6 | 0.732 | 2021.emnlp-main.160 | 5 Experiments › Results | Table 3 shows the mean and the 95 percentilefoot_8 running time when tokenizing a single word or general text (end-to-end) for each system. For single-word toke |
| 7 | 0.728 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Figure3: Speedup of the optimized GPU tokenizer relative to CPU-based tokenizers. Values above one indicate that the GPU implementation is faster. The crossover |
| 8 | 0.728 | 2311.09709v1 | 4 Results and Discussions › 4.3 GPU results | In addition to CPU tests, we performed the same BLOOM experiments on GPU and we observe that all three selection criteria including the oracle do not lead to im |
| 9 | 0.727 | 1508.06615v1 | Further Observations | • A potential drawback of our work is training speedour model requires additional convolution operations over characters, and is thus slower than a comparable w |
| 10 | 0.726 | 2301.10472v1 | 6 Analysis › 6.4 Speed vs. size | Figure4: We track training speed vs. vocabulary size using a typical training setup on XNLI: one A100 GPU, a batch size of 16, sequence length of 128, and float |

### bm25: Fast WordPiece GPU throughput

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 18.705 | 2023.acl-demo.37 | B Batched runtimes | Model Batch size Runtime seconds Throughput sequences / sec Throughput kB / sec GPU memory MiB GPU memory MiB / sequence ByT5 16 128 5.0 4.2 696.2 833.6 80.5 96 |
| 2 | 16.870 | 2023.acl-demo.37 | 4 Experiments › 4.4 Results | Table 4 (4.4 Results): Inference runtimes on our Runtime benchmark (see Section 4.1) on a NVIDIA A100 GPU and an Intel Xeon Platinum 8358 CPU with mixed precisi |
| 3 | 16.654 | 2601.05531v1 | A Preprint › CPU-bound inference: | Deploying models on edge devices or CPU-only infrastructure cannot leverage GPU tokenization. However, the simpler algorithmic approaches (character-level or fi |
| 4 | 16.508 | 2511.11346v1 | Architecture Components: | Table 5 (Architecture Components:): More expressive archi- tectures such as MTPC-BTREE outperform MTPC-CP on longer windows in terms of throughput for n = 8 and |
| 5 | 15.963 | 2607.29678v3 | 7 Limitations | Three measurements place the implementation at that floor. First, measurements across five GPUs spanning three architecture generations follow sustained clock m |
| 6 | 15.769 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Around two thousand tokens the optimized GPU kernel reaches parity with tiktoken, and beyond this point the speedup grows steadily. Figure 3 and Table 2 report  |
| 7 | 15.753 | 2601.05531v1 | 1 Introduction › 1.2 The systems gap | Genomic models provide limited systems-level approaches to overcome tokenization as a throughput bottleneck in production workloads. The focus remains primarily |
| 8 | 15.677 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 2 (5.1 Latency and throughput): Speedup ratios of GPU-Optimized relative to CPU and CPU-based tokenizers. Values > 1 indicate GPU advantage. Seq. Len GPU- |
| 9 | 15.604 | 2511.11346v1 | 4 MTPCS IN ACTION: RETROFITTING A BYTE-LEVEL LLM › 4.3 MTPCS WITHOUT ADAPTERS | Table 1 (4.3 MTPCS WITHOUT ADAPTERS): Increasing the mixture components (r) increases the throughput (µ tok/s ) as seen for MTPC-CP (n = 8) over our baseline, E |
| 10 | 15.499 | 2601.05531v1 | 3 Results › 3.1 Experimental Setup › DNATokenizer: A GPU-First Byte-to-Identifier Tokenizer for High-Throughput DNA Language Models | A Preprint |

### dense: Fast WordPiece GPU throughput

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.809 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 2 (5.1 Latency and throughput): Speedup ratios of GPU-Optimized relative to CPU and CPU-based tokenizers. Values > 1 indicate GPU advantage. Seq. Len GPU- |
| 2 | 0.794 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Table 1 (5.1 Latency and throughput): Latency comparison across tokenizers on WikiText-103 (ms). Seq. Len HF GPT2 tiktoken CPU-BPE GPU-Base GPU-Opt 256 \| 4.21 \| |
| 3 | 0.791 | 2610.04951v1 | C. Tokenization Throughput | We define throughput as the number of bytes a tokenizer processes per unit time, reported in MB/s. Formally, given a corpus of total size B bytes and a measured |
| 4 | 0.790 | 2606.20993v1 | H Experimental setup H.1 Tokenizer training hyper-parameters › H.3 Computational footprint | All experiments were run on a single GPU on the Snellius cluster, using either an NVIDIA H100 GPU (for GPT-2 pre-training runs) or an NVIDIA A100 GPU (for all o |
| 5 | 0.786 | 2610.04951v1 | b) Platform: | All experiments were run on a GPU node of the Perlmutter supercomputer at NERSC. Specifically, we used an NVIDIA A100 GPU with 80GB of memory, paired with an AM |
| 6 | 0.785 | 2607.29678v3 | 5 Evaluation › 5.7 Cost and resource use | Applying the measured per-path costs to the 153,529 calls with complete token accounting gives 13.4 ms of CPU time per request for fastokens and 2.3 ms for TokT |
| 7 | 0.785 | 2507.15773v2 | 5. Language Detection: › 5.3 Training Efficiency › 5.3.1 Hardware Utilization | Training was conducted on a cluster of 8 NVIDIA A100 40GB GPUs, achieving high utilization efficiency across compute, memory, and bandwidth resources. The Model |
| 8 | 0.785 | 2507.15773v1 | 5. Language Detection: › 5.3 Training Efficiency › 5.3.1 Hardware Utilization | Training was conducted on a cluster of 8 NVIDIA A100 40GB GPUs, achieving high utilization efficiency across compute, memory, and bandwidth resources. The Model |
| 9 | 0.783 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Around two thousand tokens the optimized GPU kernel reaches parity with tiktoken, and beyond this point the speedup grows steadily. Figure 3 and Table 2 report  |
| 10 | 0.782 | 2603.02597v1 | 5 Experimental results and analysis › 5.1 Latency and throughput | Figure3: Speedup of the optimized GPU tokenizer relative to CPU-based tokenizers. Values above one indicate that the GPU implementation is faster. The crossover |

### bm25: LinMaxMatch WordPiece tokenization on GPU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 22.238 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | Algorithm 1: LinMaxMatch Tokenization Function LINMAXMATCH( ):1 tokens, , ← MATCHLOOP( , 0) 2 if < \| \| or ∉ { , ♯ } then 3 tokens ← [<unk>] |
| 2 | 22.238 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | Algorithm 1: LinMaxMatch Tokenization Function LINMAXMATCH( ):1 tokens, , ← MATCHLOOP( , 0) 2 if < \| \| or ∉ { , ♯ } then 3 tokens ← [<unk>] |
| 3 | 21.206 | 2012.15524v3 | A Mathematical Formulations and Proofs of LinMaxMatch › A.2 MinPop Matching › Definition 6. MinPop Matching | Algorithm 4: LinMaxMatch as an FSTFunction LINMAXMATCH( ):1 tokens, , ← MATCHLOOP( , 0) 2 if < \| \| or ∉ { , ♯ } then 3 tokens ← [<unk>] |
| 4 | 21.206 | 2021.emnlp-main.160 | A Mathematical Formulations and Proofs of LinMaxMatch › A.2 MinPop Matching › Definition 6. MinPop Matching | Algorithm 4: LinMaxMatch as an FSTFunction LINMAXMATCH( ):1 tokens, , ← MATCHLOOP( , 0) 2 if < \| \| or ∉ { , ♯ } then 3 tokens ← [<unk>] |
| 5 | 20.741 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization | In this section, we present LinMaxMatch, an ( ) algorithm for single-word WordPiece tokenization. |
| 6 | 20.741 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization | In this section, we present LinMaxMatch, an ( ) algorithm for single-word WordPiece tokenization. |
| 7 | 20.414 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | 0 |
| 8 | 20.414 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | 0 |
| 9 | 20.325 | 2012.15524v1 | 4.4 Inference Algorithm | [<unk>]. Algorithm 2: 1 if = ♯ then return ORIGINALMAXMATCH( , ) 2 , 3 for in $ do 4 while ( , ) = ∅ do 5 if: LinMaxMatch: Inference Function LINMAXMATCH( , , ) |
| 10 | 20.227 | 2012.15524v1 | 5 Experiments | We compare the practical behavior of our LinMaxMatch algorithm (as used for WordPiece tokenization) against two popular implementations: • HuggingFace Tokenizer |

### dense: LinMaxMatch WordPiece tokenization on GPU

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.896 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization | In this section, we present LinMaxMatch, an ( ) algorithm for single-word WordPiece tokenization. |
| 2 | 0.896 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization | In this section, we present LinMaxMatch, an ( ) algorithm for single-word WordPiece tokenization. |
| 3 | 0.882 | 2012.15524v3 | 6 Conclusion | We proposed LinMaxMatch for single-word Word-Piece tokenization, which is asymptoticallyoptimal linear-time with respect to the input length, without a vocabula |
| 4 | 0.882 | 2021.emnlp-main.160 | 6 Conclusion | We proposed LinMaxMatch for single-word Word-Piece tokenization, which is asymptoticallyoptimal linear-time with respect to the input length, without a vocabula |
| 5 | 0.878 | 2012.15524v3 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | 0 |
| 6 | 0.878 | 2021.emnlp-main.160 | 3 Linear-Time Single-Word Tokenization › 3.3 LinMaxMatch Tokenization | 0 |
| 7 | 0.878 | 2012.15524v1 | 5 Experiments | We compare the practical behavior of our LinMaxMatch algorithm (as used for WordPiece tokenization) against two popular implementations: • HuggingFace Tokenizer |
| 8 | 0.865 | 2012.15524v1 | 7 Conclusion | We proposed an asymptotically-optimal linear-time MaxMatch algorithm for WordPiece tokenization. Experimental results show that our algorithm is significantly f |
| 9 | 0.865 | 2012.15524v1 | 1 Introduction | WordPiece tokenization segments the input text using a greedy longest-match-first strategy: iteratively pick the longest prefix of the remaining text that match |
| 10 | 0.863 | 2012.15524v1 | 2 Related Work | Maximum Matching (or MaxMatch) has been used for Chinese word segmentation (CWS) since the 1980s [21,16,26]. Recent CWS work focuses on machine-learning-based s |

## sentencepiece-korean-speed

> How quickly does SentencePiece segment Korean text?

Drafter's reading: SentencePiece times English and Japanese segmentation only. ONE-Piece (2021.naacl-industry.13) times Korean morphological analysers, not SentencePiece.

### bm25: How quickly does SentencePiece segment Korean text?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 19.279 | 2302.09207v3 | 4 Evaluation: Speed | In this section, we evaluate how quickly RETVec can process and vectorize datasets compared to the other commonly used vectorizers. We considered SentencePiece  |
| 2 | 19.232 | 2302.09207v1 | 4. Experiment: Speed | In this section, we evaluate how quickly RetVec can process datasets compared to the other commonly used tokenizers with a layer on learned embedding on top. We |
| 3 | 18.345 | 1812.08621v1 | 5 Results › Language SentencePiece | Table 4: English to German translation examples comparing SentencePiece, Open-NMT tokenizer and Moses tokenizer. First line corresponds to the source sentence i |
| 4 | 16.459 | 2502.12560v1 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 5 | 16.459 | 2502.12560v2 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 6 | 15.796 | 2502.12560v1 | 3 Extended Tokenizer | Well-known open-source models, such as Mistral [Jiang et al., 2023] Llama-2 [Touvron et al., 2023], Yi [AI et al., 2024], MT5 [Xue et al., 2021], Giraffe [Nieme |
| 7 | 15.796 | 2502.12560v2 | 3 Extended Tokenizer | Well-known open-source models, such as Mistral [Jiang et al., 2023] Llama-2 [Touvron et al., 2023], Yi [AI et al., 2024], MT5 [Xue et al., 2021], Giraffe [Nieme |
| 8 | 15.727 | 2004.14870v1 | 5 Model-Independent Analyses | Although wrapping an existing pretrained subword tokenizer and model like WordPiece and BERT base allows us to quickly reap the benefits of BITE without the com |
| 9 | 15.311 | 1812.08621v4 | 6 Qualitative Analysis | Example 1 Source Revalidation of single-pilot single-engine class ratings Reference verlängerung von klassenberechtigungen für einmotorige flugzeuge mit einem p |
| 10 | 15.232 | 10.1109/ACCESS.2020.3004879 | 1) SUBWORD TOKENIZATION EVALUATION | First, the performance was the lowest when subword tokenization consisted of entity restriction only, that is, restricting the entity only has a negative effect |

### dense: How quickly does SentencePiece segment Korean text?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.844 | D18-2012 | 4.2 Segmentation performance | larger performance improvements when applying it to raw Japanese data (w/o pre-tok). The segmentation speed of SentencePiece is about 380 times faster than that |
| 2 | 0.833 | 1808.06226v1 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |
| 3 | 0.795 | 2025.loresmt-1.8 | A Architecture and Training Details › A.1 Tokenization and Segmentation | We use SentencePiece for BPE tokenization. Table 8 gives the flags for the Korean and English tokenizers. We used SacreBLEU to compute the metrics. The text was |
| 4 | 0.788 | 1808.06226v1 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 5 | 0.788 | D18-2012 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 6 | 0.786 | 1808.06226v1 | 4.2 Segmentation performance | Table 2 (4.2 Segmentation performance): Segmentation performance. KFTT corpus (440k sentences) is used for evaluation. Experiments are executed on Linux with Xe |
| 7 | 0.785 | 1905.13656v3 | 3 Experiment | For (iii) and (iv), we adopted a vector set that is distributed publicly in Cho et al. (2018a), reported to be extracted from a drama script corpus of size 2M.  |
| 8 | 0.784 | 2105.09680v1 | 3 KLUE Benchmark › 3.2 Semantic Textual Similarity (STS) › 3.2.1 Dataset Construction | Result: Set of sentence pairs SET in a corpus C Prepare corpus C, Let SET = []; while size of C ≥ 2 do 1. Choose a random sentence S from C; 2. Find a sentence  |
| 9 | 0.784 | 2105.09680v4 | 3 KLUE Benchmark › 3.2 Semantic Textual Similarity (STS) › 3.2.1 Dataset Construction | Result: Set of sentence pairs SET in a corpus C Prepare corpus C, Let SET = []; while size of C ≥ 2 do 1. Choose a random sentence S from C; 2. Find a sentence  |
| 10 | 0.783 | D18-2012 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |

### bm25: SentencePiece segmentation speed Korean

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 18.298 | 1808.06226v1 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |
| 2 | 18.032 | D18-2012 | 4.2 Segmentation performance | larger performance improvements when applying it to raw Japanese data (w/o pre-tok). The segmentation speed of SentencePiece is about 380 times faster than that |
| 3 | 17.819 | 2021.naacl-industry.13 | 1 Introduction | All the experiments are made on a Korean dataset, which is a representative of low-resource and morphologically rich language (MRL). In particular, we propose O |
| 4 | 14.956 | D18-2012 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |
| 5 | 14.509 | 2025.loresmt-1.8 | A Architecture and Training Details › A.1 Tokenization and Segmentation | We use SentencePiece for BPE tokenization. Table 8 gives the flags for the Korean and English tokenizers. We used SacreBLEU to compute the metrics. The text was |
| 6 | 14.085 | 2502.12560v1 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 7 | 14.085 | 2502.12560v2 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 8 | 13.943 | 1808.06226v1 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 9 | 13.943 | D18-2012 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 10 | 13.665 | 2511.05324v1 | 4 Experimental Setup › 4.6 Summary of Experimental Design | The table shows that the suggested BengaliBPE provides the most linguistically rich segmentation, generating more than twice as many tokens per character, even  |

### dense: SentencePiece segmentation speed Korean

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.882 | D18-2012 | 4.2 Segmentation performance | larger performance improvements when applying it to raw Japanese data (w/o pre-tok). The segmentation speed of SentencePiece is about 380 times faster than that |
| 2 | 0.875 | 1808.06226v1 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |
| 3 | 0.851 | 2025.loresmt-1.8 | A Architecture and Training Details › A.1 Tokenization and Segmentation | We use SentencePiece for BPE tokenization. Table 8 gives the flags for the Korean and English tokenizers. We used SacreBLEU to compute the metrics. The text was |
| 4 | 0.833 | 1808.06226v1 | 4.2 Segmentation performance | Table 2 (4.2 Segmentation performance): Segmentation performance. KFTT corpus (440k sentences) is used for evaluation. Experiments are executed on Linux with Xe |
| 5 | 0.832 | D18-2012 | 4.2 Segmentation performance | Table 2 summarizes the training and segmentation performance of various configurations. We can see that the training and segmentation speed of both SentencePiec |
| 6 | 0.826 | 1808.06226v1 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 7 | 0.826 | D18-2012 | 3 Library Design › 3.2 Efficient subword training and segmentation | Existing subword segmentation tools train subword models from pre-tokenized sentences. Such pre-tokenization was introduced for an efficient subword training (S |
| 8 | 0.823 | 2026.eacl-short.22 | Abstract | Tokenization plays a crucial role in the performance of language models. However, most existing tokenizers rely on frequency-based segmentation, which fails to  |
| 9 | 0.820 | D18-2012 | 3 Library Design › 3.6 Library API for on-the-fly processing › Figure 5: TensorFlow API usage | Table 1 shows the experimental results. First, as can be seen in the table, subword segmentations with SentencePiece consitently improve the BLEU scores compare |
| 10 | 0.819 | 1808.06226v1 | 3 Library Design › 3.6 Library API for on-the-fly processing › Figure 5: TensorFlow API usage | Table 1 shows the experimental results. First, as can be seen in the table, subword segmentations with SentencePiece consitently improve the BLEU scores compare |

### bm25: SentencePiece sentences per second Korean

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 14.898 | 2021.acl-long.571 | 5 Experiments › 5.3 Discussion › VOLT Beats SentencePiece and WordPiece. | Table 6 demonstrates that vocabularies searched by VOLT also works on Convolutional Seq2Seq with competitive BLEU but much smaller size. In this work, we verify |
| 2 | 14.851 | 2010.02534v1 | 5.1.2 BPE Modeling | Prior to training, we do simple preliminary experiments to decide which dataset to use for learning BPE. There are two choices: AI Hub news training data and op |
| 3 | 14.749 | 2502.12560v1 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 4 | 14.749 | 2502.12560v2 | 3 Extended Tokenizer | Despite its ability to handle unseen tokens by splitting them into bytes, SentencePiece BPE can cause issues when processing languages underrepresented in the t |
| 5 | 14.388 | 2025.loresmt-1.8 | A Architecture and Training Details › A.1 Tokenization and Segmentation | We use SentencePiece for BPE tokenization. Table 8 gives the flags for the Korean and English tokenizers. We used SacreBLEU to compute the metrics. The text was |
| 6 | 14.093 | 10.17671/gazibtd.1856668 | 4. EXPERIMENTS AND RESULTS › 4.5. Runtime Benchmark | The benchmark results indicate that tokenizers implemented entirely in compiled engines (e.g., Rust/C++) and operating without an additional preprocessing layer |
| 7 | 13.948 | 2021.naacl-industry.13 | 2 Proposed Method › 2.1 Morphologically-Aware SentencePiece | Korean is classified as an agglutinative language according to its type of morphemes. Due to the nature of agglutinative languages, one word can comprises subst |
| 8 | 13.460 | 2506.15138v1 | 3 Methods › 3.3 Branching Entropy | Branching Entropy is typically calculated by measuring the diversity of characters adjacent to a target token. However, in the Korean language, even the same ch |
| 9 | 13.442 | 2021.naacl-industry.13 | 2 Proposed Method › 2.4 ONE-Piece | M A indicates morphological analyzer for source language. By M A, morpheme-unit-segmented sentence Seg i is generated from source sentence S i . k i denotes mor |
| 10 | 13.292 | 2020.aacl-main.17 | 5.1.2 BPE Modeling | Prior to training, we do simple preliminary experiments to decide which dataset to use for learning BPE. There are two choices: AI Hub news training data and op |

### dense: SentencePiece sentences per second Korean

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.782 | 10.7469/JKSQM.2020.48.3.421 |  | Table 2: Results of performance metrics for SentencePiece and Mecab-Ko using kNN DT \| Mecab-Ko \| 1500 \| 2000 \| Number of Tokens in SentencePiece 3000 5000 10000 |
| 2 | 0.775 | 10.7469/JKSQM.2020.48.3.421 |  | 지도 기반 접근 방식 과 달리, SentencePiece는 사전 토큰화된 데이터 집합이 필요하지 않으므로 여러 언어가 혼합적으로 사용된 텍스트 나 사전에 없는 단어를 포함하는 텍스트 코퍼스에 더 적합하다. SentencePiece 알고리즘과 일반적인 형태소 분석 엔진과의 중요한 차이점  |
| 3 | 0.765 | 10.7469/JKSQM.2020.48.3.421 |  | 영어, 일본어, 중국어, 프랑스어 등의 고객 리뷰 를 대상으로 감성 분석을 수행한 기존 연구에서 SentencePiece를 활용하여 정확도를 높인 결과들이 보고되었기 때 문에, 한국어 상품평을 기반으로 한 감성 분류의 정확도를 개선하기 위해 SentencePiece의 적용 가능성 여부를 |
| 4 | 0.762 | 2105.09680v4 | 2.2. Multiple-Sentence Reasoning (Type 2) › Trajan(AD 98-AD 117) / Trajan / AD 98-AD 117 | Table 16 (Trajan(AD 98-AD 117) / Trajan / AD 98-AD 117): Multiple sentence reasoning question type example for Korean and its English translation Type \| Korean  |
| 5 | 0.761 | 10.7469/JKSQM.2020.48.3.421 |  | 다양한 종류의 언어에서 감성 분석 시 SentencePiece의 우수성이 조사되었기 때문에, 한국어 기반 상품평과 리뷰에 대한 연구가 이뤄질 필요가 있다. 3. 연구방법 3.1 훈련 및 시험 데이터 세트 본 연구에서는 국내 최대 가격 비교 사이트인 다나와(www.danawa.com)에서 |
| 6 | 0.757 | 10.7469/JKSQM.2020.48.3.421 |  | )에 의해 제안된 SentencePiece는 신경망 기반의 텍스트 생성 모델을 위한 비지도 텍스트 토크나이저 및 해독기이다. SentencePiece는 원시 문장에서 직접 학습 개념을 확장하여 2개의 하위 단어 분류 알고리즘인 byte-pair encoding(BPE)과 유니그램 언어  |
| 7 | 0.757 | 2025.loresmt-1.8 | 6 Results › 6.3 Korean↔Jeju-eo | Both 16.43 39.57 88.13 (a) English→Korean Representation Dropout (p = 0.1) BLEU CHRF COMET Syllable None 32.30 59.83 80.49 Korean 33.36 60.73 81.02 English 32.1 |
| 8 | 0.757 | 2105.09680v1 | 3 KLUE Benchmark › 3.2 Semantic Textual Similarity (STS) › 3.2.1 Dataset Construction | Result: Set of sentence pairs SET in a corpus C Prepare corpus C, Let SET = []; while size of C ≥ 2 do 1. Choose a random sentence S from C; 2. Find a sentence  |
| 9 | 0.757 | 2105.09680v4 | 3 KLUE Benchmark › 3.2 Semantic Textual Similarity (STS) › 3.2.1 Dataset Construction | Result: Set of sentence pairs SET in a corpus C Prepare corpus C, Let SET = []; while size of C ≥ 2 do 1. Choose a random sentence S from C; 2. Find a sentence  |
| 10 | 0.754 | 1905.13656v3 | 3 Experiment | For (iii) and (iv), we adopted a vector set that is distributed publicly in Cho et al. (2018a), reported to be extracted from a drama script corpus of size 2M.  |

## byt5-learning-rate

> Which learning rate schedule did ByT5 use for pre-training?

Drafter's reading: ByT5 gives a constant learning rate of 0.001 for fine-tuning, not a pre-training schedule. MANTa follows ByT5's optimiser but states its own schedule.

### bm25: Which learning rate schedule did ByT5 use for pre-training?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 26.307 | 2308.09440v3 | 3 COMPCODER: pre-training a code LM on HPC code › Experimental setup. | All pre-training experiments were trained with the Adam optimizer, and followed a learning rate schedule with a linear warmup for the first 10% of steps and a c |
| 2 | 24.600 | 2022.findings-emnlp.207 | 3 MANTa › 3.2 Model Training › 3.2.1 Pre-Training Details | Following T5 and ByT5, we use the Adafactor optimizer with a learning rate of 10 -2 for the encoder-decoder model, parameter scaling for the whole system and no |
| 3 | 24.600 | 2212.07284v1 | 3 MANTa › 3.2 Model Training › 3.2.1 Pre-Training Details | Following T5 and ByT5, we use the Adafactor optimizer with a learning rate of 10 -2 for the encoder-decoder model, parameter scaling for the whole system and no |
| 4 | 23.078 | 2606.30140v1 | 3 Training Scheme › 3.2 Masked Language Modelling | All models are trained for 30 epochs using the AdamW optimizer [4]. We use a one-cycle learning-rate schedule [9], with a maximum learning rate of 10 -3 , and a |
| 5 | 22.996 | 1905.10453v1 | 3 Analysis Setup › 3.2 Architecture | Per the experiment setting in Vaswani et al. (2017), we apply label smoothing with ε ls = 0.1 for all of our Transformer experiments. We use Adam optimizer (Kin |
| 6 | 22.692 | 2510.21372v2 | 3. Methods › 3.3. Pre-training | Following the setup of GottBERT, we pre-trained HalleluBERT base and HalleluBERT large using the fairseq framework (Ott et al., 2019) on a 128-core TPUv4 pod (J |
| 7 | 22.414 | 2410.03730v3 | 5 Base Model › 5.4 Continued Pre-Training | We want to emphasize that the initial goal has been to train our base model up to 3T tokens, which are beyond compute-optimal based on the scaling laws presente |
| 8 | 22.398 | 2023.emnlp-main.829 | A Hyperparameters and Experiment Details | Further pretraining. We used the same hyperparameters for all target languages, as detailed in Table 5. We trained for a total of 50 million samples with batche |
| 9 | 21.492 | 2508.15390v3 | I Detailed Experimental Setting | Table 8 (I Detailed Experimental Setting): Training configurations. LR Schedule denotes learning-rate schedule. Global Batch Size Weight Decay Sequence Length O |
| 10 | 21.252 | W19-6620 | 3 Analysis Setup › 3.2 Architecture | For Transformer experiments, we use the learning rate scheduling settings in Vaswani et al. (2017), including the inverse square root learning rate scheduler, 4 |

### dense: Which learning rate schedule did ByT5 use for pre-training?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.737 | 2506.04079v1 | 2.3 PRE-TRAINING PHASES | Figure 2: Scheme of the learning rate scheduler. |
| 2 | 0.737 | 2506.04079v2 | 2.3 PRE-TRAINING PHASES | Figure 2: Scheme of the learning rate scheduler. |
| 3 | 0.730 | 2022.tacl-1.17 | 6 Ablation Study › 6.4 Character Vocabulary | Table 9: Pre-training speed and computation of mT5 vs. ByT5. Left: Sequences per second pre-training on a TPUv3-64 device. Right: Total einsum operations for a  |
| 4 | 0.728 | 2602.05879v1 | 2 PRE-TRAINING › 2.2 TRAINING PHASES | Figure 1: Scheme of the learning rate scheduler. |
| 5 | 0.718 | 2105.13626v3 | 6 Ablation Study › 6.4 Character Vocabulary | sequences / sec einsum ops ×1e 12 mT5 ByT5 mT5 ByT5 Small 1646 1232 (0.75×) 87 98 (1.13×) Base 747 576 (0.77×) 168 194 (1.15×) Large 306 232 (0.76×) 346 416 (1. |
| 6 | 0.718 | 2023.findings-emnlp.923 | 5 Methods and Tools | ByT5. ByT5 is a multilingual pre-trained model of the T5 family (Raffel et al., 2020). These models We run all models on our base setup (entire sentence instanc |
| 7 | 0.714 | 2105.13626v1 | 1 Introduction | Table 9 (1 Introduction): compares the pre-training FLOPs of ByT5 vs. mT5, as well as the pre-training speed on fixed hardware, as sequences per second with seq |
| 8 | 0.711 | 2022.tacl-1.17 | 4 Core Results | In this section, we compare ByT5 against mT5 on a wide range of tasks. We show that ByT5 is competitive with mT5 on standard English and multilingual NLP benchm |
| 9 | 0.710 | 2105.13626v3 | 4 Core Results | In this section, we compare ByT5 against mT5 on a wide range of tasks. We show that ByT5 is competitive with mT5 on standard English and multilingual NLP benchm |
| 10 | 0.707 | 2105.13626v1 | 6 Ablation Study › 6.4 Character Vocabulary | sequences / sec einsum ops ×1e 12 mT5 ByT5 mT5 ByT5 Small 1646 1232 (0.75×) 87 98 (1.13×) Base 747 576 (0.77×) 168 194 (1.15×) Large 306 232 (0.76×) 346 416 (1. |

### bm25: ByT5 pre-training learning rate schedule inverse square root

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 33.741 | W19-6620 | 3 Analysis Setup › 3.2 Architecture | For Transformer experiments, we use the learning rate scheduling settings in Vaswani et al. (2017), including the inverse square root learning rate scheduler, 4 |
| 2 | 33.667 | 2608.18087v1 | 15. Experimental Setup for Neural Machine Translation › 15.1. Neural Machine Translation › 15.1.3. Training and Optimization | Models are trained for 100k updates using the Adam optimizer (β1 = 0.9, β2 = 0.98) with a label smoothing factor of 0.1. We utilize an inverse-square-root learn |
| 3 | 33.667 | 2608.18087v2 | 15. Experimental Setup for Neural Machine Translation › 15.1. Neural Machine Translation › 15.1.3. Training and Optimization | Models are trained for 100k updates using the Adam optimizer (β1 = 0.9, β2 = 0.98) with a label smoothing factor of 0.1. We utilize an inverse-square-root learn |
| 4 | 32.079 | 1905.10453v1 | 3 Analysis Setup › 3.2 Architecture | Per the experiment setting in Vaswani et al. (2017), we apply label smoothing with ε ls = 0.1 for all of our Transformer experiments. We use Adam optimizer (Kin |
| 5 | 31.788 | 2201.13242v2 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | Sometimes, better results can be achieved by scheduling learning rate values during the training. There is, typically, the so-called warm-up period in the begin |
| 6 | 31.370 | 2021.wnut-1.54 | 4 Experiments | The MultiLexNorm shared task consists of 12 social media datasets in 11 languages, including two code-switching datasets. All these datasets are based on Twitte |
| 7 | 31.370 | 2110.15248v1 | 4 Experiments | The MultiLexNorm shared task consists of 12 social media datasets in 11 languages, including two code-switching datasets. All these datasets are based on Twitte |
| 8 | 31.370 | 2110.15248v2 | 4 Experiments | The MultiLexNorm shared task consists of 12 social media datasets in 11 languages, including two code-switching datasets. All these datasets are based on Twitte |
| 9 | 30.639 | 2203.03583v1 | 4.2. Model and Training Setup | We use Conformer-M [31] as the ASR encoder, following [32]. The input frames are 80-dim log-Mel filterbanks extracted from 25ms window and 15ms overlap. We trai |
| 10 | 29.753 | 2506.03101v1 | 3 Proposed Approach › 3.3 Downstream Tasks | Table 9 (3.3 Downstream Tasks): Finetuning details for X-SUM. \| 350M \| 2.7B Peak LR \| 4.5e-4 \| 8e-5 LR schedule \| Inverse Square-root \| Batch size \| 256 \| Preci |

### dense: ByT5 pre-training learning rate schedule inverse square root

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.796 | 2201.13242v2 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | Sometimes, better results can be achieved by scheduling learning rate values during the training. There is, typically, the so-called warm-up period in the begin |
| 2 | 0.791 | 1905.10453v2 | 3 Analysis Setup › 3.2 Architecture | For Transformer experiments, we use the learning rate scheduling settings in Vaswani et al. (2017), including the inverse square root learning rate scheduler, 4 |
| 3 | 0.785 | 2506.04079v1 | 2.3 PRE-TRAINING PHASES | Figure 2: Scheme of the learning rate scheduler. |
| 4 | 0.785 | 2506.04079v2 | 2.3 PRE-TRAINING PHASES | Figure 2: Scheme of the learning rate scheduler. |
| 5 | 0.781 | W19-6620 | 3 Analysis Setup › 3.2 Architecture | For Transformer experiments, we use the learning rate scheduling settings in Vaswani et al. (2017), including the inverse square root learning rate scheduler, 4 |
| 6 | 0.778 | 2022.tacl-1.17 | 6 Ablation Study › 6.4 Character Vocabulary | Table 9: Pre-training speed and computation of mT5 vs. ByT5. Left: Sequences per second pre-training on a TPUv3-64 device. Right: Total einsum operations for a  |
| 7 | 0.770 | 2105.13626v3 | 6 Ablation Study › 6.4 Character Vocabulary | sequences / sec einsum ops ×1e 12 mT5 ByT5 mT5 ByT5 Small 1646 1232 (0.75×) 87 98 (1.13×) Base 747 576 (0.77×) 168 194 (1.15×) Large 306 232 (0.76×) 346 416 (1. |
| 8 | 0.767 | 2105.13626v3 | 3 ByT5 Design › 3.2 Comparing the Models | given a fixed input sequence length and number of training steps, the model will be exposed to roughly 4× less actual text during pre-training. With these facto |
| 9 | 0.764 | 2105.13626v1 | 6 Ablation Study › 6.4 Character Vocabulary | sequences / sec einsum ops ×1e 12 mT5 ByT5 mT5 ByT5 Small 1646 1232 (0.75×) 87 98 (1.13×) Base 747 576 (0.77×) 168 194 (1.15×) Large 306 232 (0.76×) 346 416 (1. |
| 10 | 0.763 | 2105.13626v1 | 1 Introduction | Table 9 (1 Introduction): compares the pre-training FLOPs of ByT5 vs. mT5, as well as the pre-training speed on fixed hardware, as sequences per second with seq |

### bm25: ByT5 Adafactor learning rate warmup

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 25.151 | 2201.13242v2 | 6 Experiment Details › 6.1 ByT5 Model Fine-Tuning | We used the Adafactor [104] optimizer with a constant learning rate of 0.001. The same setup was employed by the ByT5 [8] authors for fine-tuning experiments. M |
| 2 | 23.385 | 2024.tacl-1.22 | A Hyperparameters | We train models using the AdaFactor (Shazeer and Stern, 2018) optimizer with 4000 warmup batches and a final constant learning rate of 1e-4. We batch by # of to |
| 3 | 23.385 | 2302.14220v3 | A Hyperparameters | We train models using the AdaFactor (Shazeer and Stern, 2018) optimizer with 4000 warmup batches and a final constant learning rate of 1e-4. We batch by # of to |
| 4 | 22.292 | 2302.14220v1 | A Hyperparameters | For training our models, we use AdaFactor (Shazeer and Stern, 2018) for optimization, with a learning rate of 1e-4. We use a constant learning rate schedule wit |
| 5 | 22.069 | 2408.07065v1 | 4 Experiments › 4.2 Ablations | Ablation: Compare T5-Base vs. ByT5-Base trained on noisy YouTube-ASL. 3. RQ3: What happens if we train a sign language translation model on fingerspelling recog |
| 6 | 21.949 | 2201.13242v1 | 6 Experiment Details › 6.1 ByT5 Model Fine-Tuning | We chose the batch size of 256 and default ByT5 maximum sequence length of 1024. Such configuration matches the total maximum number of tokens (256 × 1024 = 204 |
| 7 | 21.258 | 2408.07065v1 | C How2Sign Results | model zero-shot finetuned Rust et al. (2024) 7.1 (41.8) 15.5 (49.6) T5 (YT) 5.7 (38.1) 16.8 (49.0) ByT5 (YT) 6.8 (42.2) 18.1 (50.8) ByT5 (YT+FS) 6.3 (42.1) 17.8 |
| 8 | 20.903 | 2201.13242v2 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | The last important parameter in (2) is the learning rate η. It controls how much the model parameters have to be updated. Low values of η ensure smooth monotoni |
| 9 | 20.027 | 2022.coling-1.309 | A Finetuning Details | The experiments were carried out in a single NVIDIA A100 80GB GPU. We use the Adafactor optimizer (Shazeer and Stern, 2018) with a constant learning rate of 10  |
| 10 | 20.027 | 2209.11035v1 | A Finetuning Details | The experiments were carried out in a single NVIDIA A100 80GB GPU. We use the Adafactor optimizer (Shazeer and Stern, 2018) with a constant learning rate of 10  |

### dense: ByT5 Adafactor learning rate warmup

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.825 | 2201.13242v1 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | The last important parameter in (2) is the learning rate η. It controls how much the model parameters have to be updated. Low values of η ensure smooth monotoni |
| 2 | 0.807 | 2201.13242v2 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | The last important parameter in (2) is the learning rate η. It controls how much the model parameters have to be updated. Low values of η ensure smooth monotoni |
| 3 | 0.799 | 2201.13242v2 | 4 Our Methodology › 4.3 Training Hyperparameters › 4.3.3 Learning Rate | Sometimes, better results can be achieved by scheduling learning rate values during the training. There is, typically, the so-called warm-up period in the begin |
| 4 | 0.778 | 2024.tacl-1.22 | A Hyperparameters | We train models using the AdaFactor (Shazeer and Stern, 2018) optimizer with 4000 warmup batches and a final constant learning rate of 1e-4. We batch by # of to |
| 5 | 0.778 | 2302.14220v3 | A Hyperparameters | We train models using the AdaFactor (Shazeer and Stern, 2018) optimizer with 4000 warmup batches and a final constant learning rate of 1e-4. We batch by # of to |
| 6 | 0.775 | 2022.tacl-1.17 | 6 Ablation Study › 6.4 Character Vocabulary | Table 9: Pre-training speed and computation of mT5 vs. ByT5. Left: Sequences per second pre-training on a TPUv3-64 device. Right: Total einsum operations for a  |
| 7 | 0.771 | 2203.09963v1 | 4 Methods › 4.3 Training Details | To train the models, we used a GeForce RTX 2080 Ti GPU. Following the best practices with the T5 family of models [15,18,30,31], we used the total batch size (n |
| 8 | 0.762 | 2410.03730v3 | A Appendix › A.2 Training Ablation Experiments | Adan (4× base LR): replace the AdamW optimizer with the Adan optimizer [57], using the baseline's learning rate multiplied by 4. The increased learning rate was |
| 9 | 0.761 | 2105.13626v3 | 7 Speed Comparisons | Table 9 compares the pre-training FLOPs of ByT5 vs. mT5, as well as the pre-training speed on fixed hardware, as sequences per second with sequence length of 10 |
| 10 | 0.761 | 2022.tacl-1.17 | 7 Speed Comparisons | Table 9 compares the pre-training FLOPs of ByT5 vs. mT5, as well as the pre-training speed on fixed hardware, as sequences per second with sequence length of 10 |

## vitamin-d

> How much vitamin D should an adult take each day?

Drafter's reading: No Chunk is about nutrition; the nearest is a maths word problem that mentions Vitamin Water.

### bm25: How much vitamin D should an adult take each day?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 19.811 | 2604.22709v1 | B Generative Reward Model Prompt › Verbal CoT | Close with warmth and openness. Invite them to share their feelings or let you know how you can make things right. Ending with a lighthearted or affectionate re |
| 2 | 19.811 | 2604.22709v2 | B Generative Reward Model Prompt › Verbal CoT | Close with warmth and openness. Invite them to share their feelings or let you know how you can make things right. Ending with a lighthearted or affectionate re |
| 3 | 18.633 | 2404.05892v1 | 5. Continue this process: › The day before two days after the day before tomorrow is Saturday. What day is it today? Please explain your answer in detail. | To solve this problem, we can use the given information to construct a logical statement and then apply the principle of transitivity to reach the desired concl |
| 4 | 18.633 | 2404.05892v4 | 5. Continue this process: › The day before two days after the day before tomorrow is Saturday. What day is it today? Please explain your answer in detail. | To solve this problem, we can use the given information to construct a logical statement and then apply the principle of transitivity to reach the desired concl |
| 5 | 18.384 | 2407.03232v1 | C Other Template Modification Experiments › C.2 Impact of Modification Position | An adversary with full access to the template may insert a token at any position. We measure the impact of the inserted token's location on attack success. Usin |
| 6 | 18.179 | 2602.03195v1 | 6. Experiment › 6.4. Comparison with Explicit Selector Policy for Token Selection › Contextual text Promising tokens | A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take? Answer: It takes 2/2=1 bolt of white fiber. [Total, It, |
| 7 | 18.179 | 2602.03195v2 | 6. Experiment › 6.4. Comparison with Explicit Selector Policy for Token Selection › Contextual text Promising tokens | A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take? Answer: It takes 2/2=1 bolt of white fiber. [Total, It, |
| 8 | 16.974 | 2606.15521v1 | A.6 GSM8K Python | Inspired by previous work [Chowdhery et al., 2023], we also evaluate a code-mediated variant of GSM8K in which each word problem is converted into a Python func |
| 9 | 16.317 | 2411.06096v2 | 4 Debiasing length normalization in minimal pairs › 4.2 Goal of debiasing length normalization | An ideal f will generate similar model predictions no matter how the length varies between two sentences in a pair. We take the accuracy on split D = as referen |
| 10 | 16.084 | 2403.05434v2 | 5 Conclusion › Dataset Language covered Example | Arabic, Bengali, Telugu, Thai, Swahili, Chinese Question: Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for he |

### dense: How much vitamin D should an adult take each day?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.614 | 2502.03275v2 | E Interpreability Examples › Example Generation of Our Latent Approach | Prompt: In a 8 fluid ounce bottle of Vitamin Water, there are 125 calories. How many calories would be contained in a 12 fluid ounce bottle? Express your answer |
| 2 | 0.604 | 2603.15644v1 | 4 Discussion | Any antifungal 86729 51130 2142 2.47 Any chemotherapy 83359 50997 3092 3.71 Any antiepileptics 78305 48262 6578 8.40 Any glucocorticoid 67347 40508 14145 21.00  |
| 3 | 0.601 | 2603.15644v1 | 4 Discussion | Low mean platelet volume 83497 49309 7682 9.20 High fibrinogen 86881 50852 2074 2.39 Low fibrinogen 84828 49769 1568 1.85 High partial thromboplastin time 84523 |
| 4 | 0.594 | 2402.12030v1 | A Legend of Confucius › Does the leukocyte count correlate with the severity of injury | Figures from the British Defence Dental Services reveal that serving personnel in the British Army have a persistently lower level of dental fitness than those  |
| 5 | 0.594 | 2405.04163v1 | B Experimental Results › B.2 Human Evaluation | The annotations were conducted on the Prolific 10 platform using 30 participants in total. Each participant was shown 10 random samples from a pool of 100 summa |
| 6 | 0.594 | 2025.findings-acl.1179 | B Results | Reference Summary (OOV Concentration: 17.72%) A comparative randomized controlled trial with multiple crossovers involving 33 children found that a self-hypnosi |
| 7 | 0.593 | 2603.15644v1 | 4 Discussion | Task Total Admissions Total Patients Positive Cases Prevalence (%) MRI head 85777 50391 5237 6.11 MRI whole body 87441 51178 158 0.18 PET 87444 51182 190 0.22 L |
| 8 | 0.592 | 2405.04163v2 | B Experimental Results › B.2 Human Evaluation | The annotations were conducted on the Prolific § platform using 30 participants in total. Each participant was shown 10 random samples from a pool of 100 summar |
| 9 | 0.589 | 2603.15644v1 | Supplementary Material | 0.928 0.912 0.919 0.926 0.924 Low albumin 0.879 0.888 0.885 0.888 0.874 0.884 0.880 0.888 High alanine transaminase 0.859 0.870 0.879 0.882 0.858 0.866 0.874 0. |
| 10 | 0.587 | 2510.15346v1 | 1 INTRODUCTION › Answer | Terry eats 2 yogurts a day. They are currently on sale at 4 yogurts for $5.00. How much does he spend on yogurt over 30 days? |

### bm25: vitamin D recommended daily intake adults

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 14.983 | 2608.03999v1 | I Extended Baseline Comparisons | Figure8: The listening-study interface (captures of the deployed page). Left: intake. Middle: a trial. Right: the closing screen. |
| 2 | 12.311 | 2412.11704v1 | C Analysis and Discussion › C.2 Additional Qualitative Analysis | There are more than 400,000 reported cases in the United States. It is the leading cause of death in young and middle-aged adults. (MS). In Tamil There are more |
| 3 | 11.882 | 1810.01480v1 | 4 Experiments › ASPEC Analysis. | As shown in Table 5, it is mostly the Hiragana letter 'き' that starts the seg-Ref in social groups of animals , the juveniles always look different than the adu |
| 4 | 11.834 | 2408.07065v1 | { } | In the last 3 months, over 80 arrestees were released from the Central Booking facility without being formally charged. { booking } In April this year, a tempor |
| 5 | 11.345 | 2510.15346v1 | C CORRECTNESS OF ENSEMBLE DISTRIBUTION VERIFICATION › UniTE + SAFE | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption cost: Ter |
| 6 | 11.274 | 2510.15346v2 | C CORRECTNESS OF ENSEMBLE DISTRIBUTION VERIFICATION › UniTE + SAFE | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption cost: Ter |
| 7 | 11.265 | 2105.09680v1 | 2 Source Corpora › 2.2 Selected Corpora › Acrofan News (ACROFAN) | ACROFAN is a corpus consisting of news articles released by ACROFAN. Most articles are press release-like in that they often introduce new products or events of |
| 8 | 11.265 | 2105.09680v4 | 2 Source Corpora › 2.2 Selected Corpora › Acrofan News (ACROFAN) | ACROFAN is a corpus consisting of news articles released by ACROFAN. Most articles are press release-like in that they often introduce new products or events of |
| 9 | 11.098 | 2501.10582v3 | 5 Optimizing language models for AAC › 5.4 Domain adaptation procedure | Adaptation data Fine-tuning Perplexity type steps Written Spoken Avg ---2.41 2.19 2.30 C4+Sub+BOLT+Daily full 1 2.30 2.08 2.19 C4 )Sub )BOLT )Daily full 4 2.16  |
| 10 | 10.867 | 2018.iwslt-1.25 | 4. Experiments › Analysis of Segmentation and Outputs. | While this letter also occurs as singleton (183× in the dev set, vs. 52× as part of a learned segment), and is frequent in the training set (239k), it is not th |

### dense: vitamin D recommended daily intake adults

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.636 | 2403.01858v3 | G Detailed results of various models on different benchmarks | 問題：人體的食物來源多樣，食物的營養成分包含有機物質及無機物質，而食物加工 過程有時會加入特定食品添加物，我國政府為了替民眾的食品安全把關，訂有食品安 全衛生管理法及食品安全衛生管理法施行細則，下列相關敘述何者最正確？ Question: The human body has a variety of food sou |
| 2 | 0.624 | 2408.07065v1 | { } | { box jellyfish, estuaries, October, April, October, April } Sharks do exist, however they rarely attack humans. Most sharks are scared of humans and would swim |
| 3 | 0.622 | 2402.12030v1 | A Legend of Confucius › Does the leukocyte count correlate with the severity of injury | Figures from the British Defence Dental Services reveal that serving personnel in the British Army have a persistently lower level of dental fitness than those  |
| 4 | 0.622 | 2510.13481v2 | 4 EVALUATION › 4.1 CHALLENGES IN MMLU: A FOCUS ON ENGLISH, ARABIC, AND NEW SAUDI CULTURE DATASET › 4.1.1 ARB-MMLU: DIAGNOSTIC CHALLENGES AND CORRECTIVE APPROACHES › Stage 1: Mapping and Alignment | Topic Questions (%) Answers (%) Overall (%) Anatomy 80.65 83.87 74.19 Astronomy 88.35 95.15 84.47 Business Ethics 87.63 89.69 84.54 Clinical Knowledge 91.67 91. |
| 5 | 0.619 | 2510.13481v1 | 4 EVALUATION › 4.1 CHALLENGES IN MMLU: A FOCUS ON ENGLISH, ARABIC, AND NEW SAUDI CULTURE DATASET › 4.1.1 ARB-MMLU: DIAGNOSTIC CHALLENGES AND CORRECTIVE APPROACHES › Stage 1: Mapping and Alignment | Topic Questions (%) Answers (%) Overall (%) Anatomy 80.65 83.87 74.19 Astronomy 88.35 95.15 84.47 Business Ethics 87.63 89.69 84.54 Clinical Knowledge 91.67 91. |
| 6 | 0.618 | 2311.09325v1 | 5 Results › 5.1 Main result: how temperature-scaled surprisal improves human reading time prediction | Table 1 (5.1 Main result: how temperature-scaled surprisal improves human reading time prediction): Models Original ∆ llh Best T Best ∆ llh ∆ llh improvement (% |
| 7 | 0.617 | 2210.14642v2 | 3 Results › 3.3 Case studies | In our literature research on the ALDH1 enzyme family, NCT-501 molecule, which shows in vitro activity against cisplatin-resistant Cal-27 as well as head and ne |
| 8 | 0.615 | 2311.09325v1 | 5 Results › 5.1 Main result: how temperature-scaled surprisal improves human reading time prediction | Table 1 (5.1 Main result: how temperature-scaled surprisal improves human reading time prediction): Models Original ∆ llh Best T Best ∆ llh ∆ llh improvement (% |
| 9 | 0.614 | 2022.jeptalnrecital-taln.34 | 2 Extraction d'événements épidémiologiques › 2.3 Évaluation des modèles › Modèle | TABLE 4 -Corrélation (p-value) entre les scores F 1 et les caractéristiques du lexique de chaque langue. Nous observons dans le Tableau 4 de fortes corrélations |
| 10 | 0.614 | 2402.00786v1 | 6 Foundation Model Transparency Index › Risk Assessment. | Our extensive evaluation process and the small scale of the CroissantLLM models allow us to confidently release all artifacts in our efforts of transparency wit |

### bm25: dietary supplement dosage IU per day

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 14.924 | 2406.14312v1 | 3 Results › 3.1 Tokeniser Evaluation Design and Datasets › Clinical research article classification | Table 2 (Clinical research article classification): Results of ClinicalBERT models employing BERT Tokeniser and K-Tokeniser on clinical concepts and relation ex |
| 2 | 13.387 | 2510.15346v1 | 1 INTRODUCTION › Problem | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption in terms  |
| 3 | 13.341 | 2510.15346v1 | C CORRECTNESS OF ENSEMBLE DISTRIBUTION VERIFICATION › UniTE | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption in terms  |
| 4 | 13.187 | 2510.15346v2 | 1 INTRODUCTION › Problem | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption in terms  |
| 5 | 13.142 | 2510.15346v2 | C CORRECTNESS OF ENSEMBLE DISTRIBUTION VERIFICATION › UniTE | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption in terms  |
| 6 | 13.129 | 2403.05434v2 | 5 Conclusion › Dataset Language covered Example | Arabic, Bengali, Telugu, Thai, Swahili, Chinese Question: Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for he |
| 7 | 13.108 | 2404.09492v1 | 1 Introduction | Large language models (LLMs) have demonstrated impressive performance across various natural language processing tasks (Anil et al., 2023;Touvron et al., 2023;C |
| 8 | 12.928 | 2410.01487v1 | B Full BLiMP scores | 51.19% supplement_qa_congruence_easy 48.44% 54.69% 56.25% 57.81% supplement_qa_congruence_tricky 26.67% 39.39% 25.45% 25.45% supplement_subject_aux_inversion 78 |
| 9 | 12.784 | 1804.06506v1 | 3 Proposed Architecture › 3.1 The Embedded Morphology Table › stem-c stem-c w-space stem-c stem-c stem-c stem-c stem-c stem-c stem-c siz-c siz-c siz-c lik-c lik-c lik-c w-space stem-c stem-c stem-c stem-c | Figure 1: The target label that each output channel is supposed to predict when generating the Turkish sequence 'bu 1 terbiyesizlik 2 için 3 ' meaning 'because  |
| 10 | 12.784 | N18-1006 | 3 Proposed Architecture › 3.1 The Embedded Morphology Table › stem-c stem-c w-space stem-c stem-c stem-c stem-c stem-c stem-c stem-c siz-c siz-c siz-c lik-c lik-c lik-c w-space stem-c stem-c stem-c stem-c | Figure 1: The target label that each output channel is supposed to predict when generating the Turkish sequence 'bu 1 terbiyesizlik 2 için 3 ' meaning 'because  |

### dense: dietary supplement dosage IU per day

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.669 | 2604.16775v1 | 6. Conclusion | Table 3 continued from previous page Outcome Definition and source field(s) ICU admission (Experiments 1-2; icu/icustays) Derived binary label: at least one lin |
| 2 | 0.666 | 2603.15644v1 | Supplementary Material | 0.928 0.912 0.919 0.926 0.924 Low albumin 0.879 0.888 0.885 0.888 0.874 0.884 0.880 0.888 High alanine transaminase 0.859 0.870 0.879 0.882 0.858 0.866 0.874 0. |
| 3 | 0.665 | 2604.16775v1 | 6. Conclusion | 220052 or 220181 is <65 mmHg, or minimum post-24h systolic blood pressure from icu/chartevents.itemid 220050, 220179, or 225309 is <90 mmHg. Regression outcomes |
| 4 | 0.663 | 2604.16775v1 | 3. Methods | Table 3 (3. Methods): Maximum post-24h heart rate from icu/chartevents.itemid 220045. continued from previous page Outcome \| Definition and source field(s) Maxi |
| 5 | 0.663 | 2603.15644v1 | Supplementary Material | 0.902 0.884 0.890 0.896 0.896 High partial thromboplastin time 0.890 0.897 0.898 0.897 0.886 0.888 0.895 0.897 High international normalized ratio 0.866 0.873 0 |
| 6 | 0.661 | 2603.15644v1 | 4 Discussion | Low mean platelet volume 83497 49309 7682 9.20 High fibrinogen 86881 50852 2074 2.39 Low fibrinogen 84828 49769 1568 1.85 High partial thromboplastin time 84523 |
| 7 | 0.654 | 2510.15346v2 | C CORRECTNESS OF ENSEMBLE DISTRIBUTION VERIFICATION › UniTE + SAFE | To determine how much Terry spends on yogurt over 30 days, we can break down the problem into several steps: 1. Calculate the daily yogurt consumption cost: Ter |
| 8 | 0.653 | 2603.15644v1 | Supplementary Material | 0.874 0.876 0.883 High creatinine kinase 0.901 0.904 0.909 0.923 0.872 0.895 0.897 0.910 High C-reactive protein 0.844 0.850 0.851 0.859 0.835 0.854 0.842 0.851 |
| 9 | 0.653 | 2603.15644v1 | Supplementary Material | Supplementary Figure S1. Cohort Construction for Pretraining and Downstream Evaluation Task-specific exclusions (e.g., outcomes occurring before prediction time |
| 10 | 0.653 | 2603.15644v1 | 4 Discussion | Any antifungal 86729 51130 2142 2.47 Any chemotherapy 83359 50997 3092 3.71 Any antiepileptics 78305 48262 6578 8.40 Any glucocorticoid 67347 40508 14145 21.00  |

## world-cup-2018

> Which country won the 2018 FIFA World Cup?

Drafter's reading: No Chunk is about football.

### bm25: Which country won the 2018 FIFA World Cup?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 32.945 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 2 | 24.938 | 2607.17689v1 | 4 Evaluation › 4.2 Machine Translation › Data | Instance Analysis It is difficult to find examples in well-established translation datasets where false friends occur in contexts that can throw Englishto-L2 tr |
| 3 | 21.197 | 2106.06297v1 | 3 DYNAMIC LANGUAGE MODELING › 3.5 Token Semantic Shift | We use country hashtags in our Country Hashtag Prediction task as a case study. We pick 1,000 most frequently co-occurring words for the hashtags from 2014 and  |
| 4 | 18.432 | 2205.05093v1 | 4 Richer Countries are Most Distinct in Embedding Space | Table 5 (4 Richer Countries are Most Distinct in Embedding Space): OLS Regression Results: Using training data frequency (logged) to predict the average cosine  |
| 5 | 17.199 | 2601.22710v1 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 6 | 17.199 | 2601.22710v2 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 7 | 16.501 | 2606.09861v1 | E Broader Impacts | Table 9 (E Broader Impacts): Full forecasting MASE (lower is better) on GIFT-Eval. Task \| Naive \| Seasonal-Naive \| Auto-Theta \| Auto-Arima \| Crossformer \| DLine |
| 8 | 16.264 | 2603.22774v3 | I. INTRODUCTION | • Deployment relevance. We analyze 4.65 million realworld cluster allocation records to show that CPU underprovisioning is common in practice, and demonstrate t |
| 9 | 16.198 | 2606.09861v1 | E Broader Impacts | Table 8 (E Broader Impacts): Full forecasting MAPE (lower is better) on GIFT-Eval. During aggregation, N/A values are replaced with 1.0. Task \| Naive \| Seasonal |
| 10 | 16.198 | 2606.09861v1 | E Broader Impacts | Table 8 (E Broader Impacts): Full forecasting MAPE (lower is better) on GIFT-Eval. During aggregation, N/A values are replaced with 1.0. Task \| Naive \| Seasonal |

### dense: Which country won the 2018 FIFA World Cup?

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.618 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 2 | 0.598 | 2408.07065v1 | 4 Experiments › 4.3 Results › Reference | Tournament top seeds South Africa started on the right note when they had a comfortable 26 -00 win against 5th seeded Zambia. T5 (YT) In South Africa, there is  |
| 3 | 0.592 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { Namibia, parliamentary, Hifikepunye Pohamba } 0 The ruling party, South West Africa People's Organisation (SWAPO), also retained a majority in the parliamenta |
| 4 | 0.590 | 2103.06874v4 | 4 Experiments › 4.2 TYDI QA Results › Question Passage Answer | Chelsea ina milikiwa na nani? Kwa kawaida Chelsea huvaa jezi ya blu, kaptula blu na soksi nyeupe. Nembo ya klabu imebadilishwa mara nyingi kulingana na wakati n |
| 5 | 0.585 | 2408.07065v1 | { } | For the Springboks, it ended a five-match losing streak. { Springboks } It was the final match for the All Blacks, who had already won the trophy two weeks ago. |
| 6 | 0.582 | 2022.tacl-1.5 | 4.2 TYDI QA Results | \| the club's appearance. The current emblem shows a picture of a \| lion carrying a spear. Since July 2003, Chelsea has been owned \| by Russian billionaire Roman |
| 7 | 0.581 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { proton, electron, atom } The games kicked off at 10:00am with great weather and apart from mid morning drizzle which quickly cleared up, it was a perfect day  |
| 8 | 0.579 | 2106.06297v1 | A APPENDIX A.A Vocabulary Shift Analysis › A.G Country Hashtag Prediction Task | For the Country Hashtag Prediction task, we collect 16 popular country hashtags (#australia, #canada, #china, #india, #iran, #iraq, #israel, #italy, #japan, #ni |
| 9 | 0.578 | 2410.10665v1 | 4 Methodology › 4.1 Linguistic and Socio-economic Indicators › 4.1.1 Number of Speakers for Each Language | Ethnologue is an extensive database offering in-depth details about languages spoken globally [21]. It notably includes data on the number of speakers per count |
| 10 | 0.573 | 2106.06297v1 | 3 DYNAMIC LANGUAGE MODELING › 3.5 Token Semantic Shift | We use country hashtags in our Country Hashtag Prediction task as a case study. We pick 1,000 most frequently co-occurring words for the hashtags from 2014 and  |

### bm25: 2018 FIFA World Cup winner

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 26.761 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 2 | 24.640 | 2607.17689v1 | 4 Evaluation › 4.2 Machine Translation › Data | Instance Analysis It is difficult to find examples in well-established translation datasets where false friends occur in contexts that can throw Englishto-L2 tr |
| 3 | 16.984 | 2601.22710v1 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 4 | 16.984 | 2601.22710v2 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 5 | 16.501 | 2606.09861v1 | E Broader Impacts | Table 9 (E Broader Impacts): Full forecasting MASE (lower is better) on GIFT-Eval. Task \| Naive \| Seasonal-Naive \| Auto-Theta \| Auto-Arima \| Crossformer \| DLine |
| 6 | 16.198 | 2606.09861v1 | E Broader Impacts | Table 8 (E Broader Impacts): Full forecasting MAPE (lower is better) on GIFT-Eval. During aggregation, N/A values are replaced with 1.0. Task \| Naive \| Seasonal |
| 7 | 16.198 | 2606.09861v1 | E Broader Impacts | Table 8 (E Broader Impacts): Full forecasting MAPE (lower is better) on GIFT-Eval. During aggregation, N/A values are replaced with 1.0. Task \| Naive \| Seasonal |
| 8 | 15.353 | 2606.09861v1 | E Broader Impacts | Table 7 (E Broader Impacts): Full forecasting CRPS (lower is better) on GIFT-Eval. The Task column follows the format "Dataset / Frequency / Prediction Term". T |
| 9 | 15.353 | 2606.09861v1 | E Broader Impacts | Table 7 (E Broader Impacts): Full forecasting CRPS (lower is better) on GIFT-Eval. The Task column follows the format "Dataset / Frequency / Prediction Term". T |
| 10 | 13.466 | 2411.06096v1 | 2 Related work | RELATIVIZATION 4 我所厌恶的那位领导来了。 我所厌恶他的那位领导来了。 The leader I despise came. The leader I despise him came. TOPICALIZATION 4 他在喝一杯咖啡。 一杯咖啡他在喝。 He is drinking a cup of |

### dense: 2018 FIFA World Cup winner

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.646 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 2 | 0.637 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations | Table 10 (D Complete FLEURS-ASL-FS Annotations): Complete set of FLEURS-ASL-FS annotations.Each reference sentence is paired with a multiset of human-annotated  |
| 3 | 0.630 | 2103.06874v4 | 4 Experiments › 4.2 TYDI QA Results › Question Passage Answer | Chelsea ina milikiwa na nani? Kwa kawaida Chelsea huvaa jezi ya blu, kaptula blu na soksi nyeupe. Nembo ya klabu imebadilishwa mara nyingi kulingana na wakati n |
| 4 | 0.628 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | Singer, Raju Khandelwal was accompanying him. { Sanju Sharma, Jai Shankar Choudhary, chhappan bhog bhajan, Raju Khandelwal } Then, Lakkha Singh took the lead in |
| 5 | 0.626 | 2022.tacl-1.5 | 4.2 TYDI QA Results | \| the club's appearance. The current emblem shows a picture of a \| lion carrying a spear. Since July 2003, Chelsea has been owned \| by Russian billionaire Roman |
| 6 | 0.625 | 2403.05519v1 | 4 METHODOLOGY › 4.5 Training › 4.5.2 Language model Fine-tuning. | Word level: িতন মাস দীঘ সময় ধের ধের যাওয়া এক ধরেণর ভয়ংকর খলা । এ ট এক ট song খলা যােক সাধারণত সাধারণভােব বলা হয় হাফ -অফ খলা । এই খলা উৎসেবর সময় রােতর বলা রােতর  |
| 7 | 0.615 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { Anna Jochemsen, Super-G, Katja Saarinen } 0 Australia's Mitchell Gourley finished eleventh in the men's standing Super-G. Czech competitor Oldrich Jelinek fin |
| 8 | 0.613 | 2306.13651v1 | A Appendix › A.2 Toxicity | Example: Figure 15 shows an example of the the original x and the transformed x ′ for the toxicity experiments. Original (x): Lionel Andrés Messi is an Argentin |
| 9 | 0.613 | 2510.18840v1 | G PERTURBATION IMPLEMENTATION DETAILS › Visual Attack. | In line with Eger et al. (2019), each of the 26 uppercase and lowercase letters is substituted with a visually similar letter at varying probabilities p ∈ {0.2, |
| 10 | 0.612 | 2024.emnlp-main.543 | E Model Vocabularies | Table 5 (E Model Vocabularies): Llama-3-8b Wikipedia results (892 sequences Token Sequence \| n ct ψ 1992 births 19th-century dehydrogen Swahili Chuck Liddell it |

### bm25: football World Cup final France Croatia

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 25.894 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 2 | 21.728 | 2607.17689v1 | 4 Evaluation › 4.2 Machine Translation › Data | Instance Analysis It is difficult to find examples in well-established translation datasets where false friends occur in contexts that can throw Englishto-L2 tr |
| 3 | 21.543 | 2408.07065v1 | { } | { flu, strain, H5N1, Lyon, marsh, H5N1 } France is the seventh country in the European Union to suffer this virus; following Austria, Germany, Slovenia, Bulgari |
| 4 | 18.219 | 2106.06297v1 | 3 DYNAMIC LANGUAGE MODELING › 3.3 Vocabulary Composition for Hashtags | As hashtags often mark the topics in the posts, we believe that understanding hashtags is key to the language model quality. Hashtags can consist of a single wo |
| 5 | 17.995 | 2106.06297v1 | 3 DYNAMIC LANGUAGE MODELING › 3.5 Token Semantic Shift | We use country hashtags in our Country Hashtag Prediction task as a case study. We pick 1,000 most frequently co-occurring words for the hashtags from 2014 and  |
| 6 | 16.984 | 2601.22710v1 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 7 | 16.984 | 2601.22710v2 | B Formalization of Alien Language and Translator › B.2 Alien Language as a Vocabulary-Level Bijection | Toy example. Suppose we want to pair a token come with a different-looking but semantically related token. For each candidate, we combine semantic closeness (em |
| 8 | 16.322 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { Dillon, km, miles, Butte, km, miles } The strain of bird flu lethal to humans, H5N1, has been confirmed to have infected a dead wild duck, found on Monday, in |
| 9 | 16.308 | 2024.emnlp-main.543 | E Model Vocabularies | Table 5 (E Model Vocabularies): Llama-3-8b Wikipedia results (892 sequences Token Sequence \| n ct ψ 1992 births 19th-century dehydrogen Swahili Chuck Liddell it |
| 10 | 15.693 | 2601.09089v1 | A.5 Safety-style Masking › Expect Output: | <answer> \| Name \| Age \| Occupation \| City \| Country \| \|- --------\|-----\|------------\|-----------\|----------- \| \| Alice \| 28 \| Engineer \| Boston \| USA \| \| Bob \|  |

### dense: football World Cup final France Croatia

| Rank | Score | Pinned id | Section | Text |
|---:|---:|---|---|---|
| 1 | 0.652 | 2408.07065v1 | { } | For the Springboks, it ended a five-match losing streak. { Springboks } It was the final match for the All Blacks, who had already won the trophy two weeks ago. |
| 2 | 0.651 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { alpine, stiff } Think of the skiing route as of a similar hiking route. { } In good conditions you will be able to cover somewhat greater distances than walki |
| 3 | 0.636 | 2402.00786v1 | 6 Foundation Model Transparency Index › Model. | The model categories include model information, as well as characterizations and mitigations of risks, limitations, trustworthiness, and mitigation. CroissantLL |
| 4 | 0.617 | 2607.17689v1 | 4 Evaluation › 4.2 Machine Translation › Data | Instance Analysis It is difficult to find examples in well-established translation datasets where false friends occur in contexts that can throw Englishto-L2 tr |
| 5 | 0.617 | 10.26794/3033-7097-2025-1-3-19-29 | По языковой и доменной специфике. | Если же текст крайне короткий, то ограничение на 512 или 1024 токена вообще не играет роли, но стоит учитывать, что модель все равно будет работать с фиксирован |
| 6 | 0.614 | 10.26907/1562-5419-2026-29-2-546-564 | РЕЗУЛЬТАТЫ И ИХ ОБСУЖДЕНИЕ | При этом выбор между HuggingFace-и SentencePiece-реализациями также должен учитывать требования к скорости предобработки и интеграции в рабочий пайплайн. Наконе |
| 7 | 0.614 | 10.26794/3033-7097-2025-1-3-19-29 | По единице разбиения. | токенов, чтобы уменьшить среднюю длину представления документов финансового корпуса, несмотря на рост параметров модели. |
| 8 | 0.613 | 2408.07065v1 | D Complete FLEURS-ASL-FS Annotations › { } | { Anna Jochemsen, Super-G, Katja Saarinen } 0 Australia's Mitchell Gourley finished eleventh in the men's standing Super-G. Czech competitor Oldrich Jelinek fin |
| 9 | 0.612 | 10.26794/3033-7097-2025-1-3-19-29 | По языковой и доменной специфике. | На практике разбиение Unigram может быть менее интерпретируемым, поскольку основывается на глобальной вероятностной модели. Э.Ф. Болтачев, М.П. Фархадов, А.И. Т |
| 10 | 0.611 | 10.26907/1562-5419-2026-29-2-546-564 | РЕЗУЛЬТАТЫ И ИХ ОБСУЖДЕНИЕ | Одновременно в распределениях фиксируются повторяющиеся символьные пары (например, ('ӯ', 'ӯ')), что может отражать фонетико-орфографические особенности таджикск |
