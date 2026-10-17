# Setup and everyday commands. Run `just` to list them. See ADR 0022 and, for GROBID, ADR 0023.

set positional-arguments := true

# The GROBID container's name; its image, port and URL come from config/parse.toml.
grobid_container := "chatbot-rag-tokenizers-grobid"

# The start of every bash recipe, after it sets $recipe: strict mode and the shared helpers.
# load_grobid and load_judge use `uv run --no-sync` so reading a pin never syncs or creates .venv:
# init has just synced every group, and the GROBID recipes need init to have run.
_bash_prelude := '''
    set -euo pipefail
    fail() { printf 'just %s: %s\n' "$recipe" "$1" >&2; exit 1; }
    require_docker() {
        command -v docker >/dev/null 2>&1 || fail "Docker is not installed. Install a Docker daemon such as Docker Desktop, OrbStack or Colima (see Prerequisites in the README)."
        docker info >/dev/null 2>&1 || fail "the Docker daemon is not answering. Start Docker Desktop, OrbStack or Colima, then rerun just $recipe."
    }
    load_grobid() {
        local settings
        settings=$(uv run --no-sync python -m chatbot_rag_tokenizers.parsing.grobid_env) \
            || fail "could not read the GROBID pin in config/parse.toml. Run just init first."
        eval "$settings"
    }
    load_judge() {
        local settings
        settings=$(uv run --no-sync python -m chatbot_rag_tokenizers.collection.judge_env) \
            || fail "could not read the judge pin in config/scope.toml"
        eval "$settings"
    }
    # The digest Ollama has for model $1, or nothing (also when Ollama doesn't answer). /api/tags lists each model as one object whose
    # name and digest come before its nested "details", so splitting on "{" keeps them together.
    ollama_digest() {
        curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" | tr '{' '\n' \
            | grep -F "\"name\":\"$1\"" | sed -n 's/.*"digest":"\([0-9a-f]*\)".*/\1/p' | head -n1 || true
    }
'''

# List the recipes
default:
    @just --list --unsorted

# Check uv, Docker and Ollama, install every dependency group and pull the pinned images and judge model (safe to rerun)
init:
    #!/usr/bin/env bash
    recipe=init
    {{_bash_prelude}}

    command -v uv >/dev/null 2>&1 || fail "uv is not installed. Install it with: brew install uv"
    # Only the >= lower bound is checked here; uv itself enforces the whole specifier.
    spec=$(sed -n 's/^required-version *= *"\(.*\)".*/\1/p' pyproject.toml)
    [ -n "$spec" ] || fail "pyproject.toml sets no [tool.uv] required-version"
    required=$(printf '%s\n' "$spec" | sed -n 's/.*>= *\([0-9][0-9.]*\).*/\1/p')
    [ -n "$required" ] || fail "pyproject.toml's [tool.uv] required-version '$spec' has no >= lower bound to check"
    uv_version=$(uv --version | awk '{print $2}')
    if [ "$(printf '%s\n%s\n' "$required" "$uv_version" | sort -V | head -n1)" != "$required" ]; then
        fail "uv $uv_version is older than the required $required. Upgrade it with: brew upgrade uv"
    fi

    require_docker

    uv sync --all-groups --locked

    load_grobid
    if docker image inspect "$GROBID_REFERENCE" >/dev/null 2>&1; then
        echo "GROBID $GROBID_TAG is already pulled."
    else
        echo "Pulling GROBID $GROBID_TAG ($GROBID_REFERENCE)"
        docker pull "$GROBID_REFERENCE" || fail "could not pull $GROBID_REFERENCE. Check the network, then rerun just init."
    fi

    # The judge's runtime and weights are both pinned (ADR 0021): a different Ollama version or
    # model digest changes the scores, so init stops rather than fixing either behind your back.
    load_judge
    judge_summary="the judge does not run on Ollama"
    if [ -n "$OLLAMA_MODEL" ]; then
        install="Install Ollama $OLLAMA_VERSION from https://github.com/ollama/ollama/releases/tag/v$OLLAMA_VERSION"
        command -v ollama >/dev/null 2>&1 || fail "Ollama is not installed. $install (see Prerequisites in the README)."
        running=$(curl -fsS --max-time 5 "$OLLAMA_URL/api/version" 2>/dev/null | sed -n 's/.*"version":"\([^"]*\)".*/\1/p') || true
        [ -n "$running" ] || fail "Ollama is not answering at $OLLAMA_URL. Start the Ollama app or run: ollama serve"
        [ "$running" = "$OLLAMA_VERSION" ] || fail "Ollama $running is running, but the judge is pinned to $OLLAMA_VERSION. $install"
        installed=$(ollama_digest "$OLLAMA_MODEL")
        if [ -z "$installed" ]; then
            echo "Pulling the judge model $OLLAMA_MODEL"
            ollama pull "$OLLAMA_MODEL" || fail "could not pull $OLLAMA_MODEL. Check the network, then rerun just init."
            installed=$(ollama_digest "$OLLAMA_MODEL")
        else
            echo "The judge model $OLLAMA_MODEL is already pulled."
        fi
        [ "$installed" = "$OLLAMA_DIGEST" ] \
            || fail "$OLLAMA_MODEL in Ollama has digest ${installed:0:12}, not the pinned ${OLLAMA_DIGEST:0:12} in config/scope.toml. Remove it with: ollama rm $OLLAMA_MODEL, then rerun just init (the registry may no longer serve the pinned weights)."
        judge_summary="Ollama $running with the judge model $OLLAMA_MODEL, pinned by digest"
    fi

    echo
    echo "Ready:"
    echo "  uv $uv_version (required $spec)"
    echo "  $(uv run --no-sync python --version) with every dependency group in .venv"
    echo "  Docker daemon $(docker info --format '{{{{.ServerVersion}}')"
    echo "  GROBID $GROBID_TAG, pinned by digest (start it with: just grobid-up)"
    echo "  $judge_summary"

