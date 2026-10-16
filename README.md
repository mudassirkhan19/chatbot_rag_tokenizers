# Tokenizer literature RAG

A grounded chatbot over research papers about tokenization for language models. See `docs/ASSIGNMENT.md` for the brief, `GLOSSARY.md` for the terms used here (Edition, Candidate, Snapshot, …) and `docs/adr/` for the design decisions.

## Setup

```sh
uv sync
```

## Collect the corpus

```sh
uv run chatbot-rag-tokenizers collect
```

This runs the keyword queries in `config/scope.toml` against arXiv and Semantic Scholar, fetches each arXiv Edition's full record, applies the rule pre-filter and the LLM judge, and writes `data/manifest.csv`, with one row per Edition.

- **Reruns are offline.** Every source response and judge verdict is stored in the committed Snapshot (`data/snapshot/`) the first time it is fetched or scored. A rerun reads from there, makes no network calls, loads no model and writes a byte-identical manifest. No API keys are needed.
- **Only missing responses are fetched.** After you add or change a query in `config/scope.toml`, only the new requests go to the network. arXiv is queried at most once every 3 seconds, so the first run spends about 3 seconds per arXiv Edition fetching its record. Semantic Scholar works without a key but throttles the shared pool, so requests are retried with backoff; set `S2_API_KEY` in the environment for faster fetches. The key is sent as a header and never stored.
- **One row per Edition, never per Work.** Candidates from different sources combine only on an exact identifier for that Edition (the arXiv ID for a preprint, the ACL ID or DOI for a venue Edition), and the row lists every Discovery channel that found it. A preprint and its venue Edition stay two rows, each with the `arxiv_id`, `doi`, `acl_id` and `s2_id` that were reported, for the dedup stage to link.
- **arXiv Editions are pinned to their latest Version**, whichever channel found them. `versions` lists every Version with its submission time, and `arxiv_comments` and `licence` (`unknown` when arXiv has none) come from the same arXiv record.
- **Rejected Candidates keep their row.** `relevance_stage` is `rules` and `rule_pattern` names the pattern that fired, or `judge` with the judge's probability and the threshold it was compared with.
- **The judge is a local model.** Candidates that pass the rules are scored by the open-weight model set in `[judge]`: P("Yes") from its next-token logits for "Yes" and "No". The threshold is applied when the manifest is written, so changing it needs no re-scoring. Changing the model, its revision or the prompt invalidates the cached verdicts.

The command prints the counts at each stage. Options: `--config`, `--snapshot` and `--manifest` change the paths. `--refresh` re-scores every Candidate that passes the rules, and `--no-judge` never loads the model, so Candidates without a cached verdict stay `pending`.

Scoring needs torch and transformers, which are kept out of the default install:

```sh
uv sync --group judge
```

The first scoring run downloads the model weights (about 8 GB for the default model) from Hugging Face. Until the full judge run is committed (#11), most Candidates have no cached verdict, so run `collect --no-judge` to rebuild the manifest without the model.

## Tests

```sh
uv run pytest
```

The tests run `collect` offline against a small hand-built fixture Snapshot with cached judge verdicts (`tests/fixtures/`). They fail if anything touches the network, and they never load a model.
