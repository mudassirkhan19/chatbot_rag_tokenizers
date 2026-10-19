# 0046. The Evaluation set: short quotes committed, a check per question, and absence evidence

- **Date:** 2026-10-19
- **Status:** Accepted

## Context
Issue #37 drafts the real Evaluation set: 36 questions in `data/eval/evaluation-set.jsonl` (12 single-paper, 8 multi-paper, 8 follow-ups, 8 unanswerable), about 25 grounded in Seeds and about 10 in non-Seed papers. An agent drafts them and the developer checks them. Three things needed deciding.

- **Quotes.** Each Passage holds a verbatim quote from a paper, so the committed set holds paper text. [0002](0002-no-pdfs-or-secrets-in-git.md) keeps the papers out of git because their licences aren't ours to decide. [0033](0033-cc-by-tei-fixtures-may-be-committed.md) lets paper text in only as whole fixtures from CC BY 4.0 Versions. The quoted Versions are under several licences. In the manifest, 9 of the 22 are CC BY 4.0, 4 CC BY-SA, 2 CC BY-NC-SA, and 7 have arXiv's non-exclusive licence, which grants nothing to third parties.
- **Who checked a question.** Spec #31 (story 15) says no agent-drafted question is scored before a person has checked it. Nothing in the set recorded that.
- **Unanswerable questions.** A question is only unanswerable if no Chunk in the corpus answers it. Absence has to be shown, since an answer in some other paper would make the agent's "the paper doesn't say" wrong.

## Decision
**Passage quotes of at most 300 characters are committed as quotation for evaluation, whatever the paper's licence.**
- A quote is one sentence or part of one, the shortest span that answers the question. `eval-check` fails any quote over 300 characters (`MAX_QUOTE_CHARACTERS`). At drafting, the 37 Passages ran from 58 to 217 characters.
- Each quote names its source: the pinned Edition id (with its Version, for an arXiv Edition) and the Section it comes from. That is the attribution a citation gives.
- A quote is there to mark where the answer is, so a retrieved Chunk can be matched against it ([0041](0041-passage-matcher-eval-check-and-calibration.md)). It doesn't stand in for the paper. This is brief quotation for scholarship, the use a citation in a paper makes. It isn't redistribution, which is what 0002 and 0033 are about. So the licence doesn't decide it, and 0033's CC BY rule stays for fixtures, which hold whole files.
- The same rule covers `data/eval/absence-evidence.md`. It shows 160 characters of each retrieved Chunk, with its pinned id and Section.

**Every question records who checked it, and `eval-check` fails any question that nobody has checked.**
- A question's `checked_by` names who checked it: the developer, or an agent review the developer approved. An empty or missing value fails `eval-check` with "nobody has checked this question (checked_by is empty)". `evaluate` refuses any set that fails `eval-check`, so nothing is scored until every question has been checked.
- The agent commits the drafted set with every `checked_by` empty. The developer reads each question and its Passages, edits what needs it, and fills in `checked_by`.
- The developer may hand the routine checks to an agent review and check by hand only what the review flags. Such a question's `checked_by` says so (`agent review, approved by Mudassir`), so the set shows which questions a person read and which they delegated. For the first set, two were checked by hand and 34 through an agent review. That review made seven clear fixes: four rewordings that lowered overlap with the quotes, and three Passages extended so they answer the whole question. It also flagged one unanswerable question that was answerable after all (see below).
- `hack/check_evalset.py` serves a local page for this: each quote marked in its whole Section, the absence evidence with each Chunk in full, and eval-check rerun on every save. An edit saved there clears the question's `checked_by`.

**Absence is shown by searching every Chunk with both retrievers, and the evidence is committed.**
- `hack/absence_search.py` runs each unanswerable question through BM25 and the dense baseline, together with two probe queries per question worded the way an answer would read. It writes each top 10 to `data/eval/absence-evidence.md`, with the drafter's reading of the nearest miss.
- A candidate that turned out answerable was dropped, not reworded. Six were dropped this way:
  - the Llama 3 tokenizer's premium for Shan "according to Petrov et al.": it passed the retriever searches, but the review found Table 2 of 2601.13328v1 (§3.3) with a Llama 3 column giving Shan 15.13×, worked out the way Petrov et al. define the premium. A question that is unanswerable only because of who it credits is a trap, not a near-miss, so it was replaced by the GPU-hours spent pre-training the 8B Byte Latent Transformer;
  - the compute spent training a ZeTT hypernetwork: 2411.18553v3 gives about 3 days on a TPUv4-32 pod for a 7B model;
  - the optimal vocabulary for Llama 3.1 405B: the scaling-law paper's appendix predicts 487K for "Llama3-400B";
  - CANINE on GLUE: HASHFORMER (2022.emnlp-main.536) reports CANINE-C on GLUE;
  - CANINE on XNLI: 2210.07111v1 evaluates CANINE-S on XNLI;
  - under-trained tokens in GPT-4: Fishing for Magikarp v1 has a section on GPT-3.5 and GPT-4.
- The 8 kept are 6 in-topic near-misses and 2 out of topic (vitamin D intake, the 2018 FIFA World Cup). The developer confirms each one against the evidence when checking it, so `checked_by` on an unanswerable question also records that its absence was confirmed.

**Sources, counted per question at drafting.** 19 answerable questions quote only Seeds. 9 quote a non-Seed paper: XLM-V, Fishing for Magikarp (2), SuperBPE (2), Fast WordPiece, Unpacking Tokenization, MEGABYTE and Zouhar et al.'s Rényi efficiency. Of the unanswerable questions, 5 near-misses are about Seeds and 1 is about a non-Seed (Fast WordPiece on a GPU). So 24 questions rest on Seeds, 10 on non-Seeds, and 2 on neither.

## Alternatives considered
- **Committing only pointers (pinned id, Section, character offsets), with the quotes resolved from the local parse cache.** No paper text would be in git. But the set couldn't be read or reviewed without a full parse, and offsets break whenever chunking or GROBID output changes. The quote is what `eval-check` and the matcher use, so the set would depend on the parse cache it is meant to check.
- **Quoting only CC BY papers, as 0033 does for fixtures.** That would leave out SentencePiece, BPE-dropout, CANINE, ByT5 and subword regularization. All are arXiv non-exclusive, and they are among the Seeds the questions are about. A few short quotes are not the whole files 0033 is about.
- **A set-level "reviewed" flag.** A per-question value shows which questions are still unchecked after a partial review. It also survives one question being edited later.
- **Showing absence with BM25 alone.** BM25 misses paraphrases, which is what the dense baseline catches. The 405B candidate's answer showed up only in the dense ranking.

## Consequences
- `just eval-check` fails on the committed set until the developer has checked every question. That is intended: `evaluate` waits for the check.
- Editing a question's wording or Passages after it is checked should clear or update its `checked_by`. Nothing enforces this; it is up to the editor.
- Adding an unanswerable question means adding probes and a reading to `hack/absence_search.py` and rerunning it. The evidence file is regenerated whole.
- If the corpus changes (a new parse or more papers), the absence evidence goes stale and should be rerun before the set is trusted again.
