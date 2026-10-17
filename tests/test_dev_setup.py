"""The justfile is the setup entry point (ADRs 0022 and 0023). These run `just` itself, so they skip without it.

The other tests put a fake docker, ollama, curl and uv on PATH, so they need neither Docker, Ollama nor
the network.
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


def just(*args: str, env: dict[str, str] | None = None, justfile: Path = ROOT / "justfile") -> subprocess.CompletedProcess[str]:
    assert JUST is not None
    return subprocess.run(
        [JUST, "--justfile", str(justfile), *args],
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
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
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
# A container is three files: its image, its host port binding ("ip:port") and whether it is running.
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
      *PortBindings*) echo "$(cat "$state/running") $(cat "$state/container") $(cat "$state/binding")" ;;
      *State.Running*) cat "$state/running" ;;
      *) echo "[]" ;;
    esac
    exit 0 ;;
  run)
    while [ $# -gt 1 ]; do [ "$1" = -p ] && echo "${2%:*}" > "$state/binding"; shift; done
    echo "$1" > "$state/container"; echo true > "$state/running"; echo 1234abcd; exit 0 ;;
  rm) rm -f "$state/container" "$state/running" "$state/binding"; exit 0 ;;
  logs) echo "fake GROBID log"; exit 0 ;;
esac
exit 0
"""
# curl answers GROBID's health check and Ollama's /api/version and /api/tags. Ollama is up and at
# the pinned version unless FAKE_OLLAMA_DOWN or FAKE_OLLAMA_VERSION says otherwise.
FAKE_CURL = r"""#!/bin/bash
state="$FAKE_STATE"
echo "$*" >> "$state/curl"
case "$*" in
  *11434/api/version*)
    [ -n "${FAKE_OLLAMA_DOWN:-}" ] && exit 7
    echo "{\"version\":\"${FAKE_OLLAMA_VERSION:-0.40.5}\"}" ;;
  *11434/api/tags*)
    [ -n "${FAKE_OLLAMA_DOWN:-}" ] && exit 7
    printf '{"models":['
    [ -f "$state/models" ] && sed 's/^\([^ ]*\) \(.*\)$/{"name":"\1","digest":"\2","details":{"format":"gguf"}},/' "$state/models" | tr -d '\n' | sed 's/,$//'
    echo ']}' ;;
  *)
    if [ -f "$state/healthy" ] && [ -f "$state/container" ]; then echo true; else exit 7; fi ;;
esac
"""
# ollama only pulls: it installs the model at FAKE_OLLAMA_PULLED_DIGEST, or the pinned digest.
FAKE_OLLAMA = r"""#!/bin/bash
echo "$*" >> "$FAKE_STATE/ollama"
[ "$1" = pull ] && echo "$2 ${FAKE_OLLAMA_PULLED_DIGEST:-$PINNED_DIGEST}" >> "$FAKE_STATE/models"
exit 0
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
JUDGE_MODEL = "tev1:4b"
JUDGE_DIGEST = "4d24c6f6d61a48d9b72902f4805c5f1da53010736b834b0372377fb4bb7e53d3"


class FakeTools:
    """Puts a fake docker, ollama, curl and uv first on PATH and runs `just` with them."""

    def __init__(self, root: Path):
        self.state = root / "state"
        self.state.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, script in [("docker", FAKE_DOCKER), ("ollama", FAKE_OLLAMA), ("curl", FAKE_CURL), ("uv", FAKE_UV)]:
            (bin_dir / name).write_text(script)
            (bin_dir / name).chmod(0o755)
        real_uv = shutil.which("uv")
        assert real_uv is not None
        self.env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_STATE": str(self.state), "REAL_UV": real_uv,
                    "PINNED_DIGEST": JUDGE_DIGEST}

    def just(self, *args: str, justfile: Path = ROOT / "justfile") -> subprocess.CompletedProcess[str]:
        return just(*args, env=self.env, justfile=justfile)

    def calls(self, command: str) -> list[str]:
        path = self.state / "calls"
        rows = path.read_text().splitlines() if path.exists() else []
        return [row for row in rows if row.split(" ", 1)[0] == command]

    def ollama_calls(self) -> list[str]:
        path = self.state / "ollama"
        return path.read_text().splitlines() if path.exists() else []

    def has_judge_model(self, digest: str = JUDGE_DIGEST) -> None:
        (self.state / "models").write_text(f"{JUDGE_MODEL} {digest}\n")

    def has_image(self) -> None:
        (self.state / "images").write_text(REFERENCE + "\n")

    def has_running_container(self, image: str, binding: str) -> None:
        (self.state / "container").write_text(image + "\n")
        (self.state / "binding").write_text(binding + "\n")
        (self.state / "running").write_text("true\n")

    def becomes_healthy(self) -> None:
        (self.state / "healthy").touch()


@pytest.fixture
def fake_tools(tmp_path):
    if shutil.which("uv") is None:
        pytest.skip("uv is not installed")
    return FakeTools(tmp_path)


@needs_just
def test_init_pulls_the_pinned_grobid_image_by_digest(fake_tools):
    result = fake_tools.just("init")

    assert result.returncode == 0, result.stderr
    assert fake_tools.calls("pull") == [f"pull {REFERENCE}"]


@needs_just
def test_init_skips_the_pull_when_the_image_is_present(fake_tools):
    fake_tools.has_image()

    result = fake_tools.just("init")

    assert result.returncode == 0, result.stderr
    assert fake_tools.calls("pull") == []


@needs_just
def test_init_stops_with_a_clear_message_when_ollama_is_missing(fake_tools):
    bin_dir = fake_tools.state.parent / "bin"
    (bin_dir / "ollama").unlink()
    # Only the fakes and the system shell tools, so a real ollama is never found.
    fake_tools.env["PATH"] = f"{bin_dir}:/usr/bin:/bin"

    result = fake_tools.just("init")

    assert result.returncode != 0
    assert "Ollama is not installed" in result.stderr
    assert "0.40.5" in result.stderr


@needs_just
def test_init_stops_with_a_clear_message_when_ollama_is_not_answering(fake_tools):
    fake_tools.env["FAKE_OLLAMA_DOWN"] = "1"

    result = fake_tools.just("init")

    assert result.returncode != 0
    assert "Ollama is not answering at http://localhost:11434" in result.stderr


@needs_just
def test_init_stops_when_ollama_runs_another_version_than_the_judge_pin(fake_tools):
    fake_tools.env["FAKE_OLLAMA_VERSION"] = "0.41.0"

    result = fake_tools.just("init")

    assert result.returncode != 0
    assert "Ollama 0.41.0 is running, but the judge is pinned to 0.40.5" in result.stderr


@needs_just
def test_init_pulls_the_judge_model_when_ollama_lacks_it(fake_tools):
    result = fake_tools.just("init")

    assert result.returncode == 0, result.stderr
    assert fake_tools.ollama_calls() == [f"pull {JUDGE_MODEL}"]
    assert f"{JUDGE_MODEL}" in result.stdout


@needs_just
def test_init_skips_the_pull_when_the_judge_model_is_present(fake_tools):
    fake_tools.has_judge_model()

    result = fake_tools.just("init")

    assert result.returncode == 0, result.stderr
    assert fake_tools.ollama_calls() == []


@needs_just
def test_init_stops_when_the_judge_model_has_another_digest(fake_tools):
    fake_tools.has_judge_model("0" * 64)

    result = fake_tools.just("init")

    assert result.returncode != 0
    assert f"{JUDGE_MODEL} in Ollama has digest 000000000000" in result.stderr
    assert fake_tools.ollama_calls() == []


@needs_just
def test_init_stops_when_the_pulled_judge_model_has_another_digest(fake_tools):
    fake_tools.env["FAKE_OLLAMA_PULLED_DIGEST"] = "1" * 64

    result = fake_tools.just("init")

    assert result.returncode != 0
    assert f"{JUDGE_MODEL} in Ollama has digest 111111111111" in result.stderr


@needs_just
def test_grobid_up_runs_the_pinned_image_and_returns_once_it_is_alive(fake_tools):
    fake_tools.becomes_healthy()

    result = fake_tools.just("grobid-up")

    assert result.returncode == 0, result.stderr
    [run] = fake_tools.calls("run")
    assert run.endswith(REFERENCE)
    assert "-p 127.0.0.1:8070:8070" in run
    assert "http://localhost:8070/api/isalive" in (fake_tools.state / "curl").read_text()
    assert "http://localhost:8070" in result.stdout


@needs_just
def test_grobid_up_times_out_with_a_clear_message_when_grobid_never_answers(fake_tools):
    result = fake_tools.just("grobid-up", "1")

    assert result.returncode != 0
    assert "GROBID did not answer http://localhost:8070/api/isalive within 1 s" in result.stderr
    assert "docker logs" in result.stderr


@needs_just
def test_grobid_up_twice_starts_one_container(fake_tools):
    fake_tools.becomes_healthy()

    first, second = fake_tools.just("grobid-up"), fake_tools.just("grobid-up")

    assert (first.returncode, second.returncode) == (0, 0), second.stderr
    assert len(fake_tools.calls("run")) == 1
    assert "already running" in second.stdout


@needs_just
def test_grobid_down_removes_the_container_and_is_harmless_twice(fake_tools):
    fake_tools.becomes_healthy()
    fake_tools.just("grobid-up")

    first, second = fake_tools.just("grobid-down"), fake_tools.just("grobid-down")

    assert (first.returncode, second.returncode) == (0, 0), second.stderr
    assert "GROBID stopped" in first.stdout
    assert "not running" in second.stdout
    assert not (fake_tools.state / "container").exists()


@needs_just
def test_grobid_up_stops_with_a_clear_message_when_the_daemon_is_down(fake_tools):
    fake_tools.env["FAKE_DOCKER_DOWN"] = "1"

    result = fake_tools.just("grobid-up")

    assert result.returncode != 0
    assert "the Docker daemon is not answering" in result.stderr
    assert fake_tools.calls("run") == []


@needs_just
def test_grobid_up_replaces_a_running_container_published_on_another_port(fake_tools):
    fake_tools.has_running_container(REFERENCE, "127.0.0.1:9999")
    fake_tools.becomes_healthy()

    result = fake_tools.just("grobid-up")

    assert result.returncode == 0, result.stderr
    [run] = fake_tools.calls("run")
    assert "-p 127.0.0.1:8070:8070" in run


@needs_just
def test_grobid_up_replaces_a_running_container_from_another_image(fake_tools):
    fake_tools.has_running_container("grobid/grobid@sha256:" + "0" * 64, "127.0.0.1:8070")
    fake_tools.becomes_healthy()

    result = fake_tools.just("grobid-up")

    assert result.returncode == 0, result.stderr
    [run] = fake_tools.calls("run")
    assert run.endswith(REFERENCE)


@needs_just
def test_grobid_recipes_only_ever_inspect_containers(fake_tools):
    fake_tools.becomes_healthy()

    fake_tools.just("grobid-up")
    fake_tools.just("grobid-down")

    inspects = fake_tools.calls("inspect")
    assert inspects
    assert all("--type container" in call for call in inspects), inspects


@needs_just
def test_grobid_up_rejects_a_timeout_that_is_not_a_number_without_running_it(fake_tools, tmp_path):
    marker = tmp_path / "ran"

    result = fake_tools.just("grobid-up", f"1$(touch {marker})")

    assert result.returncode != 0
    assert "the timeout must be a whole number of seconds" in result.stderr
    assert not marker.exists()
    assert fake_tools.calls("run") == []


def justfile_with_required_uv(tmp_path: Path, required_version: str) -> Path:
    """A copy of the justfile next to a pyproject.toml with another [tool.uv] required-version."""
    (tmp_path / "pyproject.toml").write_text(f'[tool.uv]\nrequired-version = "{required_version}"\n')
    shutil.copy(ROOT / "justfile", tmp_path / "justfile")
    return tmp_path / "justfile"


@needs_just
@pytest.mark.parametrize("required_version", [">=0.10.8", ">=0.10.8,<100", "<100, >= 0.10.8"])
def test_init_reads_the_lower_bound_among_other_uv_specifiers(fake_tools, tmp_path, required_version):
    # The fake uv is 99.0.0; with the daemon down, init stops right after the uv check.
    fake_tools.env["FAKE_DOCKER_DOWN"] = "1"
    project = tmp_path / "project"
    project.mkdir()

    result = fake_tools.just("init", justfile=justfile_with_required_uv(project, required_version))

    assert "the Docker daemon is not answering" in result.stderr


@needs_just
def test_init_names_the_required_version_it_cannot_check(fake_tools, tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    result = fake_tools.just("init", justfile=justfile_with_required_uv(project, "==0.10.8"))

    assert result.returncode != 0
    assert "required-version '==0.10.8' has no >= lower bound" in result.stderr
