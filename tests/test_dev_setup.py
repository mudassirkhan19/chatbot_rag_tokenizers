"""The justfile is the setup entry point (ADRs 0021 and 0022). These run `just` itself, so they skip without it.

The GROBID tests put a fake docker, curl and uv on PATH, so they need neither Docker nor the network.
"""

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
JUST = shutil.which("just")
needs_just = pytest.mark.skipif(JUST is None, reason="just is not installed")


def just(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    assert JUST is not None
    return subprocess.run(
        [JUST, "--justfile", str(ROOT / "justfile"), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@needs_just
def test_just_lists_every_recipe_with_a_description():
    listing = just("--list").stdout
    for recipe in ["init", "grobid-up", "grobid-down", "test", "typecheck", "lint", "collect", "fetch"]:
        line = next((row for row in listing.splitlines() if row.strip().startswith(recipe)), None)
        assert line is not None, f"`just --list` has no {recipe!r} recipe"
        assert "#" in line, f"{recipe!r} has no one-line description"


def test_project_sets_a_minimum_uv_version():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["tool"]["uv"]["required-version"].startswith(">=")


@needs_just
def test_init_stops_with_a_clear_message_when_docker_is_missing(tmp_path):
    # A PATH holding only uv, just and the system shell tools, so docker is never found.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ["uv", "just"]:
        found = shutil.which(tool)
        assert found is not None
        (bin_dir / tool).symlink_to(found)
    env = {**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin"}

    result = just("init", env=env)

    assert result.returncode != 0
    assert "Docker is not installed" in result.stderr


# A fake docker CLI and curl, keeping their state in files, so the GROBID recipes run without Docker.
FAKE_DOCKER = r"""#!/bin/bash
state="$FAKE_STATE"
echo "$*" >> "$state/calls"
case "$1" in
  info) [ -n "${FAKE_DOCKER_DOWN:-}" ] && exit 1; [ "${2:-}" = "--format" ] && echo 99.0.0; exit 0 ;;
  image) grep -qxF "$3" "$state/images" 2>/dev/null; exit $? ;;
  pull) echo "$2" >> "$state/images"; echo "pulled $2"; exit 0 ;;
  inspect)
    [ -f "$state/container" ] || { echo "Error: No such object: ${@: -1}" >&2; exit 1; }
    case "$*" in
      *State.Running*) cat "$state/running" ;;
      *Config.Image*) cat "$state/container" ;;
      *) echo "[]" ;;
    esac
    exit 0 ;;
  run) echo "${@: -1}" > "$state/container"; echo true > "$state/running"; echo 1234abcd; exit 0 ;;
  rm) rm -f "$state/container" "$state/running"; exit 0 ;;
  logs) echo "fake GROBID log"; exit 0 ;;
esac
exit 0
"""
FAKE_CURL = r"""#!/bin/bash
echo "$*" >> "$FAKE_STATE/curl"
if [ -f "$FAKE_STATE/healthy" ] && [ -f "$FAKE_STATE/container" ]; then echo true; else exit 7; fi
"""
# uv answers --version and sync itself, so no test changes .venv, and hands run to the real uv.
FAKE_UV = r"""#!/bin/bash
case "$1" in
  --version) echo "uv 99.0.0" ;;
  sync) echo "fake uv sync $*" ;;
  *) exec "$REAL_UV" "$@" ;;
esac
"""
REFERENCE = "grobid/grobid@sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd"


class FakeDocker:
    def __init__(self, root: Path):
        self.state = root / "state"
        self.state.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, script in [("docker", FAKE_DOCKER), ("curl", FAKE_CURL), ("uv", FAKE_UV)]:
            (bin_dir / name).write_text(script)
            (bin_dir / name).chmod(0o755)
        real_uv = shutil.which("uv")
        assert real_uv is not None
        self.env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_STATE": str(self.state), "REAL_UV": real_uv}

    def just(self, *args: str) -> subprocess.CompletedProcess[str]:
        return just(*args, env=self.env)

    def calls(self, command: str) -> list[str]:
        path = self.state / "calls"
        rows = path.read_text().splitlines() if path.exists() else []
        return [row for row in rows if row.split(" ", 1)[0] == command]

    def has_image(self) -> None:
        (self.state / "images").write_text(REFERENCE + "\n")

    def becomes_healthy(self) -> None:
        (self.state / "healthy").touch()


@pytest.fixture
def docker(tmp_path):
    return FakeDocker(tmp_path)


@needs_just
def test_init_pulls_the_pinned_grobid_image_by_digest(docker):
    result = docker.just("init")

    assert result.returncode == 0, result.stderr
    assert docker.calls("pull") == [f"pull {REFERENCE}"]


@needs_just
def test_init_skips_the_pull_when_the_image_is_present(docker):
    docker.has_image()

    result = docker.just("init")

    assert result.returncode == 0, result.stderr
    assert docker.calls("pull") == []


@needs_just
def test_grobid_up_runs_the_pinned_image_and_returns_once_it_is_alive(docker):
    docker.becomes_healthy()

    result = docker.just("grobid-up")

    assert result.returncode == 0, result.stderr
    [run] = docker.calls("run")
    assert run.endswith(REFERENCE)
    assert "-p 8070:8070" in run
    assert "http://localhost:8070/api/isalive" in (docker.state / "curl").read_text()
    assert "http://localhost:8070" in result.stdout


@needs_just
def test_grobid_up_times_out_with_a_clear_message_when_grobid_never_answers(docker):
    result = docker.just("grobid-up", "1")

    assert result.returncode != 0
    assert "GROBID did not answer http://localhost:8070/api/isalive within 1 s" in result.stderr
    assert "docker logs" in result.stderr


@needs_just
def test_grobid_up_twice_starts_one_container(docker):
    docker.becomes_healthy()

    first, second = docker.just("grobid-up"), docker.just("grobid-up")

    assert (first.returncode, second.returncode) == (0, 0), second.stderr
    assert len(docker.calls("run")) == 1
    assert "already running" in second.stdout


@needs_just
def test_grobid_down_removes_the_container_and_is_harmless_twice(docker):
    docker.becomes_healthy()
    docker.just("grobid-up")

    first, second = docker.just("grobid-down"), docker.just("grobid-down")

    assert (first.returncode, second.returncode) == (0, 0), second.stderr
    assert "GROBID stopped" in first.stdout
    assert "not running" in second.stdout
    assert not (docker.state / "container").exists()


@needs_just
def test_grobid_up_stops_with_a_clear_message_when_the_daemon_is_down(docker):
    docker.env["FAKE_DOCKER_DOWN"] = "1"

    result = docker.just("grobid-up")

    assert result.returncode != 0
    assert "the Docker daemon is not answering" in result.stderr
    assert docker.calls("run") == []
