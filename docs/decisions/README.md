# Decision log

Short records of design decisions and the reasoning behind them, so choices can be revisited with context.
One file per decision, numbered in the order they were made. If a decision is reversed, add a new record that supersedes the old one rather than editing history.

| # | Decision | Status |
|---|---|---|
| [0001](0001-python-3.12-with-uv.md) | Python 3.12, managed with uv | Accepted |
| [0002](0002-no-pdfs-or-secrets-in-git.md) | Keep PDFs, downloaded data and secrets out of git | Accepted |
| [0003](0003-prior-work-as-inspiration-only.md) | Treat earlier internal work as inspiration only | Accepted |

## Template

```markdown
# NNNN. Title

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by NNNN

## Context
What problem or constraint forced a choice.

## Decision
What we chose.

## Alternatives considered
What else we looked at and why we didn't pick it.

## Consequences
What this makes easier or harder.
```
