# 0041. The Passage matcher, eval-check and the v1/vN calibration

- **Date:** 2026-10-18
- **Status:** Accepted. Since [0051](0051-work-grouping-in-collect.md), `eval-check` takes an Edition's Work from the manifest's `work_id`, and the identifier rule only where it is blank.

## Context
Spec #31 scores a retriever by whether its top Chunks hold a question's Passages. A Passage is a verbatim quote from one Edition, but any Chunk holding its text answers it, whichever Edition the Chunk comes from. So a v1 Chunk counts for a quote taken from v5, as long as v1 says the same thing. The tracer ([0039](0039-retrieval-tracer-bm25-index-and-evaluate.md)) used a substring stand-in, which misses any reworded Version.

#34 asks for three things:
- the real matcher. A Chunk holds a Passage when at least 60% of the quote's words appear in it in order, and every number in the matched span equals the quote's.
- `eval-check`, which checks the Evaluation set against the parsed text, and an `evaluate` that refuses a set failing it.
- a calibration of the 60% on real Seeds with several Versions.

## Decision
**Normalisation.** Both texts are normalised the same way before they are compared:
- NFKC, then case folding.
- Citations are dropped: numbered ones such as `[47]`, `[23,55]` or `[3-5]`, and any parenthesis holding a year, such as `(Gage, 1994)`, `(2012)` or `(Jean et al., 2015a)`.
- A word hyphenated at a line end is joined again. So is a hyphen between two letters, so "Ger-man" and "German" are one word.
- The text is then cut into words the way BM25 cuts it: runs of letters and digits, with "0.05" and "1,000" kept whole.
- A word holding a digit counts as a number.

**The rule** (`evaluation/matching.py`):
1. `difflib.SequenceMatcher` lines the quote's words up with the Chunk's, in order. Its blocks of at least two words are kept, and a number may also match on its own.
2. Of those blocks, the run covering the most words within twice the quote's length of the Chunk is kept.
3. The Chunk holds the Passage when the kept blocks cover at least `threshold` of the quote's words, and every number in the quote is in a block.
4. **Edge rule.** When the blocks run into the Chunk's first or last word, the quote's words beyond that edge are left out of the share. The blocks must then cover at least `edge_min_words` (6) words.

`config/evaluation.toml` holds `threshold = 0.65` and `edge_min_words = 6`. `eval-check` and `evaluate` read the same rule. The spec's 60% is not kept: the calibration below puts the line at 65%.

Why each part is there:
- **Blocks of two words.** A single shared word, such as "the", is no evidence of the same sentence.
- **The window.** Without it, pairs such as "our baseline", "is a" and "model with a", scattered over a 300-word Chunk, held "Our baseline WDict is a word-level model with a back-off dictionary." A reworded sentence stays about as long as it was.
- **Only the quote's numbers are checked.** A changed number leaves the quote's number out of every block, so the quote side catches it. The spec's wording also checked the Chunk's side of the span, but that failed a v1 Chunk that only added list markers ("which (1) uses … and (2) learns") and changed nothing the quote says.
- **A number may match alone.** Rewording around a number ("rare (0.05% of test tokens)" against "rare (about 0.05% in the test set)") leaves it a block of one.
- **Citations are dropped.** In 2407.13623 v3 nearly every citation is renumbered from v1 ("[43]" became "[47]"). With citations kept, all 5 calibration quotes with a citation failed the number rule against an otherwise identical v1 sentence. A citation's number is not a finding.
- **The edge rule** makes a quote that runs across a Chunk boundary match both Chunks, since Chunks never overlap. This rule was chosen with the developer over two others. Matching against the Chunk plus its neighbours would make the matcher depend on Chunk order. A plain 60% rule would match neither half of an even split.

