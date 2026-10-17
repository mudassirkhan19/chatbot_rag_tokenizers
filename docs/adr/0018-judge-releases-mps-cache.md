# 0018. The judge releases the MPS allocator cache after every batch

- **Date:** 2026-10-17
- **Status:** Accepted. Amends [0007](0007-local-llm-judge.md).

## Context
The judge ([0007](0007-local-llm-judge.md)) scores one prompt at a time in float32 on MPS. On the first full run, 7,203 Candidates passed the rules. After 2,975 of them, Claude Code killed the run because the 32 GB machine was critically low on memory. Each prompt has its own length, so PyTorch's MPS allocator keeps caching buffers of new sizes. On 150 synthetic abstracts of 40–450 words with Qwen3-4B-Instruct-2507, the model held a steady 15.1 GB, while the memory the MPS driver had allocated rose from 17.7 GB to 19.7 GB (0.85 s per prompt).

## Decision
- **After scoring each batch, which is every 25 Candidates when the verdict cache is saved, the judge calls `torch.mps.empty_cache()`.** On the same 150 abstracts the driver stayed at 15.6 GB throughout, and all 150 scores were bit-identical to the run without it. The cost is about 0.2 s per prompt (1.07 s against 0.85 s).

## Alternatives considered
- **`logits_to_keep=1`, to compute logits only for the last position:** with the cache release it also held memory flat at 15.5 GB, but it changed P("Yes") by up to 3×10⁻⁵ because the matmul has a different shape. Verdicts cached before and after the change would then come from slightly different computations.
- **bf16:** half the memory, but [0007](0007-local-llm-judge.md) rejected it because P("Yes") becomes too coarse, and it would invalidate every cached score.
- **Cap the allocator with `PYTORCH_MPS_HIGH_WATERMARK_RATIO`:** an environment setting each reviewer would have to know about. A cap below what a long prompt needs raises an out-of-memory error instead of freeing cached blocks.

## Consequences
- The judge's memory use stays about where the model's weights put it (~16 GB) however many Candidates it scores.
- Scoring the full set takes about 0.2 s longer per Candidate, roughly 25 minutes on 7,200.
- The fix has no offline test: the test suite never loads torch or a model. The 150-prompt probe above is the evidence.
