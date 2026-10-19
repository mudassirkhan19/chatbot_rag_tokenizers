# 0060. The Comparison: wins, ties, losses and paired bootstrap intervals against a baseline, and the Cost table

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0039](0039-retrieval-tracer-bm25-index-and-evaluate.md): `evaluate` stops when the Comparison's baseline isn't among the retrievers it scores, and the eval report's Timings section becomes the Cost table.

## Context
Spec #55 picks a retriever by a rule fixed before any run. The rule recommends the cheaper retriever when the better one's lead is within noise. The *all answerable* row has 28 questions, so a difference of 0.04 in Recall@5 may be one question. Slice #59 gives the eval report what the rule needs: how many questions each retriever wins and loses against `dense.bge-small`, intervals on its means and on its difference from bge-small, and its model size and index size next to its build time and latency. The report gives the numbers. The ADR for #60 and #61 applies the rule.

## Decision
**A `[comparison]` table in the retrieval config.** It has three fields, all required:
- `baseline`: the retriever every other is compared with, by its `--retriever` name. It is `dense.bge-small`, the baseline of the earlier reports. A name that isn't configured stops loading.
- `resamples`: 10,000.
- `seed`: 55, the spec's issue number. Any fixed seed would do: it makes two runs draw the same resamples.

**The baseline must be scored.** `evaluate --retriever X` without the baseline stops before loading any index: `the Comparison's baseline, dense.bge-small, is not among the retrievers scored (X); add --retriever dense.bge-small, or name another baseline in [comparison] of the retrieval config`. Building one model at a time with `index --retriever` is unchanged.

**What is compared.** The *all answerable* row's queries: each answerable question once, a follow-up alone, as a user asks it (`harness.all_answerable`). The spec's rule reads that row. Each raw ranking is compared with the baseline's raw ranking. Each `+collapsed` twin is compared with `dense.bge-small+collapsed`, so the collapsed numbers #61 decides on are compared like with like. The baseline's own rows are listed too. They give its intervals, and its difference from itself is exactly 0.

**Wins, ties and losses** count the questions where the retriever's Recall@5, or reciprocal rank for MRR@10, is higher than the baseline's, equal to it, or lower. Both values come from the same counts (Passages found, rank of the first hit) as the per-question lines, so the counts can be checked against those lines. A test does that.

**Paired percentile bootstrap.** NumPy's default generator, seeded, draws a `resamples` × *n* array of question positions with replacement, once per report. Every retriever, raw and collapsed, uses the same array. A retriever's interval is the 2.5th to 97.5th percentile of the draws' means, and its difference interval is the same over the per-question differences from the baseline. So the difference is paired: a question that every retriever finds hard counts against them all in the same draw. The baseline's differences are all exactly 0, so its interval is exactly [0, 0]. **Within noise** means the difference's interval holds 0, judged on the unrounded values. A rounded `+0.00` bound can therefore sit beside either label.

**The report.** A `## Comparison` section follows the results tables. It states the baseline, the question count, the seed and the resample count, and holds:
- one table per metric (`### Comparison: Recall@5` and `### Comparison: MRR@10`). Each row is a retriever with its baseline, mean, interval, difference, difference interval, noise label, wins, ties and losses;
- `### First hit: raw ranking` and `### First hit: Collapsed ranking`, with a row per answerable question as a user asks it and a column per retriever: the rank of the first hit, or `none`.

No winner is named.

**The Cost table.** It replaces `## Timings` and stays last, so the reproducibility check still compares everything above it. It has one row per run: parameters (counted from the loaded model; `—` for BM25), vector dimension (`—` for BM25), the index's files on disk without its record, where and how long it took to build, the number of queries, where they ran, and p50 and p95 latency. A hybrid's parameters, dimension and size are its members' summed, with BM25 adding only its index. A `+collapsed` twin shows its retriever's index. On the full corpus, bge-small has 33.4M parameters, 384 dimensions and 220.6 MB of vectors, and BM25's postings take 140.3 MB.

## Alternatives considered
- **Unpaired intervals**, each retriever bootstrapped on its own draws, and a difference read off two overlapping intervals. This throws away the pairing. Every retriever answers the same questions, and most of the spread between draws comes from which questions are drawn, so the paired difference is much tighter. On the full corpus, bm25's interval [0.04, 0.30] and bge-small's [0.14, 0.48] overlap widely. Their paired difference interval is [-0.32, +0.02].
- **A sign test or Wilcoxon test on wins and losses.** Either gives a p-value, not an interval on the metric the rule reads, and a test of ties needs its own convention. The win/tie/loss counts are reported as they are, beside the interval.
- **BCa or studentised intervals.** These are more accurate in small samples, but harder to explain and to check by hand. The rule needs only "does the interval hold 0", and the percentile interval answers that plainly.
- **Score the baseline automatically when it isn't named.** That would make `--retriever X` quietly score and time a retriever the user didn't ask for. The issue asks for a stop with a clear message.
- **Keep Timings as lines and put the sizes in the Retrievers section.** The issue asks for sizes next to the build time and latency, and a table lines all the costs up in one place.

## Consequences
- `just evaluate --retriever …` must name the baseline too. The README's reproduce command already does.
- The committed eval report gains the Comparison section and the Cost table. On the full corpus, neither BM25 nor `hybrid.bm25+bge-small` differs from bge-small beyond noise, raw or collapsed.
- #60 and #61 read the Comparison tables when they apply the decision rule. A new retriever gets its rows from its config table alone.
- The Retriever interface gains `parameters` and `dimension`. The Embedder gains `parameters`, and the tests' fake embedder declares one.