# Start the pinned GROBID service on localhost and wait until it answers (safe to rerun)
grobid-up timeout="180":
    #!/usr/bin/env bash
    recipe=grobid-up
    {{_bash_prelude}}
    timeout=$1
    [[ "$timeout" =~ ^[0-9]+$ ]] || fail "the timeout must be a whole number of seconds, not '$timeout'"
    require_docker
    load_grobid
    name={{grobid_container}}
    # Published on localhost only, so GROBID is not reachable from the network.
    binding="127.0.0.1:$GROBID_PORT"

    # "running image ip:port" of the existing container, or empty if there is none.
    current=$(docker inspect --type container --format \
        '{{{{.State.Running}} {{{{.Config.Image}} {{{{range (index .HostConfig.PortBindings "8070/tcp")}}{{{{.HostIp}}:{{{{.HostPort}}{{{{end}}' \
        "$name" 2>/dev/null || true)
    if [ "$current" = "true $GROBID_REFERENCE $binding" ]; then
        echo "GROBID $GROBID_TAG is already running."
    else
        # A stopped container, or one from an older pin or port, is replaced.
        docker rm -f "$name" >/dev/null 2>&1 || true
        echo "Starting GROBID $GROBID_TAG ($GROBID_REFERENCE) on $binding"
        docker run -d --name "$name" --init --ulimit core=0 -p "$binding:8070" "$GROBID_REFERENCE" >/dev/null \
            || fail "docker could not start GROBID. Is port $GROBID_PORT already in use? Free it, or change port in config/parse.toml."
    fi

    deadline=$((SECONDS + timeout))
    until [ "$(curl -fsS --max-time 2 "$GROBID_URL/api/isalive" 2>/dev/null)" = true ]; do
        if [ "$(docker inspect --type container --format '{{{{.State.Running}}' "$name" 2>/dev/null || true)" != true ]; then
            fail "the GROBID container stopped while starting. See: docker logs $name"
        fi
        if [ "$SECONDS" -ge "$deadline" ]; then
            fail "GROBID did not answer $GROBID_URL/api/isalive within $timeout s. It may still be loading: rerun just grobid-up, or see: docker logs $name"
        fi
        sleep 1
    done
    echo "GROBID $GROBID_TAG is up at $GROBID_URL"

# Stop the GROBID service (safe to rerun)
grobid-down:
    #!/usr/bin/env bash
    recipe=grobid-down
    {{_bash_prelude}}
    require_docker
    # `docker rm` only removes containers; inspect needs --type so it never matches an image or volume.
    if docker inspect --type container {{grobid_container}} >/dev/null 2>&1; then
        docker rm -f {{grobid_container}} >/dev/null
        echo "GROBID stopped."
    else
        echo "GROBID is not running."
    fi

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
