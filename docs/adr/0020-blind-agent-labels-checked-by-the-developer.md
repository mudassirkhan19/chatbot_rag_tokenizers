# 0020. Audit set labels from blind agents, checked by the developer

- **Date:** 2026-10-17
- **Status:** Accepted

## Context
[0011](0011-audit-set-and-relevance-metrics.md) planned for the developer to correct all 180 draft labels, which are the pipeline's own verdicts. The export from the first full run (#11) has 60 Candidates in each stratum. After checking the first dozen rows by hand, the developer found the CSV hard to read and asked for agents to label the rest. The developer would then check the hard cases.

## Decision
- **Blind agent labels.** Three agents each labelled a third of the rows. They saw only the title, abstract and link, not the stratum, the judge's probability or any other read, so they could not anchor on the system's own answer. They looked up missing abstracts where they could. Each label came with a confidence and a one-line reason. The developer's own earlier labels were kept.
- **The developer checks the hard cases.** A row was flagged when:
  - the agent was unsure
  - the agent overturned the pipeline without an earlier independent read by Claude agreeing
  - Claude's earlier read was borderline
  - the agent disagreed with the developer

  37 rows were flagged. The developer checked all of them and changed two labels. Together with the 11 other rows checked before the agents ran, the developer checked 48 of 180.
- **Provenance in the file.** Two columns record how each label was set:
  - `labelled_by`: `draft`, `agent` or `developer`
  - `review_note`: why the row was flagged

  `audit export` writes `draft` and an empty note. A reviewer can see which labels a person checked without trusting this record.
- **A page for checking labels.** `audit label` serves a local page with one Candidate per screen. It shows the abstract, the pipeline's verdict in plain words (the judge's probability and threshold, or which rule fired), the review note, and the label. Every save rewrites that row and marks it `developer`. The agents' prompts and the merge script were one-off tooling and are not in the repository.

## Alternatives considered
- **The developer corrects all 180 drafts** ([0011](0011-audit-set-and-relevance-metrics.md)): the most direct, but slow, and it anchors on the judge's answer.
- **Agents see the pipeline's verdict:** faster to merge, but the agents would inherit the judge's anchoring, which is what the Audit set has to measure.
- **Only the agents, no developer check:** the Audit set would then measure the judge against another model's opinion, with no person in the loop on the disputed cases.

## Consequences
- The risk moves from anchoring on the judge to sharing the agents' blind spots. The developer's check of the hard cases limits it, and `labelled_by` shows where it applies.
- The report's "labels changed from the draft" now counts agent and developer changes together.
- Choosing "Unsure / skip" on the page leaves the label empty but still marks the row `developer`. The report ignores rows without a label.
