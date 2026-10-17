# 0025. Parse tracer: paragraph packing, a pinned tokenizer, the parse cache and the report

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
Issue #18 is the tracer bullet of the parse step (#14): `parse --files <pdf>...` sends Seed PDFs to the pinned GROBID ([0023](0023-grobid-crf-image-pinned-by-digest.md), [0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)) and turns body text into Chunks that never cross a Section, each with a context header and a citation anchor. Chunks must fit the 512-token limit of the candidate embedding models with room for the header, be counted with one fixed tokenizer, and be cached locally by file hash, since the text is derived from papers whose licences aren't ours. A committed report summarises the run.

Tables, captions, references, appendices and acknowledgements (#19), the quality gate and errors (#20), cache invalidation on a config change and the determinism tests (#21) and the full-text-record input (#22) come later and build on this.

## Decision
- **Modules** (`chatbot_rag_tokenizers.parsing`), as #14 lists them:
  - `grobid`: the parser client. `POST /api/processFulltextDocument` with consolidation off (header, citations, funders), raw citations and sentence segmentation on, and coordinates for `head`, `p`, `s`, `figure`, `formula`, `biblStruct`, `note` and `title`: the request the spike measured. The GROBID version is read from the TEI header (`application/@version`), so no second request is needed and a cached TEI still names its version.
  - `tei`: the TEI reader. It reads only content the spike showed to be stable: the title, the abstract (a Section titled "Abstract"), and each body `div`'s head and `s` sentences, with pages from their coordinates. It never reads `application/@when`, funders or graphics.
  - `chunker`: a pure function of the document, the file's identity, the token budget and a token counter.
  - `cache`, `report`, `inputs` (where files and pinned ids come from) and `pipeline` (the loop that ties them together).
- **Section paths are rebuilt from the numbers.** GROBID's Sections are flat. A numbered Section sits under every Section whose number is a prefix of its own and that the paper has: 5.2.2 under 5 and 5.2, but 3.1 directly under the title when GROBID lost Section 3. An unnumbered head (usually a run-in paragraph heading) sits under the last numbered Section. A `div` with no head continues the Section before it. Path elements are the heading as printed, "3.1 Subword Embedding Computation".
- **Packing.** Within a Section, whole paragraphs are packed in order while the joined text stays within the budget; paragraphs are joined by a blank line. A paragraph over the budget is cut into its sentences (GROBID's `s` elements), which are packed the same way, joined by a space. A sentence over the budget, which happens when GROBID misses a boundary or turns a table into one long run of cells, is cut between words as a last resort, so no Chunk is ever over the budget. Chunks don't overlap.
- **Budget: 350 tokens of text**, counted without special tokens and without the header, so a Chunk plus a header of a few dozen tokens fits 512.
- **Tokenizer:** the WordPiece tokenizer of `google-bert/bert-base-uncased` at revision `86b5e09`, used through the `tokenizers` library. Its `tokenizer.json` (466 kB, Apache 2.0) is committed under `config/tokenizers/` and checked against its sha256 on load, so counting needs no network and no Hugging Face cache. Truncation and padding are switched off, so a count sees every token.
- **Chunk shape** (one JSON object per line, sorted keys): `chunk_id` (the file hash's first 16 hex digits and a 4-digit sequence number within the file), `pinned_id`, `version`, `file_sha256`, `section_number`, `section_title`, `section_path`, `appendix` (always false until #19), `kind` (`text`), `page_start`, `page_end`, `header` ("title › Section path") and `text`, `token_count`. The pinned id is the Edition id pinned to a Version, as `fetch` names files ([0015](0015-pdf-fetcher-pinned-files-and-hashes.md)): `2112.06598v2`, with `version` `v2`; a venue Edition's `version` is empty.
- **Pinned ids from file names** for `--files`: a Seed name `<seed>_<arXiv id>vN.pdf` drops its prefix; any other name is taken as `fetch`'s file name for the pinned id. The sha256 is computed from the bytes on each run.
- **Parse cache:** `data/parse-cache/` (gitignored, `--cache`), one folder per file sha256, holding `<parser key>.tei.xml` (the raw TEI as GROBID sent it) and `<parser key>.chunks.jsonl`. The parser key is `grobid-<tag>-<first 12 hex digits of the image digest>`, so a new image never reads an old parse. A file whose TEI is cached is never sent to GROBID again. Its Chunks are rebuilt from the cached TEI on every run, which takes milliseconds and means they always match the current code and config.
- **Parse report:** `data/parse-report.md` (`--report`), committed. It gives the image reference and tag, the GROBID version from the TEI, the chunking config, one line per file (pinned id, sha256, status, Section count, Chunk count) in pinned-id order, and the totals. Nothing in it depends on time or the machine. The first committed report is of the 34 Seed PDFs.

## Alternatives considered
- **A fixed-size sliding window with overlap.** It would cut paragraphs and sentences in the middle and put the same text in two Chunks, which the retrieval stage asked to avoid (#14, stories 18 and 19).
- **Character budgets.** Simpler, but the limit that matters is the embedder's token limit, and the ratio of characters to tokens varies a lot with formulas and numbers.
- **tiktoken (`cl100k_base`).** It downloads its vocabulary on first use, which the offline tests forbid, and it belongs to OpenAI's hosted embedders, not to the open models we expect to compare. BERT's WordPiece vocabulary is shared by BGE, E5 and MiniLM, so counts are close to what those models see. The embedding stage may change it; it is one config entry and one file.
- **Downloading the tokenizer at run time, pinned by revision.** One more network dependency and download path, for a 466 kB file.
- **Our own sentence splitter.** GROBID already segments sentences with `segmentSentences=1`. Its splitter is not perfect (it breaks "max. 4GiB"), but a second splitter would disagree with the page coordinates GROBID gives per sentence.
- **Caching the Chunks and skipping re-chunking.** It saves milliseconds but needs the config hash in the key to stay correct; #21 adds that key. Rebuilding every run is correct without it.
- **Prior work (research-bot).** It chunks Markdown from Marker with no Section boundaries, pages or pinned files ([0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)). We keep nothing from it here.

## Consequences
- **Plug-in points for the next tickets:**
  - #19 adds element rules in `tei.read_tei` (tables, captions, the bibliography, the appendix flag, acknowledgements, formulas) and new Chunk kinds in `chunker.chunk_document`. It adds the bibliography to the cache and table and caption counts to the report's `FileResult`.
  - #20 adds the quality gate between `read_tei` and `chunk_document` in `pipeline.parse`, statuses and reasons in `FileResult`, and the error handling around `GrobidClient.process`.
  - #21 adds the chunking-config hash to the Chunks' cache path in `ParseCache`.
  - #22 adds a second source of `InputFile`s to `inputs`, from the full-text record.
- GROBID's sentence splitter decides where a long paragraph may be cut, including its mistakes.
- Chunks hold the in-text citations as printed, and GROBID leaves no space between adjacent `ref`s ("2016;Caliskan"). That doesn't hurt retrieval much and is left as GROBID gives it.
- On the 34 Seeds, with the GROBID container already up, the first run took about 105 s and a cached rerun about 3 s. It made 1,478 Chunks, all within 350 tokens and all with page anchors.
