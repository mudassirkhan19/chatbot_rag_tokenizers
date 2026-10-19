# 0050. Named dense tables and a configurable embedder; `dense` becomes `dense.bge-small`

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md).

## Context
Spec #55 picks an embedding model with evidence, so it scores several dense models on the Evaluation set. In [0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md) there is one `[dense]` table, and the embedder's pooling ([CLS]) and token limit (512) are constants in code. Adding a model would mean changing code, and a second model could not sit next to the first. Slice #56 is the prefactor: after it, adding a model is only a config change.

The full-corpus bge-small index took 818 s to embed on MPS. Renaming the retriever should not make us embed it again.

## Decision
**Named dense tables.** `config/retrieval.toml` has one `[dense.<name>]` table per model. The retriever's name, used by `--retriever`, the index record and the eval report, is `dense.<name>`. Today's baseline is `[dense.bge-small]`, and for now it is the only table. A table's name is lower-case letters, digits and dashes.

**Every table states how its model is used**, beside its pin (repo, revision, sha256 of `model.safetensors`):
- `pooling`: `cls`, the last layer's [CLS] vector, or `mean`, the last layer's mean over the tokens that aren't padding. Both are L2-normalised.
- `max_tokens`: a longer text is cut to its first `max_tokens` tokens.
- `query_instruction`: put in front of every query and never in front of a Chunk. `""` means none.

All fields are required. A bad pooling, a revision that isn't a 40-hex commit, a weights hash that isn't 64 hex digits, a missing or mistyped field, or a `max_tokens` below 1 stops loading with a message naming the table, e.g. `[dense.bge-small] pooling 'max' is not one of cls, mean`. A table in the old flat `[dense]` form is named, and the message says to give each model its own `[dense.<name>]` table.

**The embedder boundary takes the settings from config.** `load_embedder` takes an `EmbeddingModel` (the pin, the pooling and the token limit) instead of a pin plus constants. It still returns one L2-normalised float32 row per text. The real embedder, now `TransformersEmbedder` because it is no longer bge-specific, pools as told. Mean pooling masks out padding, so a text's vector doesn't depend on what it is batched with.

**bge-small keeps its index.** The dense key still hashes the same seven settings, worded and ordered as before: the model, revision, weights hash, query instruction, the pooling *described in words*, the token limit and the search. `cls` is written into the key as "[CLS] vector of the last layer, L2-normalised", as before. The table's name is not a setting and is left out. So `dense.bge-small`'s key is `dense-784e5a0da1b5`, the key of the index built as `dense`. A test pins that key, and on the real cache `index --retriever dense.bge-small` reports it up to date. Re-running `evaluate` gave the same metrics, rankings and ranks; only the retriever's name and the query latencies changed. Two tables with different settings get different folders, and changing one table's revision rebuilds only that one.

**The fake embedder is salted by model id.** The tests' hashed bag of words chooses each token's dimension by the sha256 of the model id and the token, so two dense tables in a test config rank the fixture papers differently. Without the salt, every fake model would give the same rankings, and a test could not tell one table's results from another's.

## Alternatives considered
- **Put the table's name in the key.** A rename would then rebuild an index whose vectors are unchanged. The bge-small rename would cost one 14-minute embed of the full corpus, with an ADR amendment to record it, for nothing.
- **Keep `dense` as an alias for `dense.bge-small`.** Two names for one retriever would show up in the report and the CLI. The rename touches only the README and the eval report, both changed here.
- **A list of tables (`[[dense]]` with a `name` field).** Named tables give each model a stable address in the file and in error messages, and TOML rejects two tables with the same name for us.
- **Pooling as free text, or a key per model family.** Two poolings cover the small encoders in #55's comparison: bge uses [CLS], and e5 and MiniLM use the mean. An unknown value is refused rather than guessed.

## Consequences
- Adding a dense model is one `[dense.<name>]` table. `index` builds it beside the others, and `evaluate` scores it under its name.
- `--retriever dense` no longer exists. The README and the eval report use `dense.bge-small`.
- The `index.json` of the existing bge-small index still records `"retriever": "dense"`, because it was written before the rename. Nothing reads that field back, and a rebuild writes the new name.
- A test that compares two fake dense tables only sees differences in model id and in query instruction: the fake embedder ignores pooling and `max_tokens`. The opt-in test (`RUN_EMBEDDER_TESTS=1`) covers the real embedder for bge-small.
