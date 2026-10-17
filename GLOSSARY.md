# Tokenizer literature RAG

A grounded chatbot over research papers about tokenization for language models. This glossary fixes the words we use for papers, their copies and how they enter the corpus.

## Language

### Papers and their copies

**Work**:
A paper as an intellectual contribution, independent of where or how often it was published.
_Avoid_: Paper (when the distinction matters), document, article

**Edition**:
One distinct publication of a Work, such as its arXiv preprint or its ACL proceedings paper.
_Avoid_: Copy, variant, manifestation

**Version**:
One numbered revision (v1, v2, …) of an arXiv preprint Edition.
_Avoid_: Revision, release

**Survey**:
A Work that reviews or restates other Works' findings; it is always its own Work, never an Edition of the Works it covers.
_Avoid_: Review paper, overview

### Collection

**Candidate**:
Any record found during discovery, before it has a relevance verdict.
_Avoid_: Hit, result, raw paper

**Seed**:
A hand-picked landmark Work used as a starting point for citation expansion.
_Avoid_: Anchor, root paper

**Discovery channel**:
The route by which a Candidate was found: a keyword query on a named source, or citation expansion from a Seed.
_Avoid_: Origin, provenance

**Relevance verdict**:
The decision on whether a Candidate belongs in the corpus, with the stage that made it and the reason.
_Avoid_: Score, label, classification

**Snapshot**:
The dated, committed record of everything collection depended on: source responses, relevance verdicts and the pinned Edition identifiers. Rerunning from a Snapshot reproduces the same corpus.
_Avoid_: Cache (the local, uncommitted copy), dump

**Audit set**:
A hand-labelled sample of Candidates used to choose and measure the relevance verdict, never to train it.
_Avoid_: Gold set, test set (the RAG evaluation set is a different thing)

### Parsing

**Section**:
A headed division of a paper's body as its authors numbered it; an appendix is a Section too, marked as one.
_Avoid_: Heading, part

**Chunk**:
A contiguous run of text from one Section of one parsed file, and the unit that is retrieved and cited.
_Avoid_: Passage (that word is for an evaluation question's answer span, which may cover several Chunks or part of one), segment, split
