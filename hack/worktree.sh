#!/usr/bin/env bash
# worktree.sh - create, list and clean up fully working git worktrees (see docs/adr/0013).
#
#   hack/worktree.sh create <name> [--base <ref>] [--branch <branch>] [--judge | --no-judge] [--no-verify]
#   hack/worktree.sh list
#   hack/worktree.sh cleanup <name|path> [--force] [--delete-branch]
#
# Worktrees live in <main checkout>/.claude/worktrees/<name>, where Claude Code's EnterWorktree
# can switch into them. `create` copies the local files listed in .worktreeinclude, runs
# `uv sync`, and checks the result with the test suite; if any step fails, it removes what it made.
#
# `cleanup` refuses to discard work: it stops if the worktree has uncommitted changes (unless
# --force), and keeps the branch unless it is merged into the default branch, fully pushed, or
# --delete-branch is given.

set -euo pipefail

if [ -t 2 ]; then RED=$'\033[0;31m' GREEN=$'\033[0;32m' YELLOW=$'\033[1;33m' NC=$'\033[0m'; else RED="" GREEN="" YELLOW="" NC=""; fi

info() { printf '%s\n' "$*"; }
ok() { printf '%s✓%s %s\n' "$GREEN" "$NC" "$*"; }
warn() { printf '%s!%s %s\n' "$YELLOW" "$NC" "$*" >&2; }
die() {
  printf '%s✗ %s%s\n' "$RED" "$*" "$NC" >&2
  exit 1
}

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

# The main checkout, even when this runs from inside a worktree.
MAIN_ROOT=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
WORKTREES_BASE="$MAIN_ROOT/.claude/worktrees"
INCLUDE_FILE="$MAIN_ROOT/.worktreeinclude"

