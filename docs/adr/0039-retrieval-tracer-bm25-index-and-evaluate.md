# 0039. Retrieval tracer: BM25, the index cache and the evaluate harness

- **Date:** 2026-10-18
- **Status:** Accepted. Amended by [0043](0043-recover-numbered-headings-grobid-left-in-paragraphs.md): the index record's corpus fingerprint also hashes the Chunks, so Chunks rebuilt differently under the same config rebuild the index. Amended by [0053](0053-collapsed-ranking-and-collapsed-twins.md): each retriever is also scored on its Collapsed ranking, as a `+collapsed` twin.

## Context
Spec #31 needs a number for every retrieval choice that follows: duplicate handling, the embedding comparison and the chatbot. Its tracer, #33, asks for the thinnest path from an Evaluation set to a committed eval report:
- an `index` command that builds BM25 from the parse cache;
- an `evaluate` command that scores it;
- three hand-written questions on the 34 parsed Seeds.

The choices below are the ones the spec leaves open, or the ones later slices build on.

## Decision
**The corpus is the parse report's parsed files.**
- `index` and `evaluate` read the files the parse report lists as parsed, then read their Chunks from the parse cache.
- They don't read every Chunk file in the cache. The cache keeps Chunks that are no longer in the corpus: files of withdrawn preprints, old pins, and earlier runs ([0038](0038-parse-only-the-files-of-included-editions.md)). Today the local cache holds 2,307 Chunk files, and the report lists 34.
- The report is checked against `config/parse.toml`: the same GROBID image and the same chunking settings. A mismatch, an empty cache, or a file whose Chunks are only under another chunking key stops the run with a message that points to `just parse`.
- `parsing/report.py` writes the report and now reads it back too, so both sides of its format live in one module.

**The index cache** is `data/index-cache/<chunking key>/<retriever key>/`. It is gitignored.
- The chunking key is the parse cache's own key. The retriever key is the retriever's name plus a 12-hex hash of its settings, e.g. `bm25-4e42ab0ca936`. A change to either builds a new folder and leaves the old one.
- `index.json` records:
  - the settings;
  - a fingerprint of the corpus (a hash of the GROBID parser key and the sorted file hashes);
  - the file and Chunk counts;
  - the build time.

  It is written last. If the fingerprint differs, the index is rebuilt: the report gained or lost files under the same config, or a new GROBID image parsed the same files again. The parser isn't in the folder name, because the parse cache keeps only one parse per image and an index over an old one couldn't be reused anyway. An interrupted build leaves no record, so the next run builds it again. Otherwise a rerun says "up to date" and writes nothing.
- `evaluate` never builds an index. It stops and says to run `just index`, so building cost stays in one place and is recorded once.

**The retriever interface.**
- A retriever's config (`RetrieverConfig`) has a name, a key and its settings, and it builds a retriever from Chunks or loads one from its folder.
- A retriever answers `query(text, k)` with up to k Chunk ids and scores, best first, and can save itself.
- Retrievers index the context header, a newline, then the Chunk text. The Chunk keeps the two apart.
- `config/retrieval.toml` lists the retrievers. The dense baseline will be added there.

**BM25**
- Tokens are runs of letters and digits, lower-cased, with a decimal or thousands-separated number kept whole (`\d+(?:[.,]\d+)+|[^\W_]+`). There is no stemming and there are no stop words. "50k", "0.1" and "1,000" are one token each; "59 500" is two, as the text spaces it.
- The idf is Lucene's, ln(1 + (N − df + 0.5)/(df + 0.5)), so it is never negative. k1 = 1.2 and b = 0.75 are the common defaults, and they live in the config.
- Each distinct query term counts once. A Chunk that shares no term with the query is not ranked. Ties keep corpus order, and terms are summed in query order, so rankings are the same on every run.
- It is about 80 lines of plain Python, stored as JSON postings. The index of the 2,055 Seed Chunks builds in 0.1 s, and a query takes about 3 ms. At ~160k Chunks the JSON will be large, but there is still no need for a dependency.

