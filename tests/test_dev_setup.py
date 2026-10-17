"""The justfile is the setup entry point (ADR 0021). These run `just` itself, so they skip without it."""

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
    for recipe in ["init", "test", "typecheck", "lint", "collect", "fetch"]:
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
