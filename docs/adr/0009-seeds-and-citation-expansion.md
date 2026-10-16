# 0009. Scope boundary, keyword query set, Seeds and citation expansion

- **Date:** 2026-10-16
- **Status:** Proposed. The Seeds and queries are a draft for the developer to review (#4).

## Context
The corpus has to be broad and relevant, and a reviewer has to be able to see how discovery was driven (#2, user stories 11–16). Keyword search alone misses papers that use their own vocabulary: an arithmetic paper that talks about "digit splitting", or a model paper whose abstract says "patches" and never "tokenizer". Papers about tokenization also cite each other heavily, so one hop of the citation graph from a few landmark Works reaches many papers that keyword search can't. The two must stay distinguishable so the report can show what expansion adds.

Semantic Scholar's Graph API ([spec](https://api.semanticscholar.org/api-docs/graph)) serves `/paper/{id}` for one record and `/paper/{id}/references` and `/paper/{id}/citations` for its links. The links come in pages of up to 1,000 with a `next` offset. A reference or citation that Semantic Scholar couldn't resolve to a paper comes back with a null `paperId`. The citations endpoint refuses any page that reaches past the 10,000th entry ("offset + limit must be < 10000", observed on 2026-10-16).

## Decision

### Scope boundary
`config/scope.toml` lists the five in-scope topics from the spec: subword algorithms for text LMs, byte-level and tokenizer-free models, foundational NMT-era subword papers, effects of tokenization (multilingual fertility and fairness, arithmetic, code, reasoning, vocabulary size and scaling), and vocabulary adaptation and transfer. Out of scope: tokenizers for other modalities (VQ image tokens, audio codecs) and uses of "token" that aren't about tokenization (token pruning or merging, KV caches, crypto tokens). Mixed-modality papers are in only when text tokenization is a central contribution, and the judge decides those. There is no date floor.

### Keyword queries
- Every query is tagged with one topic, and every topic has at least one query. A test checks this on the committed config.
- **Semantic Scholar carries most topics** (12 queries). It stems every term and matches title and abstract, so a bare `tokenization` matches "token" and returns about 100k papers ([0008](0008-semantic-scholar-keyword-discovery.md)). The queries therefore use phrases ("tokenization premium", "byte-level language model") or require two concepts together (`("tokenization" | tokenizer) + (arithmetic | numeracy)`).
- **arXiv carries the parts where its field syntax helps** (6 queries): title words (`ti:tokenizer`, `ti:vocabulary`, `ti:subword`, `ti:"byte-level"`) and abstract phrases (`abs:"byte pair encoding"`, `abs:"byte-level"`), each restricted to cs.CL, cs.LG and cs.AI. These catch recent preprints that Semantic Scholar hasn't indexed yet.
- Query sizes measured on 2026-10-16 are in the Consequences section.

### Seeds
- 21 Seeds, each with a topic and a one-line reason in the config. They spread across the topics: one foundational NMT paper, seven on subword algorithms (including one survey), three byte-level models, seven on effects and three on vocabulary adaptation.
- A Seed is named by any id Semantic Scholar accepts (`ARXIV:1508.07909`, `DOI:…`). WordPiece's origin (Schuster and Nakajima, ICASSP 2012) has no arXiv id, so it is named by its DOI.
- Seeds are chosen as hubs, not just as famous papers. A good Seed is cited mainly by tokenization work, or has a bibliography that covers the area (the open-vocabulary survey lists 200 references).

### Citation expansion
- **One hop in both directions, for every Seed.** The Seed's own record, every paper in its bibliography and every paper that cites it become Candidates. They are tagged `seed:<id>`, `seed-references:<id>` and `seed-citations:<id>`, so the manifest shows which Seed found each one and in which direction.
- **Same normalisation and relevance stages as keyword Candidates.** A linked paper is read into an Edition exactly like a bulk-search Candidate (0008), combines with the same Edition from any other channel on an exact identifier, and then goes through the rules and the judge.
- **Every page is stored in the Snapshot** under its request description (`url` and `fields`, `offset`, `limit`), like every other response ([0003](0003-commit-the-snapshot.md)). The next page's offset is read from the stored page, so a replay follows the same chain offline.
- **Unresolved links are skipped.** An entry with no `paperId` has no identifier to name an Edition by.
- **Citations stop at 9,999 per Seed**, with a message, because the API serves no further. The most-cited Seed (Sennrich et al., 9,121 citations) is under the limit today.
- **Report:** besides the per-channel counts, `collect` prints how many Editions keyword search found and how many it included, and how many Editions the citation hops reached, how many of those no keyword query found, and how many of those were included. A Seed's own record doesn't count as a citation hop, because it was picked by hand.

## Alternatives considered
- **Keyword search only:** simpler and cheaper, but it misses papers whose abstracts use other vocabulary, and there would be nothing to compare it against to show the coverage is broad.
- **Citations only for the less-cited Seeds:** the Sennrich and SentencePiece citers (about 13.5k) are mostly papers that just use BPE or SentencePiece. Leaving them out would save fetching and judging, but it would also drop tokenization papers that cite only those two. The rule pre-filter rejects most of them cheaply, so we expand every Seed fully.
- **Filtering citations by Semantic Scholar's `isInfluential` flag or by citation intent:** it cuts the noise, but the flags come from a model whose recall we can't measure, and they would add a relevance decision that happens before our own stages and leaves no row.
- **Two hops, or expanding from every included paper (snowballing):** grows the Candidate set much faster than the judge can score it (about 1.2 s per abstract, [0007](0007-local-llm-judge.md)), and makes the corpus depend on the order in which the judge accepts papers.
- **Running one query text on both sources:** the query languages differ (0008).
- **Prior work (research-bot):** it discovers papers only through arXiv keyword queries grouped by research area, some of them whole categories (`cat:cs.AI`), capped per query and limited to recent months. Its reference handling comes after discovery: it pulls references out of already-parsed PDFs to draw lineage graphs, resolving at most 20 per paper through a paid search API. It has no Seeds, no citation expansion as a discovery channel and no per-channel counts. We keep the idea of queries grouped by topic, but tag each query with a scope topic so coverage can be checked, add Semantic Scholar, and make expansion a measured channel of its own.

## Consequences
- Query sizes on 2026-10-16, before rules: the arXiv queries return 3.3k (`tokenizer-titles`), 848 (`subword-abstracts`), 967 (`byte-level-abstracts`), 167 (`subword-titles`), 171 (`byte-level-titles`) and 677 (`vocabulary-titles`) papers. The new Semantic Scholar queries return 672 (`subword-methods`), 309 (`byte-level-models`), 417 (`nmt-subwords`), 188 (`multilingual-fairness`), 586 (`arithmetic`), 512 (`code`), 562 (`spelling-and-characters`), 588 (`vocabulary-size`), 80 (`token-artifacts`), 1,197 (`reasoning`) and 914 (`vocabulary-adaptation`), about 6k in all next to the 1.2k of `subword-phrases`. The two sources overlap heavily.
- Expansion is the largest channel: the 21 Seeds have about 19k citations and 1.1k references in all, mostly from Sennrich et al. (9.1k) and SentencePiece (4.4k). Without an API key Semantic Scholar throttles hard, so the first expansion run takes a while. It is about 40 pages, each fetched once.
- To keep that run to hours rather than a day, arXiv records are fetched only for Editions that pass the rules ([0010](0010-arxiv-records-for-rule-passes-only.md)).
- The Snapshot grows by roughly 15–25 MB of compressed citation pages, still under the 50 MB warning in the spec.
- Byte Latent Transformer has no references in Semantic Scholar yet, so only its citations expand. A later `--refresh` picks up its references once they are indexed.
- Semantic Scholar sometimes leaves out the abstract of a linked paper, and the arXiv record doesn't fill it in. Such a Candidate is judged on its title alone, so expansion may lose more Candidates to `missing-required-term` than keyword search does, since keyword Candidates matched on their abstract. The first full run should check how often linked papers have no abstract.
- The funnel counts per channel come from the first full run (#11). That is the evidence for whether expansion earns its cost.
