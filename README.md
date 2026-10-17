# Tokenizer literature RAG

A grounded chatbot over research papers about tokenization for language models. See `docs/ASSIGNMENT.md` for the brief, `GLOSSARY.md` for the terms used here (Edition, Candidate, Snapshot, …) and `docs/adr/` for the design decisions.

## Prerequisites

Setup is supported on **macOS only**. Install these yourself; the repo installs none of them (ADR 0022):

- **uv and just:** `brew install uv just`.
- **A Docker daemon,** such as Docker Desktop, OrbStack or Colima. It must be running for `just init`.
- **[Ollama](https://ollama.com) 0.40.5 exactly,** from its [release page](https://github.com/ollama/ollama/releases/tag/v0.40.5), for the relevance judge. Another version changes the judge's scores, so the judge refuses to run on it (ADR 0021). It must be running for `just init`.

Tested with macOS 26.6, uv 0.10.8, just 1.46.0, Docker 29.2.1 and Ollama 0.40.5. `pyproject.toml` sets the oldest uv the repo accepts (`[tool.uv] required-version`); `uv.lock` pins Python 3.12 and every package.

## Setup

```sh
just init
```

This checks that uv is recent enough, that Docker is installed and that its daemon answers, and says what to install or start if not. Then it installs every dependency group into `.venv` (`uv sync --all-groups --locked`) and pulls the pinned GROBID image unless Docker already has it. Last, it checks that Ollama answers at the version the judge is pinned to, pulls the judge model (`tev1:4b`) unless Ollama already has it, and checks its digest against the pin in `config/scope.toml`. It prints what is ready. It installs nothing system-wide outside Docker's image store and Ollama's model store, and running it again changes nothing.

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
- **Rejected Candidates keep their row.** `relevance_stage` is `rules` and `rule_pattern` names the pattern that fired, or `judge` with the judge's probability and the threshold it was compared with.
- **The judge is a local model.** Candidates that pass the rules are scored by the open-weight model set in `[judge]`: Tev1 4B, a decision model served by [Ollama](https://ollama.com), which gives P("Yes") for the `[judge.decision]` question (ADR 0021). Chat models give P("Yes") from their next-token logits for "Yes" and "No", run with transformers or Ollama. The threshold is applied when the manifest is written, so changing it needs no re-scoring. Changing the model, its revision (for Ollama, the model digest and the Ollama version), the prompt or the decision question invalidates the cached verdicts.

The command prints the counts at each stage, including, per Discovery channel and per source, the Editions nothing else found and how many of those pass the rules and the judge. Options: `--config`, `--snapshot` and `--manifest` change the paths. `--refresh` re-scores every Candidate that passes the rules, and `--no-judge` never loads the model, so Candidates without a cached verdict stay `pending`.

Scoring with the default judge needs Ollama running at the pinned version (0.40.5) with the model at its pinned digest; `just init` checks both and pulls the model (by hand: `ollama pull tev1:4b`). Scoring the full set takes about 1.5 h on an M1 Max. A transformers model in `[[audit.models]]` also needs torch and transformers, which `just init` installs (by hand: `uv sync --group judge`), and downloads its weights from Hugging Face. Until the full judge run is committed (#11), most Candidates have no cached verdict, so run `collect --no-judge` to rebuild the manifest without the model.

## Fetch the full texts

```sh
just fetch --limit 5   # smoke test: at most 5 downloads (uv run chatbot-rag-tokenizers fetch --limit 5)
just fetch             # everything; resumes where it stopped
```

This downloads the PDFs of every `included` row of `data/manifest.csv` into `data/pdfs/`, which is never committed. Run `collect` first. See ADR 0015.

- **Pinned files only.** An arXiv preprint gets its latest Version and, when it has several, v1, from `https://export.arxiv.org/pdf/<id>vN`, never from an unversioned URL. A venue Edition gets its ACL Anthology PDF, or else the first of its OpenAlex `oa_pdf_urls` that serves a PDF. arXiv is asked at most once every 3 seconds, other hosts once a second.
- **Hashes are recorded in the Snapshot** (`data/snapshot/fulltext/pdfs.jsonl`). The manifest's `pdf_files` lists `<file> <sha256>` for each one, and `collect` rebuilds it from the record, so a rerun needs neither the PDFs nor the network. A file already in `data/pdfs/` with the recorded hash is never downloaded again, and a re-download must match the record.
- **Funnel status:** `full text` once every pinned file is fetched; `no_fulltext` when there is no open PDF (no source, or every source answered with an error page). The row stays either way.
- **Errors don't stop the run.** At the end, `fetch` lists every file it couldn't get and exits non-zero. *Upstream drift* means a recorded file is gone or now has a different hash: the source changed, not the pipeline. Delete its line from the record to re-pin it. *Fetch failed* means a file never fetched before couldn't be (a network or server error, or no PDF): nothing was recorded, so rerun.

## Measure the Relevance verdict

The Audit set (`data/audit/audit-set.csv`) is a hand-labelled, stratified sample of Candidates used to choose the judge model and threshold and to report precision and recall. See ADR 0011.

```sh
uv run chatbot-rag-tokenizers audit export   # sample about 180 Candidates with draft labels
uv run chatbot-rag-tokenizers audit label    # check and correct labels on a local page, one Candidate at a time
uv run chatbot-rag-tokenizers audit report   # precision, recall and F1 by threshold, per model
```

- **Export** draws an even share from each stratum (rule rejects, judge rejects, judge accepts, and rule passes still `pending` a verdict, which get no draft), with a fixed `--seed`. Export after the judge has scored the corpus (#11), or most rule passes will be pending. `label` and `reason` start as the pipeline's own verdict, and `draft_label` and `draft_reason` keep it. The export never overwrites an existing file unless you pass `--force`.
- **Label** serves a page at http://localhost:8765. It shows each Candidate's abstract, the pipeline's verdict in plain words, and the current label, and saves each change straight to the file. `labelled_by` records who set each label (`draft`, `agent` or `developer`), and `review_note` says why a row was flagged for checking.
- **Report** writes `data/audit/report.md`. It covers the rule stage alone and rules plus each model in `[[audit.models]]` (the `[judge]` model when there are none) at thresholds 0.1 to 0.9 (`--thresholds` sets others), with a comparison of each model at its best threshold and the scoring time per Candidate. Each row is weighted by the size of its stratum, so the figures describe all Candidates, not the sample. Missing verdicts are scored and cached in `data/audit/verdicts.jsonl` (`uv sync --group judge`); `--no-judge` reports cached verdicts only.

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

The tests run `collect`, `fetch` (against an in-memory web) and `audit export` offline against a small hand-built fixture Snapshot with cached judge verdicts, and `audit report` against a tiny labelled Audit set with fixture verdicts for two models (`tests/fixtures/`). They fail if anything touches the network, and they never load a model. `tests/test_dev_setup.py` also runs `just` to check the recipes, that `init` stops when Docker is missing, and, with a fake `docker` and `curl` on PATH, that `init` pulls GROBID by digest and that `grobid-up` and `grobid-down` behave; it skips without just.
