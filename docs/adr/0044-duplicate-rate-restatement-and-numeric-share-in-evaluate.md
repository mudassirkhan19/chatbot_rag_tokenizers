# 0044. Duplicate rate, Survey restatement and the numeric-Chunk share in evaluate

- **Date:** 2026-10-19
- **Status:** Accepted

## Context
Spec #31 asks for the "before" numbers for duplicate handling: how much of the top 5 is taken by Chunks of a Work already ranked higher. It also asks for #26's question to be answered: do mostly-numeric text Chunks, most of them a missed table's cells ([0035](0035-missed-table-cells-stay-in-text-chunks.md)), crowd the top 5, and does any of them ever answer a question? Issue #36 builds the measurement into `evaluate`. Issue #38 then groups the baseline top-5 Editions by hand and commits the baseline report.

The spec fixes the definitions:
- the duplicate rate is two numbers: the share of top-5 slots holding a Chunk from a Work already ranked higher, and the share of questions with at least one such slot;
- it is measured against Work groups given as input, never computed by the system being measured;
- a Survey restating a finding is reported as restatement, never as a duplicate.

The choices below are the ones it leaves open.

## Decision
**The Work groups file** is `data/eval/work-groups.csv` (`--work-groups`), committed.
- Its columns are `edition_id,work_id,survey,title,authors,year,venue`, one Edition per row. Editions with the same `work_id` are one Work. `survey` is `yes` or `no`.
- Title, authors, year and venue aren't read. They are there so the person grouping can see what they are grouping, and so an exported row can be pasted in as it is.
- A row with a blank `work_id` is an Edition with no Work group yet, which is how the export writes it.
- Loading fails on a missing column, an Edition listed twice, a `survey` other than `yes` or `no`, and a Work whose Editions are partly Surveys. A Survey is always its own Work (the glossary), so its Editions are all Surveys.
- It is committed with only its header. #38 fills it.

**The export** is `evaluate --export-ungrouped <csv>`. It writes every Edition in any retriever's top 5, for any query of an answerable question (all three follow-up modes too), that has no Work group, in Edition-id order, with its title, authors, year and venue from the manifest. `evaluate` writes its report as usual alongside. It is part of `evaluate` because only `evaluate` has the rankings; a separate command would have to run every query again.

**What a slot is.** Each of the top 5 Chunks of a query, best first. A retriever that ranks fewer than 5 Chunks has fewer slots.
- A **duplicate** slot holds a Chunk whose Work, not a Survey, is the Work of a Chunk ranked higher. That is another Edition of the Work (the venue Edition of a preprint), another Version of it (a v1 next to the latest Version), or another Chunk of the same file. The spec's definition counts all three: each gives the reader the same paper again in place of another.
- A **restatement** slot holds a Chunk from a Survey. A second Chunk of the same Survey is restatement too, never a duplicate. A Survey ranked higher never makes a Chunk of another Work a duplicate.
- A **mostly-numeric** slot holds a text Chunk that `is_mostly_numeric` (more than 35% of its words numbers): the parse report's own test, so the two counts agree.

**Only grouped questions count.** Duplicates and restatement are counted for a query only when every Edition in its top 5 has a Work group. Any other query is left out of both totals, and its line in the report says `ungrouped`. Counting the grouped slots of a partly grouped top 5 would read a missing group as "no duplicate", since the slot above might be the same Work. The numeric share needs no grouping and counts every query. `evaluate` prints the Editions with no Work group, and the report lists them.

**Which queries make the totals.** The *all answerable* row's: each answerable question once, as a user would ask it, a follow-up alone. Unanswerable questions are left out, as they are from the metrics. Every query of an answerable question still gets its line, with its duplicate, restatement and numeric slots.

**The eval report** gains:
- a *Crowding* section, after the results: the Work groups file with its sha256, the definitions, then a table per retriever with each measure's slots and questions as counts and shares, how many questions were grouped, and how many mostly-numeric slots hold a Passage;
- an *Editions without a Work group* section;
- three columns in each question's line: duplicate, restatement and numeric slots.

Like the rest of the report above the timings, all of it depends only on the inputs.

## Alternatives considered
- **Group Editions from the manifest's identifiers**, as `eval-check` does ([0041](0041-passage-matcher-eval-check-and-calibration.md)). It needs no hand work. But it is the kind of rule the duplicate stage will use, so the stage would be scored by its own grouping. It also misses duplicates that share no identifier, and can't tell a Survey.
- **Count only other Editions and Versions as duplicates, not other Chunks of the same file.** Two Chunks of one file can both be relevant, and a multi-paper question can need both. But the spec's definition is about Works, and a second Chunk of the same paper still takes a slot another paper could have had. The before/after comparison needs one definition; the per-question lines show where the slots went.
- **Count grouped slots in a partly grouped top 5.** This uses more of the data while the groups are incomplete. But it undercounts duplicates without saying so. Once #38 groups every Edition, the two agree.
- **A separate `export` command.** It would need the index and the Evaluation set, and would run every query again.
- **research-bot**, the colleague's earlier project, used as inspiration only. It removes duplicates only when extracting references (it strips an arXiv id's version suffix before comparing) and when storing records (database unique constraints). It never measures duplicates in what it retrieves. We measure them on the raw ranking, against groups checked by hand, so that the duplicate stage has a number to beat.

## Consequences
- Until #38 fills the Work groups file, every question is `ungrouped`, and the duplicate and restatement figures count no question. The numeric share is reported already.
- The Work groups file covers only the Editions the baseline retrievers rank in their top 5. A new retriever, or a changed Evaluation set, may rank Editions it lacks. `evaluate` says so, and `--export-ungrouped` writes them for grouping.
- Retrievers in the embedding comparison are scored against the same groups, so their duplicate rates compare directly.
- `evaluate` now reads the manifest for the export's titles as well as for `eval-check`'s Works.
