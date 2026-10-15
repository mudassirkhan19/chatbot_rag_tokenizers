# AI Engineer take-home assignment

## Talk to the literature: a RAG chatbot over LLM tokenizer research

Here is an applied assignment. It builds on RAG work, but in a new domain: research papers on tokenizers for large language models. It also includes two problems worth digging into: near-duplicate content cluttering retrieval, and choosing an embedding model with evidence.

*Expected effort: about two full days plus half a day for the write-up. Please don't spend much longer than that; we care more about your reasoning than about polish.*

### Illustrative example

**Question:** "What evidence is there that byte-level tokenization beats BPE for low-resource languages?"

| # | Naive top-5 | What we want |
|---|---|---|
| 1 | Paper A, arXiv v1, results section | Paper A, latest version *(3 versions merged)* |
| 2 | Paper A, arXiv v3, results section *(same paper)* | Paper C, fertility across languages |
| 3 | Paper A, conference version *(same paper)* | Paper D, downstream accuracy comparison |
| 4 | Survey B, restating Paper A's result *(same finding)* | Paper E, counter-evidence on compute cost |
| 5 | Paper C, tokenizer fertility across languages | Survey B, for broader context |

*Illustrative only. Your corpus and questions will differ.*

## The task

Collect as large a set as you can of research papers about **tokenizers for LLMs**, then build a RAG application and a chatbot that lets someone have a grounded conversation with that literature. Topics in scope include BPE, WordPiece, Unigram and SentencePiece, byte-level and tokenizer-free models, vocabulary size, multilingual fairness and fertility, and how tokenization affects arithmetic, code or reasoning. You decide where the boundary of the topic sits; tell us how you drew it.

### Collect the corpus

Build a repeatable collection pipeline using open sources such as the arXiv API, Semantic Scholar, ACL Anthology or OpenReview. Breadth counts: more relevant papers is better, but tell us how you judged relevance and how many you rejected. Keep metadata for every paper (title, authors, year, venue, source link) and respect rate limits and licences.

### Parse and chunk papers

Turn PDFs or LaTeX into clean, section-aware chunks. Decide what to do with tables, equations, figure captions and reference lists, and explain why.

### Handle versions and near-duplicates *(challenging)*

The same paper appears as several arXiv versions, a preprint and a conference version, and surveys restate other papers' findings. Detect these and stop them from crowding the top results, without merging papers that are genuinely different. Show results before and after, including a duplicate rate in the top-5.

### Pick an embedding model with evidence *(challenging)*

Compare at least two embedding models, for example a general-purpose model and one suited to scientific text. Tokenizer research is full of exact terms like "SentencePiece" or "fertility", so consider whether keyword search should sit alongside vector search. Report Recall@5 and MRR on your evaluation set, note cost and latency, and recommend one.

### A labelled evaluation set

Write 30–40 questions with the passages that answer them. Mix specific lookups ("what vocabulary size did paper X use?"), questions that need several papers, follow-up questions, and at least 5 questions your corpus cannot answer.

### A grounded chatbot

Support multi-turn conversation, so follow-ups like "how does that compare with WordPiece?" resolve correctly. Every answer should cite paper and section, and the bot should say plainly when the corpus doesn't support an answer. Measure how often answers are grounded and how it handles the unanswerable questions.

**Optional, if you have time:** a reranker, filters by year or venue, or a simple web UI. A command-line chat or notebook is perfectly fine; we won't score UI.

## What to send us

- **A GitHub repository is your submission.** Create it when you start, and make it public (or ask for a username to add if you'd prefer it private). Include a README that gets us running in a few commands. Don't commit the PDFs; include the script that downloads them.
- **A full commit history.** Commit small and often as you work, with clear messages, rather than one large commit at the end. Please don't squash or rewrite history; we'll read it to see how your work progressed.
- A corpus manifest (CSV or JSON) listing every paper you collected, with its metadata and whether it made it into the index.
- A short write-up (2–3 pages, Markdown is fine) covering your design decisions, a results table, and why you chose your embedding model and duplicate strategy.
- A transcript of one conversation of at least five turns, including a follow-up question and an unanswerable one.
- A failure analysis with at least three questions your system still gets wrong, and why you think it does.

## A suggested plan

| Day 1 | Day 2 | Half day |
|---|---|---|
| Collection pipeline, parsing and chunking, a baseline index with one model, and your evaluation set. | Version and duplicate handling, the embedding comparison, and the multi-turn chatbot with citations. | Run the final evaluation, write up results and failure cases, and tidy the README. |

## How we'll look at it

| What | What good looks like | Weight |
|---|---|---|
| Corpus | Broad, relevant coverage collected by a pipeline we can rerun, with clear inclusion rules. | 20% |
| Retrieval and duplicates | A clear approach to versions and near-duplicates with measured impact, and awareness of what it might wrongly merge. | 25% |
| Evaluation rigour | A sensible evaluation set, honest numbers, and comparisons that actually test the decision being made. | 25% |
| Chat quality | Follow-ups resolve correctly, citations point to the right place, and the bot abstains when it should. | 15% |
| Code and reproducibility | Readable, organised code that runs from the README, with a commit history that shows how the work progressed. | 15% |

## Ground rules

- Use any language, libraries, frameworks and AI coding assistants you like. You should be able to explain and change any line of your code without them.
- A CPU-only setup is fine. Free tiers and open models are fine; you shouldn't need to spend money.
- Keep API keys out of the repository.
- If something in the brief is unclear, make a reasonable assumption and write it down.

## After you submit

Send the GitHub repository link. A call of about an hour follows:

- 15 minutes to walk through your approach and results.
- 20 minutes of a small live change to your code together, without AI assistance.
- The rest for questions both ways, followed by conversations with the hiring manager.
