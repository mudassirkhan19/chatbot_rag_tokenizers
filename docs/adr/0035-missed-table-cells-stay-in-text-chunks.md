# 0035. The cells of a missed table stay in text Chunks and are counted

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
GROBID finds about half the tables ([0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)). The cells of a table it misses don't disappear: GROBID puts them in the paragraphs of the Section around them, so they become `text` Chunks ([0028](0028-element-rules-and-chunk-kinds.md)). Issue #24 asks whether to keep these Chunks, mark them (a kind such as `table-text`) or drop the text Chunks above a numeric-word ratio. They hold numbers someone may search for, but with no row or column labels, and they may crowd out real text for queries made of numbers.

We measured it on the 34 Seed PDFs, at 350 tokens. A word counts as a number when, apart from the punctuation around it, it is digits with `.` or `,` and an optional sign and unit letter (`31.78`, `(+2.8)`, `50k`). 176 of the 1,640 text Chunks have more than 35% of their words numeric (the issue's 172 came from a slightly different word rule). 107 of the 176 are from Tokenizer Unfairness v1 and v2 (2305.15425), whose extended appendix tables GROBID gives as one long paragraph. What the Seeds show:

- **The cells share sentences with prose.** GROBID gives a missed table's cells as `<s>` elements of a paragraph, and often runs them into a sentence of prose or a footnote: "Compared to Kudo (2018), among the 12 BPE BPE-dropout src-only dst-only both 250k 26.94 27.98…" (BPE-dropout v1). 31 of the 176 Chunks also hold at least five 12-word runs of plain prose. Sennrich v5's 4.1 is one: a paragraph of prose, then the cells of Table 1.
- **Lost captions sit among the cells.** 25 of the 176 contain "Table N:" or "Figure N:". For a missed table, that is the only copy of its caption.
- **No threshold separates cells from prose.** Some real sentences are mostly numbers, and are what a search for vocabulary sizes wants: "The choices of vocabulary size are 8K, 10K, 16K, 24K, 32K and 48K." is 46% numeric (Scaling Laws with Vocabulary). A sentence-level test on the share of function words ("the", "of", "are" …) flags block equations, BPE segmentation examples, lists of language names and Swahili examples as cells too. GROBID's box coordinates overlap as well: inline maths gives prose narrow boxes, and some cell runs have wide ones.

## Decision
- **Keep them as `text` Chunks.** The parse stage neither drops, marks nor splits them.
- **Count them in the parse report.** Each file's line gets a Numeric column, the number of its text Chunks in which more than 35% of the words are numbers, and the totals give the sum (`is_mostly_numeric` in `parsing/report.py`). It is a measure only: no Chunk changes. Like the table count (0028), it shows where GROBID lost tables, and the full-corpus run (#11) will show how big the problem is. The 35% is the issue's figure. It is a constant in the report writer and not in the chunking config, because it doesn't change any Chunk and so must not change the chunking key ([0030](0030-parse-cache-keys-and-determinism-checks.md)).
- **The question moves to the retrieval evaluation.** Whether these Chunks reach the top results for queries made of numbers, and whether any is ever the Passage that answers a question, can only be measured once retrieval exists. #26 carries it. If they do crowd out real text, the fix belongs at retrieval: the retriever can compute the same share from the Chunk text and weight it there.

## Alternatives considered
- **Drop text Chunks above the ratio.** This would drop 176 Chunks on the Seeds, with the prose in 31 of them and the only copy of a caption in 25.
- **Mark them with a kind such as `table-text`.** The kind would be wrong for the Chunks that are part prose, and the line between `text` and `table-text` would be a guess until the evaluation measures it. It also adds nothing a retriever can't compute from the text.
- **Filter or split at the sentence level.** Cells and prose share sentences, and the signals tried (numeric share, function-word share, box widths) each catch real prose, equations or examples.
- **Rebuild the missed table from its cells, or cut the stray caption out.** GROBID gives no column or row boundaries for them, and its `figure` for the missed table is often empty or has another table's rows (Sennrich v5, Tables 2 and 3). It is too fragile for the gain.
- **A second parser for tables.** Docling found 94% of the Seed tables against GROBID's 46%, but it was ruled out as the parser on speed (0024). Running it only on pages with missed tables is the fix to try if the evaluation shows these Chunks matter.

## Consequences
- On the Seeds, the parse report's Numeric column sums to 176, in 25 of the 34 files. The Chunks are unchanged.
- The count is a heuristic. It also counts a few prose Chunks dense with figures, and misses the axis labels of figures, which are mostly words. It should be read as a rough measure, not as a list of the bad Chunks.
- Retrieval may still return cell-only Chunks for queries made of numbers until the evaluation decides.
- A new trimmed fixture, `tests/fixtures/tei/missed-table.tei.xml` (Sennrich v5, CC BY 4.0, [0033](0033-cc-by-tei-fixtures-may-be-committed.md)), holds both cases: a 5.1 Chunk of cells only and a 4.1 Chunk of prose followed by cells.
