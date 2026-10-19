# Corpus funnel and channel report

Written by `collect`, `fetch` and `index` from the manifest: judge `tev1:4b@4d24c6f6d61a48d9b72902f4805c5f1da53010736b834b0372377fb4bb7e53d3@0.40.5` at threshold 0.8. One row per Edition.

## Funnel

| Stage | Editions |
| --- | ---: |
| Discovered | 26386 |
| Rejected by the rules | 19185 |
| Withdrawn from arXiv | 15 |
| Not a paper | 152 |
| Rejected by the judge | 4329 |
| File belongs to another Edition | 0 |
| Pending a judge verdict | 0 |
| Included | 2705 |
| With full text | 2067 |
| Indexed | 2066 |
| With full text, not indexed | 1 |
| No open PDF | 636 |
| Still to fetch | 2 |

## With full text, not indexed

A file failed the parse quality gate (see the parse report), or `index` hasn't run since the Edition was fetched.

- `2508.13058v1`

## Works

Included Editions are one Work when they share an identifier (arXiv id, DOI, ACL ID), a file's bytes, or a title and first-author surname. A Work of several Editions is counted by the weakest signal it needed.

| | Editions or Works |
| --- | ---: |
| Included Editions | 2705 |
| Works | 2393 |
| Works of several Editions, joined by an identifier | 260 |
| Works of several Editions, joined by file bytes | 0 |
| Works of several Editions, joined by title and first author | 50 |
| Canonical Edition is a venue Edition | 1174 |
| Canonical Edition is a preprint | 1219 |
| Surveys | 15 |
| Suspected pairs | 5 |

### Suspected pairs

Works with the same title whose first authors differ, or are missing on one side. They are never joined.

| Editions | Title | First author | Editions | Title | First author |
| --- | --- | --- | --- | --- | --- |
| `10.5281/zenodo.17945025` | When Multilingual Evaluation Assumptions Fail: Tokenization Effects Across Scripts | K H, Manodnya | `2026.loreslm-1.4` | When Multilingual Evaluation Assumptions Fail: Tokenization Effects Across Scripts | Manodyna K H |
| `10.5281/zenodo.18148445` | Racka: Efficient Hungarian LLM Adaptation on Academic Infrastructure | Dávid Márk Nemeskey | `2601.01244v2` | Racka: Efficient Hungarian LLM Adaptation on Academic Infrastructure | Zsolt Csibi |
| `1511.04586v1` | Character-based Neural Machine Translation | Wang Ling | `1603.00810v3`, `P16-2058` | Character-based Neural Machine Translation | M. Costa-jussà |
| `2202.13590v2` | LCP-dropout: Compression-based Multiple Subword Segmentation for Neural Machine Translation | Keita Nonaka | `6acddaf40e5cf53e1612bf8ce2c34bb0c997f169` | LCP-dropout: Compression-based Multiple Subword Segmentation for Neural Machine Translation | Kazutaka Yamanouchi |
| `2608.18062v3` | TokEval: A Tokenizer Evaluation Suite | Clara Meister | `ba0a8743d2dc10a09f5425953deaa0d3677afadc` | TokEval: A Tokenizer Evaluation Suite |  |

## Rule rejections by pattern

| Pattern | Editions |
| --- | ---: |
| crypto-assets | 87 |
| kv-cache | 49 |
| missing-required-term | 18616 |
| other-modality-tokenizer | 92 |
| token-reduction | 341 |

## By source

A Seed and its citation hops count as the source `seeds`.

| Source | Editions | Included | Found by no other | of those: pass the rules | included | pending |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arxiv | 5640 | 1417 | 3594 | 1614 | 256 | 0 |
| openalex | 1588 | 845 | 493 | 410 | 176 | 0 |
| seeds | 17285 | 1842 | 14995 | 1322 | 430 | 0 |
| semantic-scholar | 6648 | 1511 | 4169 | 1310 | 191 | 0 |

## By Discovery channel

