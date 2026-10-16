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

This runs the keyword queries in `config/scope.toml`, applies the rule pre-filter and writes `data/manifest.csv`, with one row per Edition.

- **Reruns are offline.** Every source response is stored in the committed Snapshot (`data/snapshot/`) the first time it is fetched. A rerun reads from there, makes no network calls and writes a byte-identical manifest. No API keys are needed.
- **Only missing responses are fetched.** After you add or change a query in `config/scope.toml`, only the new requests go to the network. arXiv is queried at most once every 3 seconds.
- **Rejected Candidates keep their row.** `relevance_stage` is `rules` and `rule_pattern` names the pattern that fired. Candidates that pass the rules are `pending` until the LLM judge stage exists.

The command prints the counts at each stage. Options: `--config`, `--snapshot` and `--manifest` change the paths.

## Tests

```sh
uv run pytest
```

The tests run `collect` offline against a small hand-built fixture Snapshot (`tests/fixtures/`) and fail if anything touches the network.