**`eval-check`** (`evaluation/check.py`) fails a set with:
- a Passage whose quote, normalised, is not a run of words in its named Edition and Section. Edition means the Passage's `edition_id` is the Chunk's pinned id. Section means the Section path joined with " › ", as the context header shows it. The Section's Chunks are joined, so a quote across a Chunk boundary is found.
- a quote over 300 characters.
- a follow-up without a history or a rewrite, or another question type with either.
- an answerable question with no Passage, or an unanswerable one with a Passage.
- a multi-paper question whose Passages all come from one Work.

It also prints:
- for each question, the share of its distinct words that are in its Passages' quotes (for a follow-up, of its rewrite too);
- for each Passage, the number of Chunks holding it, by pinned id.

It lists every failure, then exits non-zero. The loader now checks only that each line reads as a question (JSON, known fields and types, unique ids), so a malformed question is reported with all the others instead of stopping the load.

**Works**, for the multi-paper check:
- The manifest's `work_id` stays empty until the duplicate stage. Until then, Editions that share an arXiv id, DOI or ACL Anthology id are one Work (`evaluation/works.py`). An arXiv preprint records its venue DOI and ACL id, so `1508.07909v5` and `P16-1162` are one Work.
- This can miss a duplicate with no shared identifier, but it never joins two Works. The hand-checked Work groups of spec #31 replace it.

**The gate.** `evaluate` runs the same check first and stops on any failure, naming each one and pointing to `just eval-check`. On the full corpus (145,074 Chunks) the check takes about 20 s: every Chunk is cut into words once, and a bound on shared word pairs rules most Chunks out before they are aligned.

## Calibration
`data/eval/calibration.jsonl` holds 48 quotes from the latest Version of three CC BY 4.0 Seeds:
- Sennrich et al., *Neural Machine Translation of Rare Words with Subword Units*, 1508.07909v5 against v1;
- Minixhofer et al., *WECHSEL*, 2112.06598v2 against v1;
- Tao et al., *Scaling Laws with Vocabulary*, 2407.13623v3 against v1.

A fourth CC BY Seed with two parsed Versions, 2402.01035, has no sentence that changed between them.

The quotes were picked from sentences aligned between the two Versions. Each was then labelled by reading both Versions:
- 26 *reworded*: v1 says the same, with the same numbers, in other words. These should match.
- 5 *citation*: the same sentence with a renumbered or re-dated citation. These should match.
- 4 *number*: a figure in the finding changed, such as "an ensemble of all 8 models" against v1's "4". These should not match.
- 1 *different*: v1 says much the same words about another subject ("word-level models are unable to translate…" against "a back-off dictionary is unable to translate…"). It should not match.
- 12 *absent*: content added after v1. For each, it was checked that no run of five of its words is in v1. These should not match.

`hack/calibrate_matcher.py` reruns the sweep. For each threshold it gives how many of each kind come out as expected against the v1 file. It also gives how loose the rule is over the whole corpus: how many quotes are held by Chunks outside the quote's Work, and how many such Chunks there are.

| Threshold | reworded | citation | number | different | absent | as expected | quotes held outside their Work | such Chunks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.40 | 25/26 | 5/5 | 4/4 | 0/1 | 12/12 | 46/48 | 21 | 331 |
| 0.45 | 24/26 | 5/5 | 4/4 | 0/1 | 12/12 | 45/48 | 16 | 106 |
| 0.50 | 24/26 | 5/5 | 4/4 | 0/1 | 12/12 | 45/48 | 14 | 54 |
| 0.55 | 24/26 | 5/5 | 4/4 | 0/1 | 12/12 | 45/48 | 10 | 24 |
| 0.60 | 22/26 | 5/5 | 4/4 | 0/1 | 12/12 | 43/48 | 7 | 21 |
| **0.65** | 22/26 | 5/5 | 4/4 | 1/1 | 12/12 | **44/48** | 5 | 16 |
| 0.70 | 20/26 | 5/5 | 4/4 | 1/1 | 12/12 | 42/48 | 4 | 12 |
| 0.75 | 17/26 | 5/5 | 4/4 | 1/1 | 12/12 | 39/48 | 3 | 11 |
| 0.80 | 15/26 | 5/5 | 4/4 | 1/1 | 12/12 | 37/48 | 3 | 11 |
| 0.85 | 12/26 | 5/5 | 4/4 | 1/1 | 12/12 | 34/48 | 2 | 8 |
| 0.90 | 8/26 | 5/5 | 4/4 | 1/1 | 12/12 | 30/48 | 1 | 6 |

