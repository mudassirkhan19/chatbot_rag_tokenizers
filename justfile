# Setup and everyday commands. Run `just` to list them. See ADR 0021.

set positional-arguments := true

# List the recipes
default:
    @just --list --unsorted

# Check uv and Docker, then install every dependency group (safe to rerun)
init:
    #!/usr/bin/env bash
    set -euo pipefail
    fail() { printf 'just init: %s\n' "$1" >&2; exit 1; }

    command -v uv >/dev/null 2>&1 || fail "uv is not installed. Install it with: brew install uv"
    required=$(sed -n 's/^required-version *= *">=\([0-9.]*\)".*/\1/p' pyproject.toml)
    [ -n "$required" ] || fail "pyproject.toml sets no [tool.uv] required-version"
    uv_version=$(uv --version | awk '{print $2}')
    if [ "$(printf '%s\n%s\n' "$required" "$uv_version" | sort -V | head -n1)" != "$required" ]; then
        fail "uv $uv_version is older than the required $required. Upgrade it with: brew upgrade uv"
    fi

    command -v docker >/dev/null 2>&1 || fail "Docker is not installed. Install a Docker daemon such as Docker Desktop, OrbStack or Colima (see Prerequisites in the README)."
    docker info >/dev/null 2>&1 || fail "the Docker daemon is not answering. Start Docker Desktop, OrbStack or Colima, then rerun just init."

    uv sync --all-groups --locked

    # The pinned GROBID image is pulled here (#16).

    echo
    echo "Ready:"
    echo "  uv $uv_version (required >=$required)"
    echo "  $(uv run --no-sync python --version) with every dependency group in .venv"
    echo "  Docker daemon $(docker info --format '{{{{.ServerVersion}}')"

# Run the test suite; extra arguments go to pytest
test *args:
    uv run pytest "$@"

# Type-check src and tests with mypy
typecheck:
    uv run mypy src tests

# Lint src and tests with ruff
lint:
    uv run ruff check src tests

# Collect the corpus and write the manifest; extra arguments go to the CLI
collect *args:
    uv run chatbot-rag-tokenizers collect "$@"

# Download the pinned PDFs of included Editions; extra arguments go to the CLI
fetch *args:
    uv run chatbot-rag-tokenizers fetch "$@"
