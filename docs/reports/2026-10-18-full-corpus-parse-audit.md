# Full-corpus parse audit, 2026-10-18

An audit of the full-corpus parse (#32, `data/parse-report.md`): GROBID 0.9.1 (CRF image), chunking key `215005ae4889`, 2,712 files, 145,074 Chunks, 2 quality-gate failures. It asks what ADR 0029 left open ("revisit after the full-corpus run") and whether the Chunks are fit to index. Nothing here changes the pipeline; the follow-up work is in the issues it led to.

## Method

1. **Every file, automatically.** Per-file metrics from the parse cache (Sections, Chunks by kind, numeric share, duplicate Chunks, `(cid:N)`/U+FFFD glyphs, 60+ character tokens) and a text-coverage ratio: the parsed non-whitespace characters over those pypdf 5.4.0 extracts from the whole PDF.
2. **A sample of 37 files, by an agent, checked by page.** 25 outliers (the lowest and highest coverage, most garbled glyphs, most duplicates, highest numeric share, longest tokens, smallest and fewest-Section passing files) and 12 random files (5 arXiv, 3 ACL, 3 DOI, 1 OpenAlex). Chunks were compared with the PDF's text page by page (recall of word 5-grams per page), with pages rendered where text couldn't settle a question.
3. **Corpus-wide counts** for each pattern the sample found, so that the follow-ups are sized on the corpus, not the sample.

## Corpus-wide results

- **Coverage** (parsed ÷ PDF characters): median 0.77, p5 0.61, p95 0.89, range 0.27–1.36. Reference lists are not parsed into Chunks, so values below 1 are expected; every low outlier in the sample is explained by long reference lists, dropped appendix tables or a real loss (below).
- **No truncation found:** no passing file ends its Chunks before half its pages, none has only an Abstract, and every one has text Chunks.
- **Junk Chunks:** 585 Chunks in 19 files are base64 from invisible `<latexit>` figure text, spaced one character apart; 63 are mostly dot leaders; 333 text Chunks have 4 words or fewer (mostly figure labels and running headers).
- **Appendix opened by a junk head:** about 7 files ("A R T I C L E I N P R E S S", "A Preprint", base64, "A B C D E F G H", a DNA string), where the appendix flag then covers nearly the whole body (192 of 205 Chunks in 2603.15953v1).
- **Chunks with an empty Section path:** 312.
- **Two quality-gate failures**, both genuine: `10.32614/cran.package.rtiktoken`, a 5-page CRAN reference manual, and `2508.13058v1`, a Turkish paper whose printed headings ("I. GİRİŞ") GROBID doesn't find.
- **Four files are cited under two pinned ids each:** `2409.17171v1`/`v2` (byte-identical Versions), `2022.nsurl-1.1`/`2301.06736v1` (venue and arXiv Editions of one paper), `arXiv:2607.05691v1`/`2607.05691v1` (an id with an `arXiv:` prefix) and `L18-1473`/`10.32614/cran.package.sentencepiece` (the CRAN Edition's PDF is the LREC paper).

The sample review follows as the agent wrote it. Chunk ids are given by their last 4 digits; "recall" is per PDF page.

Method: for each file I compared the Chunks with pypdf text page by page. "Recall" below is the share of a PDF page's word 5-grams that appear anywhere in the file's Chunks. I also listed Section paths against the PDF headings, scanned for glyph noise, reference and acknowledgement leaks, running headers and duplicates, and rendered single pages where text could not settle a question (2211.15199v1 p2, 10.1017/S1351324920000145 p2, 10.13064/ksss p3, 2603.15953v1 p4). Chunk ids are given by their last 4 digits.

## Per-file verdicts

| # | pinned_id | verdict | summary |
|---|---|---|---|
| 0 | 2025.wnut-1.0 | not a paper | Workshop proceedings front matter. Only the preface and one keynote abstract are parsed; the second keynote (p7) is lost. |
| 1 | 2605.07533v1 | major issues | Low coverage comes from 11 pages of references plus Appendix E (6 large tables, p24) being dropped. Missed Table 2 ended up as numeric text under "Abstract". "2 Related Work" heading lost. |
| 2 | 2602.05879v1 | major issues | 16 Chunks of the Gemma-3 author list (from the references, p15-17) are indexed as text under "D ASSESSMENT PROMPTS". Most appendix tables are dropped. |
| 3 | 2504.02122v1 | minor issues | Coverage is low only because of 14 pages of references. Appendix tables are garbled, 3.5 heading lost, Table 10 filed under "6 Related Work". |
| 4 | 2504.02122v2 | minor issues | Same as v1. Table 14's Chunk holds Table 15's rows. Table 10 filed under "7 Conclusion". |
| 5 | 2311.08849v1 | major issues | Coverage 1.36 because 73k of the 193k chars are repeated caption+header lines across 225 table Chunks. From Table 8 on, every table carries the next table's rows. References leak into Limitations. |
| 6 | 2026.loreslm-1.16 | minor issues | GROBID reverses the Urdu text (pypdf gives "لکھ", the Chunk gives "ھکل") and wraps it in bidi control chars. An Urdu fragment and a table row became headings. "4 Experimental Setup / 4.1" lost. |
| 7 | 2407.08818v1 | minor issues | The "�" in Telugu/Hindi is already in the PDF text layer. Figure 1 labels became Sections ("Boundary predictor", "DTP"). Stray paragraphs filed under "Abstract". |
| 8 | 2407.08818v2 | minor issues | Same as v1. The "D Technical Details" heading is also lost. |
| 9 | D18-1278 | minor issues | The "�" is in the PDF itself (math glyphs). "3 Experiments" was absorbed into 2.3, "4 Analysis" lost, and a footnote and a table header became headings. |
| 10 | 2605.03799v3 | not a paper | A 188-page lab-course textbook. The running header made 19 Chunks of just "A PREPRINT" and dozens of fake Sections. Duplicates are the textbook's repeated assessment boilerplate. Wrong title. |
| 11 | 2604.14053v1 | minor issues | Duplicates are real repeated sub-captions ("(b) Pruning order: under-trained first."). 36 captions for Figures 9-26 are filed under "J LLM Usage Statement". "2 Related Work" lost. |
| 12 | 2603.15953v1 | major issues | Invisible `<latexit sha1_base64=…>` text in the figures gives 90 of 205 Chunks (42% of chars) of spaced base64. A base64 head starting with "B " triggered the appendix rule, so the whole body from p4 on has appendix=true. |
| 13 | 2601.23169v1 | minor issues | Figure labels became tiny Chunks and Sections ("Cross-Attention" ×2, "4A"). Duplicates are repeated sub-captions. "2 Related Work" lost. |
| 14 | 2405.09913v2 | major issues | References leak into Limitations (42-44). About 7 pages of per-language tables are dropped (p17, p19-23, p27) and the rest are numeric text with table header rows as Section heads. "2 Related Work" lost. |
| 15 | 2024.findings-eacl.9 | minor issues | Appendix I tables became 76 numeric text Chunks, and p19-20 (about 16k chars) were dropped. "2 The Tokenization Task" lost. Acknowledgements dropped correctly. |
| 16 | 10.1017/S1351324920000145 | major issues | The tables' dotted row rules come out as ". . . ." text: 28 of 48 Chunks are mostly dots (54% of chars). This causes the "numeric share" flag. |
| 17 | 2308.07037v6 | good | Long tokens are the paper's real text8 samples (underscore-joined). Math is lossily linearised, as expected. A few subsection heads (4.3, 6.5) lost. |
| 18 | 2308.07037v1 | good | Same as v6. |
| 19 | 2211.15199v1 | major issues | Pages 2-4 are image-only (no text layer; rendered page 2 shows normal text), so half the paper is missing. Limitations text glued into the Introduction (0003). |
| 20 | cran.package.wordpiece | not a paper | R package manual. Title empty, contents dot leaders as captions. |
| 21 | cran.package.morphemepiece | not a paper | R package manual. Title "Encoding UTF-8". Duplicates are repeated argument docs. |
| 22 | cran.package.tokenizers.bpe | not a paper | R package manual. Function docs became "caption" Chunks with empty section_path. |
| 23 | 10.13064/ksss.2024.16.3.079 | major issues | Korean two-column paper. No headings found (empty section_path), body prose sits inside "table" Chunks, and pages 3-7 have recall 0.09-0.39 (e.g. the "평가셋에 포함된 정답전사" paragraph is missing). |
| 24 | 10.7469/JKSQM.2020.48.3.421 | major issues | Korean paper. No headings found ("1. 서 론" is inline text), 53 Chunks with empty path, pages 6, 9 and 11 have recall ≤0.05. |
| 25 | 2606.18717v2 | minor issues | Body is good. "2 Related Work", "4.8 Efficiency" and "6 Limitations" headings lost into neighbours. |
| 26 | 1809.04259v1 | good | Clean. |
| 27 | 2412.13377v2 | minor issues | Coverage 0.47 is 4 pages of references. The "A Appendix" heading is lost, so the appendix Table 4 is not flagged and is filed under "Ethical Considerations". |
| 28 | 2601.04469v1 | minor issues | The appendix table after the references became numeric text under "6 Conclusion > Vocabulary", not flagged as appendix. List items became headings. |
| 29 | 2407.00894v1 | minor issues | "10 Limitations" is merged into "9 Conclusion". Otherwise clean. |
| 30 | 2020.lrec-1.333 | good | Clean, correct numbering. |
| 31 | 2020.lrec-1.450 | minor issues | The tail of the reference list became an appendix Section "Monolingual Corpora Only. Proceedings…" (32-33). |
| 32 | 2026.acl-long.1696 | good | Clean. The PDF itself numbers "1 Abstract / 2 Introduction". "4.2 Data" lost, and an algorithm line "22: end for" became a head. |
| 33 | 10.1007/s40747-025-01936-3 | minor issues | Springer unnumbered heads, so the hierarchy is flat. A numbered conclusion list item became a head. "Ethical Approval Not applicable." is an appendix Section. |
| 34 | 10.1109/ACCESS.2020.3004879 | minor issues | IEEE "A./B./1)" subsections all sit at the top level. "V. EXPERIMENTS" is lost into "IV … C.". Text is clean. |
| 35 | 10.1038/s41598-026-37438-6 | major issues | The letter-spaced stamp "A R T I C L E I N P R E S S" became a head starting with "A ", so everything after the Introduction is appendix=true. Case-study tables on p28-35 are dropped. |
| 36 | W7165988237 | minor issues (borderline relevance) | Undergraduate honours thesis. Title is wrong ("The Department of Applied Mathematics…"). Acknowledgements leak as a caption under Abstract (0001). Introduction heading lost (empty path, p7-14). |

Tally: good 5, minor 17, major 10, not a paper 5.

## Per-file notes (evidence)

- **0 2025.wnut-1.0**: Two Chunks. 0001 "Introduction" runs from p3 to p9 and ends with the programme schedule "09:15 -09:30 Opening Remarks … Closing viii" (the page number "viii" leaks). The p7 keynote "What Can We Learn from Perspectives on Noisy User-Generated Text?" has recall 0.00. The committee and contents pages (p4-5, p8) give nothing, which is fine.
- **1 2605.07533v1**:
  - Chunks 0001-0003 are Table 2's cells ("Model TAR GENETIC GEOGRAPHIC … Qwen3-30B-A3B-Instruct-2507 0.5352 -0.1294") with section_path ["Abstract"] and page 6.
  - "Table E.1" appears in no Chunk, and p24 (12,383 chars of results) has recall 0.01.
  - Appendix order is D, A, C (TEI order). The B heading is lost; its caption "Figure B. 1" sits in C.
  - "2 Related Work" is inline at the end of 0006, so "LLM Translation" sits under "1 Introduction".
  - Acknowledgements (p11) are correctly dropped.
- **2 2602.05879v1**:
  - 0057-0072 (A, "p15-34", "D ASSESSMENT PROMPTS") are author lists: "McLean, Jonathan Lai, Jennifer Beattie, Nate Kushman…" (Gemma-3 reference). Pages 15-17 have recall 0.96-0.98 while every other reference page has 0.00.
  - Missed tables: 0073-0080 are numeric text. Pages 34 and 37-39 (recall 0.05-0.10) and 43-44 (0.08-0.09) are mostly gone.
  - Table header rows became Section heads ("Model Hellaswag MMMLU MMLU-ProX ARC-C…"). "4.3 BASELINES" lost.
- **3/4 2504.02122**:
  - 14 of 27 pages are references (recall 0.01 each), which explains the 0.40 coverage. Body pages have recall 0.83-0.95.
  - Appendix B: GROBID glues subscripts ("53.20.36" for 53.2±0.36). Table 14's Chunk (0045) has the caption "Copy of Table1including standard deviations." followed by Table 15's rows (18.8/11.7/13.3…). 0046 is nearly empty rows.
  - The "Published as a conference paper at COLM 2025" header leaks once (0048).
- **5 2311.08849v1**:
  - Table 7's caption is the sentence "Table 7, 8, 9 10 (SR-B), Table 11 (SR-T)…" rather than its real caption.
  - Page-by-page mapping: the p16 caption is "Table 8", but its Chunks (0076-0099) start "mam_Latn", which is the first row of p17 (Table 9). Table 9 holds p18's "san_Deva…", and so on through Table 17 (p25 caption, p26's afr_Latn rows). So every numeric row from Table 8 on is labelled with the wrong task.
  - Pages 16, 23 and 24 (own rows) have recall 0.02-0.05.
  - 0039-0040 under "7 Conclusion > Limitations" are references ("Benjamin Minixhofer, Fabian Paischer… WECHSEL").
- **6 2026.loreslm-1.16**:
  - 0001: "the root ‫"(ھکل‬write")" against pypdf "the root لکھ(“write”)". The letters are in visual order, with U+202B/U+202C embedding marks. Glyph flag: 44 U+FFFD, which come from the PDF too.
  - Section "3.7 … > ‫ےک‬ ‫اس‬ ‫ھت‬" (0019) and "5.5 Error Analysis > Error Type QARI (% of errors)" (0032) are fake heads.
  - "4 Experimental Setup / 4.1 Datasets" are absent, so "4.2 Baselines" sits at the top level.
- **7/8 2407.08818**:
  - pypdf gives the same "తోటి మల� యుద�". The PDF fonts lack ToUnicode, so this is not GROBID's fault.
  - 0003 is just "Transformer Block" under the path "1 Introduction > Boundary predictor".
  - 0001 (v2, "Abstract", p2-3) holds footnote 2 plus "Upsampling This module converts h M l to probabilities…", a paragraph from 2.1. This comes from the reader rule (tei.py `_div`): a headless div at the start of the body is appended to the last draft, which is the Abstract.
- **9 D18-1278**: 0008 starts "3 Experiments Data We experiment on twelve languages…" under "2.3 Computing word representations". "4.1 Why do characters beat words?" has no parent. The head "* Work done while at the University of Edinburgh." is a footnote.
- **10 2605.03799v3**:
  - Self-described "a textbook for undergraduate and graduate students" (p2 "Arabov M.K. … — Kazan, 2026. — 117 pp.").
  - 19 identical "A PREPRINT" Chunks, e.g. 0019. Many Sections are titled "Natural Language Processing: A Comprehensive Practical Guide…" (the running header).
  - 14 copies of "The learner is entitled to choose one of three formats…" are the book's real per-chapter boilerplate.
- **11 2604.14053v1**: 12× "order: under-trained first." and 6× "Pruning order: under-trained first." are split sub-captions of Figures 9-26. Section I cites them as a range ("In Figures 9-26"), so the page fallback puts them in J. The figure filler text "Loremipumdolorsitamet…" is not indexed (0 hits), which is good.
- **12 2603.15953v1**:
  - pypdf finds 23 "latexit" strings on p4. The rendered p4 shows only a diagram, so the text is invisible.
  - Sections like "B K f A A 1 V Q A 9 e g D h q…" (0013, appendix=A) are base64. Every later Section, including "3 Model" through "10 Conclusion", is flagged appendix. Duplicate Chunks are repeated base64 blobs (0013/0051, 0031/0090/0101).
- **14 2405.09913v2**:
  - 0043 "Telmo Pires, Eva Schlinger, and Dan Garrette. 2019. How multilingual is multilingual BERT?…" is under "Limitations".
  - Table 17 (p20): its row "gle_Latn 24.2 28.8 34.6" is in no Chunk, while other tables' gle_Latn rows are.
  - Section "6 Analysis 6.1 Which Merge Mode Wins" merges two heads.
- **15 2024.findings-eacl.9**: 0040 "Treebank dev +splits #splits … UD_Afrikaans-AfriBooms 100.0000 100.0000 0…" is numeric text in Appendix I. Pages 12-18 have recall 1.00 (kept as text) and p19-20 have 0.01-0.04 (dropped). "1 Introduction > Multi-word expansions:" is really "2 The Tokenization Task".
- **16 10.1017/S1351324920000145**: The rendered p2 shows Table 1 with dotted row separators. 0003/0004 are pure ". . . . ." and 0005 is ". . . .. dipotassium 7 dip-ota-ssi-um di-potassium .. . . .". Table chunk 0024 does have rows ("unidirectional | 10 | un-idi-re-ction-al | uni-directional").
- **17/18 2308.07037**: 0115 "nd_philip_melanchthon_in_one_five_six_one…" is a text8 model sample, as printed. 0079 shows typical lossy math ("p(k | c; ω) = 1-ω K m-c k 1-ω K…").
- **19 2211.15199v1**: pypdf gives 0 chars on p2-4, and the rendered p2 shows two columns of normal text ("2 A New Model: AlephBERTGimmel"). Chunk 0003 runs "…in particular regarding The primary limitation of the AlephBERTGimmel model…" from p1 to p5.
- **20-22 CRAN**: wordpiece 0003 is a caption "load_or_retrieve_vocab: Contents load_or_retrieve_vocab . . . ."; tokenizers.bpe 0000 "Abstract" is "Encoding UTF-8 LazyData true RoxygenNote 7.3.2".
- **23 10.13064/ksss**: The rendered p3 shows clear heads "4. 실험 및 분석" and "4.1. 인코더 모델에 따른 인식 성능". Table chunk 0009 contains body prose "실험에 사용한 단말은 라즈베리파이 5 단말로…" with words split at line ends ("클\n럭"). "정답전사" appears in no Chunk.
- **24 10.7469/JKSQM**: 0009 is "NB는 다른 4. 연구결과 4.1 분류 알고리즘 별 지도 비지도 학습 토크나이저 비교 분석…", with heads inline in the text.
- **25 2606.18717v2**: 0006 "…instead of a small hand-picked set. 2 Related Work Subword tokenization and its limits for Turkish." is filed under "1 Introduction".
- **27 2412.13377v2**: p11 ends "A Appendix". Table chunk 0024 is "Table 4 (Ethical Considerations): Generated by Spread-LaTeX", with appendix flag "-".
- **28 2601.04469v1**: 0041-0043 "Estonian 8,000 5,705 11.27% 65.79% …" sit under "6 Conclusion > Vocabulary" (p11, after the references).
- **31 2020.lrec-1.450**: 0032 is "Neubig, G. and Hu, J. (2018). Rapid Adaptation of Neural Machine Translation…", flagged A.
- **35 10.1038/s41598-026-37438-6**: 0002 is the Introduction's continuation, filed under "A R T I C L E I N P R E S S" and flagged A. All later Sections ("2 Related Work", "3.1 BPE Algorithm", "5 Results…") are A. Pages 28-35 (recall 0.00-0.23) are response tables.
- **36 W7165988237**: 0001 is a caption "Acknowledgements: Thank you to my advisor Steven Clancy…" under "Abstract". 0002/0003 (Abbreviations, the Introduction) have an empty path.

Things that work well: reference lists are excluded in 33 of 37 files, and acknowledgements are dropped in every paper except the thesis (only 1 leak found by a keyword scan). Running headers leak only 3 times (4: 0048, 7: 0002, 14: 0043). Body prose of born-digital English papers is faithful, with good dehyphenation and no column interleaving seen. Pages and appendix boundaries are right whenever the headings were found.

## Patterns (ranked by retrieval impact)

1. **Junk text indexed as prose** (4 papers plus 4 non-papers; GROBID/PDF, with no filter in the rules). Sources: invisible latexit base64 (12: 42% of chars), dotted table rules (16: 54% of chars; also the CRAN contents pages 20-22), running headers and stamps ("A PREPRINT" ×19 in 10, "A R T I C L E I N P R E S S" in 35), and figure labels as 1-4 word Chunks ("Cross-Attention", "Transformer Block", "Fully-open": 7, 8, 11, 13, 2). These Chunks match nothing useful, waste index space, and the base64 ones look unique to a lexical retriever. A cheap Chunk-level filter would remove almost all of them: drop Chunks whose text is mostly single characters separated by spaces, mostly ". ", or shorter than about 5 words with no sentence.
2. **Lost section headings** (≥19 of 31 papers; GROBID's fault). GROBID puts the head inside the first `<s>` of a paragraph (TEI for 13: `<s …>2 Related Work <ref…>Işık et al.`). "2 Related Work" alone is lost in 5 of the sample's papers (1, 11, 13, 14, 25). Other examples: "3 Experiments" and "4 Analysis" (9), Limitations (19, 25, 29), "A Appendix" (27), and every head in the Korean papers (23, 24). The text survives, but section_path and the header are wrong for every Chunk of that Section (Related Work filed as Introduction). The TEI `<s>` boxes do carry the larger font height (12.62 against 8.74 for body lines in 13), so the reader could recover numbered heads from a first sentence matching `^\d+(\.\d+)* [A-Z]` with a taller box.
3. **Appendix rule fooled by junk heads** (2 files: 12 and 35; the chunking rules' fault). The A-H opener in `_appendix_number` fires on a base64 head starting "B " and on the stamp "A R T I C L E…". Every later body Chunk is then appendix=true. The reverse (an appendix not flagged because its heading was lost or because it comes after the references) shows in 3, 4, 27 and 28. A fix: require the opener head to be a short title (no single-letter runs) and/or have no numbered body Sections after it. Today numbered Sections such as "3 Model" are accepted inside the appendix.
4. **Tables: missed, dropped or mislabelled** (12 papers; GROBID's fault, kept as is by 0035).
   - Numeric text Chunks: 1, 2, 4, 6, 9, 14, 15, 28.
   - Whole table pages dropped from both table and text: 1 (p24), 2 (p34, 37-39, 43-44), 5, 14 (≈7 pages), 15 (p19-20), 35 (p28-35).
   - Rows under the wrong caption: 5 (systematic off-by-one from Table 8 on), 4 (Table 14), 23 (body prose inside table Chunks).

   The mislabelled ones are the worst case for retrieval, because the numbers come with a confident but wrong caption. Large multi-page per-language appendix tables are where it all happens.
5. **Text outside the reference list leaks, and reference text leaks into the body** (4 files: 2 (16 Chunks), 5, 14, 31; GROBID's fault). Pages of author lists (Gemma-3, GPT-4 style) and the tail of the reference list become body paragraphs or a fake appendix Section. These match every name query.
6. **Corpus relevance** (5 of 37 are not papers, plus 1 thesis): proceedings front matter (0), a textbook (10), 3 CRAN manuals (20-22), and an honours thesis (36). They also carry bad titles, which go into every Chunk header. Pre-parse filtering (DOI prefix 10.32614/cran, front-matter ids like `*.0`, page count >100) would catch them.
7. **Non-Latin scripts and missing text layers** (5 files). Urdu reversed by GROBID (6). Telugu/Devanagari "�" from the PDF fonts (7, 8). Korean two-column papers lose headings and large parts of the body (23, 24). Image-only pages are lost without OCR (19: 3 of 6 pages). The quality gate passed all of these. Coverage only catches 19 and 23, and 24 (0.58) is borderline.
8. **Orphan text filed under "Abstract"** (1, 7, 8, 36; the reader rule). A headless div at the start of the body is appended to the Abstract draft (tei.py `_div`). It brings misplaced table cells (1: p6), stray paragraphs and footnotes (8), and acknowledgements (36) into the Abstract, with pages far from p1. They would be better as a Section with an empty path, or joined to the next headed Section.
9. **Duplicates** (cosmetic, 6 files). Mostly real repeated text: sub-captions (11, 13), textbook boilerplate (10), R docs (21), and a repeated figure caption (36). Only 12 (base64) and 10 ("A PREPRINT") are junk, and those are covered by pattern 1.
10. **Hierarchy cosmetics**: unnumbered heads nest under the last numbered Section ("8 Conclusion > Limitations"). Springer and IEEE heads stay flat (33, 34). List items become heads (28, 33). Low impact.
11. **Coverage outliers explained**:
    - Low coverage is mostly long reference lists (1, 2, 3, 4, 27; e.g. 3/4 have 14 of 27 pages of references) plus dropped appendix tables (1, 2, 14).
    - Real loss only in 0 (non-paper), 19 (image pages) and 23 (Korean layout).
    - 1.36 for 5 is the repeated table header lines (73k of 193k chars). By design, but it shows that a 225-Chunk table set dominates the file's index footprint.
    - The "long tokens" flag in 17/18 is a false positive (text8 samples).

## Candidates for the developer's manual check

Questions that rendering did not settle, mostly judgement calls:

1. **2311.08849v1 (OFA), pages 16-18**: Is each "Table N:" caption printed below its table, so that GROBID gave every caption the next table's rows? Look at whether p16's caption "Table 8" sits under the gla_Latn rows. Also: should 12 pages of per-language result tables (225 Chunks) be indexed at all? (yes/no)
2. **2602.05879v1 (EuroLLM-22B), pages 14-17**: Are pages 15-17 entirely the Gemma-3 reference's author list, with no body text? (yes/no) If yes, Chunks 0057-0072 should not be indexed.
3. **10.13064/ksss.2024.16.3.079 and 10.7469/JKSQM.2020.48.3.421, pages 3-7 and 6-9**: Is the missing Korean body text (e.g. the ksss p3 paragraph starting "평가셋에 포함된 정답전사에는") worth a second parser or OCR? Or are Korean-language papers out of scope for an English RAG? (keep / drop / fix)
4. **2211.15199v1, pages 2-4**: These pages have no text layer. Is OCR for image-only pages worth adding, or should such files fail the quality gate? (OCR / fail / accept)
5. **2605.03799v3 (NLP textbook), W7165988237 (honours thesis), 2025.wnut-1.0 (proceedings front matter), the 3 CRAN manuals**: Keep each in the corpus? (yes/no each)
6. **10.1017/S1351324920000145 (Church), pages 2-5**: Do the table Chunks (0022-0025, 0041-0043) hold every row of Tables 1-6? If yes, the 28 dot-only text Chunks are pure noise and can be dropped. (yes/no)
7. **2405.09913v2 (TransMI), pages 14-27**: About 7 of these 14 table pages are not indexed at all and the rest are numeric text. Are these per-language tables something users would query? This decides whether dropped tables matter. (yes/no)

## Overall verdict

For born-digital English papers, the body text is good enough to index. Prose is faithful, references and acknowledgements are reliably excluded, and pages are plausible. About half the sample is good or has only minor issues. Three cheap fixes should come before indexing, in order:

1. **A junk-Chunk filter** at Chunk level: spaced single characters (latexit), dot leaders, Chunks of ≤4 words with no verb or full stop, and repeated running-header lines. This removes the largest share of junk Chunks in the sample (12, 16, 10, figure labels).
2. **Harden the appendix opener** so a head like "B K f A A 1…" or "A R T I C L E I N P R E S S" cannot start the appendix. Reject heads made of single-letter runs, and stop treating numbered body-style Sections that come after the opener as appendix. Today this rule mislabels the whole body of 2 of 37 files.
3. **Recover inline numbered headings** from the first `<s>` of a paragraph (pattern `^\d+(\.\d+)* Title` plus the taller coord box). This fixes the most common structural defect, which mislabels Related Work, Experiments and Limitations in about half of the papers.

Then make two corpus decisions: drop non-papers before parsing, and decide on non-Latin and image-only PDFs. The quality gate should also catch files with large unparsed spans (per-page recall), not only low overall coverage. Table problems (mislabelled rows and dropped pages) are GROBID's limit and best left to the retrieval evaluation (#26) as 0035 plans. Note, though, that the OFA off-by-one case puts wrong captions on correct numbers, which is worse than a missed table.
