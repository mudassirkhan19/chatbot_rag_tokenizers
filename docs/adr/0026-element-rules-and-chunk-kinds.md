# 0026. Element rules: tables, captions, references, appendices and the Chunk kinds

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
The parse tracer ([0025](0025-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md)) turned only body paragraphs into Chunks. Issue #19 (part of #14) asks for a rule for each kind of element GROBID finds. Numbers that appear only in tables and findings stated only in captions must be retrievable. Bibliographies, which mention every keyword, and acknowledgements must stay out of search. The bibliography is still worth keeping for the duplicate stage. The assignment also asks us to explain what happens to tables, equations, figure captions and reference lists.

The spike ([0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)) showed how GROBID 0.9.1 lays these out. Figures and tables come at the end of `body` or of the annex, with no link to a Section. In-text `ref`s point to them by id, or carry only the printed number. Appendices are often in `body` and not in `div[@type="annex"]`, with the letter in the head text and no `@n`. GROBID finds about half the tables, and some of the ones it finds have wrong rows.

## Decision
The rules are applied in the TEI reader (`parsing/tei.py`). The Chunker only packs what the reader gives it.

- **Tables** become Chunks of kind `table`. The first line names the table, its Section and its caption: `Table 2 (5.1 Transferring RoBERTa): Results from fine-tuning…`. Then comes one line per row, with cells joined by ` | `. Empty cells are kept, so the columns still line up, and a spanning cell is one cell. The Section heading goes in the text as well as in the context header, so a search for a table's numbers sees what they measure. Pages come from the caption's sentences and the `table` element's coordinates.
  - **A table over the token budget** is cut between rows, and each part repeats the first line and the table's first row. GROBID doesn't mark header rows, but the first row holds the column heads in 40 of the 41 Seed tables that are cut, and without it a later part's numbers don't say what they measure (#23). When the first line and the first row together would take more than half the budget, only the first line is repeated. When the first line alone would too, nothing is repeated, and the whole table is cut like a paragraph. A row over the budget is cut between words. #14 says "one Chunk per table", but a Chunk over the budget would be truncated by the embedder and lose the numbers we want to find. So "one table, one or more table Chunks, each naming the table" is the closest rule that keeps every Chunk within the budget.
- **Figure captions** become Chunks of kind `caption`, packed like a paragraph. They are prefixed `Figure 5: ` unless GROBID kept the label in the caption text already. A figure with an empty caption gives no Chunk. Graphics are never read, because their coordinates move between parses (0024).
  - **A caption over the token budget** is cut at its sentences (and a sentence over the budget between words), like a paragraph, so it becomes several `caption` Chunks of the same Section, and only the first carries the label. This departs from #14's "one Chunk each" for the same reason as tables: a Chunk over the budget would be truncated by the embedder. It doesn't happen on the Seeds: the longest of the 181 captions is 315 tokens (vocabulary-scaling, both Versions), within the 350-token budget, so every Seed caption is one Chunk. Repeating the label on each part, as tables do, was left out until a real caption needs it.
- **Each table and caption belongs to one Section.** It is the first Section whose text cites the element's `xml:id`. If none does, it is the first Section that cites its printed number in a `ref` of the same type with no target. If none does that either, it is the last Section that starts on or before the element's first page. Within a Section, the text Chunks come first, then its tables, then its captions, each in document order.
- **Reference lists** give no Chunks. Each file's bibliography goes to the parse cache as `<parser key>.bibliography.jsonl`, one line per `biblStruct` in order, with the following fields:
  - `key`: GROBID's `b0`, `b1`, …;
  - `title`: the analytic title, or the monograph's when there is no analytic part;
  - `authors`: forenames and surname as GROBID split them;
  - `year`: from `date[@type="published"]/@when`;
  - `identifiers`: every typed `idno`, such as `DOI` and `arXiv`, as printed, plus `url` from a `ptr`;
  - `raw`: the printed reference, from `includeRawCitations`.

  Nothing is normalised. That is the duplicate stage's job.
- **Equations** stay inline. A block `formula` joins the paragraph before it as one more sentence, with GROBID's lossy linearisation and its label (`u x = g∈G (x) w g`). It starts a paragraph only when nothing comes before it in its `div`. So a long paragraph is never cut inside a formula, and the sentence that leads into it stays next to it. Inline maths was already part of the sentence text.
- **Acknowledgements** are dropped: the `back` acknowledgement div, which is never read, and a body Section headed "Acknowledg(e)ments", together with the headless divs that continue it.
- **Appendices** are Sections with `appendix: true`, a flag that every Chunk from them carries:
  - **In the annex:** every Section in `back/div[@type="annex"]`. One exception: an annex Section numbered like `5.4` under a body Section 5 is a body Section that GROBID misplaced (WECHSEL v1, subword regularisation), so it stays in the body's numbering and isn't flagged.
  - **In the body:** a Section whose unnumbered head starts with a letter from A to H opens the appendix, as do "B.2 Data", "C. Examples" (ICML prints a full stop after the letter) and "Appendix …". The head must come after at least one numbered body Section and must not end in a full stop, since run-in headings like "A closer look." do. Every later body Section is an appendix Section too, including run-in headings and NeurIPS checklist items. Letters up to H can open the appendix because GROBID sometimes loses Appendix A's heading (tokenization-counts starts at B).
  - **Numbering:** appendix Sections take their number from the head's letter ("A Grid search over k and τ" becomes number `A`, title "Grid search over k and τ"), and they number their own Sections: `A.1` sits under `A`, never under a body Section.
- **Front matter** other than the title and the abstract isn't read: authors, emails, affiliations, keywords and funders. The abstract stays a Section titled "Abstract".
- **Footnotes** aren't read. GROBID collects them at the end of `body`, outside every Section, so they have no Section to be cited by. They are mostly URLs and asides.
- **Other back matter** (`div[@type="availability"]`, funding `listOrg`) isn't read either.
- **Chunk shape** changes only in `kind`, which is now `text`, `table` or `caption`. `appendix` is now set. Every other field is as in 0025, and table and caption Chunks have the same context header and citation anchor as text Chunks.
- **The parse report** gives, for each file, its table Chunks and caption Chunks beside its Sections and Chunks, and their totals. GROBID misses about half the tables (0024), so the per-file count shows where table recall is low.

## Alternatives considered
- **One table Chunk regardless of size.** This is #14's literal wording. But big tables, such as WECHSEL's Table 2 at about 790 tokens, would be truncated at embedding. Cutting the table without repeating the caption would leave parts that nobody can tell apart.
- **Tables as Markdown.** Header separators and pipes on both ends add tokens and nothing for retrieval. GROBID doesn't say which row is the header anyway.
- **Captions inside the text Chunks of their Section.** They would break up the reading order and could push a paragraph into the next Chunk. As separate small Chunks, they can be found on their own, which is what #14 asks.
- **Placing tables and figures by page only.** Cheap, but a table at the top of a page often belongs to the Section that ends there. Citations are the better signal, and the page is the fallback.
- **Marking appendices from `div[@type="annex"]` alone.** This is wrong for 3 of the 34 Seeds, where most appendices are in `body` (0024).
- **Formulas as their own paragraphs, or dropped.** A paragraph of its own could be packed away from the sentence that introduces it. Dropping it loses the symbols that searches for a method may use.
- **Keeping footnotes as Chunks of the Section that cites them.** It is possible through their `ref[@type="foot"]`, but they add little, and none of the tickets asks for them. This can be revisited if the evaluation finds answers in footnotes.
- **Prior work (research-bot).** Its Marker Markdown keeps tables and captions inline in the page text and keeps reference lists ([0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)). We keep nothing from it.

## Consequences
- Run on the 34 Seed TEI files from the spike, at 350 tokens, the rules give the following:
  - 1,640 text, about 235 table and 181 caption Chunks, none over the budget;
  - 2,056 references;
  - appendix Sections in 25 files. In each, the appendix starts right after the Conclusion, Limitations or Ethics Section, and no body Section after it is flagged by mistake.
- **Seed run (#23).** `parse --files data/pdfs/seeds/*.pdf` against the pinned GROBID gives 889 Sections and 2,055 Chunks: 1,640 text, 234 table and 181 caption Chunks, none over the budget. The committed `data/parse-report.md` is that run. Two runs from empty caches, with the files in opposite orders, give a byte-identical report, Chunks and bibliographies. Of the 140 tables GROBID read, 41 are over the budget and cut, into 2 to 8 parts. Cutting is sound on the Seeds: every part names its table and Section, every row after the first is in exactly one part, in order, and with the first row repeated, 40 of the 41 cut tables keep their column heads in every part. The exception is ByT5 v3's Table 4 (2105.13626v3), whose caption GROBID filled with table cells: its first line takes more than half the budget, so it is cut like a paragraph.
- **Spot-checks against the PDFs (#23)** of Sennrich v5, BPE-dropout v2, WECHSEL v2, languages-cost v1, how-good-is-your-tokenizer v1 and vocabulary-scaling v3: anchor pages, Section paths and the appendix flag match the PDFs for every text, table and caption Chunk checked, and the appendix starts in the right place in each. The mistakes found are GROBID's, not the rules':
  - a table's rows can belong to another table (Sennrich v5's Table 2 holds Table 1's rows, and Table 3 has no rows, its cells being a text Chunk in 5.1), and a caption can be wrong (BPE-dropout v2, Table 1);
  - a formula fragment can become a Section head (Sennrich v5, "←h m ).");
  - text from appendix figures can join a body Section, which then spans pages 10 to 18 (languages-cost v1, "Language statistics of ChatGPT training data").
  
  Tables GROBID misses turn up as text Chunks that are mostly numbers: 172 of the 1,640 text Chunks have more than 35% of their words numeric. They are kept for now (#24).
- How good the table Chunks are depends on GROBID. Tables it misses still turn up as noise paragraphs, and some rows hold text from another caption (Sennrich v5, Table 2). The quality gate (#20) doesn't judge tables.
- When GROBID splits an appendix between `body` and the annex, the Sections come in TEI order: the body part first (how-good-is-your-tokenizer v1: A.2, B, C, then A, A.1).
- An unnumbered body head that starts with "A " to "H " and doesn't end in a full stop, after the numbered body, opens the appendix. A run-in heading like "A Simple Baseline" late in a paper would be misread. None of the Seeds has one.
- The bibliography is stored but not yet used. The duplicate stage reads it from the cache.
