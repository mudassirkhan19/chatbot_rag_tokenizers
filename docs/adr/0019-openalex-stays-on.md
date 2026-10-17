# 0019. OpenAlex stays on

- **Date:** 2026-10-17
- **Status:** Accepted. Records the verdict that [0014](0014-openalex-discovery-channel.md) left open.

## Context
[0014](0014-openalex-discovery-channel.md) added OpenAlex as a separate, switchable Discovery channel, with one query (`openalex-subword-phrases`) that mirrors only the Semantic Scholar phrases query `s2-subword-phrases`. OpenAlex stays on if at least 20 of its OpenAlex-only Editions are included, or if `oa_pdf_urls` gives at least 20 included venue Editions their only PDF source. The first full run (Snapshot commit "Record the first full collection run in the Snapshot") had all channels, the 21 Seeds and the judge (Qwen3-4B-Instruct-2507, threshold 0.5), with no verdict pending.

## Decision
**OpenAlex stays on (`enabled = true` under `[sources.openalex]`).** Both criteria pass by a wide margin:

- **OpenAlex-only Editions:** the report line is `openalex: 1590 Editions, 495 found by no other source (412 pass the rules, 332 included, 0 pending)`. **332 included**, against a bar of 20. Of these, 328 are venue Editions and 4 are preprints. 18 of them are the venue Edition of a paper whose preprint, found by another source, is also included. Without those, 314 are papers no other source reached.
- **Only PDF source:** of the 1,718 included venue Editions, **204** have `oa_pdf_urls`, no `pdf_link` and no included preprint sharing their DOI, ACL ID or arXiv ID. 72 of those were found only by OpenAlex. The other 132 are rows other channels found, which OpenAlex enriched with an open-access PDF.

## Alternatives considered
- **Switch it off:** would drop the 314 papers only OpenAlex found and the only PDF source of 204 included venue Editions.
- **Wait for the judge chosen in #1 before deciding:** a different model or threshold will move these counts, but not from hundreds down below 20.

## Consequences
- Fetching keeps needing `OPENALEX_API_KEY`. A replay from the Snapshot doesn't. The OpenAlex responses are 2.2 MB of the Snapshot.
- The OpenAlex-only includes are recent and broad: 167 of the 332 are from 2026, and some are other-modality work (for example SMILES tokenization for chemistry). The Audit set (#9) should check how many of them the judge gets right.
- The query mirrors only `s2-subword-phrases`, so these counts are a lower bound on what OpenAlex could add. More OpenAlex queries, or a DOI lookup for every venue Edition ([0014](0014-openalex-discovery-channel.md), alternatives), are now worth considering.
