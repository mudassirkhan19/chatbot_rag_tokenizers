# 0041. Recover numbered headings GROBID left in paragraphs

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
#41: GROBID often doesn't recognise a heading and leaves it in a paragraph. It can sit at the start (`<s>2 Related Work Işık et al. …`), as a paragraph of its own, or at the end of a sentence (`… a finding of 4 Analysis</s>`). The text survives, but every Chunk of the lost Section takes the previous Section's path and context header, so Related Work is cited as the Introduction. The Sections under it lose their parent too. The full-corpus parse audit (`docs/reports/2026-10-18-full-corpus-parse-audit.md`) found this in at least 19 of its 31 papers. It had to be settled before the Evaluation set (#37) names Sections, because `eval-check` (#34) checks each Passage's Section.

The TEI holds no boundary between a heading at the start of a sentence and the text after it. It does hold each sentence's boxes ("page,x,y,width,height"), and a heading is set in larger type than the body lines.

## Decision
- **The TEI reader splits a body `div` at each lost heading** (`parsing/lost_headings.py`), before the Section rules of [0028](0028-element-rules-and-chunk-kinds.md) run. Each heading becomes the head of a new `div`, so numbering, paths, acknowledgements and the appendix start apply to it as to any head. The figure and table citations follow the text they sit in.
- **A heading is recovered only when all of these hold:**
  - A paragraph's first sentence starts with a Section number and a capital (`^\d+(\.\d+)* +[A-Z]`), or a sentence ends with one. The capital rules out "3 models were trained…". A full stop after the number ("2. Let…") is a list item and is never taken.
  - Its boxes are in one type, within 0.3 pt of each other. They are more than 10% taller than the body lines of the document and of the `div`, whichever is taller, and than the rest of the paragraph's lines.
  - The number counts on from the last numbered body Section. It goes up by one or two at some level, any level below starts at 1, and no part is 0. After 2.1 can come 2.1.1, 2.2, 2.3, 3, 3.1 or 4, but not 2.1 again, 1.5, 2.10 or 0.2.
  - The document's own numbered heads of the same height give the glyph width per point of box. The words fill the tall boxes' width to within 10%.
- **The width decides where a heading at the start ends.** Each character is weighted by a rough serif advance width, because a capital is wider than an "i". The candidate whose weight is closest to the boxes' estimate wins. It then drops a trailing word that typically opens a sentence ("In", "We", "The") or is a bare number, and it stops before a Section number ("4.4 … 4.4.1 …" is two headings). Leave-one-out on the corpus's real numbered heads, followed by their paragraph's text, measured how well this works. With plain character counts the right extent is picked 87% of the time. With weighted glyphs it is 97%, and 99% after the trailing-word rule, for estimates within the 10% tolerance. At the end of a sentence the Section number marks where the heading starts, so the width only confirms it.
- **Appendices are skipped.** The reader stops looking once the appendix has begun, because appendices number with letters.
- **Tests at the CLI seam** (`tests/test_parse_lost_headings.py`, against the fake GROBID service) use two committed CC BY fixtures ([0033](0033-cc-by-tei-fixtures-may-be-committed.md)):
  - `lost-heading.tei.xml` (2604.14053v1): a heading at the start of a paragraph becomes its own Section. Sentences that start with a number on body-height lines stay text, and so does a tall heading whose number doesn't continue the Sections.
  - `lost-heading-at-sentence-end.tei.xml` (D18-1278): headings at a paragraph's start and at a sentence's end, and the Section under the second gets it as a parent.
- **It applies by re-chunking.** The Chunks are rebuilt from the cached TEI on every run ([0030](0030-parse-cache-keys-and-determinism-checks.md)), so `just parse` applies it without GROBID calls.

## Alternatives considered
- **Re-parsing with other GROBID settings or another parser.** [0024](0024-grobid-stays-the-parser-after-the-docling-spike.md) keeps GROBID, and the heading model is what misses these heads. Re-parsing would cost the full 1.5 h run and wouldn't fix them.
- **Splitting on the text pattern alone.** The pattern matches list items, footnote marks, table cells and sentences such as "4 Of the three…". The box height and the number sequence are what make it safe.
- **Taking the heading as the words up to the first sentence-like capital.** "2 Related Work Işık et al. (2025)" and "2 Numeracy Case Study: DROP QA This section" can't be cut by case. The width can.
- **Measuring against the paragraph's own lines only.** That misses a heading that is a paragraph of its own, which is the most common shape. It also misses a heading whose paragraph has only one more line.
- **Unnumbered and letter headings** ("Limitations", "A Appendix", the two Korean papers' headings). Without a number there is no sequence check, and run-in headings and figure text look the same. They are left for later.

## Consequences
- Across the 2,708 cached TEI files, the reader recovers about 1,000 headings in about 800 files. About 3,000 Sections get a different path: their own heading, or a recovered parent. No word of text, table or caption is lost. A heading's number glued to a citation, as in `<ref>6</ref>5 Experiments`, now reads as the citation and a heading, where it was the word "65".
- Of 50 recovered headings sampled at random, one long heading broken over two lines was cut short. A rare wrong extent leaves one or two words in the wrong place, the heading or the text.
- The committed parse report is rerun from the cached TEI, and its Section counts change.
