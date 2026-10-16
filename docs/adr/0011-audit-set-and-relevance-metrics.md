# 0011. Audit set sampling and relevance metrics

- **Date:** 2026-10-16
- **Status:** Accepted

## Context
The Relevance verdict has two stages: the rules ([0005](0005-rule-pre-filter.md)) and the LLM judge ([0007](0007-local-llm-judge.md)). Issue #1 must choose the judge model and threshold with evidence, and the spec (#2) asks for precision and recall reported against a hand-labelled Audit set of about 150–200 Candidates. Most Candidates are rule rejects, so a uniform sample would label few of the hard cases near the judge's boundary.

## Decision
- **Stratified sample.** `audit export` runs collection from the Snapshot without loading the model. It splits the Candidates into strata (`rules-rejected`, `judge-excluded`, `judge-included`, and `pending` for rule passes not yet scored) and deals the sample out evenly, one Candidate per stratum in turn, until it reaches `--size` (default 180). A stratum smaller than its share is taken in full. Each stratum is sampled with a fixed seed (`--seed`, default 0), so the export is reproducible.
- **Weights.** Each row records `stratum_size`, the number of Candidates in its stratum at export. The report weights each labelled row by `stratum_size / labelled rows in that stratum`, so precision and recall estimate the whole population, not the sample's even shares. Without weights, the oversampled judge strata would inflate the rules' apparent precision and hide most of the rule rejects' false negatives.
- **Draft labels from the pipeline.** The draft label is the pipeline's verdict (`yes` if included, `no` if excluded, empty while pending) and the draft reason is its `relevance_reason`. The export copies the draft into `label` and `reason` for the developer to correct, and keeps `draft_label` and `draft_reason` unchanged. The report counts how many labels were changed. The developer chose this over drafting by an independent agent; the risk is anchoring on the system's own answer, so every row must be checked against its abstract.
- **One file, committed.** The Audit set is `data/audit/audit-set.csv`. The export refuses to overwrite it without `--force`, because it holds corrected labels.
- **What the report measures.** `audit report` re-applies the current rules to each row's title and abstract, so a rule change shows up without a new export. It reports:
  - the rule stage alone (rule pass = relevant), whose recall is the ceiling for the whole pipeline
  - rules plus each judge model at a range of thresholds (default 0.1 to 0.9 in steps of 0.1, plus the configured one), with the best F1
  - each model's mean scoring time per Candidate and an estimate for all rule passes, checked against the ~1 h budget from #1.
- **Models and verdicts for the audit.** The models to compare are `[[audit.models]]` in `config/scope.toml` (model id and pinned revision), sharing the `[judge]` prompt. Without that section the report measures only the configured judge. Their verdicts go in `data/audit/verdicts.jsonl`, apart from the collection's cache, keyed by Edition, model, revision and prompt hash, with the seconds each took. The collection cache holds one verdict per Edition, so comparing models there would overwrite verdicts. `--no-judge` reports cached verdicts only, and a model missing any is reported as such, not scored partially.
- **Optimism stated.** The threshold is tuned on the same Audit set it is measured on, and the report says so.

## Alternatives considered
- **Uniform random sample:** with about 70% rule rejects, a 180-row sample would hold only a few dozen judge decisions, too few to compare models or thresholds.
- **Unweighted metrics on the stratified sample:** simpler, but they describe a population in which each stratum is equally common, which is not the corpus.
- **Report from the manifest instead of re-running the rules:** the manifest has no abstract and is frozen at its last build, so rule changes would need a full collection run.
- **Prior work (research-bot):** it has no labelled set and reports no precision or recall; its 1–5 score threshold was set by hand. We keep nothing from it here.

## Consequences
- Choosing a model in #1 is: add the shortlist to `[[audit.models]]`, run `audit report`, apply the decision rule from #2. Then set `[judge]` and its threshold.
- The Audit set only means something once the judge has scored the rule passes (#11). An export made before then has a single `pending` stratum for all rule passes, which is valid but samples them less sharply.
- Edition ids are pinned to an arXiv Version, so an Edition re-pinned by a later refresh drops out of the judge verdict lookups until it is scored again; its label stays valid.
- Weighted estimates from a few rows per stratum are noisy, so a difference of a point or two of F1 between models is within that noise.
