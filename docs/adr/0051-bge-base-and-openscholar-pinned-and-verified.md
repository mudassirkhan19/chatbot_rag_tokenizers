# 0051. bge-base and OpenScholar_Retriever pinned, and checked by the opt-in model test

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0050](0050-named-dense-tables-and-a-configurable-embedder.md).

## Context
Spec #55 compares a scientific model and a size control with the bge-small baseline. The candidates are `OpenScholar/OpenScholar_Retriever` (Contriever-base trained further on peS2o) and `BAAI/bge-base-en-v1.5` (bge-small's 110M-parameter sibling). Each must be pinned and used as its model card or reference code says ([0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md), [0050](0050-named-dense-tables-and-a-configurable-embedder.md)). The comparison is only fair if each model really is used that way.

In [0050](0050-named-dense-tables-and-a-configurable-embedder.md) the pin is the sha256 of `model.safetensors`. OpenScholar_Retriever's repo has no such file: it holds only `pytorch_model.bin`. Its `config.json` names the architecture `Contriever`, a `BertModel` subclass saved without the pooling layer, so transformers loads it as a `BertModel` whose pooler is random.

## Decision
**Two new tables.**

| Table | Repo @ revision | Weights file (sha256) | Pooling | max_tokens | Query instruction |
|---|---|---|---|---|---|
| `dense.bge-base` (size control) | `BAAI/bge-base-en-v1.5` @ `a5beb1e3e68b` | `model.safetensors` (`c7c1988aae20…`) | `cls` | 512 | bge's, as bge-small |
| `dense.openscholar` (scientific candidate) | `OpenScholar/OpenScholar_Retriever` @ `ef4f3120d33b` | `pytorch_model.bin` (`fb5226976e36…`) | `mean` | 512 | none |

The revisions are each repo's latest commit on 2026-10-19 (bge-base's from 2024-02-21, OpenScholar's from 2024-11-19).

**The embedder checks the weights file the repo has.** It looks for `model.safetensors`, then `pytorch_model.bin`, and checks the pinned sha256 against the first one it finds. It then loads the model from that same file (`use_safetensors` set to match), never from another format the repo also holds. A repo with neither file is refused, naming both. Offline, Hugging Face can't tell a file the repo lacks from one it hasn't cached, so an uncached `model.safetensors` also falls through to `pytorch_model.bin`; the hash check then stops a file that isn't the pinned one. The table has no field for the file name: the repo decides it. bge-small's key does not change.

**The embedder refuses a checkpoint that doesn't fill the encoder.** It reads transformers' loading report. Only `pooler.*` weights may be missing: no pooling we use reads them, and Contriever is saved without them. Any other missing weight, any weight the model didn't use, and any shape mismatch stops loading. A random encoder layer would otherwise give vectors that still look like vectors.

**OpenScholar is used as Contriever's reference code uses it.** That is `src/contriever.py` in `facebookresearch/contriever`, also vendored in `AkariAsai/OpenScholar/retriever/contriever`. It takes the last layer with padding positions zeroed, summed and divided by the number of real tokens, and puts no instruction before queries. The opt-in test makes vectors that way, one text at a time with a `BertModel` built without its pooler. After normalisation they differ from the embedder's batched, padded vectors by at most 6.1e-8 per dimension on five texts: four Chunks from shortest to longest, and a question.

`max_tokens` is 512, the model's position limit and the default `passage_maxlength` of the reference `embed.py`. OpenScholar's own peS2o datastore cut passages of 256 words at 256 tokens (`retriever/api/conf/pes2o.yaml`). Our Chunks are sized to fit 512 with their header (ADR 0042), so a 256 limit would cut most of them. Queries are cut at 512, as there (`question_maxlength`).

**Normalising stays, as #55 decided, and its effect is recorded.** Every embedder returns L2-normalised rows, so OpenScholar is scored by cosine, not by Contriever's raw inner product. The opt-in test measures the difference on the fixture: two papers, 60 Chunks and 5 questions. **Normalising changes the top 10 of all 5 fixture questions.** For each question the set of Chunks itself changes, and 7 to 9 of the 10 ranks differ. It is a large effect, so cosine OpenScholar is not quite the model its authors evaluated. The full-run comparison (#60) has to read OpenScholar's numbers with that in mind.

**What the opt-in test checks for all three models** (`RUN_EMBEDDER_TESTS=1`):
- the weights file and its sha256;
- a vocabulary equal to the chunker's uncased BERT WordPiece;
- the same top 10 on CPU and MPS for every fixture question.

CPU and MPS vectors differ by at most 2.1e-7 (bge-small), 3.8e-7 (bge-base) and 7.3e-7 (OpenScholar) per dimension. No fixture Chunk is cut at 512 tokens.

**Cost on a sample.** `index` over 1,155 real Chunks from the first 20 parsed files, on MPS (M1 Max), took 6.8 s with bge-small, 15.6 s with bge-base and 19.9 s with OpenScholar. None of the Chunks was cut. Scaled from bge-small's 818 s for the full corpus, bge-base should take about 30 minutes and OpenScholar about 40. The full-corpus builds belong to #60.

## Alternatives considered
- **Score OpenScholar by raw inner product, as Contriever does.** This is closer to how the model was trained and evaluated, and the fixture shows it ranks differently. #55 settled on normalised rows for every embedder, and the measurement is what it asked for. Changing that means a table setting (`normalise = false`) that the dense key and the report would carry. Whether to add one is for #55 to decide, with this measurement in hand.
- **A `weights_file` field in each table.** It is explicit, but it is one more field to keep in step with the repo. Adding it to the key would also change bge-small's key and rebuild its index for nothing ([0050](0050-named-dense-tables-and-a-configurable-embedder.md) avoided that). The repo already says which file it holds.
- **Convert OpenScholar's `pytorch_model.bin` to safetensors and pin that.** The pin would then be of a file we made, not the author's (#55, user story 9).
- **Load OpenScholar with `add_pooling_layer=False`.** That silences transformers' report of the missing pooler, but a bge checkpoint would then report its pooler as unused, and the pooling layer would differ by model. Allowing only `pooler.*` to be missing covers both families with one rule.
- **`max_tokens = 256` for OpenScholar, as its peS2o datastore used.** That datastore cut 256-word passages; our Chunks hold up to 350 tokens plus a header, so the tail of most Chunks would never be embedded.

## Consequences
- `index` builds four retrievers by default. `--retriever dense.bge-base` and `--retriever dense.openscholar` build each alone.
- Each new model downloads about 440 MB into the Hugging Face cache on first use.
- transformers prints a load report naming OpenScholar's missing pooler on every load. The embedder has already checked that nothing else is missing.
- The fake embedder in the offline tests ignores pooling and normalisation, as before. Only the opt-in test exercises them.