What the sweep shows:
- **The number rule and the absent quotes don't depend on the threshold.** Every changed number fails at any threshold. No absent quote shares more than 29% of its words with v1, except "Again, we observe consistent improvements using WECHSEL on all languages.": its 2 words at a Chunk edge are stopped by `edge_min_words`.
- **Rewording is where the threshold matters.** The reworded quotes score from 0.53 to 1.00 against v1. There is a gap between 0.58 and 0.67 with only the different-subject sentence in it, at 0.64.
- **0.65 sits at the top of that gap.** It keeps the 22 reworded quotes that 0.60 keeps, rejects the different-subject sentence, and leaves fewer quotes held outside their Work (5 against 7). The run starts to lose reworded quotes at 0.70.
- **Below 0.55, the rule is loose.** At 0.40, 21 quotes are held by 331 Chunks of other Works.

**The 4 reworded misses at 0.65:**
- 3 changed more than a third of their words: 0.53, 0.57, and 0.58. The 0.58 one gained a clause in v5 ("which we expect to depend on the language pair and amount of training data") that v1 doesn't have.
- "…shared translation task of WMT 2015." against v1's "…of the 2015 Workshop on Statistical Machine Translation". The aligner pairs "2015" elsewhere, so the number counts as unmatched.

**The 5 quotes held outside their Work at 0.65 are restatements, not noise.** Four are sentences from the BPE paper that other papers repeat almost word for word, such as "the final symbol vocabulary size is equal to the size of the initial vocabulary, plus the number of merge operations". The fifth is the different-subject sentence, which 2207.00552 states again verbatim. `eval-check`'s per-Passage count is how such a Passage shows up in the real set.

## Alternatives considered
- **Exact substring after normalisation** (the tracer). It misses every reworded Version: 0 of the 26 reworded quotes match.
- **Word-set overlap.** research-bot, the colleague's earlier project, is used as inspiration only. It has no Evaluation set and no Passage matching. Its only text comparison is for titles: a containment test, else a Jaccard overlap of lower-cased word sets of at least 0.8. That ignores word order and numbers, so it can't tell a v1 sentence saying "4 models" from one saying "8", and over a 300-word Chunk any short quote's words are present somewhere. The in-order blocks, the window and the number rule here address exactly those cases.
- **Character-level fuzzy matching** (edit distance, `rapidfuzz.partial_ratio`). It is one more dependency, and its scores are harder to state as a rule. A number that differs by one digit costs almost nothing.
- **Keeping the 60% the spec proposed.** It matches the different-subject sentence and keeps two more quotes held outside their Work, while matching no more reworded quotes than 65%.
- **Embedding similarity.** It needs a model just to score Passages, and two texts can be close in meaning without holding the same quote.

## Consequences
- **A rerun changes the committed eval report.** `evaluate` now scores with this matcher, and the report's metric definitions describe it. The committed eval report is still the tracer's, until the baseline run (#37, #38) is redone.
- **Setup gains a config file.** `eval-check` and `evaluate` take `--eval-config` (default `config/evaluation.toml`) and `--manifest` (default `data/manifest.csv`, for Works). `evaluate` takes about 20 s longer on the full corpus.
- **Calibration covers only real Version changes.** The Seeds with several Versions are short on Chunk boundaries that split a Passage, so the edge rule's 6 words is set by the fixture tests, not by this sweep.
- **The calibration set is committed.** Its quotes are each under 300 characters, from CC BY 4.0 Versions, attributed above. Rerunning the sweep needs the full-corpus parse cache.
