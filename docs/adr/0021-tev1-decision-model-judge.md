# 0021. Tev1 4B as the judge, served by Ollama and pinned with its runtime

- **Date:** 2026-10-17
- **Status:** Accepted. Amends [0007](0007-local-llm-judge.md): the judge model, how it is run, and the threshold. Amended by [0025](0025-judge-cuts-only-refused-inputs.md) for inputs too long for the model.

## Context
Issue #1 asks for the judge model and its threshold to be chosen on the Audit set ([0011](0011-audit-set-and-relevance-metrics.md), [0020](0020-blind-agent-labels-checked-by-the-developer.md)). The decision rule: the smallest model within about 2 F1 points of the best, as long as a full run over the 7,203 rule passes takes about 1 h or less on the M1 Max.

The first shortlist, Granite-4.1-8B and Gemma-4-E4B, doesn't fit: [0007](0007-local-llm-judge.md) runs transformers in float32, which needs about 4 bytes per parameter, and the machine has 32 GB. The float32 shortlist was Qwen3-4B-Instruct-2507, Qwen3-1.7B and Granite-4.0-Micro. None of them met the rule, so the developer asked for models served by Ollama:
- Gemma 4 E2B, already installed.
- Two decision models: Together AI's Tev1 (4B and 0.8B), and Bespoke Labs' Nimble v3 (9B).

## Decision
- **The judge is `tev1:4b`, served by Ollama 0.40.5, at threshold 0.8.**
  - Tev1 is a decision model fine-tuned from Qwen3.5-4B. It is asked through Ollama's `/v1/systemone` endpoint, not through chat.
  - The state is the title and abstract. The question is one true/false (`noul`) question in `[judge.decision]`, with the same scope wording as the chat prompt.
  - P("Yes") is the probability Tev1 gives that the question is true.
- **The results.** All six models were measured on the Audit set's 120 rule passes, the rows that reach the judge (the 60 rule rejects are rejected before it), with precision and recall weighted to the 26,388 Candidates (`data/audit/report.md`, written with `audit report --thresholds 0.001,0.005,0.01,0.02,0.05,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.95`). Each model is shown at its best threshold:

  | model | runs with | threshold | precision | recall | F1 | s per Candidate | full run |
  |---|---|---|---|---|---|---|---|
  | **Tev1 4B** | Ollama decision | 0.8 | 0.810 | 0.872 | **0.840** | 0.69–0.89 | 83–106 min |
  | Gemma 4 E2B (nvfp4) | Ollama chat | 0.005 | 0.744 | 0.821 | 0.781 | 0.06–0.12 | 7–15 min |
  | Granite-4.0-Micro | transformers fp32 | 0.8 | 0.725 | 0.744 | 0.734 | 0.61–0.63 | ~75 min |
  | Qwen3-4B-Instruct-2507 | transformers fp32 | 0.95 | 0.579 | 0.847 | 0.688 | 0.78–1.07 | 94–128 min |
  | Qwen3-1.7B | transformers fp32 | 0.9 | 0.459 | 0.974 | 0.624 | 0.25–0.27 | 30–33 min |
  | Tev1 0.8B | Ollama decision | 0.7 | 0.467 | 0.898 | 0.615 | 0.03–0.10 | 4–12 min |

  - Timings were measured on AC power with nothing else running. Each range covers two runs: the audit pass behind `report.md` and a separate pass in collection-sized batches of 25. They vary by up to ±30% between runs. With all three Ollama models loaded, they held about 26 GB of the 32 GB, and `tev1:4b` alone held 12.9 GB.
  - For comparison, the rules alone give precision 0.326 and recall 1.000.
- **The rule is broken on time, deliberately.** No other model is within 2 F1 points of Tev1 4B: Gemma, the runner-up, is 6 points behind. Tev1 4B's full run takes 83–106 min, against the ~1 h budget. The developer accepted that, for three reasons:
  - The full run is a one-off.
  - Verdicts are cached, so reruns are free.
  - A 6-point F1 gain over every Candidate is worth 20 more minutes once.
