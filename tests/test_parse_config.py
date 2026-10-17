import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.parsing.config import load_grobid_config

ROOT = Path(__file__).parents[1]
REPO_CONFIG = ROOT / "config" / "parse.toml"
DIGEST = "sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd"
FIELDS = {"image": '"grobid/grobid"', "tag": '"x"', "digest": f'"{DIGEST}"', "port": "8070"}


def write_config(tmp_path: Path, **overrides: str | None) -> Path:
    fields = {**FIELDS, **overrides}
    lines = [f"{key} = {value}" for key, value in fields.items() if value is not None]
    path = tmp_path / "parse.toml"
    path.write_text("[grobid]\n" + "\n".join(lines) + "\n")
    return path


def test_repo_pins_grobid_by_digest():
    grobid = load_grobid_config(REPO_CONFIG)
    assert grobid.reference == f"grobid/grobid@{DIGEST}"
    assert grobid.tag == "0.9.1-crf"
    assert grobid.url == "http://localhost:8070"


@pytest.mark.parametrize("digest", ["", "sha256:abc", "0.9.1-crf", "sha512:" + "a" * 64])
def test_a_digest_that_is_not_a_sha256_is_rejected(tmp_path, digest):
    with pytest.raises(ConfigError, match="digest"):
        load_grobid_config(write_config(tmp_path, digest=f'"{digest}"'))


@pytest.mark.parametrize("port", ['"8070"', "8070.0", "true", "0", "65536"])
def test_a_port_that_is_not_a_tcp_port_number_is_rejected(tmp_path, port):
    with pytest.raises(ConfigError, match="port"):
        load_grobid_config(write_config(tmp_path, port=port))


@pytest.mark.parametrize("field", ["image", "tag", "digest"])
def test_a_text_field_that_is_not_a_string_is_rejected(tmp_path, field):
    with pytest.raises(ConfigError, match=field):
        load_grobid_config(write_config(tmp_path, **{field: "1"}))


def test_a_missing_field_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="port"):
        load_grobid_config(write_config(tmp_path, port=None))


def test_an_unknown_field_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="hostname"):
        load_grobid_config(write_config(tmp_path, hostname='"localhost"'))


def test_the_shell_printer_gives_the_justfile_every_grobid_setting():
    printed = subprocess.run(
        [sys.executable, "-m", "chatbot_rag_tokenizers.parsing.grobid_env"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    settings = dict(shlex.split(line)[0].split("=", 1) for line in printed.splitlines())
    assert settings == {
        "GROBID_REFERENCE": f"grobid/grobid@{DIGEST}",
        "GROBID_TAG": "0.9.1-crf",
        "GROBID_PORT": "8070",
        "GROBID_URL": "http://localhost:8070",
    }