**The Evaluation set** is `data/eval/evaluation-set.jsonl`, one question per line.
- Each line has an `id`, a `type` (`single-paper`, `multi-paper`, `follow-up` or `unanswerable`), the `question` and its `passages`. Each Passage has an `edition_id`, a `section` (the Section path as the context header gives it) and a verbatim `quote`.
- A follow-up also has a `history` (the prior turns, oldest first) and a `rewrite`.
- Loading checks the shape: known types and fields, unique ids, Passages exactly when the question is answerable, and a history and rewrite exactly when it is a follow-up. Checking quotes against the text is `eval-check`'s job, in the next slice.

**Scoring.**
- Passage matching is a stand-in until the real matcher. A Chunk holds a Passage when the quote is a substring of the Chunk's text, after NFKC, case folding and whitespace collapsing are applied to both. The Edition is never compared, so a Chunk from any Edition can hold it.
- Recall@5 is the share of a question's Passages held in the top 5, averaged over questions.
- MRR@10 is 1 / the rank of the first Chunk holding any Passage, or 0 when none is in the top 10.
- Hit@5 is the share of questions with a Passage held in the top 5.
- All metrics use the raw ranking.
- Unanswerable questions are run, for their line and their latency, but are left out of every metric.
- Each follow-up is run three ways: alone; with its history then the follow-up, joined by spaces; and as its reference rewrite. Each way has its own row.
- The *all answerable* row takes each follow-up alone, as a user would type it. A rewriter must then earn its gain.

**The eval report** is `data/eval/eval-report.md`, and it is committed. It has these sections, in order:
- the Evaluation set's path and sha256;
- the chunking config with the file and Chunk counts;
- each retriever's key and settings;
- the metric definitions;
- a results table per retriever and question type;
- a line per question and query (type, rank of first hit, Passages found);
- the timings, last.

Everything above the timings is a function of the inputs, so two runs differ only in that last section.

**The first Evaluation set** has 3 questions, written by the agent and quoting only CC BY 4.0 Seeds: WECHSEL (2112.06598v2) and the BPE paper (1508.07909v5). Each quote is under 300 characters. The quotation ADR the spec plans covers the full set, which will quote papers under other licences.

## Alternatives considered
- **Index every Chunk file in the cache.** This needs no report parsing. But it would index files that are not in the corpus, and nothing would say so.
- **Have `evaluate` build missing indexes.** This saves a command. But build time would then be recorded by whichever command ran first, and a slow dense build would hide inside an evaluate run.
- **`rank_bm25` or `bm25s`.** Both are small libraries. But their tokenisation and idf variants differ from what the report must document, `rank_bm25`'s Okapi idf can go negative on common terms, and our own version is shorter than the code that would pin and explain theirs.
- **A stemmer or stop-word list.** Either would help recall on paraphrases: the first report shows "neighbours" missing "neighbors". But it would blur exact terms like "SentencePiece" that the spec wants to keep distinctive. The dense baseline is where paraphrase recall should come from.
- **Pickle or numpy for the BM25 statistics.** These would be faster to load. JSON is readable and safe to load, and it is fast enough at this size. The dense index will need numpy anyway, and it can revisit this.
- **research-bot**, the colleague's earlier project, used as inspiration only. It retrieves with ChromaDB over paper-level embeddings only: no keyword retriever, no Chunk-level index, and no labelled set or metrics, so its retrieval quality was never measured. We keep BM25 as a baseline and index Chunks, with a key that says exactly what was indexed. The harness is new.

## Consequences
- After every `just parse`, `just index` must be rerun. If it isn't, `evaluate` says so instead of scoring a stale index.
- The parse report's format is now an input. A change to `write_report` must keep `read_report` working, and the tests cover both.
- The dense baseline (slice 4) adds a `RetrieverConfig` and a `[dense]` table. The harness and report don't change.
- The real Passage matcher (slice 3) replaces `evaluation/matching.py` behind the same `holds` function.
- The first report's numbers are low (Recall@5 0.17 over 3 questions). The questions were written without looking at BM25's rankings, as spec #31 intends, so the numbers measure paraphrase, not luck.
