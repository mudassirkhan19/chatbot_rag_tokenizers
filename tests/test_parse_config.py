from pathlib import Path

import pytest

from chatbot_rag_tokenizers.parsing.config import ConfigError, load_grobid_config

REPO_CONFIG = Path(__file__).parents[1] / "config" / "parse.toml"


def test_repo_pins_grobid_by_digest():
    grobid = load_grobid_config(REPO_CONFIG)
    assert grobid.reference == (
        "grobid/grobid@sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd"
    )
    assert grobid.tag == "0.9.1-crf"
    assert grobid.url == "http://localhost:8070"


@pytest.mark.parametrize("digest", ["", "sha256:abc", "0.9.1-crf", "sha512:" + "a" * 64])
def test_a_digest_that_is_not_a_sha256_is_rejected(tmp_path, digest):
    path = tmp_path / "parse.toml"
    path.write_text(f'[grobid]\nimage = "grobid/grobid"\ntag = "x"\ndigest = "{digest}"\nport = 8070\n')
    with pytest.raises(ConfigError, match="digest"):
        load_grobid_config(path)
