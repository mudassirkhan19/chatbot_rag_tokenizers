"""The retrieval config file (ADRs 0039, 0042 and 0050): BM25's table and the named dense tables."""

from pathlib import Path

import pytest

from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config

REPO_CONFIG = Path(__file__).parents[1] / "config" / "retrieval.toml"


def test_the_repo_config_names_bge_small_with_the_key_of_the_index_built_before_dense_tables_were_named():
    config = load_retrieval_config(REPO_CONFIG)

    [dense] = config.dense
    assert dense.name == "dense.bge-small"
    assert (dense.pooling, dense.max_tokens) == ("cls", 512)
    # The key of the full-corpus index built as `dense` (data/eval/eval-report.md), so it isn't embedded again.
    assert dense.key == "dense-784e5a0da1b5"
    assert list(config.retrievers) == ["bm25", "dense.bge-small"]


def with_bge_small(tmp_path: Path, old: str, new: str) -> Path:
    """The repo's retrieval config with one line of [dense.bge-small] replaced (or removed, when new is "")."""
    config = REPO_CONFIG.read_text()
    assert config.count(old) == 1
    path = tmp_path / "retrieval.toml"
    path.write_text(config.replace(old, new))
    return path


@pytest.mark.parametrize(
    "old, new, message",
    [
        ('pooling = "cls"', 'pooling = "max"', r"\[dense.bge-small\] pooling 'max' is not one of cls, mean"),
        ('revision = "5c38ec7c', 'revision = "main', r"\[dense.bge-small\] revision 'main.*' is not a 40-hex commit"),
        ('model_sha256 = "3c9f', 'model_sha256 = "3c9', r"\[dense.bge-small\] model_sha256 '3c9.*' is not 64 hex digits"),
        ("max_tokens = 512\n", "", r"\[dense.bge-small\] in .* has no max_tokens"),
        ("max_tokens = 512", 'max_tokens = "512"', r"\[dense.bge-small\] max_tokens '512' is not a int"),
    ],
    ids=["pooling", "revision", "weights-hash", "missing-field", "mistyped-field"],
)
def test_a_bad_dense_table_stops_with_a_message_naming_the_table(tmp_path, old, new, message):
    with pytest.raises(ConfigError, match=message):
        load_retrieval_config(with_bge_small(tmp_path, old, new))


def test_a_dense_table_written_the_old_way_is_named_and_told_how_to_change(tmp_path):
    path = with_bge_small(tmp_path, "[dense.bge-small]", "[dense]")

    with pytest.raises(ConfigError, match=r"\[dense\] model .* is not a table; give each dense model its own \[dense.<name>\] table"):
        load_retrieval_config(path)
