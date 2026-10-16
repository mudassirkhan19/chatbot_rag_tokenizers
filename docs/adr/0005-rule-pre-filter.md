# 0005. Stage-1 rule pre-filter for the Relevance verdict

- **Date:** 2026-10-16
- **Status:** Accepted

## Context
Keyword queries return many Candidates that use "token" in a sense unrelated to tokenization: token pruning and merging, KV-cache eviction, crypto assets, and tokenizers for images or audio. The LLM judge (stage 2) is the expensive step, and a reviewer needs to see why each Candidate was rejected. The spec (#2) asks for a deterministic first stage made of a required term group plus exclusion patterns that report which pattern fired.

## Decision
Rules live in `[rules]` in `config/scope.toml` and are case-insensitive regular expressions.
1. **Keep guard:** a title that matches a strong on-topic term (`keep_if_title`: subword, BPE, byte-level, tokenizer-free, vocabulary, …) skips the exclusion patterns.
2. **Exclusion patterns:** each has a name, and they match the **title only**. The first one that fires rejects the Candidate, and its name is recorded.
3. **Required term group:** the title or abstract must match at least one term (`tokeni[sz]`, subword, byte-pair, WordPiece, SentencePiece, vocabulary, byte-level, character-level). Otherwise the Candidate is rejected as `missing-required-term`.

Exclusions run before the required-term check. Both orders reject the same Candidates, but this one records the specific off-topic sense (`token-reduction`, `kv-cache`) instead of the generic missing-term reason. That makes the recorded patterns useful for auditing.

A rejected Candidate keeps its manifest row with `rule_outcome=reject`, `rule_pattern` set to the pattern name, `relevance_verdict=excluded`, `relevance_stage=rules` and a reason quoting the matched text. A Candidate that passes gets `relevance_verdict=pending` until the judge stage exists.

## Alternatives considered
- **Exclusions over title and abstract:** this catches more off-topic papers, but an on-topic abstract often mentions token merging or image tokenizers in passing. A wrong rejection here is never seen by the judge, so stage 1 should err towards keeping Candidates.
- **No keep guard:** the first live run rejected "MrT5: Dynamic Token Merging for Efficient Byte-level Language Models", which is in scope. The guard was added because of that, and the fixture tests cover it.
- **Judge everything with the LLM:** simpler, but it spends judge time on clearly irrelevant papers and makes the cheap, explainable rejections depend on a model.
- **Prior work (research-bot):** it sends every Candidate to a paid LLM, with no deterministic stage and no recorded reason. We keep LLM judging for the hard cases only.

## Consequences
- On the first arXiv query (3,285 Candidates), the rules pass 980 and reject 2,305: 1,884 for a missing required term and 421 by a named exclusion pattern (312 of them `token-reduction`). Most rejections come from arXiv stemming "tokenizer" to "token" (see [0004](0004-arxiv-keyword-queries.md)).
- Rules will reject some good papers. The Audit set (issue #9) samples rule rejects so that their recall can be measured, and the recorded pattern names show which rule to fix.