- **The threshold is 0.8, the best F1.** Tev1's F1 is 0.78–0.84 between 0.5 and 0.8, and it falls off on both sides (0.743 at 0.4, 0.778 at 0.9). One relevant row in the judge-excluded or judge-included stratum stands for about 60 Candidates, or about 2.6 points of recall. So 0.8 is only loosely better than 0.7 (F1 0.822, recall 0.949). It was chosen on the same Audit set, so the F1 is optimistic.
- **Ollama models are pinned as `<digest>@<Ollama version>`.** Upgrading Ollama from 0.34.2 to 0.40.5 kept Gemma's digest but moved its P("Yes") by up to 0.16. Three of the 120 rule passes crossed the threshold. So the version decides scores as much as the weights do.
  - The judge refuses to start unless the running server version and the installed digest both match the pin.
  - The pin is the verdict's `revision`, so an upgrade invalidates cached verdicts the way a model change does. The cache format doesn't change.
- **A decision model's verdicts are kept under a hash of its `[judge.decision]` question.** That covers the state template, instructions and both criteria. A chat model's verdicts stay under the hash of the prompt, so existing verdicts keep their keys. Neither hash covers the request the code builds from the text, such as the `noul` question type, so a change there needs a new question or prompt to re-score.
- **Chat templates are rendered with thinking off** (`enable_thinking=False`). Hybrid models such as Qwen3-1.7B would otherwise reason before answering, so the next token wouldn't be the answer. The Qwen3-4B-Instruct and Granite templates ignore the switch: they render byte-identically with and without it, so their cached verdicts still hold. Ollama chat models get `think: false` for the same reason.
- **Repeat scoring isn't bit-identical on Ollama**, unlike float32 transformers. The cache is what makes reruns reproducible.
  - Scoring the 120 rule passes twice on Ollama 0.40.5 moved 24 of Tev1 4B's scores, by up to 0.018. None crossed 0.8, but one sits 0.0016 from it, so on the full run a few Candidates that close may land either side.
  - Gemma's scores moved by up to 0.0095.
  - Tev1 0.8B's scores were identical.

## Alternatives considered
- **Gemma 4 E2B through Ollama chat logprobs.** It runs in about 15 min, inside the budget, but its F1 is 0.781, 6 points behind. Its best threshold is 0.005, because it pushes many relevant papers close to 0. Below 0.05 the labels are mixed, so that threshold rests on a handful of rows.
- **Granite-4.0-Micro.** The best of the float32 transformers models (F1 0.734), and the fallback the developer named. It is both slower and less accurate than Tev1 4B.
- **Qwen3-4B-Instruct-2507, the default until now.** Its P("Yes") saturates near 0 or 1, so the threshold barely matters: F1 stays at 0.67–0.69 whatever the threshold. About 43% of what it accepts isn't relevant, and it is the slowest.
- **Qwen3-1.7B and Tev1 0.8B.** Both are inside the budget, but at F1 0.62 more than half of what they accept is noise.
- **Nimble v3 (9B).** Not measured: the developer stopped its 9.3 GB download after Tev1 4B's result. It is twice Tev1's size, so it would very likely be slower than Tev1 and over the budget. Its weights are CC BY-NC 4.0, noncommercial only.
- **A sharper prompt.** The hand-off from #9 suggested the prompt might matter more than the model. Tev1's precision of 0.81 against Qwen3-4B's 0.58, with the same scope wording, shows the model mattered here. Tuning the wording on the same 180 rows would make the figures more optimistic still.
- **Speeding up Tev1.**
  - The endpoint reuses only about 46 tokens of each request from the one before: the paper comes before the question in its template, so the long question can't be cached as a prefix.
  - A request holds one state, so papers can't be batched.
- **Recording the Ollama version in a separate verdict field.** That would change both verdict file formats and every reader of them. Folding the version into the revision keeps the pin, the cache key and the manifest's `judge_model` in one string.

## Consequences
- A full judge run (#11) re-scores all 7,203 rule passes with Tev1: about 1.5 h, with Ollama 0.40.5 and `tev1:4b` installed. Unload other Ollama models first (`ollama stop <model>`). The Snapshot's cached Qwen verdicts no longer match the config.
- Scoring with the default judge needs no torch, transformers or Hugging Face download: only Ollama and a 4.4 GB model. The transformers backend stays, for the models compared in `[[audit.models]]`.
- Upgrading Ollama means re-scoring the Audit set and the corpus, and updating every Ollama pin. The judge refuses to run until the pins match, so an upgrade can't silently mix runtimes.
- The weights of `tev1:4b` have no licence on the Ollama page. Only its dataset builders and training scripts are said to be MIT. The verdicts are committed, but the model itself isn't redistributed.
- Tev1 is described as experimental, and its readme warns against relying on it alone for high-stakes decisions. The Audit set stays the check on it.
