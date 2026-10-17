# 0007. Stage-2 local LLM judge and verdict cache

- **Date:** 2026-10-16
- **Status:** Accepted. The judge releases the MPS allocator cache after every batch ([0018](0018-judge-releases-mps-cache.md)). The model, now Tev1 4B served by Ollama, and the threshold, now 0.8, were chosen in [0021](0021-tev1-decision-model-judge.md).

## Context
The rule pre-filter ([0005](0005-rule-pre-filter.md)) passes about 980 of the first 3,285 Candidates. Many are still off-topic, and the rules can't decide the hard cases: mixed-modality papers, or papers that use a tokenizer without studying one. The spec (#2) asks for a second stage that judges each Candidate's title and abstract against the scope question, and a reviewer must be able to rerun collection without the model, a GPU or an API key.

## Decision
- **Question.** The judge asks whether the paper *makes a substantive contribution or finding about tokenization*, not whether it is *mainly* about tokenization. The prompt lives in `[judge]` in `config/scope.toml` and states the scope boundary.
- **Score, not an answer.** The judge runs one forward pass and takes the next-token logits for "Yes" and "No" right after the chat template's assistant prefix. P("Yes") is the softmax over those two logits only. Nothing is generated, so there is nothing to parse and no sampling. Both answers must be single tokens for the configured tokenizer, and the judge refuses to start otherwise.
- **Model.** A local open-weight instruction model run with transformers, on MPS (or CUDA, or the CPU). The model id and a pinned Hugging Face commit go in the config. The default is `Qwen/Qwen3-4B-Instruct-2507` until issue #1 benchmarks the shortlist on the Audit set.
- **Precision.** The judge runs in float32, one prompt at a time, with no padding. On 24 rule-passing Candidates on the M1 Max (MPS) with Qwen3-4B:
  - **bf16:** P("Yes") snapped to a few values. Two different papers both scored exactly 0.5, because the two logits tied at bf16 resolution. Batching 8 prompts with left padding moved one score by 0.32 compared with scoring it alone, even with position ids counted from each prompt's first token.
  - **float32:** batched and single scores agreed to four decimals. Batching was slower, not faster: 3.9 s per paper batched against 1.2 s single (bf16: 0.9 s against 0.8 s).
  - **Cost:** at 1.2 s per Candidate, the ~980 rule passes take about 20 minutes, inside the ~1 h budget from #1, and float32 weights for a 4B model take about 16 GB of memory.
- **Verdict cache.** Each verdict is stored in the Snapshot at `verdicts/judge.jsonl`: one sorted JSON line per Edition with the model id, revision, prompt hash (sha256 of the prompt template) and P("Yes"). A cached verdict is reused only while all three match the config, so changing any of them re-scores. `collect --refresh` re-scores everything, and `collect --no-judge` never loads the model and leaves unscored Candidates `pending`. The cache is saved every 25 Candidates, so an interrupted run keeps its progress.
- **Threshold at build time.** The threshold is applied when the manifest is written, not stored with the verdict. The manifest records `judge_probability`, `judge_threshold` and `judge_model`, and a Candidate is `included` (funnel status `relevant`) when P("Yes") ≥ threshold, else `excluded` with stage `judge`. The threshold is 0.5 until the Audit set (#9) tunes it.
- **Dependencies.** torch 2.14.1 and transformers 5.20.0 are pinned in a `judge` dependency group (`uv sync --group judge`). They are imported only when something needs scoring, so a rerun from a complete Snapshot needs neither.

## Alternatives considered
- **Generate an answer and parse it:** this needs a parser for free text, depends on sampling settings and gives a yes/no with no confidence to put a threshold on.
- **Store the verdict, not the probability:** every threshold change would re-score about 1,000 Candidates. With the probability stored, tuning is a rebuild of the CSV.
- **Prompt hash over each rendered prompt:** this would also catch an edited abstract, but the pinned Edition id already changes when arXiv's text does. Hashing the template keeps the hash identical across verdicts, so it is easy to read.
- **One cache file per verdict, like the source responses:** about 1,000 tiny files for one number each. A sorted JSON-lines file stays small, diffs line by line and is rewritten deterministically.
- **Prior work (research-bot):** it sends every paper to a paid API (DeepSeek through OpenRouter) at temperature 0.1, asks for a JSON object with a 1–5 score and stores the parsed answer in SQLite. That needs a key and money for each run, gives a coarse score the model can format wrongly, and leaves nothing a reviewer can reuse without calling the API again. We keep its idea of an LLM relevance judge, but run an open model locally, read the probability instead of a generated answer and commit the verdicts with the model and prompt that made them.

## Consequences
- A reviewer reproduces the manifest offline from the committed verdicts, without torch. Scoring Candidates needs an 8 GB download of model weights, about 16 GB of memory in float32 and about 1.2 s per abstract on an M1 Max.
- `--refresh` currently means re-scoring only. The spec (#2) also wants it to re-fetch source responses while keeping verdicts for unchanged Candidates. When source refreshing lands, the two need separate flags or a recorded decision.
- Switching the judge model (issue #1) or editing the prompt invalidates every cached verdict. That is deliberate.
- The probabilities depend on the hardware and library versions they were scored with. The cache is the record, so reruns don't depend on either.
- Tests use fixture verdicts and a fake judge. They never load a model, so the model's quality is measured on the Audit set (#1, #9), not by the test suite.
