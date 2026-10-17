# 0024. GROBID stays the parser after the spike against Docling

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
The parse step (#14) turns each pinned PDF into Section-bounded Chunks with page anchors. The spec picks GROBID ([0023](0023-grobid-crf-image-pinned-by-digest.md)) for its section-aware TEI with a structured bibliography at corpus scale on CPU. Before the parser is locked in, the spike (#17) compares it with Docling on the 34 Seed PDFs, using the rule set in #14:
- Docling replaces GROBID only if it is within about 2× of GROBID's speed **and** clearly better on Sections and tables.
- A parser whose output is not byte-stable is ruled out.

Corpus scale once `fetch` runs: about 5k pinned files and 100k pages.

## Setup
- **Machine:** M1 Max (10 cores, 32 GB), Docker Desktop with 8 GB for containers. The judge (Ollama, Tev1 4B) was running a `collect` in another checkout during every timed run, for both parsers. That load hits the GPU, which Docling uses, more than the CPU, which GROBID uses. So Docling's times may be a little pessimistic. The gap below is much bigger than that effect.
- **GROBID:** `grobid/grobid:0.9.1-crf` pinned by digest, started with `just grobid-up`. `POST /api/processFulltextDocument` with `consolidateHeader=0`, `consolidateCitations=0`, `consolidateFunders=0`, `includeRawCitations=1`, `segmentSentences=1`, and `teiCoordinates` for `head`, `p`, `s`, `figure`, `formula`, `biblStruct`, `note` and `title`.
- **Docling:** 2.140.0 (docling-parse 7.22.3, docling-ibm-models 4.0.3, torch 2.14.1), in a throwaway venv outside the repo (1.2 GB, plus 506 MB of models). Default PDF pipeline: docling-parse backend, layout model, TableFormer table structure, accelerator `auto` (MPS). OCR off, because the Seeds are born-digital and OCR is out of scope in #14. Output: `export_to_dict()` with sorted keys, and `export_to_markdown()`.
- **Runs:**
  - GROBID: four runs. One sequential on a fresh container, then 4 and 8 concurrent requests, then a cold container restart and a sequential run again.
  - Docling: two runs, each in a fresh process (so its models were reloaded).
- **Hand checks:** five hard papers, compared with each PDF's text layer and pages: WECHSEL v2 (two-column ACL, appendices A–F, 11 tables), How Good is Your Tokenizer v1 (two columns, 11 tables, long appendix), Byte Latent Transformer v1 (27 pages, 12 tables, formulas), Scaling Laws with Vocabulary v3 (33 pages, appendices to A.12, NeurIPS checklist) and Tokenizer Unfairness v2 (28 pages, extended appendix tables).
- **Counts:** "Printed tables" is the highest table number in the PDF's text layer. A table counts as found when the parser's caption carries that number and the table has more than one row.

## Results

| | GROBID 0.9.1-crf | Docling 2.140.0 |
|---|---|---|
| Files parsed | 34/34 | 33/34 (SentencePiece: "Page N failed to parse" on all 6 pages) |
| Sequential, 623 pages | 93 s (0.15 s/page; 0.13 s/page after an 11.5 s first request) | 667 s on the 33 files it parsed (1.08 s/page), plus 3–5 s model load per process |
| Same 33 files, sequential | 92 s | 667 s, **7.3× slower** |
| Concurrent | 23 s with 4 requests, **12 s with 8** (0.02 s/page) | one MPS device; not parallelised |
| Projected 100k pages | about 4 h sequential, about 35 min with 8 requests | about 30 h |
| Tables found / printed | 125/270 (46 %) | 251/268 (94 %) |
| Structured bibliography | yes (`biblStruct`, with the raw string) | no (references are body paragraphs under "References") |
| Appendix marked | `div type="annex"`, but often wrong (below) | no flag; headings only |
| Raw output byte-identical on rerun | 0/34 (all 4 runs) | Markdown 34/34; JSON 28/34 |
| Kept content identical on rerun | 34/34 (all 4 runs) | 34/34 (Markdown) |

**Determinism.**
- **GROBID.** Raw TEI is never byte-identical. Three causes, and nothing else changed:
  - `application/@when` is the request time.
  - Funders get random `xml:id`s and change order.
  - In both BPE-Dropout files, a figure's `graphic` box moves between two figures.

  Everything the TEI reader will keep was identical across all four runs, cold restart included, for all 34 files: title, abstract, Sections, sentences, formulas, pages, table rows, captions and bibliography.
- **Docling.** On the cold rerun, 6 JSON files differed only in layout boxes, by at most 6.1 × 10⁻⁵ pt (MPS float jitter). The text did not change.

So neither parser is byte-stable as raw output. Both are stable in content. GROBID's variation is in fields we drop; Docling's is in model output, which could in principle tip a borderline layout decision.

**Hand checks** (GROBID / Docling):

| Paper | Sections | Tables | Reading order |
|---|---|---|---|
| WECHSEL v2 | GROBID loses 3, 4, 6 and 6.1 (their text joins the previous Section) and merges 5.2 into 5.2.1's heading. Run-in headings become Sections. A–F are correct and marked. / Docling: all 17 Sections and A–F correct. | 5 of 11 usable: Table 6 is labelled "Table 5", Table 10 has one row, Tables 1, 3, 4 and 11 are missing. / 11 of 11, with captions. | Both follow the columns. GROBID moves figures, tables and footnotes to the end of the body, so paragraphs stay whole. Docling interleaves captions, and splits chart labels into dozens of short paragraphs. |
| How Good is Your Tokenizer v1 | GROBID loses 2, 4 and 5. A and A.1 land in the annex, but A.2–C land in the body after the Conclusion, so they would not be marked as appendices. A "References" stub sits inside the acknowledgements. / Docling: all correct, though some words are glued ("RelatedWork"). | 9 of 11, one of them (Table 2) garbled; Tables 1 and 11 are missing. / 11 of 11. | Same as above. Docling makes 189 paragraphs of chart labels in C. |
| Byte Latent Transformer v1 | GROBID: 1–6 and 9–10 correct. 8 is lost into a run-in heading under 7, and table cells such as "12.1" and "Overall Average" become Sections. The appendix is mixed with "Contributors". / Docling: all correct, but bold headings lose their spaces ("StridedPatchingEveryKBytes"). Body text is fine. | 2 of 12; two more have one row. / 12 of 12. | Docling breaks one paragraph at Figure 3 ("compute is" … caption … rest). GROBID keeps it whole. |
| Scaling Laws with Vocabulary v3 | GROBID: 1–7 correct. Every appendix Section lands in the body, A.3, A.5, A.7, A.7.1, A.10, A.12 and C are lost, two checklist items leak into the body, and a table header row becomes a Section. / Docling: all correct, including the checklist. | 1 of 5. / 5 of 5. | Both are fine. |
| Tokenizer Unfairness v2 | GROBID: 1–8 correct. Run-in headings ("Summary.") become Sections. A–C land in the body, and the extended tables become one 24,425-character paragraph. / Docling: correct, except that Table 1's caption is merged into the 4.1 heading. | 4 of 8. / 5 of 8, plus the 6 extended appendix tables found but uncaptioned. 112 s for this file. | Both are fine. |

Per-file timings and counts are in the appendix below.

## Decision
- **GROBID stays the parser**, as #14 assumes: `grobid/grobid:0.9.1-crf` pinned by digest ([0023](0023-grobid-crf-image-pinned-by-digest.md)), with the request parameters above. Docling does fail on the speed condition, and decisively: 7.3× slower sequentially, and about 50× slower than GROBID with 8 requests, against a bar of about 2×. Docling *is* clearly better on Sections and tables, so the decision rests on speed, on the structured bibliography the dedup stage needs, and on Docling's hard failure on one of 34 files.
- **Determinism means the content, not the raw TEI.** The parse cache stores the raw TEI, keyed by file hash and parser version as #14 says. The byte-identical guarantee applies to the Chunks and the report, which are built only from content shown to be stable. The TEI reader ignores `application/@when`, funders and `graphic` boxes.
- **What the later tickets must handle in the TEI reader** (details and examples in the spike notes passed to #18):
  - Sections are flat `div`s, with the number in `head/@n` for the body and in the head text ("A.2 …") for appendices. Rebuild paths from the numbers, and allow a missing parent (6.2 with no 6).
  - Mark an appendix by its letter-numbered head, or by its position after the Conclusion, not only by `div type="annex"`.
  - Drop `div type="acknowledgement"` whole.
  - Expect noise Sections from table cells and very long numeric paragraphs from tables GROBID missed. The quality gate and Chunker should not let them dominate.
  - Make a table Chunk only from a `figure type="table"` with rows. A table GROBID missed is lost as a table. Its caption is often lost too, but any text that leaked into the body is still chunked as text.

## Alternatives considered
- **Docling.** It is better on headings and much better on tables (94 % against 46 %), and its Markdown is byte-stable. But:
  - It fails the speed bar by a wide margin: about 30 h for the corpus against under an hour.
  - It has no structured bibliography for the dedup stage.
  - It failed SentencePiece outright with its default backend. The pypdfium2 backend parsed that file in 6.4 s, so a fallback would be one more code path.
  - Its torch and model stack (1.7 GB) would join the lock file.
  - Its layout boxes jitter between runs.

  Revisit it if the evaluation shows table questions failing for want of table Chunks. A Docling pass for tables only, on the pages where GROBID found none, would cost far less than a full switch, but it would be a second parser to pin.
- **GROBID full image.** Not tested. It is amd64 only ([0023](0023-grobid-crf-image-pinned-by-digest.md)), and its deep-learning models cover header, references, affiliations and funding. Nothing shows they would fix the Section and table losses seen here.
- **Prior work: research-bot's Marker.** It was not run here; this compares its code. research-bot converts each PDF with Marker (Surya layout and OCR models, about 4–5 GB, GPU or MPS) to Markdown and HTML, saves the images, and counts tables by regex over the output. When Marker fails, it falls back to Mistral's paid OCR API.
  - Its output is a flat Markdown file per paper, with no Sections, pages or bibliography as data. It is not chunked by Section, and nothing is pinned: models are downloaded at first run, there is no hash of the input (it fetches the unversioned arXiv URL), and every result is stamped with `extraction_date`. A cloud fallback also makes the output depend on a remote service.
  - Marker is a model-based Markdown converter in the same family as Docling, so the speed and stability findings above probably apply to it too.

  We keep its lesson that tables matter enough to count, but we take the structure from GROBID's TEI rather than from Markdown, and we never call a remote parser.

## Consequences
- The whole corpus can be parsed in well under an hour with a few concurrent requests, and on CPU only, so the GPU stays free for the judge and the embedding comparison.
- Table recall is the known weakness: about half the printed tables in the Seeds will have no table Chunk. The parse report should count tables per file so this stays visible.
- The TEI reader needs the extra rules above for appendices and missing parent Sections. Tests should include a fixture where appendices sit in the body.
- Fixture candidates are CC BY Seeds: WECHSEL v2, Do All Languages Cost the Same v1 and Sennrich BPE v5. Their raw TEI is kept with the spike notes, not committed. Before committing one, set its `application/@when` to a fixed value.
- The spike's scripts, raw outputs and Docling environment were throwaway and are not in the repo. Rerunning the GROBID half needs only `just grobid-up` and the request above.

## Appendix: per-file results

Times are seconds for one sequential request (GROBID's first file includes the 11.5 s first-request load). Sections counts GROBID body plus annex `div`s, or Docling section headings; the number in brackets is how many carry a Section number.

| File | Pages | GROBID s | Docling s | GROBID Sections (numbered) | Docling headings (numbered) | Printed tables | GROBID tables | Docling tables |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bpe-dropout_1910.13267v1 | 10 | 11.5 | 7.9 | 20 (20) | 27 (23) | 5 | 0 | 5 |
| bpe-dropout_1910.13267v2 | 11 | 4.2 | 7.5 | 28 (28) | 34 (29) | 8 | 2 | 7 |
| bpe-suboptimal_2004.03720v1 | 7 | 1.5 | 5.7 | 5 (4) | 16 (5) | 3 | 0 | 2 |
| bpe-suboptimal_2004.03720v2 | 8 | 1.6 | 20.5 | 9 (8) | 15 (9) | 5 | 2 | 5 |
| byt5_2105.13626v1 | 17 | 2.4 | 40.1 | 22 (22) | 27 (23) | 14 | 5 | 13 |
| byt5_2105.13626v3 | 16 | 2.2 | 12.9 | 18 (18) | 22 (18) | 10 | 5 | 10 |
| byte-latent-transformer_2412.09871v1 | 27 | 2.5 | 16.6 | 45 (36) | 43 (38) | 12 | 2 | 12 |
| canine_2103.06874v1 | 16 | 2.0 | 4.4 | 22 (15) | 22 (19) | 4 | 0 | 4 |
| canine_2103.06874v4 | 18 | 2.2 | 8.7 | 30 (21) | 29 (25) | 8 | 1 | 7 |
| code-tokenizer_2402.01035v1 | 21 | 2.8 | 17.8 | 32 (17) | 34 (25) | 11 | 6 | 11 |
| code-tokenizer_2402.01035v2 | 21 | 2.8 | 19.4 | 32 (17) | 35 (25) | 11 | 6 | 11 |
| focus_2305.14481v1 | 15 | 2.0 | 6.7 | 19 (10) | 16 (10) | 7 | 2 | 7 |
| focus_2305.14481v2 | 15 | 2.2 | 8.6 | 23 (10) | 17 (11) | 8 | 5 | 8 |
| how-good-is-your-tokenizer_2012.15613v1 | 28 | 4.1 | 23.6 | 30 (22) | 34 (25) | 11 | 9 | 11 |
| how-good-is-your-tokenizer_2012.15613v2 | 18 | 3.0 | 26.0 | 27 (23) | 28 (24) | 10 | 6 | 9 |
| languages-cost_2305.13707v1 | 20 | 2.5 | 5.2 | 19 (9) | 24 (16) | 2 | 2 | 2 |
| more-than-compression_2402.18376v1 | 23 | 2.6 | 29.2 | 39 (33) | 44 (36) | 12 | 7 | 12 |
| more-than-compression_2402.18376v2 | 25 | 2.8 | 38.4 | 40 (34) | 45 (37) | 14 | 8 | 14 |
| open-vocabulary-survey_2112.10508v1 | 27 | 2.9 | 6.5 | 29 (28) | 36 (32) | 0 | 0 | 0 |
| sennrich-bpe_1508.07909v1 | 11 | 1.7 | 8.1 | 13 (12) | 17 (12) | 7 | 2 | 6 |
| sennrich-bpe_1508.07909v5 | 11 | 1.7 | 8.1 | 13 (12) | 17 (12) | 5 | 3 | 5 |
| sentencepiece_1808.06226v1 | 6 | 1.5 | failed | 11 (10) | – | 2 | 1 | – |
| subword-regularization_1804.10959v1 | 10 | 1.6 | 21.5 | 18 (17) | 21 (18) | 6 | 2 | 6 |
| tokenization-counts_2402.14903v1 | 21 | 2.7 | 5.8 | 27 (17) | 34 (27) | 1 | 1 | 1 |
| tokenizer-choice_2310.08754v1 | 19 | 2.1 | 12.2 | 29 (26) | 31 (27) | 11 | 6 | 10 |
| tokenizer-choice_2310.08754v4 | 17 | 2.1 | 9.8 | 30 (27) | 33 (29) | 11 | 5 | 11 |
| tokenizer-unfairness_2305.15425v1 | 27 | 3.8 | 104.3 | 31 (20) | 24 (20) | 8 | 6 | 7 |
| tokenizer-unfairness_2305.15425v2 | 28 | 3.3 | 112.2 | 30 (18) | 22 (18) | 8 | 4 | 5 |
| vocabulary-scaling_2407.13623v1 | 26 | 2.5 | 9.7 | 37 (29) | 37 (34) | 5 | 1 | 5 |
| vocabulary-scaling_2407.13623v3 | 33 | 2.8 | 8.7 | 45 (38) | 56 (50) | 5 | 1 | 5 |
| wechsel_2112.06598v1 | 14 | 2.0 | 16.4 | 20 (17) | 23 (20) | 9 | 5 | 8 |
| wechsel_2112.06598v2 | 15 | 2.1 | 17.5 | 19 (17) | 26 (23) | 11 | 5 | 11 |
| zero-shot-tokenizer-transfer_2405.07883v1 | 20 | 2.7 | 12.7 | 26 (16) | 24 (19) | 12 | 6 | 9 |
| zero-shot-tokenizer-transfer_2405.07883v2 | 22 | 2.6 | 14.2 | 28 (18) | 28 (20) | 14 | 9 | 12 |
| **Total** | 623 | 93.1 | 666.9 | | | 270 | 125 | 251 |
