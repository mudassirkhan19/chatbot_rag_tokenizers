# 0047. Hand-checked Work groups are the ground truth for the duplicate rate

- **Date:** 2026-10-19
- **Status:** Accepted. Amended by [0063](0063-versions-and-near-duplicates-measured-before-and-after.md): rows may be checked by a blind agent.

## Context
[0044](0044-duplicate-rate-restatement-and-numeric-share-in-evaluate.md) built the duplicate rate into `evaluate`, measured against a Work groups file given as input, and left that file empty. Issue #38 fills it: every Edition that either baseline ranks in its top 5, for any query of an answerable question, gets a Work and a Survey flag. The file is also the test set for the duplicate stage that comes later. So it must not come from the rule that stage will use, and a reader must be able to tell which rows a person checked.

On the full Evaluation set (36 questions, 28 answerable), BM25 and the dense baseline put 154 Editions in their top 5.

## Decision
**The Work groups are drafted by an agent and checked by the developer, Work by Work, and the file records who checked each row.**
- **The draft** joins two Editions when the manifest links them by an arXiv id, DOI or ACL id, as `eval-check` does ([0041](0041-passage-matcher-eval-check-and-calibration.md)), or when their titles match after case, accents and punctuation are dropped. The draft has 130 Works, 24 of them with more than one Edition. Eight Editions in four Works were joined by title alone, because the manifest links no identifier between a preprint and its venue Edition. Those rows carry a note.
- **Survey flags** are the agent's reading of each abstract. Two Works are drafted as Surveys: Mielke et al.'s history of open-vocabulary modelling (2112.10508), and Libovický et al.'s "literature and empirical survey" of character-level MT (2110.08191), which also runs new experiments. Four near-misses are drafted as not Surveys, each with a note: a journal article consolidating its authors' own analyses, a position paper, an essay and a tutorial.
- **Two columns record the check.** They follow the Audit set's `labelled_by` and `review_note` ([0020](0020-blind-agent-labels-checked-by-the-developer.md)):
  - `checked_by`: who checked the row. A name means a person checked it on the page. `draft, approved by <name>` means that person approved the drafted row as a whole without marking it there, as an agent review can be approved for the Evaluation set ([0046](0046-evaluation-set-quotes-checked-by-and-absence-evidence.md)). It is blank in the draft.
  - `note`: why a drafted row needs a closer look.

  Neither is read for scoring. The export writes both blank. Both are optional, so a file without them still loads.
- **The eval report counts the checked rows.** The Work groups line now says "154 Editions in 130 Works, N of the Editions checked (who checked each is in checked_by)". It used to say "hand-checked" whatever the file held.
- **How the first file was checked.** The developer reviewed the flagged Works and the Works with several Editions on the page, and approved the rest of the draft. Seven rows were marked on the page: the five flagged single Editions and both Editions of Lee et al.'s fully character-level NMT. The other 147 rows are `draft, approved by Mudassir`. No Work was merged or split and no Survey flag changed, so the duplicate figures below are the checked ones.
- **A page for checking.** `hack/check_work_groups.py` serves a local page with one Work per screen. Each screen shows:
  - every Edition's title, authors, venue and identifiers with links;
  - the abstract and Section headings from the parse cache;
  - the draft's note;
  - up to five other Works that may be the same paper (shared title words or the same first author), each with a button to merge it in.

  The page can rename a Work, flip its Survey flag, move an Edition to another Work or split it off. Every save goes through `load_work_groups` before the file is written, so a Work with both Survey and non-Survey Editions is refused. A move or edit clears `checked_by` on the Works it touches, as an edit does for an evaluation question ([0046](0046-evaluation-set-quotes-checked-by-and-absence-evidence.md)).
- **The draft script is one-off tooling** and is not in the repository, like the Audit set's agent prompts (0020). What it did is recorded here, and the `note` column marks the rows it was unsure of.

## Alternatives considered
- **Use the manifest's identifier links as the groups.** This needs no hand work, but it is the rule the duplicate stage will start from, so the stage would be scored by its own grouping (0044). On this draft it would also have kept four preprint–venue pairs apart: BanglaByT5, Teaching Old Tokenizers New Words, Prune or Retrain, and Tokenization is Sensitive to Language Variation.
- **The developer groups 154 rows from the blank export.** This is the most direct, but most rows are a single Edition with nothing to decide. A draft with flags puts the developer's time on the 24 multi-Edition Works, the title-only joins and the Survey calls, and the page's suggestions cover the duplicates the draft missed.
- **Check by sampling.** The groups are a test set for a stage that will itself be tuned on them. An unchecked row is an unchecked label, so every row is checked, and the report says how many were.
- **research-bot**, the colleague's earlier project, used as inspiration only. It indexes arXiv papers only, one vector per paper id. It treats Versions as one paper by stripping the `vN` suffix when extracting references, and skips a repeat id within a search category through a database unique index on (id, category). The same paper can still be stored once per category. It has no venue Editions, no Surveys and no retrieval evaluation, so it never needs a ground truth for "same paper". Our corpus joins arXiv, ACL Anthology, Semantic Scholar and OpenAlex Editions, and Chunks are retrieved, not papers, so the same Work can take several slots in three ways (same file, another Version, another Edition). Version-stripping would catch only the second. A grouping that a person has checked, with Surveys marked, is what lets all three be counted and later beaten.

## Consequences
- With the draft groups, every answerable question's top 5 is grouped. The duplicate rate in the eval report is 59 of 140 top-5 slots for BM25 and 70 of 140 for the dense baseline. The report doesn't split them, but a one-off pass over the same rankings did, counting a duplicate slot as same-file when the Edition id matches the one ranked higher in that Work. Most are other Chunks of the same file: 41 of 59 for BM25 and 57 of 70 for dense. The other 18 and 13 slots are another Edition or Version of the same Work, in 16 and 11 Works. The duplicate stage has to handle both: collapsing Editions alone would leave most of the duplicate slots.
- Every row now has a `checked_by`, and the committed report says so. The file shows which rows a person marked on the page and which they approved as a draft.
- A new retriever, or a changed Evaluation set, may rank Editions the file lacks. `evaluate` names them, and `--export-ungrouped` writes them for the same draft-and-check loop.
