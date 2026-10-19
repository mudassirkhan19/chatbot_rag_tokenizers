# 0055. BM25 + dense hybrids by reciprocal rank fusion, stored as a record that points to their members

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md): a hybrid's index record names its members' keys and its folder holds nothing else.

## Context
Spec #55 picks an embedding model with evidence. The report should also answer a second question: should keyword search sit beside vector search? BM25 finds exact terms such as "SentencePiece" or "0.1"; a dense model finds paraphrases. Slice #58 adds retrievers that combine them, scored by `evaluate` like the others and usable by the `+collapsed` wrapper ([0053](0053-collapsed-ranking-and-collapsed-twins.md)) and the chatbot ([0054](0054-pinned-local-answer-model-and-the-chat-page.md)).

A full-corpus dense index takes 13 to 14 minutes to embed on MPS (818 s for bge-small), so a hybrid must not embed the corpus a second time.

## Decision
**One `[hybrid.<name>]` table per dense table.** `config/retrieval.toml` has `hybrid.bm25+bge-small`, `hybrid.bm25+bge-base` and `hybrid.bm25+openscholar`. The name is lower-case letters, digits, dashes and pluses, so it is quoted in TOML (`[hybrid."bm25+bge-small"]`). A table has three fields, all required:
- `members`: `bm25` and one dense table, by their `--retriever` names. The order matters only for ties.
- `k`: the RRF constant, 60. That is the value Cormack, Clarke and Büttcher (2009) fixed after a pilot run, and it is the usual default; it isn't tuned here, because the Evaluation set is too small to tune on and score on.
- `pool`: how many Chunks each member ranks for a query, 100.

A member that isn't configured, a member that isn't BM25 or a dense table (another hybrid, say), anything but BM25 plus one dense table, or a `k` or `pool` below 1 stops loading with a message naming the table, e.g. `[hybrid.bm25+x] member 'dense.x' is not a retriever in config/retrieval.toml; it configures bm25, …`.

**Reciprocal rank fusion.** A query takes each member's top `pool` Chunks and gives each Chunk the sum of 1 / (k + rank) over the members that ranked it, rank counting from 1. The hybrid ranks by that sum and returns it as the score. A tie goes to the Chunk the member listed first ranks higher, then to the one the second ranks higher, and a Chunk a member didn't rank comes after every Chunk it did. With two members that settles every tie: two different Chunks with the same sum and the same ranks in both members cannot exist. So the issue's last tie-break, corpus order, is never reached and isn't coded. A test fuses a fixture question by hand with k = 1 and a pool of 3: the members share one Chunk, two Chunks tie at 1/3, and the hybrid's ranking and scores are the hand-worked ones.

**A hybrid stores no vectors.** Its folder in the index cache, beside its members' folders under the same chunking key, holds only `index.json`. The record names its members' keys (`"members": {"bm25": "bm25-…", "dense.bge-small": "dense-…"}`), its build time is the sum of theirs and its device is theirs (`cpu+mps` when they differ). `index --retriever hybrid.<name>` builds any member that is missing or stale first, and a rerun builds nothing. `evaluate` loads a hybrid by loading its members from their folders, and stops with the usual pointer to `just index` when a member's index is missing.

**The members' keys are in the hybrid's key.** `describe()` gives the members with their keys, `k`, `pool` and the fusion rule, and the key hashes that. A new bge-small revision therefore gives bge-small and its hybrid new folders and leaves the other hybrids alone.

**Latency covers the whole query.** The harness times `query`, which runs both members' queries and the fusion. The eval report's hybrid line names its members, `k` and `pool`.

## Alternatives considered
- **Score fusion** (a weighted sum of normalised BM25 and cosine scores). BM25's scores are unbounded and depend on the query's length, so the weight would need tuning per collection, and the Evaluation set is too small to tune it on and score on. RRF uses only ranks and has one constant with a well-known default.
- **Store the fused rankings, or copy the members' files into the hybrid's folder.** A hybrid's ranking depends on the query, so there is nothing to precompute, and a copy would double 220 MB per dense table for nothing.
- **Let `index` build a hybrid as a standalone index (`build(chunks)` embedding afresh).** That repeats the 14-minute embed. `HybridConfig.build` still exists, for the retriever interface and a test, but `index` never calls it.
- **Allow any members** (two dense tables, three retrievers). The question #55 asks is about keyword plus vector search, and with two members the tie-break needs no corpus order. A different mix is a new table type when a question needs one.

## Consequences
- Adding a dense model to compare means adding its hybrid table too; the config's comment says so.
- `index` with no `--retriever` now writes three more records, and the eval report has a hybrid section and a `+collapsed` twin of each in every table.
- A hybrid's folder is empty apart from its record. If a member's index is deleted, the hybrid's record is left alone and `evaluate` names the missing member.
- The fake embedder in tests is a hashed bag of words, so the fixture hybrids test the fusion and the wiring, not whether fusion helps. The full-corpus report answers that.
