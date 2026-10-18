---
name: worktree
description: Create or clean up a git worktree of this repo with hack/worktree.sh. Use when starting work that needs its own worktree (a parallel issue, an isolated change), or when finishing work in one.
---

# Worktrees

`hack/worktree.sh` makes a worktree that runs like the main checkout: `.env`, uncommitted Snapshot responses and other local files from `.worktreeinclude` are copied in, `.venv` is installed with `uv sync`, and the CLI and tests are checked before it reports ready. Worktrees live in `.claude/worktrees/<name>`. `hack/worktree.sh --help` lists every option. ADR 0013 has the reasoning.

## Start

1. Pick a short kebab-case name, e.g. `issue-12-dedup`. The branch takes the same name unless you pass `--branch`.
2. Run `hack/worktree.sh create <name>` from any checkout of the repo. The base is your current branch; pass `--base <ref>` for another.
3. Done when it prints `Ready: <path>`. If it fails, it has already removed the worktree and the branch it made: fix the cause and rerun.
4. Work in that path: in Claude Code, call `EnterWorktree` with `path: <path>`; otherwise `cd` there. Run every command (`uv run …`, `git …`) from inside it.

## Commit

The copied local files are untracked in the worktree (for example `data/snapshot/responses/arxiv-oai/`). Stage your own changes by path, so commits carry only what you changed. The list of copied files is in `$(git rev-parse --git-dir)/worktree-copied`.

## Finish

1. Commit or push everything worth keeping.
2. In Claude Code, call `ExitWorktree` with `action: "keep"` first, so the session is back in the main checkout.
3. Run `hack/worktree.sh cleanup <name>`. Done when it prints `Removed worktree`.
   - It stops on uncommitted work and lists it; copied files count only if you changed them. Commit, or ask the user before rerunning with `--force`, which discards that work.
   - It deletes the branch only when its commits are merged into the default branch, pushed, or merged as a GitHub PR. Otherwise it keeps the branch and says so; report that to the user. `--delete-branch` deletes it anyway: only when the user asks.

`hack/worktree.sh list` shows every worktree, whether it is clean, and how far its branch is ahead of the default branch.
