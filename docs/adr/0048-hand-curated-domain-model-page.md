# 0048. A hand-curated domain model page, refreshed by the issue that changes a number

- **Date:** 2026-10-19
- **Status:** Accepted

## Context
The repo records every decision ([the decision log](README.md)), every term (`GLOSSARY.md`) and every number (`data/report.md`, `data/audit/report.md`, `data/parse-report.md`, `data/eval/eval-report.md`), but nothing shows the business logic as one shape: how the corpus is found, judged, parsed, retrieved and measured, and what is still to build. Issue #48 asks for one page that reads top-down, for refining the developer's own understanding first and as the source of the write-up later. It has to be readable away from the repo and on a phone, and it has to let a reader drill from a one-screen view to the decision behind any number.

## Decision
- **`docs/domain-model.html` is the map.** One self-contained HTML file, committed, with no build step and no libraries: native collapsibles for the drill-down, one inline SVG funnel, system and Google fonts. It is also published as a claude.ai Artifact for reading on a phone; the repo copy is the source.
- **The process is the spine, the glossary nouns appear where the pipeline creates them.** Five stages plus a stage 0 for the scope boundary: Scope, Discover, Judge relevance, Acquire and parse, Retrieve, Evaluate; a Foundation band under them for the decisions that make every number reproducible; a "what's left" section for the brief's requirements without a stage; a worked example tracing one Work forwards and two questions backwards. Each stage panel has the same shape: goal, input and output, nouns born there, decisions with a two-to-three sentence digest and a GitHub link, numbers, how it is checked, what could be wrong (open issues, one line each), and a one-line reproduce.
- **It is written by hand, not generated.** Numbers are copied from the committed reports and dated in the header (as-of date, commit, Snapshot date). Decision digests are written for a reader who will not open the ADR.
- **Refresh rule.** The issue that changes a stage's status or a headline number (the funnel, the baseline metrics, the duplicate rate) also refreshes the page, in the same branch. Nothing else refreshes it.
- **Links go to GitHub**, never to relative paths, so they work from the checkout, the Artifact and a phone. Issue links are the only record of open risks, so the page lists issue numbers rather than restating them.

## Alternatives considered
- **Generate the page from the glossary, ADRs and reports.** It would stay current without the refresh rule, but it needs a parser for ADR prose, and the page's value is the digest and the "why" per decision, which no generator writes. The reports' numbers are few enough to copy by hand.
- **Markdown in `docs/`.** Easier to diff, but no drill-down: a reader gets every ADR digest at once or none. The page's point is to read L0 in one screen and open only what is doubted.
- **An entity diagram (Work, Edition, Chunk, …) as the main view.** A project manager asks "how did we get the data" before "what is an Edition"; the nouns only make sense at the stage that creates them. The page keeps one entity strip under the funnel and otherwise introduces each noun in its stage.
- **Leave the unbuilt stages out.** The most useful fact for a manager's view is how far along the work is, so the embedding comparison, duplicate suppression and chatbot appear greyed with the brief's requirement and what already exists toward each.

## Consequences
- The write-up condenses this page rather than starting from the ADRs; the results table and the funnel are already in it.
- A stale page is a known failure mode. The header's as-of date and commit make staleness visible, and the refresh rule puts the cost on the issue that moved the number.
- The ADR links are a hand-kept map of ADR number to file name inside the page; a renamed ADR breaks its link until the page is refreshed.
