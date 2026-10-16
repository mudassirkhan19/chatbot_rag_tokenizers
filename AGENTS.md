# Agent instructions

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `mudassirkhan19/chatbot_rag_tokenizers`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The labels are the five defaults: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human` and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. ADRs follow the template in `docs/adr/README.md`. See `docs/agents/domain.md`.

### Worktrees

Create and remove worktrees with `hack/worktree.sh`, which sets up `.env`, `.venv` and local data so commands run as in the main checkout. See `.claude/skills/worktree/SKILL.md`.