| Channel | Editions | Included | Found by no other | of those: pass the rules | included | pending |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arxiv:arxiv-byte-level-abstracts | 1066 | 420 | 484 | 483 | 52 | 0 |
| arxiv:arxiv-byte-level-titles | 201 | 138 | 7 | 7 | 1 | 0 |
| arxiv:arxiv-subword-abstracts | 1028 | 698 | 90 | 90 | 17 | 0 |
| arxiv:arxiv-subword-titles | 218 | 187 | 2 | 2 | 0 | 0 |
| arxiv:arxiv-tokenizer-titles | 3383 | 638 | 2400 | 423 | 110 | 0 |
| arxiv:arxiv-vocabulary-titles | 735 | 181 | 488 | 487 | 20 | 0 |
| openalex:openalex-subword-phrases | 1588 | 845 | 493 | 410 | 176 | 0 |
| seed-citations:bpe-dropout | 425 | 211 | 77 | 4 | 0 | 0 |
| seed-citations:bpe-suboptimal | 383 | 228 | 67 | 8 | 3 | 0 |
| seed-citations:byt5 | 881 | 279 | 400 | 40 | 8 | 0 |
| seed-citations:byte-latent-transformer | 188 | 94 | 49 | 8 | 2 | 0 |
| seed-citations:canine | 400 | 219 | 77 | 14 | 9 | 0 |
| seed-citations:code-tokenizer | 78 | 61 | 7 | 2 | 2 | 0 |
| seed-citations:focus | 88 | 64 | 6 | 0 | 0 | 0 |
| seed-citations:how-good-is-your-tokenizer | 553 | 246 | 173 | 21 | 7 | 0 |
| seed-citations:languages-cost | 276 | 148 | 61 | 2 | 1 | 0 |
| seed-citations:more-than-compression | 126 | 84 | 28 | 7 | 0 | 0 |
| seed-citations:open-vocabulary-survey | 265 | 118 | 87 | 17 | 3 | 0 |
| seed-citations:sennrich-bpe | 10584 | 1313 | 7224 | 481 | 111 | 0 |
| seed-citations:sentencepiece | 4923 | 692 | 2684 | 166 | 36 | 0 |
| seed-citations:subword-regularization | 1660 | 590 | 383 | 26 | 9 | 0 |
| seed-citations:tokenization-counts | 144 | 50 | 70 | 4 | 1 | 0 |
| seed-citations:tokenizer-choice | 159 | 86 | 38 | 4 | 3 | 0 |
| seed-citations:tokenizer-unfairness | 319 | 148 | 84 | 6 | 1 | 0 |
| seed-citations:vocabulary-scaling | 141 | 47 | 55 | 9 | 5 | 0 |
| seed-citations:wechsel | 142 | 63 | 46 | 2 | 0 | 0 |
| seed-citations:wordpiece | 1122 | 311 | 451 | 36 | 7 | 0 |
| seed-citations:zero-shot-tokenizer-transfer | 39 | 28 | 6 | 2 | 1 | 0 |
| seed-references:bpe-dropout | 42 | 14 | 9 | 0 | 0 | 0 |
| seed-references:bpe-suboptimal | 33 | 9 | 4 | 0 | 0 | 0 |
| seed-references:byt5 | 94 | 33 | 23 | 3 | 2 | 0 |
| seed-references:canine | 120 | 56 | 25 | 3 | 3 | 0 |
| seed-references:code-tokenizer | 48 | 22 | 6 | 0 | 0 | 0 |
| seed-references:focus | 75 | 16 | 23 | 2 | 0 | 0 |
| seed-references:how-good-is-your-tokenizer | 116 | 7 | 47 | 2 | 0 | 0 |
| seed-references:languages-cost | 107 | 26 | 41 | 1 | 0 | 0 |
| seed-references:more-than-compression | 60 | 37 | 12 | 0 | 0 | 0 |
| seed-references:open-vocabulary-survey | 264 | 126 | 82 | 1 | 0 | 0 |
| seed-references:sennrich-bpe | 46 | 3 | 29 | 7 | 0 | 0 |
| seed-references:sentencepiece | 23 | 5 | 0 | 0 | 0 | 0 |
| seed-references:subword-regularization | 40 | 5 | 11 | 0 | 0 | 0 |
| seed-references:tokenization-counts | 36 | 10 | 13 | 0 | 0 | 0 |
| seed-references:tokenizer-choice | 94 | 28 | 25 | 1 | 0 | 0 |
| seed-references:tokenizer-unfairness | 136 | 28 | 56 | 0 | 0 | 0 |
| seed-references:vocabulary-scaling | 76 | 13 | 30 | 2 | 0 | 0 |
| seed-references:wechsel | 73 | 4 | 31 | 0 | 0 | 0 |
| seed-references:zero-shot-tokenizer-transfer | 93 | 33 | 19 | 2 | 0 | 0 |
| seed:bpe-dropout | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:bpe-suboptimal | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:byt5 | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:byte-latent-transformer | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:canine | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:code-tokenizer | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:focus | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:how-good-is-your-tokenizer | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:languages-cost | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:more-than-compression | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:open-vocabulary-survey | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:sennrich-bpe | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:sentencepiece | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:subword-regularization | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:tokenization-counts | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:tokenizer-choice | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:tokenizer-unfairness | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:vocabulary-scaling | 1 | 1 | 0 | 0 | 0 | 0 |
| seed:wechsel | 2 | 2 | 0 | 0 | 0 | 0 |
| seed:wordpiece | 1 | 0 | 0 | 0 | 0 | 0 |
| seed:zero-shot-tokenizer-transfer | 1 | 1 | 0 | 0 | 0 | 0 |
| semantic-scholar:s2-arithmetic | 596 | 36 | 507 | 34 | 5 | 0 |
| semantic-scholar:s2-byte-level-models | 332 | 127 | 97 | 61 | 17 | 0 |
| semantic-scholar:s2-code | 516 | 34 | 415 | 37 | 5 | 0 |
| semantic-scholar:s2-multilingual-fairness | 200 | 99 | 105 | 69 | 13 | 0 |
| semantic-scholar:s2-nmt-subwords | 480 | 258 | 54 | 32 | 10 | 0 |
| semantic-scholar:s2-reasoning | 1208 | 65 | 923 | 72 | 15 | 0 |
| semantic-scholar:s2-spelling-and-characters | 579 | 80 | 460 | 112 | 18 | 0 |
| semantic-scholar:s2-subword-methods | 723 | 327 | 307 | 119 | 25 | 0 |
| semantic-scholar:s2-subword-phrases | 1281 | 739 | 54 | 34 | 11 | 0 |
| semantic-scholar:s2-token-artifacts | 83 | 24 | 47 | 8 | 3 | 0 |
| semantic-scholar:s2-vocabulary-adaptation | 934 | 146 | 759 | 470 | 27 | 0 |
| semantic-scholar:s2-vocabulary-size | 609 | 200 | 364 | 233 | 31 | 0 |

## What citation expansion adds

A Seed's own record counts as neither: it was picked by hand, not found.

| Found by | Editions | Included | Found by no keyword query | of those: included |
| --- | ---: | ---: | ---: | ---: |
| Keyword search | 11391 | 2275 | | |
| Citation expansion | 17284 | 1841 | 14995 | 430 |
