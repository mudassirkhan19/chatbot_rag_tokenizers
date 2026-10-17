# Parse report

Written by `parse`. The Chunks themselves are in the local parse cache, which is not committed.

## Parser

- Image: `grobid/grobid@sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd` (tag `0.9.1-crf`)
- GROBID version: 0.9.1

## Chunking config

- token_budget: `350`
- tokenizer: `google-bert/bert-base-uncased`
- tokenizer_revision: `86b5e0934494bd15c9632b12f734a8a67f723594`
- tokenizer_sha256: `ce64fce797c24f68df90b40a3f74f579b336a493db14bd583fd520ea0d8c9a98`
- min_sections: `2`
- min_body_characters: `2000`

## Quality gate

A file fails when GROBID errors or times out on it, when it has fewer than 2 Sections (the abstract counts as one), or when its Sections hold fewer than 2000 characters of text. A failed file gets no Chunks.

## Files

Numeric counts the text Chunks in which more than 35% of their words are numbers. Most hold the cells of a table GROBID missed. They are kept as text Chunks.

| Pinned id | sha256 | Status | Sections | Chunks | Tables | Captions | Numeric |
|---|---|---|---:|---:|---:|---:|---:|
| 1508.07909v1 | `1c3665998df191f8a63488eff25beb7313ce27137d8f3a153b00ce94a51d0f60` | parsed | 14 | 39 | 2 | 2 | 3 |
| 1508.07909v5 | `f4e5a6bbbe0d87459997fffe892f8be485e33903cc71f923c2884639fbf96401` | parsed | 14 | 35 | 3 | 1 | 2 |
| 1804.10959v1 | `61af976a1b16ccf94c1b47e400febc61e802982583afeb055f08c7ba697fe44f` | parsed | 18 | 29 | 3 | 0 | 0 |
| 1808.06226v1 | `8a81eb8bf88f063348356e744afe9e72b305393612f7d4a35596c2701588838d` | parsed | 12 | 24 | 1 | 3 | 0 |
| 1910.13267v1 | `29618b6dc96290e45624180b6e911c2dbf9297729319fd22b9c1c66c9e14acb5` | parsed | 21 | 35 | 0 | 7 | 2 |
| 1910.13267v2 | `44f4e84ddebc86e4d48dfa401879c677cbad57d60730eb36a232efc7f2fabd0a` | parsed | 29 | 44 | 3 | 7 | 0 |
| 2004.03720v1 | `1675bd7df461cd300c918a59bb52f18eff23bcfcc955692deb70cb79185ceb32` | parsed | 6 | 17 | 0 | 1 | 0 |
| 2004.03720v2 | `e49dd1cb028c75cad9eefe9be39a582fa3c80db62bf7b86b8712d15413f331a6` | parsed | 10 | 23 | 2 | 2 | 1 |
| 2012.15613v1 | `967e19c16f20596dc2a98a48ea0ed527ae03450fa6b9d7e1d40cef08b8752148` | parsed | 30 | 91 | 19 | 8 | 5 |
| 2012.15613v2 | `e5c09b7ef60ac8e4d7dd08a3cc120767709888f09511b590638684d3fe7935db` | parsed | 28 | 74 | 22 | 3 | 2 |
| 2103.06874v1 | `832fdd105971cc281acc1b5cdcce0e09a1fbb1228f89d284918d4ceac4234660` | parsed | 23 | 45 | 0 | 1 | 1 |
| 2103.06874v4 | `33a9e90a3215b6d90b7a2cf3551fccf1ccb75553316c390c332fc7a37452f659` | parsed | 30 | 56 | 1 | 1 | 5 |
| 2105.13626v1 | `9825eeaf95519a7a635eb20f8c2596796186abf84471e26299971e6e89bc01aa` | parsed | 23 | 67 | 14 | 3 | 8 |
| 2105.13626v3 | `518d89b7aaf48bd10958f453eb0e67a88cda158df3123169dc12651c830256a6` | parsed | 19 | 56 | 9 | 3 | 3 |
| 2112.06598v1 | `62b296c72625658771c5a8017104774e6a3d5b5b710a787ac52f2609c3b65afd` | parsed | 20 | 49 | 9 | 4 | 0 |
| 2112.06598v2 | `60e34b5be09609b857dbca2caecf65e1f2008280b7a0065ef204bb4d3e5527fe` | parsed | 20 | 52 | 11 | 5 | 0 |
| 2112.10508v1 | `68c551bdd7db474d830aa07cbc6fed4ba2ac498b2d27ec0ec58b883f4750ef47` | parsed | 30 | 57 | 0 | 1 | 0 |
| 2305.13707v1 | `442d5257094043b8125dd1ed7ca96f48bdd806886d98b37fb9a0c51ff636eb4a` | parsed | 20 | 47 | 2 | 10 | 0 |
| 2305.14481v1 | `694c07c29e010daa29f3ec24bad9f3d6e203e0014470ee7f7ad09716aa5832c1` | parsed | 20 | 49 | 6 | 4 | 1 |
| 2305.14481v2 | `04e9f451d8bcd4bb0e1b0bd48141abb45c2a2c596f4f8b232dcbb88796a4a780` | parsed | 24 | 53 | 7 | 2 | 1 |
| 2305.15425v1 | `9102b999681c5419f114e160704d557730c262b57d128eea19f1b562a76bd230` | parsed | 32 | 116 | 8 | 4 | 51 |
| 2305.15425v2 | `2a867076a1020580c1072f649f569b1308c6fe0b94f311da105329f49dfd2128` | parsed | 30 | 112 | 5 | 3 | 56 |
| 2310.08754v1 | `5cb6b7f92211ea68ef0cca3432d382dc50627d820d76085715e9fdf99eae850c` | parsed | 30 | 59 | 7 | 5 | 7 |
| 2310.08754v4 | `1ebcd0f4d551be8225e5cb466055c3f4010174ece763298f4943fc1b823459e9` | parsed | 30 | 53 | 6 | 3 | 2 |
| 2402.01035v1 | `6def38737cd4c433df3ea4bd92d7f8c495ba23c78f6691445e6e2dacdade7f18` | parsed | 32 | 66 | 6 | 9 | 4 |
| 2402.01035v2 | `3ea111d46ca777bf1bc66e442ac4b4d23a8e336c78212a50e7b91b8e58788948` | parsed | 32 | 66 | 6 | 9 | 4 |
| 2402.14903v1 | `762b049e1ca2dbb3e483b3a2b69efabcf48e9db83a71e334b3d1f1237fe49a85` | parsed | 27 | 72 | 1 | 13 | 10 |
| 2402.18376v1 | `a74b986995173e40c64ac158e1addc2462386345bc34f86e38788c06929fc67e` | parsed | 40 | 88 | 18 | 13 | 1 |
| 2402.18376v2 | `45ab15dad9cc9fbe39d097e98759d114230446323de1db97f4f4b5d9bfdead02` | parsed | 41 | 110 | 32 | 13 | 1 |
| 2405.07883v1 | `235f32cc5bd4fed5ea39fc11ee9017c4b9db8ca3798f0a9540c9472ff6d4358b` | parsed | 26 | 61 | 10 | 6 | 1 |
| 2405.07883v2 | `45814e6cce164777882c49928d809138949a59acea7809294832c128affb2ff6` | parsed | 29 | 65 | 13 | 5 | 1 |
| 2407.13623v1 | `30f1e8b630a786fe1ea58e71399086bfda1f15eb4600f4fb54a8a2e18ac91aca` | parsed | 38 | 72 | 2 | 12 | 1 |
| 2407.13623v3 | `f6ab4b65efb387f6fc4872a7b76d05886b997537198ebda1e97dc2865cd12f75` | parsed | 46 | 88 | 1 | 11 | 0 |
| 2412.09871v1 | `23e0cc90e9e2ef0c11291043ca7ad4d48d5384328f31007b8b40230f370756ff` | parsed | 45 | 85 | 5 | 7 | 3 |

## Totals

- Files: 34
- Sections: 889
- Chunks: 2055
- Table Chunks: 234
- Caption Chunks: 181
- Numeric text Chunks: 176
- Parsed: 34
- Failed: 0

## Failures by reason

- none
