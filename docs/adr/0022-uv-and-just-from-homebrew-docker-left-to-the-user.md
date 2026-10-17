# 0022. uv and just from Homebrew, Docker and Ollama left to the user

- **Date:** 2026-10-17
- **Status:** Accepted. Supersedes the "setup is `uv sync`" consequence of [0001](0001-python-3.12-with-uv.md).

## Context
A reviewer who clones the repo had to piece the setup together from the README: install uv, run `uv sync` with the right dependency groups, and soon also run a Docker daemon for the GROBID parser. Nothing said which tool versions the repo is tested with, and everyday commands were long `uv run` lines. The setup only has to work on macOS.

## Decision
- **Prerequisites are installed by the reader**, as the README lists them: macOS, `brew install uv just`, a Docker daemon of their choice (Docker Desktop, OrbStack or Colima), and Ollama at the exact version the judge is pinned to (ADR 0021). The repo installs none of these.
- **Pins live where the tools already read them.** `[tool.uv] required-version` in `pyproject.toml` sets the oldest uv the repo accepts, and uv itself refuses older ones. `uv.lock` pins Python 3.12 (ADR 0001) and every package. The GROBID image is pinned by digest in `config/parse.toml` (ADR 0023). The judge model and the Ollama version that runs it are pinned together in `config/scope.toml` (ADR 0021). just only runs recipes, so its version is not pinned; the README gives the tested one.
- **`just init`** checks, in order, that uv is installed and meets `required-version`, that Docker is installed, and that its daemon answers. Each failure has its own message saying what to install or start, and exits non-zero. It then runs `uv sync --all-groups --locked`, which never rewrites `uv.lock`, so a second run changes nothing. When the judge runs on Ollama, it then checks that Ollama is installed, answers, and runs the pinned version, pulls the judge model if Ollama lacks it, and checks the model's digest against the pin. A wrong version or digest stops `init` with what to do; it never upgrades Ollama or replaces a model itself. It ends with a short summary. It installs nothing outside `.venv`, Docker's image store and Ollama's model store.
- **The `justfile` is a thin wrapper.** `test`, `typecheck` and `lint` wrap pytest, mypy and ruff; `collect` and `fetch` call the CLI and forward extra arguments, so the CLI stays the real interface. `just` alone lists the recipes with one-line descriptions.
- **ruff checks errors only** (`E4`, `E7`, `E9`, `F`), not style, so `just lint` passes on the existing code without a mass reformat.

## Alternatives considered
- **A nix flake dev shell** (with direnv). It would pin `just`, `uv` and the `docker` CLI in a lock file, but uv and Python are already pinned by `required-version` and `uv.lock`, and just needs no pin. Asking reviewers to install nix, a large and unfamiliar tool, to pin only just is not worth it. This was the first plan in #13 and was dropped.
- **A Brewfile.** `brew bundle` installs the tools in one step but cannot pin versions, so it adds a file without adding reproducibility over `brew install uv just`.
- **A plain shell script** instead of a justfile. It covers `init`, but not the short everyday recipes or the self-documenting listing.
- **Installing Docker for the user.** A daemon is a system-wide app with its own licence terms and several equivalent choices; picking one for the reader would install software outside the repo. `init` only checks that one answers.
- **Installing Ollama for the user.** The same reasons apply, and Homebrew cannot install one exact version, which the judge needs. `init` checks the version instead.
- **Leaving Ollama out of `init`.** The judge checks the version and digest itself, but only once `collect` reaches scoring. `init` reports a missing or wrong Ollama up front, as it does for Docker.

## Consequences
- Setup is two documented steps: install the prerequisites, then `just init`.
- A too-old uv, a missing Docker or Ollama, a stopped daemon, or the wrong Ollama version or judge weights is reported with what to do, instead of a later, confusing failure.
- just and the Docker daemon versions can differ between machines; neither affects the pipeline's outputs. The Ollama version cannot differ, since it does affect the judge's scores.
- If the registry stops serving the pinned judge weights, a fresh `init` stops on the digest check rather than accepting different weights.
- There is no automated test of a fresh machine. A small test checks that the recipes exist, that `required-version` is set, and that `init` stops on a missing Docker; the rest is the #13 checklist, run by hand.
