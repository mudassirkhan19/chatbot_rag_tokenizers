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

**Canonical Edition**:
The Edition that stands for a Work when its copies are merged: the venue Edition when there is one, otherwise the latest Version of its preprint. A v1 with a later Version is never canonical.
_Avoid_: Primary, main copy, latest (alone)

**Suspected pair**:
Two Editions that one signal links (such as a shared title) but that the grouping rule declines to join; they are listed so a reader can see what was not merged, and why.
_Avoid_: Near-miss, false positive, conflict

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
A contiguous run of text from one Section of one parsed file, and the unit that is retrieved and cited. Its kind is text (paragraphs), table (one linearised table, or part of one) or caption (a figure caption).
_Avoid_: Passage (an evaluation question's answer quote), segment, split

**Context header**:
The paper title and Section path a Chunk is embedded with ("WECHSEL: … › 5 Results › 5.3 Is freezing necessary?"), stored apart from the Chunk's text so citations quote clean text.
_Avoid_: Prefix, breadcrumb, title (alone)

**Citation anchor**:
What a Chunk is cited by: the pinned Edition id with its Version, the Section number and title, and the page range.
_Avoid_: Reference (that is a bibliography entry), source

**Parse cache**:
The local, uncommitted directory of GROBID's TEI, the Chunks and the bibliography for each parsed file, keyed by the file's sha256.
_Avoid_: Snapshot (that is committed), index

**Quality gate**:
The check that keeps garbled and empty parses out of the index: a file fails it when GROBID errors or times out, or when it has too few Sections or too little Section text, and a failed file gets no Chunks.
_Avoid_: Filter (that is the rule pre-filter of `collect`), validation

**Parse report**:
The committed summary of a parse run: the parser and chunking config used, one line per file and the totals.
_Avoid_: Log, manifest

### Evaluation

**Evaluation set**:
The hand-checked questions, with the Passages that answer them, used to measure retrieval and the chatbot.
_Avoid_: Audit set (that measures the relevance verdict), test set, gold set

**Passage**:
A verbatim quote from one Section of one Edition that answers an evaluation question. Any Chunk holding the quote answers it, whichever Edition of the Work that Chunk comes from.
_Avoid_: Chunk (the retrieved unit, which may hold several Passages or part of one), answer, span

**Comparison**:
Each retriever against a baseline retriever named in the retrieval config (`dense.bge-small`, and its `+collapsed` twin for the twins), question by question, over the answerable questions as a user asks them: the questions it wins, ties and loses, and paired bootstrap intervals on its metrics and on its difference from the baseline. A difference whose interval holds 0 is within noise. It names no winner.
_Avoid_: Significance test, ranking of retrievers

**Unanswerable kind**:
How far an unanswerable question is from the corpus: near-miss when the corpus holds the paper or the measure it asks about but not the answer, out-of-topic when it is about something else. Near-miss names a question here, never a Suspected pair.
_Avoid_: Difficulty, category

**Work groups**:
The checked assignment of Editions to Works, with each Work's Survey flag, that the top-5 duplicate rate and the grouping rule are measured against; each row names who checked it, a person or a blind agent.
_Avoid_: Clusters, dedup output (the duplicate stage's own grouping is what the Work groups test)

### Retrieval

**Collapsed ranking**:
A ranking in which each passage appears once, however many files of its Work hold a copy: copies of a Chunk from a Work's other Editions and Versions are merged into the slot of the best-ranked one, shown from the Canonical Edition when its copy was retrieved, with the merged Editions named beside it. A Work's other passages keep their own slots.
_Avoid_: Deduplicated results, merged results, filtered ranking

**Per-paper retrieval**:
Retrieval for a question that names two or more papers, methods or models that are different Works: the names fill the slots in rotation, each with the Chunks of its Works in the order the retriever ranks them for the whole question, then the rest of the ranking. A name is found among the indexed Works by its first author ("Goldman et al.") or by the words of a title ("MEGABYTE"); a question naming fewer is ranked as it is.
_Avoid_: Query decomposition, sub-queries, multi-query

### Chat

**Conversation**:
One user's sequence of Turns with the chatbot, from the first question until the page is reset; the unit the transcript records and the chat evaluation replays.
_Avoid_: Session, chat, thread

**Turn**:
One question and the answer it gets, with the Chunks retrieved for it. A follow-up Turn is resolved against the Conversation before it.
_Avoid_: Message, exchange, query

**Rewrite**:
The standalone question the chatbot forms from a follow-up Turn and the Conversation before it, which is what retrieval sees. The Evaluation set's hand-written reference rewrite is the ceiling it is measured against.
_Avoid_: Reformulation, expanded query, reference rewrite (that is the Evaluation set's)

**Transcript**:
A Conversation saved from the chat page as Markdown (under `docs/reports` unless `chat --transcripts` names another folder), rendered from the same Turn records the page shows: each Turn's question, Rewrite, answer with its markers and reference list.
_Avoid_: Log, chat history, export

**Citation**:
A marker in an answer that names one retrieved Chunk by its Citation anchor, so a reader can open the paper and Section it came from. An answer may cite only Chunks retrieved for its Turn.
_Avoid_: Reference (that is a bibliography entry), source, link

**Grounded**:
An answer that cites at least one Chunk, every Citation of which resolves to a Chunk retrieved for its Turn, and every number of which (a word that starts with a digit, so "50k" but not "ByT5") appears in a cited Chunk's context header or text. An Abstention is neither grounded nor not.
_Avoid_: Faithful, supported, hallucination-free

**Claim**:
A sentence of an answer that cites at least one retrieved Chunk, without its markers. The grounding judge asks of each claim and each Chunk it cites whether the Chunk supports it.
_Avoid_: Statement, assertion

**Abstention**:
An answer that says plainly the corpus does not support an answer to the question, instead of answering it. A correct Abstention answers an unanswerable question; a false one refuses an answerable question.
_Avoid_: Refusal, "I don't know", fallback
