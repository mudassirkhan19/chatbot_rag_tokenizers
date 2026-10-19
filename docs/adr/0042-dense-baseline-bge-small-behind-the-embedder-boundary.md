# 0042. Dense baseline: bge-small behind the embedder boundary, on MPS by default

- **Date:** 2026-10-18
- **Status:** Accepted. Amends [0007](0007-local-llm-judge.md) and [0013](0013-working-worktrees.md) on the `judge` dependency group. Amended by [0050](0050-named-dense-tables-and-a-configurable-embedder.md): `[dense]` is now the named table `[dense.bge-small]`, with its pooling and token limit in config, under the same index key.

## Context
Spec #31 compares BM25 ([0039](0039-retrieval-tracer-bm25-index-and-evaluate.md)) with a dense baseline before the embedding comparison and the chatbot. Slice #35 adds that baseline. It has to:
- run locally and reproducibly, with its pin in config like the chunking tokenizer ([0027](0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md));
- fit the Chunks: at most 350 tokens of text plus a context header, counted with BERT base uncased's WordPiece vocabulary;
- embed the full corpus (2,690 files, 141,360 Chunks) in minutes on the development machine, an M1 Max with 32 GB;
- keep the default tests offline and model-free.

## Decision
**The embedder boundary.** The dense retriever gets vectors only through an `Embedder`: texts in, one L2-normalised float32 row per text out, plus the model id, revision and device it runs with. `embedder.load_embedder(pin)` makes the real one. The tests replace that one function with a hashed bag of words (each token adds 1 to one of 64 dimensions chosen by its sha256), so they never download or load a model.

**The model is `BAAI/bge-small-en-v1.5`.**
- 384 dimensions, 33M parameters, a 512-token limit.
- Its vocabulary is BERT base uncased's, the one the chunker counts with (the opt-in test checks that the two vocabularies are equal). A Chunk's 350 tokens plus its header nearly always fit within 512. In the full corpus, 5 of 141,360 header-plus-text inputs are longer (at most 810 tokens, from long headers), and those are cut to their first 512 tokens. The embedder prints how many inputs it cut.
- `config/retrieval.toml` `[dense]` pins the revision (`5c38ec7c…`) and the sha256 of `model.safetensors`. The weights are checked before loading, and a mismatch stops the run.
- It is used as the model card specifies: the last layer's [CLS] vector, normalised. Each query gets the instruction "Represent this sentence for searching relevant passages: " in front, and Chunks get nothing in front.
- What is embedded is what BM25 indexes: the context header, a newline, then the Chunk's text.

**Search is an exact dot product** over every Chunk's vector, with numpy and no vector database. The full corpus is 141,360 × 384 float32, 217 MB in `vectors.npy` beside a JSON list of Chunk ids. Ties keep corpus order.

**The device is MPS when available, otherwise the CPU.**
- On 2,000 Chunks of the full corpus, CPU and MPS vectors differ by at most 5.1×10⁻⁷ in any dimension. The issue's earlier probe found 4×10⁻⁷. The opt-in test checks, on the fixture papers, that every question gets the same top 10 on both devices.
- On the M1 Max the issue measured 209 Chunks/s on MPS against 54 on the CPU.
- The device is not in the index key, because the vectors don't depend on it in any way that changes a ranking. It is recorded instead: `index.json` has the device the index was built on, and the eval report's timings give the build device and the query device for each retriever (BM25's is always the CPU).

**The cache key.** The dense key hashes the model id, revision, weights hash, query instruction, pooling, token limit and search. A new revision builds a new dense folder and leaves BM25's alone.

**Cost and latency.** The eval report's timings already gave each retriever's build time and its p50/p95 query latency, and they now apply to dense too. For dense, the latency includes embedding the query. The embedder embeds one warm-up text when it loads, so MPS's first-pass kernel compilation isn't counted in a query's latency.

**Dependencies.** torch 2.14.1, transformers 5.20.0 and numpy are now project dependencies, because `index` needs them. The `judge` group that held torch and transformers ([0007](0007-local-llm-judge.md)) is removed. `hack/worktree.sh` no longer has `--judge` / `--no-judge`, since every `.venv` has torch now ([0013](0013-working-worktrees.md)).

## Alternatives considered
- **Another small model**: `all-MiniLM-L6-v2` (384 dimensions, 256 tokens) or `e5-small-v2` (384 dimensions, 512 tokens). MiniLM's 256-token limit would cut most Chunks. E5 is about as good as bge-small on MTEB retrieval, and also shares the BERT vocabulary. bge-small has the better retrieval scores of the two and an instruction for queries only, so Chunks are embedded as they are. The embedding comparison later in #31 can still try others behind the same boundary.
- **A larger model** (bge-base, 768 dimensions): about 3× slower to embed, and double the vectors. A baseline should be cheap. The comparison slice decides whether a larger model is worth it.
- **A vector database or approximate search** (FAISS, ChromaDB, HNSW). At 141k × 384, an exact dot product is one matrix-vector product of a few milliseconds, and it is exact. An approximate index would add a dependency and recall loss for no gain at this size.
- **sentence-transformers.** It would do the pooling and normalising for us. But it is one more dependency over transformers, and pooling by hand is three lines that the ADR can state exactly.
- **CPU only, for bit-identical vectors on every machine.** It is 4× slower. MPS changes no top 10, and the device is recorded.
- **A `dense` dependency group, like the old `judge` group.** It would keep torch out of a plain `uv sync`. But `index` is a core command, and `just init` installs every group anyway, so a group would only add a way to get it wrong.
- **research-bot**, the colleague's earlier project, used as inspiration only. It embeds whole papers with `qwen/qwen3-embedding-8b` (8,192 dimensions) through OpenRouter's hosted API, and stores them in ChromaDB with an HNSW cosine index. We embed Chunks, because a Chunk is what is cited. We run a small pinned model locally, so the index can be rebuilt offline and gives the same vectors later, and no API key is needed. We search exactly, because the corpus is small enough.

## Consequences
- `index` builds both retrievers by default. The first run downloads about 130 MB of weights into the Hugging Face cache. Embedding the full corpus took 899 s on MPS (157 Chunks/s, partly while another job shared the GPU), against 10.6 s for BM25. `--retriever bm25` skips it.
- On the full corpus with the tracer's 3 questions, a dense query takes 33 ms at p50 and 72 ms at p95 on MPS, embedding included. A BM25 query takes 267 ms at p50: its plain-Python postings ([0039](0039-retrieval-tracer-bm25-index-and-evaluate.md)) are slow at 141k Chunks, which the baseline eval report (#38) will show.
- A plain `uv sync` now installs torch, about 300 MB more in `.venv`. Reproducing the corpus from the Snapshot still loads no model.
- `evaluate` loads the model to embed queries.
- MPS and CPU vectors are not bit-identical, so the scores in a dense ranking can differ in the 7th decimal from machine to machine. The eval report prints ranks, not scores, so it doesn't change.
- The embedding comparison in #31 adds embedders behind the same boundary, as other `[dense]`-like tables.