default_branch() {
  local ref
  ref=$(git -C "$MAIN_ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || ref=origin/main
  printf '%s\n' "${ref#origin/}"
}

# Where the manifest of copied-in files lives: the worktree's private git dir, so it goes away
# with the worktree. Each line is "<blob hash> <path>".
manifest_path() {
  printf '%s/worktree-copied\n' "$(git -C "$1" rev-parse --path-format=absolute --git-dir)"
}

# Uncommitted work in a worktree: tracked changes, plus untracked files that were not copied in
# by `create` or were changed since. Ignored files (.venv, caches, downloads) are regenerable.
uncommitted_work() {
  local wt=$1 manifest untracked
  git -C "$wt" status --porcelain --untracked-files=no
  untracked=$(git -C "$wt" ls-files --others --exclude-standard)
  [ -n "$untracked" ] || return 0
  manifest=$(manifest_path "$wt")
  [ -f "$manifest" ] || manifest=/dev/null
  paste -d' ' \
    <(printf '%s\n' "$untracked" | git -C "$wt" hash-object --stdin-paths) \
    <(printf '%s\n' "$untracked") |
    grep -vxF -f "$manifest" | sed 's/^[0-9a-f]* /?? /' || true
}

# Prints "<path> <branch>" for every worktree under WORKTREES_BASE (branch is "-" when detached).
worktrees() {
  git -C "$MAIN_ROOT" worktree list --porcelain | awk -v base="$WORKTREES_BASE/" '
    /^worktree / { path = substr($0, 10); branch = "-" }
    /^branch / { branch = substr($0, 8); sub("^refs/heads/", "", branch) }
    /^$/ { if (index(path, base) == 1) print path, branch; path = "" }
    END { if (path != "" && index(path, base) == 1) print path, branch }'
}

# ---------------------------------------------------------------------------------------- create

cmd_create() {
  local name="" base="" branch="" judge=auto verify=1
  while [ $# -gt 0 ]; do
    case $1 in
    --base) base=${2:?--base needs a ref}; shift 2 ;;
    --branch) branch=${2:?--branch needs a name}; shift 2 ;;
    --judge) judge=1; shift ;;
    --no-judge) judge=0; shift ;;
    --no-verify) verify=0; shift ;;
    -h | --help) usage ;;
    -*) die "unknown option: $1" ;;
    *) [ -z "$name" ] || die "unexpected argument: $1"; name=$1; shift ;;
    esac
  done
  [ -n "$name" ] || die "usage: hack/worktree.sh create <name> [--base <ref>] [--branch <branch>]"
  [[ $name =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "name may contain only letters, digits, '.', '_' and '-': $name"
  branch=${branch:-$name}
  git check-ref-format --branch "$branch" >/dev/null || die "not a valid branch name: $branch"
  base=${base:-$(git rev-parse --abbrev-ref HEAD)}
  git rev-parse --verify --quiet "$base^{commit}" >/dev/null || die "base is not a commit: $base"

  local wt="$WORKTREES_BASE/$name"
  [ ! -e "$wt" ] || die "already exists: $wt"

  local created_branch=0
  if git -C "$MAIN_ROOT" show-ref --verify --quiet "refs/heads/$branch"; then
    if git -C "$MAIN_ROOT" worktree list --porcelain | grep -qxF "branch refs/heads/$branch"; then
      die "branch $branch is already checked out in another worktree"
    fi
    info "Using existing branch $branch (--base ignored)"
  else
    created_branch=1
  fi

  # From here on, a failure removes the worktree and any branch this run created.
  rollback() {
    warn "setup failed; removing $wt"
    git -C "$MAIN_ROOT" worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"
    git -C "$MAIN_ROOT" worktree prune
    [ "$created_branch" = 0 ] || git -C "$MAIN_ROOT" branch -D "$branch" >/dev/null 2>&1 || true
  }
  trap rollback EXIT

  mkdir -p "$WORKTREES_BASE"
  if [ "$created_branch" = 1 ]; then
    git -C "$MAIN_ROOT" worktree add --quiet -b "$branch" "$wt" "$base"
    ok "Worktree at $wt on new branch $branch from $base ($(git rev-parse --short "$base"))"
  else
    git -C "$MAIN_ROOT" worktree add --quiet "$wt" "$branch"
    ok "Worktree at $wt on branch $branch"
  fi

  copy_local_files "$wt"
  install_env "$wt" "$judge"
  [ "$verify" = 0 ] || verify_env "$wt"

  trap - EXIT
  info ""
  ok "Ready: $wt"
  info "  cd $wt"
  info "  (Claude Code: EnterWorktree with path $wt)"
  info "  When done: hack/worktree.sh cleanup $name"
}

# Copies the untracked and ignored files of the main checkout that match .worktreeinclude,
# except paths the new branch tracks, and records what was copied.
copy_local_files() {
  local wt=$1 list manifest
  manifest=$(manifest_path "$wt")
  : >"$manifest"
  if [ ! -f "$INCLUDE_FILE" ]; then
    warn "no .worktreeinclude in $MAIN_ROOT; copying no local files"
    return
  fi
  list=$(mktemp)
  comm -23 \
    <(git -C "$MAIN_ROOT" ls-files --others --ignored --exclude-from="$INCLUDE_FILE" |
      grep -v '^\.claude/worktrees/' | sort) \
    <(git -C "$wt" ls-files | sort) >"$list"
  if [ -s "$list" ]; then
    tar -C "$MAIN_ROOT" -cf - -T "$list" | tar -C "$wt" -xf -
    paste -d' ' <(git -C "$wt" hash-object --stdin-paths <"$list") "$list" >"$manifest"
  fi
  ok "Copied $(wc -l <"$list" | tr -d ' ') local files listed in .worktreeinclude"
  rm -f "$list"
}

install_env() {
  local wt=$1 judge=$2
  if [ "$judge" = auto ]; then
    # Match the main checkout: install torch and transformers only if it has them.
    if compgen -G "$MAIN_ROOT/.venv/lib/python*/site-packages/torch" >/dev/null; then judge=1; else judge=0; fi
  fi
  local args=(sync --locked --quiet)
  [ "$judge" = 0 ] || args+=(--group judge)
  (cd "$wt" && env -u VIRTUAL_ENV uv "${args[@]}")
  if [ "$judge" = 1 ]; then ok "Installed .venv with uv (with the judge group)"; else ok "Installed .venv with uv"; fi
}

verify_env() {
  local wt=$1 out
  if ! out=$(cd "$wt" && env -u VIRTUAL_ENV uv run --locked chatbot-rag-tokenizers --help 2>&1); then
    printf '%s\n' "$out" >&2
    die "the CLI does not start in the worktree"
  fi
  if ! out=$(cd "$wt" && env -u VIRTUAL_ENV uv run --locked pytest -q 2>&1); then
    printf '%s\n' "$out" >&2
    die "tests fail on $(git -C "$wt" rev-parse --abbrev-ref HEAD); fix the base or pass --no-verify"
  fi
  ok "CLI starts and tests pass ($(printf '%s\n' "$out" | tail -1))"
}

# ------------------------------------------------------------------------------------------ list

cmd_list() {
  local main path branch state ahead
  main=$(default_branch)
  local rows
  rows=$(worktrees)
  if [ -z "$rows" ]; then
    info "No worktrees in $WORKTREES_BASE"
    return
  fi
  printf '%-32s %-40s %-10s %s\n' NAME BRANCH STATE "AHEAD OF $main"
  while read -r path branch; do
    if [ -n "$(uncommitted_work "$path")" ]; then state=dirty; else state=clean; fi
    ahead=-
    [ "$branch" = - ] || ahead=$(git -C "$MAIN_ROOT" rev-list --count "$main..$branch" 2>/dev/null || echo "?")
    printf '%-32s %-40s %-10s %s\n' "$(basename "$path")" "$branch" "$state" "$ahead"
  done <<<"$rows"
}

# --------------------------------------------------------------------------------------- cleanup

# Why the branch's commits are safe without the local branch, or nothing if they are not.
branch_is_safe() {
  local branch=$1 main ref upstream tip pr
  main=$(default_branch)
  tip=$(git -C "$MAIN_ROOT" rev-parse "$branch")
  for ref in "$main" "origin/$main"; do
    if git -C "$MAIN_ROOT" rev-parse --verify --quiet "$ref" >/dev/null &&
      git -C "$MAIN_ROOT" merge-base --is-ancestor "$tip" "$ref"; then
      echo "merged into $ref"
      return
    fi
  done
  upstream=$(git -C "$MAIN_ROOT" rev-parse --abbrev-ref --symbolic-full-name "$branch@{upstream}" 2>/dev/null) || upstream=""
  if [ -n "$upstream" ] && git -C "$MAIN_ROOT" merge-base --is-ancestor "$tip" "$upstream"; then
    echo "pushed to $upstream"
    return
  fi
  # A squash or rebase merge on GitHub leaves no ancestry; trust a merged PR whose head is this tip.
  if command -v gh >/dev/null 2>&1; then
    pr=$(cd "$MAIN_ROOT" && gh pr list --head "$branch" --state merged \
      --json number,headRefOid --jq ".[] | select(.headRefOid == \"$tip\") | .number" 2>/dev/null | head -1) || pr=""
    [ -z "$pr" ] || echo "merged as PR #$pr"
  fi
}

cmd_cleanup() {
  local target="" force=0 delete_branch=0
  while [ $# -gt 0 ]; do
    case $1 in
    --force) force=1; shift ;;
    --delete-branch) delete_branch=1; shift ;;
    -h | --help) usage ;;
    -*) die "unknown option: $1" ;;
    *) [ -z "$target" ] || die "unexpected argument: $1"; target=$1; shift ;;
    esac
  done
  if [ -z "$target" ]; then
    cmd_list
    info ""
    die "usage: hack/worktree.sh cleanup <name|path> [--force] [--delete-branch]"
  fi

  local wt branch path b
  case $target in
  /*) wt=${target%/} ;;
  *) wt="$WORKTREES_BASE/$target" ;;
  esac
  branch=""
  while read -r path b; do
    [ "$path" != "$wt" ] || branch=$b
  done <<<"$(worktrees)"
  [ -n "$branch" ] || die "no worktree at $wt (see: hack/worktree.sh list)"

  local work
  work=$(uncommitted_work "$wt")
  if [ -n "$work" ]; then
    if [ "$force" = 0 ]; then
      printf '%s\n' "$work" | head -20 >&2
      die "$wt has uncommitted work (above); commit it, or pass --force to discard it"
    fi
    warn "discarding uncommitted work in $wt"
  fi

  case $PWD/ in "$wt"/*) warn "your shell is inside $wt; cd elsewhere afterwards" ;; esac

  # The copied-in local files are untracked, so plain `worktree remove` would refuse; the check
  # above has already established that nothing in them is new work.
  git -C "$MAIN_ROOT" worktree remove --force "$wt"
  git -C "$MAIN_ROOT" worktree prune
  ok "Removed worktree $wt"

  if [ "$branch" = - ]; then
    return
  fi
  local safe
  safe=$(branch_is_safe "$branch")
  if [ -n "$safe" ]; then
    git -C "$MAIN_ROOT" branch -D --quiet "$branch"
    ok "Deleted branch $branch ($safe)"
  elif [ "$delete_branch" = 1 ]; then
    git -C "$MAIN_ROOT" branch -D --quiet "$branch"
    warn "Deleted unmerged branch $branch"
  else
    info "Kept branch $branch: it has commits that are neither merged nor pushed."
    info "  Delete it with: git branch -D $branch"
  fi
}

case ${1:-} in
create) shift; cmd_create "$@" ;;
list) shift; cmd_list ;;
cleanup) shift; cmd_cleanup "$@" ;;
-h | --help | help) usage ;;
*) usage 1 ;;
esac
