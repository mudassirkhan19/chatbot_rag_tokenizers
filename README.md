# Tokenizer literature RAG

A grounded chatbot over research papers about tokenization for language models. See `docs/ASSIGNMENT.md` for the brief, `GLOSSARY.md` for the terms used here (Edition, Candidate, Snapshot, …) and `docs/adr/` for the design decisions. `docs/domain-model.html` is a one-page map of the pipeline's business logic, stage by stage, with the numbers and the decisions behind each (open it in a browser).

## Prerequisites

Setup is supported on **macOS only**. Install these yourself; the repo installs none of them (ADR 0022):

- **uv and just:** `brew install uv just`.
- **A Docker daemon,** such as Docker Desktop, OrbStack or Colima. It must be running for `just init`.
- **[Ollama](https://ollama.com) 0.40.5 exactly,** from its [release page](https://github.com/ollama/ollama/releases/tag/v0.40.5), for the relevance judge and the chatbot's answer model. Another version changes the judge's scores and the chatbot's answers, so both refuse to run on it (ADRs 0021 and 0054). It must be running for `just init`.

Tested with macOS 26.6, uv 0.10.8, just 1.46.0, Docker 29.2.1 and Ollama 0.40.5. `pyproject.toml` sets the oldest uv the repo accepts (`[tool.uv] required-version`); `uv.lock` pins Python 3.12 and every package.

## Setup

```sh
just init
```

This checks that uv is recent enough, that Docker is installed and that its daemon answers, and says what to install or start if not. Then it installs every dependency group into `.venv` (`uv sync --all-groups --locked`) and pulls the pinned GROBID image unless Docker already has it. Last, it checks that Ollama answers at the version the judge is pinned to, pulls the judge model (`tev1:4b`) unless Ollama already has it, and checks its digest against the pin in `config/scope.toml`. It does the same for the chat model (`gemma4:e2b-mlx`, about 6.5 GB), pinned in the `[chat]` table of `config/retrieval.toml`. It prints what is ready. It installs nothing system-wide outside Docker's image store and Ollama's model store, and running it again changes nothing.

Run `just` to list every recipe. Each pipeline recipe forwards extra arguments to the CLI, so `just collect --no-judge` is `uv run chatbot-rag-tokenizers collect --no-judge`.

## The GROBID service

The parse step to come (#14) will send PDFs to [GROBID](https://grobid.readthedocs.io/), run as a local Docker container published on localhost only:

```sh
just grobid-up     # start it and wait until http://localhost:8070/api/isalive answers
just grobid-up 300 # the same, waiting up to 300 s instead of the default 180
just grobid-down   # stop and remove the container
```

- **One pinned image.** `config/parse.toml` pins `grobid/grobid:0.9.1-crf` by digest, and `init` and the recipes read it from there, as the parse step will. Docker always uses the digest, so a re-pushed tag changes nothing. The CRF image runs natively on Apple silicon (ADR 0023).
- **Both recipes are safe to rerun.** `grobid-up` leaves a running container from the pinned image on the configured port alone, and replaces a stopped one or one from an older pin or another port. `grobid-down` says so when nothing is running.
- **Failures say what to do.** A missing Docker or a stopped daemon is reported as in `init`. If GROBID doesn't answer in time, `grobid-up` stops with the URL it tried and points to `docker logs chatbot-rag-tokenizers-grobid`. GROBID needs about 4 GB of memory for full-text parsing, so raise Docker's limit if the container is killed.

## Reproduce the committed corpus

The corpus is committed: the Snapshot of every source response, judge verdict and PDF hash (`data/snapshot/`), the manifest (`data/manifest.csv`) and the funnel and channel report (`data/report.md`). **Snapshot date: 2026-10-16**, the day every source query was run. The arXiv records were fetched on 2026-10-16 and 2026-10-17, and the judge scores and PDF hashes were recorded on 2026-10-17 (dates are UTC, as recorded in the Snapshot). To rebuild the manifest and report from the Snapshot, offline and with no API keys, Ollama or Docker:

```sh
git clone https://github.com/mudassirkhan19/chatbot_rag_tokenizers.git
cd chatbot_rag_tokenizers
uv sync --locked              # or just init, which also sets up GROBID and the judge
just collect                  # uv run chatbot-rag-tokenizers collect
git status --short data/      # prints nothing: the manifest and report are byte-identical
```

`collect` reads everything from the Snapshot, makes no network calls and loads no model. It then prints the Snapshot's size, with a warning because it is over about 50 MB (83 MB, 48 MB of it ACL Anthology pages; see ADR 0026). The PDFs are not committed (ADR 0002). `just fetch` downloads them again (about 3.5 GB, roughly 2 h at arXiv's rate limit) and checks each one against its recorded hash. Of the 2,706 included Editions, 2,068 have full text and 636 have no open PDF; 2,067 of those with full text are indexed. 2 are still to fetch: venue PDFs whose hosts were down, so `fetch` reports them and exits non-zero until a rerun gets them.

## Collect the corpus

```sh
just collect   # uv run chatbot-rag-tokenizers collect
```

This runs the keyword queries in `config/scope.toml` against arXiv, Semantic Scholar and OpenAlex, expands one citation hop from each Seed, fetches the ACL Anthology page of each reported ACL ID, applies the rule pre-filter, fetches the full arXiv record of each arXiv Edition that passes it, runs the LLM judge, and writes `data/manifest.csv`, with one row per Edition. Downloading the PDFs is a separate step, `fetch` (below).

- **Reruns are offline.** Every source response and judge verdict is stored in the committed Snapshot (`data/snapshot/`) the first time it is fetched or scored. A rerun reads from there, makes no network calls, loads no model and writes a byte-identical manifest. No API keys are needed.
- **Only missing responses are fetched.** After you add or change a query in `config/scope.toml`, only the new requests go to the network. arXiv is queried at most once every 3 seconds, so the first run spends about 3 seconds per arXiv Edition fetching its record. Semantic Scholar works without a key but throttles the shared pool, so requests are retried with backoff; set `S2_API_KEY` in the environment for faster fetches. OpenAlex needs a free key in `OPENALEX_API_KEY` (from https://openalex.org/settings/api) to page past the first results, so fetching from it stops with an error until one is set; `enabled = false` under `[sources.openalex]` switches it off. Keys are sent as headers and never stored.
- **Discovery is driven by the scope config.** Each keyword query and each Seed is tagged with the scope topic it covers, and each Seed has a one-line reason. A Seed adds its own record, the papers it cites and the papers that cite it (from Semantic Scholar), tagged `seed:<id>`, `seed-references:<id>` and `seed-citations:<id>`. The report shows what this citation expansion adds beyond keyword search.
- **One row per Edition, never per Work.** Candidates from different sources combine only on an exact identifier for that Edition (the arXiv ID for a preprint, the ACL ID or DOI for a venue Edition), and the row lists every Discovery channel that found it. A preprint and its venue Edition stay two rows, each with the `arxiv_id`, `doi`, `acl_id`, `s2_id` and `openalex_id` that were reported, for the dedup stage to link. Venue Editions found by OpenAlex also get its venue name and `oa_pdf_urls`, every open-access PDF it lists, best first.
- **ACL Anthology Editions are venue rows of their own.** Every ACL ID a source reported, directly or as an ACL DOI (`10.18653/v1/…`), becomes a venue Edition named by its ACL ID, with its venue, year, `licence` and `pdf_link` from the Anthology. When only the preprint reported it, the venue row is new and is linked to the preprint only by the `acl_id` and `doi` both rows carry. ACL pages are fetched at most once a second.
- **arXiv Editions that pass the rules are pinned to their latest Version**, whichever channel found them. A rule-rejected one keeps the id its source reported. `versions` lists every Version with its submission time, and `arxiv_comments` and `licence` (`unknown` when arXiv has none) come from the same arXiv record.
- **Rejected Candidates keep their row.** `relevance_stage` is `rules` and `rule_pattern` names the pattern that fired, `withdrawn` for an arXiv preprint whose latest Version is a withdrawal (ADR 0037), `not a paper` for an Edition whose source metadata says it is a thesis, book, manual, dataset, proceedings front matter or another document that is not a journal, conference or workshop paper or a preprint (ADR 0040), `borrowed file` for an Edition whose only file came from an open-access link and has the same bytes as another Edition's file, with no identifier or title linking the two (ADR 0049), or `judge` with the judge's probability and the threshold it was compared with.
- **Included Editions are grouped into Works** (ADR 0051). Two are one Work when they share an arXiv id, DOI or ACL ID, a file's sha256 in the full-text record, or a title (without case, accents or punctuation) together with the first author's surname. `work_id` names the Work with a slug from its Canonical Edition, such as `sennrich-2016-neural-machine-translation`; `canonical` is `yes` for that Edition, the venue Edition when there is one and otherwise the preprint with the latest Version; `survey` is `yes` on every Edition of a Work whose canonical title has survey, review, overview or tutorial as a whole word. Excluded rows leave all three blank. Two Works that share a title but not a first author are a Suspected pair: never joined, listed in the report.
- **The judge is a local model.** Candidates that pass the rules are scored by the open-weight model set in `[judge]`: Tev1 4B, a decision model served by [Ollama](https://ollama.com), which gives P("Yes") for the `[judge.decision]` question (ADR 0021). Chat models give P("Yes") from their next-token logits for "Yes" and "No", run with transformers or Ollama. The threshold is applied when the manifest is written, so changing it needs no re-scoring. Changing the model, its revision (for Ollama, the model digest and the Ollama version), the prompt or the decision question invalidates the cached verdicts.

The command prints the counts at each stage, including, per Discovery channel and per source, the Editions nothing else found and how many of those pass the rules and the judge. It writes the same counts to `data/report.md` as Markdown tables: the funnel (discovered, rejected by the rules, withdrawn from arXiv, not a paper, rejected by the judge, file belongs to another Edition, included, full text, indexed and full text not indexed, with those Editions listed), the Works (Works of several Editions by the weakest signal that joined them, Canonical Editions by kind, Surveys and the Suspected pairs), rule rejections by pattern, per-source and per-channel counts, and what citation expansion adds (ADR 0026). The report is built from the manifest alone, so `fetch` rewrites it too. `collect` then prints the Snapshot's size, with a warning above about 50 MB. If `S2_API_KEY` or `OPENALEX_API_KEY` is set, it also stops with an error should that key's value appear anywhere in the Snapshot.

Options: `--config`, `--snapshot`, `--manifest` and `--report` change the paths. `--no-judge` never loads the model, so Candidates without a cached verdict stay `pending`.

**What `--refresh` does and doesn't do.** `--refresh` re-scores every Candidate that passes the rules with the configured judge, ignoring cached verdicts, and replaces them in the Snapshot. It needs Ollama, like any scoring. It never re-queries a source: stored responses are always reused, so `--refresh` doesn't pick up papers published after 2026-10-16. To collect newer papers, delete a source's stored responses (`data/snapshot/responses/<source>/`) and rerun with the network. That changes the manifest, so commit the new Snapshot with it. Changing the judge's model, pin, prompt or decision question re-scores without `--refresh`, because cached verdicts only count for the judge they were made with. Changing the threshold never re-scores.

Scoring with the default judge needs Ollama running at the pinned version (0.40.5) with the model at its pinned digest; `just init` checks both and pulls the model (by hand: `ollama pull tev1:4b`). Scoring the full set takes about 2.5 h on an M1 Max. Tev1 takes at most 2,048 tokens, so the few abstracts Ollama refuses as too long are cut at a word boundary until they fit. Inputs that fit are never cut (ADR 0025). A transformers model in `[[audit.models]]` runs with torch and transformers, which are installed with the other dependencies (ADR 0042), and downloads its weights from Hugging Face.

## Fetch the full texts

```sh
just fetch --limit 5   # smoke test: at most 5 downloads (uv run chatbot-rag-tokenizers fetch --limit 5)
just fetch             # everything; resumes where it stopped
```

This downloads the PDFs of every `included` row of `data/manifest.csv` into `data/pdfs/`, which is never committed. Run `collect` first. See ADR 0015.

- **Pinned files only.** An arXiv preprint gets its latest Version and, when it has several, v1, from `https://export.arxiv.org/pdf/<id>vN`, never from an unversioned URL. A venue Edition gets its ACL Anthology PDF, or else the first of its OpenAlex `oa_pdf_urls` that serves a PDF. arXiv is asked at most once every 3 seconds, other hosts once a second.
- **Hashes are recorded in the Snapshot** (`data/snapshot/fulltext/pdfs.jsonl`). The manifest's `pdf_files` lists `<file> <sha256>` for each one, and `collect` rebuilds it from the record, so a rerun needs neither the PDFs nor the network. A file already in `data/pdfs/` with the recorded hash is never downloaded again, and a re-download must match the record.
- **Funnel status:** `full text` once every pinned file is fetched; `no_fulltext` when there is no open PDF (no source, or every source answered with an error page). The row stays either way. `index` takes it on to `indexed` (see below).
- **Errors don't stop the run.** At the end, `fetch` lists every file it couldn't get and exits non-zero. *Upstream drift* means a recorded file is gone or now has a different hash: the source changed, not the pipeline. Delete its line from the record to re-pin it. *Fetch failed* means a file never fetched before couldn't be (a network or server error, or no PDF): nothing was recorded, so rerun.

## Parse the papers into Chunks

```sh
just grobid-up                            # start the pinned GROBID service
just parse                                # the recorded files of included Editions (uv run chatbot-rag-tokenizers parse)
just parse --files data/pdfs/seeds/*.pdf  # explicit files instead, such as the Seed PDFs
```

This sends each PDF to the pinned GROBID service and cuts its text into Chunks that never cross a Section (ADRs 0027, 0031 and 0038). It writes nothing to the manifest: the `indexed` funnel status belongs to the indexing stage.

- **Inputs.** By default `parse` reads the full-text record `fetch` writes (`data/snapshot/fulltext/pdfs.jsonl`, `--snapshot`) and the PDFs in `data/pdfs/` (`--pdfs`). It parses a recorded file only when an included row of the manifest (`--manifest`) lists it in `pdf_files`, so the files of excluded Editions, such as withdrawn preprints, and Versions an Edition is no longer pinned to are skipped. Editions recorded as having no open PDF are skipped too. A recorded file that is missing locally, or whose bytes don't match its recorded hash, isn't parsed: `parse` lists it at the end, suggests `just fetch`, and exits non-zero. Each file is cited by the pinned id the record gives, not by its file name: v1 of the preprint Edition `2112.06598v2` is `2112.06598v1`, and the venue Edition `10.5555/lrm.2022.7` keeps its slash although its file is `10.5555_lrm.2022.7.pdf`.
- **Seeds-only route: `--files <pdf>...`** parses those files instead of the record, which is how the Seed PDFs are used before the full fetch. A Seed PDF named `<seed>_<pinned id>.pdf` (`bpe-dropout_1910.13267v1.pdf`) is cited as `1910.13267v1`; any other file is taken to be named by its pinned id, as `fetch` names files. Its Edition is the latest Version of its arXiv id among the files given (`1910.13267v2` when both are given), or the file itself for a venue Edition. Its sha256 is computed on each run.
- **Outputs.** Chunks go to the parse cache and a summary to the parse report; nothing else changes.
- **Chunks** pack whole paragraphs up to 350 tokens, counted with the pinned BERT WordPiece tokenizer in `config/tokenizers/` (`[chunking]` in `config/parse.toml`). A longer paragraph is split at its sentences. Chunks don't overlap. Each Chunk carries its context header (title › Section path) apart from its text, and its citation anchor: the Edition id, the pinned id and Version of the file, Section and pages (ADR 0032).
- **Element rules** (ADR 0028). Each kind of element GROBID finds follows one rule:
  - *Reference lists* produce no Chunks; each file's bibliography is kept as structured data (title, authors, year, identifiers, the printed reference) in the parse cache.
  - *Tables* become `table` Chunks, linearised row by row (cells joined by ` | `) after a first line with the table's label, Section and caption. A table over the budget is cut between rows, and each part repeats that first line and the table's first row, which holds its column heads.
  - *Figure captions* become one small `caption` Chunk each; a caption over the budget would be cut at its sentences, which none of the Seeds' is. Tables and captions go to the Section that cites them, or else the one their page falls in.
  - *Equations* stay inline in the paragraph text, as GROBID renders them.
  - *Appendices* stay as Sections, marked as appendices in their Chunks, whether GROBID puts them in the annex or in the body.
  - *Acknowledgements* and footnotes are dropped.
  - *Front matter* beyond the title and abstract is dropped; the abstract is a Section.
- **Quality gate.** A file fails when GROBID errors or times out on it, or when it has fewer than 2 Sections or 2,000 characters of Section text (`min_sections`, `min_body_characters` in `[chunking]`). A failed file produces no Chunks; its line in the report gives the reason, and the report counts failures by reason. The failure is recorded in the parse cache, so a rerun under the same parser and config doesn't retry it unless run with `--retry-failed` (ADR 0029).
- **Errors.** One failed file never stops the run: every failed file, including those recorded by an earlier run, is listed at the end and the exit is non-zero. An unreachable GROBID stops the run at once with a pointer to `just grobid-up`. `--limit N` parses only the first N files in pinned-id order, for a smoke test, and writes no report unless `--report` is given, so the committed report stays the full run's.
- **The parse cache** (`data/parse-cache/`, `--cache`, never committed) keeps GROBID's TEI and the bibliography per file sha256 and parser version, and the Chunks per file sha256, parser version and chunking-config hash (ADR 0030). A file whose TEI is cached is not sent to GROBID again, so a rerun only parses new files; a new GROBID digest re-parses it, and a chunking-config change only re-chunks it from the cached TEI.
- **Reproducible.** Files are processed in sorted order and nothing in the output depends on time or the machine, so the same PDFs and config give byte-identical Chunks and report. GROBID's raw TEI is not byte-stable (ADR 0024); the Chunks are.
- **The parse report** (`data/parse-report.md`, `--report`, committed) names the GROBID image and version and the chunking config, and gives a line per file (with its table and caption Chunks, and its text Chunks that are mostly numbers, most of them the cells of a table GROBID missed: ADR 0035) and the totals.
- **The committed report is the full-corpus run** (`just parse`, 1 h 33 min on an Apple-silicon laptop, then rerun from the cached TEI in 4 min once Editions that are not papers were excluded, again once numbered headings GROBID left in paragraphs were recovered: ADR 0043, and again once an `arXiv:`-prefixed duplicate Edition was merged: ADR 0049): all 2,690 pinned files of the 2,067 included Editions with full text, 69,031 Sections and 141,348 Chunks (109,602 text, 18,034 table, 13,712 caption). 1 file fails the quality gate: `2508.13058v1`, a 4-page paper written in Turkish in which GROBID finds 1 Section.

## Index and evaluate retrieval

```sh
just index        # build BM25 and the dense baseline over the parsed Chunks (uv run chatbot-rag-tokenizers index)
just eval-check   # check the Evaluation set's questions and quotes against the parsed text
just evaluate     # score the retrievers on the Evaluation set and write the eval report
```

`index` builds the retrievers, `eval-check` checks the hand-checked Evaluation set, and `evaluate` scores the retrievers on it (ADRs 0039, 0041 and 0042). There are two retrievers, BM25 and the dense baseline, and the corpus is every file the committed parse report lists as parsed: 2,689 files of the full-corpus run.

- **`index` inputs.**
  - The parse report (`data/parse-report.md`, `--parse-report`) decides which files make up the corpus: every file it lists as parsed.
  - Their Chunks come from the parse cache (`--cache`), under the chunking config in `config/parse.toml` (`--parse-config`).
  - Each retriever's settings are in `config/retrieval.toml` (`--config`). `--retriever bm25` or `--retriever dense.bge-small` builds only the retrievers named, and a hybrid's members with it; the default is all of them.
  - `index` stops with a pointer to `just parse` when the report is missing, when the report was written with another GROBID image or chunking config, when the cache holds no Chunks for the report's files, or when it holds them only under another chunking config.
- **`index` outputs.** Each index goes to the index cache (`data/index-cache/<chunking key>/<retriever key>/`, `--index-cache`, never committed) with a record of:
  - its settings;
  - the corpus it was built over;
  - its Chunk count, build time and device.

  `index` also writes the index record (`data/snapshot/index/files.jsonl`, `--snapshot`, committed): the pinned id and sha256 of every file of the corpus. From it, `index` marks each included Edition whose pinned files are all indexed as `indexed` in the manifest (`--manifest`) and rewrites the funnel report (`--funnel-report`). It does this only when the parse report came from the full-text record: after a Seeds-only `--files` run it says so and changes none of them. `collect` and `fetch` apply the same record, so the mark survives a rebuild from the Snapshot. An Edition with one file that failed the parse quality gate stays at `full text`, and the report lists it (ADR 0045).

  A rerun with nothing changed says "up to date" and writes nothing. A change to the chunking config or to a retriever's settings builds a new folder beside the old one. A parse report that gains or loses files rebuilds the index, and so do Chunks that a code change rebuilt differently under the same config.
- **BM25** indexes each Chunk's context header plus its text, so a question naming a paper matches its title.
  - Tokens are lower-cased runs of letters and digits. Numbers are kept, a decimal such as "0.1" as one token, and there is no stemming and no stop-word list, so "SentencePiece" stays a distinctive term.
  - `k1` and `b` are in `[bm25]`.
  - A Chunk that shares no word with the question isn't ranked.
- **The dense baseline**, `dense.bge-small`, embeds the same context header plus text with [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) (ADR 0042).
  - 384 dimensions and at most 512 tokens, with the same uncased BERT WordPiece vocabulary the chunker counts with, so a Chunk of 350 tokens plus its header fits (5 Chunks of the full corpus have headers long enough to be cut; `index` says how many).
  - Each dense model has its own `[dense.<name>]` table, and the retriever is named after it (ADR 0050). `[dense.bge-small]` pins the model's revision and the sha256 of its weights, as the chunking tokenizer is pinned, and says how the model is used: `pooling` (`cls` or `mean`), `max_tokens` and `query_instruction`. All of them are part of the index's key, so a new pin builds a new index for that table only and leaves BM25 and the other dense tables alone. Adding a model to compare is one more table. The first `index` downloads the weights (about 130 MB) into the Hugging Face cache; a weights file with another hash stops it.
- **The candidates** for the embedding comparison (spec #55, ADR 0052) are two more tables, built and scored like bge-small:
  - `dense.bge-base`, [`BAAI/bge-base-en-v1.5`](https://huggingface.co/BAAI/bge-base-en-v1.5), the size control: bge-small's 110M-parameter sibling (768 dimensions), used the same way.
  - `dense.openscholar`, [`OpenScholar/OpenScholar_Retriever`](https://huggingface.co/OpenScholar/OpenScholar_Retriever), the scientific candidate: Contriever-base trained further on peS2o, mean-pooled with no query instruction, as Contriever's reference code does. Its vectors are normalised like the others, so it is scored by cosine rather than Contriever's raw inner product; on the fixture that changes every question's top 10.
  - Both have the chunker's vocabulary and a 512-token limit. Each downloads about 440 MB. The pin is the sha256 of the repo's `model.safetensors`, or of `pytorch_model.bin` when it has none, as OpenScholar's has; the embedder loads the file it checked, and refuses a checkpoint that leaves any weight but the unused pooler untrained.
  - Each query gets the model card's instruction in front ("Represent this sentence for searching relevant passages: "); Chunks don't.
  - A query is scored against every Chunk by exact dot product over the normalised float32 vectors (about 220 MB for the full corpus), with no vector database.
  - **Device.** It runs on MPS when the machine has it, otherwise on the CPU. The two agree to within 1×10⁻⁶ per dimension for each model (2×10⁻⁷ for bge-small, 4×10⁻⁷ for bge-base, 7×10⁻⁷ for OpenScholar), and give the same top 10. The index record and the eval report's timings name the device. On an M1 Max the full corpus embeds at about 200 Chunks/s on MPS against about 50 on the CPU.
- **The hybrids** answer "should keyword search sit beside vector search?" (ADR 0058). Each `[hybrid.<name>]` table fuses BM25 with one dense table by reciprocal rank fusion, and there is one per dense table: `hybrid.bm25+bge-small`, `hybrid.bm25+bge-base` and `hybrid.bm25+openscholar`.
  - A table names its `members` (`bm25` and one dense table), the RRF constant `k` (60) and a `pool` (100). A query takes each member's top `pool` Chunks, gives each Chunk the sum of 1 / (`k` + rank) over the members that ranked it, and ranks by that sum. A tie goes to the Chunk the member listed first ranks higher.
  - A hybrid stores no vectors. Its folder in the index cache holds only its record, which names its members' keys; `index --retriever hybrid.bm25+bge-small` builds any member that is missing first. Its build time is its members' and its latency covers both members' queries and the fusion.
  - A member that isn't configured, a member that isn't BM25 or a dense table, anything but BM25 plus one dense table, or a `k` or `pool` below 1 stops loading with a message naming the table.
- **The Evaluation set** (`data/eval/evaluation-set.jsonl`, `--evaluation-set`) has one JSON question per line:
  - its `id`, its `type` (`single-paper`, `multi-paper`, `follow-up` or `unanswerable`), the `question` and its `passages`;
  - each Passage has the pinned `edition_id` of the file it quotes (such as `2112.06598v2`), its `section` as the context header gives it (`5 Results › 5.3 Is freezing necessary?`) and a verbatim `quote`;
  - a follow-up also has its prior turns (`history`) and a hand-written standalone `rewrite`;
  - an unanswerable question also has its `unanswerable_kind`: `near-miss` when the corpus holds the paper or the measure but not this answer, `out-of-topic` when it is about something else. The chat report splits the abstention rate by it.
- **`eval-check`** reads the same corpus as `index`, the Evaluation set, the matching rule in `config/evaluation.toml` (`--eval-config`) and the manifest (`--manifest`, which links the Editions of a Work). It fails:
  - a Passage whose quote, normalised, isn't in its named Edition and Section (the `edition_id` must be the pinned id of a parsed file, so a quote from an Edition with no parsed PDF fails);
  - a quote over 300 characters;
  - a follow-up without a history or a rewrite, or another question with either;
  - an answerable question without a Passage, or an unanswerable one with a Passage;
  - an unanswerable question without an `unanswerable_kind` of `near-miss` or `out-of-topic`, or an answerable one with any;
  - a multi-paper question whose Passages all come from one Work (the manifest's `work_id`; for a row where it is blank, Editions sharing an arXiv id, DOI or ACL id).

  It prints each question's lexical overlap with its Passages (the share of the question's words in their quotes; a follow-up's rewrite too). It also prints, for each Passage, how many Chunks hold it and in which pinned Editions; a Passage held by dozens of Chunks shows that the rule is too loose for it. Then it lists every failure and exits non-zero, or says it passed.
- **`evaluate` inputs.** The Evaluation set, the same corpus as `index`, and the Work groups.
  - It runs `eval-check`'s checks first and refuses a set that fails them.
  - It stops with a pointer to `just index` when an index isn't built.
- **The Work groups** (`data/eval/work-groups.csv`, `--work-groups`, committed) are the ground truth for the duplicate rate (ADR 0044): the developer assigns each Edition a Work by hand, so the duplicate stage is never scored by its own grouping.
  - Its columns are `edition_id,work_id,survey,title,authors,year,venue,checked_by,note`. Editions with the same `work_id` are one Work; `survey` is `yes` for a Survey's Editions and `no` otherwise. Title, authors, year and venue are for the person grouping and aren't read. `checked_by` names who checked the row by hand, and `note` says why a drafted row needs a closer look (ADR 0047); both are optional.
  - A row with a blank `work_id` has no Work group yet. A Work whose Editions are partly Surveys, an Edition listed twice, or a `survey` other than `yes` or `no` stops `evaluate`.
  - It holds the 154 Editions the two baselines rank in their top 5, in 130 Works. An agent drafted them, and the developer checked them on a local page and approved the draft (ADR 0047 records how). To check new rows, run `uv run python hack/check_work_groups.py`, then open http://localhost:8767. The page shows each Work's Editions with their abstracts and links, and Works that may be the same paper. It can merge, split, rename and flag Surveys, and it refuses a save `evaluate` wouldn't load. The eval report says how many rows have a `checked_by`.
- **The export.** `just evaluate --export-ungrouped ungrouped.csv` also writes every Edition in any retriever's top 5, for any query of an answerable question, that has no Work group, with its title, authors, year and venue from the manifest and `work_id`, `survey`, `checked_by` and `note` left blank. Fill in the first two, add the rows to the Work groups file and check them on the page. Without the flag, `evaluate` still prints the Editions with no Work group.
- **`evaluate` output.** The eval report (`data/eval/eval-report.md`, `--report`, committed) gives:
  - the Evaluation set's sha256, the chunking config and each retriever's settings;
  - a results table per retriever and question type: Recall@5 (per Passage, averaged over questions), MRR@10 (0 when no Chunk in the top 10 holds a Passage) and Hit@5, all on the raw ranking;
  - what crowds the top 5, per retriever, over each answerable question as a user would ask it (a follow-up alone), each as a share of top-5 slots and a share of questions with at least one such slot:
    - **duplicate**: a Chunk from a Work already ranked higher (another Edition, Version or Chunk of it);
    - **restatement**: a Chunk from a Survey, never counted as a duplicate;
    - **mostly numeric**: a text Chunk with more than 35% of its words numbers, as the parse report counts them, with how many of these slots hold a Passage;
  - duplicates and restatement only over the questions whose top 5 Editions all have a Work group, and the list of Editions that have none;
  - the grouping rule's `work_id` scored against the Work groups (ADR 0060): pairwise precision and recall over the Work groups' Editions with the counts behind them, every pair the two disagree on, and every Work whose Survey flag differs from the rule's;
  - one line per question: its type, the rank of its first hit, the Passages found in the top 5, and its duplicate, restatement and mostly-numeric slots (`ungrouped` when an Edition in its top 5 has no Work group);
  - the Comparison (ADR 0061): each retriever against the baseline named in `[comparison]` of the retrieval config (`dense.bge-small`), each `+collapsed` twin against the baseline's twin, over the answerable questions as a user asks them. Per metric (Recall@5 and MRR@10), it gives the questions won, tied and lost, a 95% percentile bootstrap interval on the mean and on the paired difference from the baseline (10,000 resamples, seed 55, the same draws for every retriever), and "within noise" when the difference's interval holds 0. It also gives the rank of each question's first hit, one column per retriever. It names no winner. `evaluate` stops if the baseline isn't among the retrievers it scores;
  - the Cost table, last: each retriever's parameters, vector dimension and index size on disk (a hybrid's are its members' summed), its index build time and device, and its query latency (p50 and p95) and device.
- **Scoring rules.**
  - Each follow-up is scored three ways, in separate rows: alone, after its history, and as its reference rewrite.
  - Unanswerable questions are left out of the metrics.
  - A Chunk holds a Passage when at least 65% of the quote's words match the Chunk's in order, and every number in the quote matches (ADR 0041), whichever Edition the Chunk comes from. Before matching, unicode, case, whitespace and hyphenation are normalised and citations are dropped. The 65% was calibrated on three CC BY Seeds with several Versions; `hack/calibrate_matcher.py` reruns the sweep from `data/eval/calibration.jsonl`.
- **Reproducible.** Two runs on the same index give the same report apart from the times in the Cost table.

The committed Evaluation set has 36 checked questions (ADR 0046), and the committed eval report is the baseline over the full corpus.

## Reproduce the baseline

The baseline eval report (`data/eval/eval-report.md`) gives the "before" numbers for BM25, the dense baseline and their hybrid (ADR 0058), each with its `+collapsed` twin, on the full corpus and the 36-question Evaluation set. These numbers are Recall@5, MRR@10 and Hit@5 per question type and per follow-up mode, the duplicate, restatement and mostly-numeric shares of the top 5, the Comparison with bge-small (wins, ties, losses and paired bootstrap intervals), and each retriever's size, build time and latency. To reproduce it from a clone:

```sh
just init        # dependencies, the pinned GROBID image and the judge model
just fetch       # the pinned PDFs, checked against their recorded hashes (about 3.5 GB, roughly 2 h)
just grobid-up   # start GROBID on localhost
just parse       # every recorded file into Chunks (about 1.5 h on an Apple-silicon laptop)
just index --retriever hybrid.bm25+bge-small   # BM25 (about 10 s), the dense baseline (14 to 22 min on MPS) and their hybrid
just evaluate --retriever bm25 --retriever dense.bge-small --retriever hybrid.bm25+bge-small   # rewrites data/eval/eval-report.md
git diff --stat data/   # only the times in the report's Cost table differ
```

`evaluate` reads the committed Evaluation set and Work groups. On an unchanged index it writes the same report every time apart from the timings, and `git diff` shows only the latency cells of the Cost table. The parse report and index record are committed, so `parse` and `index` also show whether the corpus you rebuilt matches the committed one.

## Chat with the corpus

```sh
just chat        # serves the chat page and prints its URL, http://localhost:8766 (--port sets another)
```

Type a question and the page answers it from the papers. Each question retrieves the top 5 Chunks from the retriever the `[chat]` table of `config/retrieval.toml` names, which is the dense baseline (`dense.bge-small`) until the embedding comparison names its choice. The pinned answer model, `gemma4:e2b-mlx` on Ollama with thinking off and temperature 0, answers from those Chunks only (ADR 0054). An answer takes one to three seconds on an Apple-silicon laptop, and a follow-up a second or two more for its Rewrite.

- **The answer** carries a numbered marker such as `[2]` for each Chunk it uses. A marker that names no retrieved Chunk is struck through as invalid, never dropped.
- **The references** under the answer give, for each cited Chunk, the paper's title, its pinned Edition id with Version, the Section number and title, and the pages.
- **The panel** beside the answer shows each cited Chunk's text and Citation anchor. The retrieved Chunks the answer didn't cite are folded away under it.
- **An Abstention** is the fixed sentence "The papers in this corpus do not answer this question.", which the model is told to write when the Chunks don't answer. The retrieved Chunks are still shown.
- **A follow-up** such as "how much did that help on MMLU?" is understood from the Conversation so far. On every question after the first, the answer model first rewrites it as a standalone question from the earlier questions and answers, and retrieval uses that Rewrite, shown under the question as "Searched as:". The answer model then sees the last three Turns before the Rewrite and its Chunks (`history` in `[chat]`, ADR 0056). **New conversation** forgets the Turns so far, as reloading the page does.

`chat` needs the retriever's index (`just index --retriever dense.bge-small`) and Ollama running with the pinned model (`just init`). When Ollama is stopped, runs another version or lacks the model, `chat` says so in the terminal and on the page, and the next question tries again once Ollama is started.

### Measure the chatbot

```sh
just chat-eval   # asks every question of the Evaluation set; rewrites data/eval/chat-report.md and data/eval/chat-answers.jsonl
git diff --stat data/eval/   # mostly the report's Timings section; see below
```

`chat-eval` asks the chatbot every question of the Evaluation set through the same Conversation code as the page (ADR 0059). Each single-paper, multi-paper and unanswerable question is a Conversation of one Turn. A follow-up is a Conversation that first asks its stored history, the bot answering each, then the follow-up, so its Rewrite is written from the bot's own answers. It refuses a set that fails `eval-check`, and needs what `chat` needs: the retriever's index and Ollama with the pinned model. The full set, 44 Turns, takes about 2.5 minutes on an Apple-silicon laptop with the model cold, and under a minute warm.

The pinned model is not quite deterministic run to run, even at temperature 0 with a fixed seed (ADR 0059): over three runs the retrieved Chunks and the Abstentions were the same, but about a third of the replies changed wording and one grounded verdict flipped. Expect `git diff` to show a line or two of the answers and the report besides the timings.

- **The chat report** (`data/eval/chat-report.md`, `--report`, committed) names the Evaluation set's sha256, the corpus, the retriever, the answer model's pin and settings, and the sha256 of the system prompt and of the rewrite prompt. Then it gives, per question type and overall:
  - the **abstention rate**: on the unanswerable questions, the share answered with the Abstention sentence, split into near-miss and out-of-topic; on the answerable ones, the false-abstention rate;
  - the **grounded rate** over the answers that are not Abstentions. An answer is grounded when it cites at least one retrieved Chunk, every marker names a Chunk retrieved for its Turn, and every number in it (a word that starts with a digit, cut and normalised as the Passage matcher cuts words) appears in a cited Chunk's context header or text. An uncited answer is not grounded;
  - **Recall@5** of the Chunks each question's Turn actually retrieved, with the Passage matcher;
  - one line per question: its type, whether it abstained, whether it is grounded, its invalid Citations, its numbers that no cited Chunk holds, and the Passages in its Chunks;
  - timings, last: p50 and p95 per Turn of retrieval, rewriting (over the Turns that were rewritten) and answering.
- **The answers** (`data/eval/chat-answers.jsonl`, `--answers`, committed) hold every Turn asked, a follow-up's history included, one per line: the question id, the Turn's place in its Conversation and whether it is the scored one, the question and its Rewrite, the retrieved Chunk ids, the model's raw reply, the cited Chunk ids, the invalid markers, the Abstention and grounding verdicts and the Passages found. They hold no timings, so they change only where the model's replies do.

## Measure the Relevance verdict

The Audit set (`data/audit/audit-set.csv`) is a hand-labelled, stratified sample of Candidates used to choose the judge model and threshold and to report precision and recall. See ADR 0011.

```sh
uv run chatbot-rag-tokenizers audit export   # sample about 180 Candidates with draft labels
uv run chatbot-rag-tokenizers audit label    # check and correct labels on a local page, one Candidate at a time
uv run chatbot-rag-tokenizers audit report   # precision, recall and F1 by threshold, per model
```

- **Export** draws an even share from each stratum (rule rejects, judge rejects, judge accepts, and rule passes still `pending` a verdict, which get no draft), with a fixed `--seed`. Export after the judge has scored the corpus, or most rule passes will be pending. `label` and `reason` start as the pipeline's own verdict, and `draft_label` and `draft_reason` keep it. The export never overwrites an existing file unless you pass `--force`.
- **Label** serves a page at http://localhost:8765. It shows each Candidate's abstract, the pipeline's verdict in plain words, and the current label, and saves each change straight to the file. `labelled_by` records who set each label (`draft`, `agent` or `developer`), and `review_note` says why a row was flagged for checking.
- **Report** writes `data/audit/report.md`. It covers the rule stage alone and rules plus each model in `[[audit.models]]` (the `[judge]` model when there are none) at thresholds 0.1 to 0.9 (`--thresholds` sets others), with a comparison of each model at its best threshold and the scoring time per Candidate. Each row is weighted by the size of its stratum, so the figures describe all Candidates, not the sample. Missing verdicts are scored and cached in `data/audit/verdicts.jsonl`; `--no-judge` reports cached verdicts only.

The committed Audit set has 180 Candidates from the first full run:
- Three agents labelled them blind, from title, abstract and link only.
- The developer checked all 37 rows the agents' labels flagged as hard.
- Together with 11 rows checked by hand before the agents ran, the developer checked 48 rows in all (`labelled_by = developer`).

ADR 0020 has the details. ADR 0021 records the judge models compared on it and the choice of Tev1 4B. To compare another model, add it to `[[audit.models]]` in `config/scope.toml`, pinned, and rerun `audit report`.

## Tests

```sh
just test        # uv run pytest; extra arguments go to pytest
just typecheck   # uv run mypy src tests
just lint        # uv run ruff check src tests (errors only, not style)
```

The test against the real GROBID container is opt-in. It parses `data/pdfs/seeds/wechsel_2112.06598v2.pdf` twice from an empty cache and checks that it passes and that both runs give byte-identical Chunks and report:

```sh
just grobid-up
RUN_GROBID_TESTS=1 just test tests/test_parse_grobid.py
```

The test of the real embedder is opt-in too. For every dense table it downloads the pinned model on its first run (about 1 GB for all three) and checks the weights file's sha256, that the model's vocabulary is the chunker's, and that each fixture question gets the same top 10 on the CPU and on MPS over the fixture papers' Chunks. For OpenScholar_Retriever it also checks the embedder's vectors against vectors made as Contriever's reference code makes them, and prints which fixture top 10s change when the vectors are normalised (`-s` shows it):

```sh
RUN_EMBEDDER_TESTS=1 just test tests/test_embedder.py -s
```

The test of the real answer model is opt-in as well. It needs Ollama with the pinned chat model (`just init`). It asks a fixture question through the chat page and checks that the answer cites a retrieved Chunk with no invalid marker and is the same when asked twice, and that an off-topic question gets the Abstention:

```sh
RUN_OLLAMA_TESTS=1 just test tests/test_chat_page.py -k real -s
```

`tests/test_retrieval.py` runs `index` and `evaluate` on Chunks parsed from the CC BY TEI fixtures through the fake GROBID service, with a fixture Evaluation set that has a question of each type and fixture Work groups that join each paper with its venue Edition (`tests/fixtures/eval/`). `tests/test_eval_check.py` runs `eval-check` on the same papers plus a v1 of the BPE paper edited by hand (a reworded sentence, a changed number, a re-dated citation), and checks that `evaluate` refuses a set that fails it. The tests run `collect`, `fetch` (against an in-memory web) and `audit export` offline against a small hand-built fixture Snapshot with cached judge verdicts, and `audit report` against a tiny labelled Audit set with fixture verdicts for two models (`tests/fixtures/`). They fail if anything touches the network, and they never load a model: the dense retriever embeds with a hashed bag of words in their place, and the chatbot answers with a scripted fake model. `tests/test_chat_page.py` runs `chat` over the same fixture papers and posts questions to the page. `tests/test_chat_eval.py` runs `chat-eval` over them with the fake model and reads the chat report and the answers. `tests/test_ollama.py` checks the answer model's requests and pin against a stand-in Ollama server, as `tests/test_ollama_judge.py` does for the judge. `tests/test_dev_setup.py` also runs `just` to check the recipes, that `init` stops when Docker is missing, and, with a fake `docker` and `curl` on PATH, that `init` pulls GROBID by digest and that `grobid-up` and `grobid-down` behave; it skips without just.
