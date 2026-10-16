# 0013. Fully working worktrees for parallel work

- **Date:** 2026-10-16
- **Status:** Accepted

## Context
Agents work on several issues at once, each in its own git worktree. A bare `git worktree add` only checks out tracked files: there is no `.env` (ADR 0002), no `.venv`, and none of the Snapshot responses that are fetched but not yet committed (ADR 0003). In such a worktree `collect` goes back to the network, possibly for hours at arXiv's rate limit, and commands cannot be tested as they would run in the main checkout. Removing a worktree carelessly can also lose uncommitted work or an unmerged branch.

## Decision
- `hack/worktree.sh create <name>` adds the worktree in `.claude/worktrees/<name>` (where Claude Code's `EnterWorktree` can switch into it) on a branch of the same name, then:
  - copies every untracked or ignored file of the main checkout that matches `.worktreeinclude` (gitignore syntax), skipping paths the new branch tracks, and records each copied file with its blob hash in the worktree's private git dir;
  - runs `uv sync --locked`, adding the `judge` group when the main checkout's `.venv` has torch;
  - checks that the CLI starts and `pytest` passes.
  If any step fails, it removes the worktree and the branch it created, so a half-set-up worktree is never left behind.
- `hack/worktree.sh cleanup <name>` refuses while the worktree has uncommitted work: tracked changes, or untracked files that were not copied in or have changed since. It deletes the branch only when its tip is merged into the default branch (locally or on `origin`), contained in its upstream, or is the head of a merged GitHub PR (squash merges leave no ancestry). Otherwise it keeps the branch. `--force` and `--delete-branch` override each check separately.
- The workflow is a project skill (`.claude/skills/worktree/`), so agents reach it when they start or finish work in a worktree.

## Alternatives considered
- **Symlinking `.env`, `.venv` and `data/` to the main checkout.** Cheaper, but a worktree's `collect` would then write into the main checkout's Snapshot, and `.venv` holds an editable install pointing at the main checkout's `src/`, so the worktree would run the wrong code.
- **Copying the whole `.claude/` directory** (as the `statement-processing` script does). Here it holds the worktrees themselves; only `settings.local.json` is worth carrying.
- **Claude Code's own `EnterWorktree` alone.** It creates the checkout but none of the local state, and has no guarded cleanup.

## Consequences
- A new worktree is ready to run any command offline in a few seconds; the `.venv` is linked from uv's cache rather than downloaded again.
- Copied Snapshot responses show as untracked in the worktree, so agents must stage their own changes by path.
- A new kind of local state the repo needs goes in `.worktreeinclude`, or worktrees will lack it.
