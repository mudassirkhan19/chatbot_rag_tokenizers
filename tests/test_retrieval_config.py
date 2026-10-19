"""The retrieval config file (ADRs 0039, 0042, 0050 and 0051): BM25's table and the named dense tables."""

from pathlib import Path

import pytest

from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config

RETRIEVAL_CONFIG = Path(__file__).parents[1] / "config" / "retrieval.toml"


def test_the_repo_config_names_bge_small_with_the_key_of_the_index_built_before_dense_tables_were_named():
    config = load_retrieval_config(RETRIEVAL_CONFIG)

    dense = config.dense[0]
    assert dense.name == "dense.bge-small"
    assert (dense.pooling, dense.max_tokens) == ("cls", 512)
    # The key of the full-corpus index built as `dense` (data/eval/eval-report.md), so it isn't embedded again.
    assert dense.key == "dense-784e5a0da1b5"
    assert list(config.retrievers) == ["bm25", "dense.bge-small", "dense.bge-base", "dense.openscholar"]


def test_the_repo_config_pins_the_size_control_and_the_scientific_candidate():
    tables = {dense.name: dense for dense in load_retrieval_config(RETRIEVAL_CONFIG).dense}
    bge_base, openscholar = tables["dense.bge-base"], tables["dense.openscholar"]

    # The pins are the repos' commits on 2026-10-19 and the sha256 Hugging Face lists for each weights file.
    assert (bge_base.model, bge_base.revision) == ("BAAI/bge-base-en-v1.5", "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a")
    assert bge_base.model_sha256 == "c7c1988aae201f80cf91a5dbbd5866409503b89dcaba877ca6dba7dd0a5167d7"  # model.safetensors
    assert (bge_base.pooling, bge_base.max_tokens) == ("cls", 512)
    assert bge_base.query_instruction == tables["dense.bge-small"].query_instruction
    assert (openscholar.model, openscholar.revision) == ("OpenScholar/OpenScholar_Retriever", "ef4f3120d33b3ca57e12fce2b369f5982a7bb929")
    assert openscholar.model_sha256 == "fb5226976e362e070ad5b3f6c5bd38ed03a770b7d349b9334e4db8d61cc5f8fa"  # pytorch_model.bin
    assert (openscholar.pooling, openscholar.max_tokens, openscholar.query_instruction) == ("mean", 512, "")


def with_bge_small(tmp_path: Path, old: str, new: str) -> Path:
    """The repo's retrieval config with one line of [dense.bge-small] replaced (or removed, when new is "")."""
    config = RETRIEVAL_CONFIG.read_text()
    start = config.index("[dense.bge-small]")
    end = config.index("\n[", start)
    table = config[start:end]
    assert table.count(old) == 1
    path = tmp_path / "retrieval.toml"
    path.write_text(config[:start] + table.replace(old, new) + config[end:])
    return path


@pytest.mark.parametrize(
    "old, new, message",
    [
        ('pooling = "cls"', 'pooling = "max"', r"\[dense.bge-small\] pooling 'max' is not one of cls, mean"),
        ('revision = "5c38ec7c', 'revision = "main', r"\[dense.bge-small\] revision 'main.*' is not a 40-hex commit"),
        ('model_sha256 = "3c9f', 'model_sha256 = "3c9', r"\[dense.bge-small\] model_sha256 '3c9.*' is not 64 hex digits"),
        ("max_tokens = 512\n", "", r"\[dense.bge-small\] in .* has no max_tokens"),
        ("max_tokens = 512", 'max_tokens = "512"', r"\[dense.bge-small\] max_tokens '512' is not a int"),
        ("max_tokens = 512", "max_tokens = 0", r"\[dense.bge-small\] max_tokens 0 must be at least 1"),
        ("[dense.bge-small]", "[dense.BGE_small]", r"\[dense.BGE_small\] in .*: a dense table's name is lower-case letters, digits and dashes"),
    ],
    ids=["pooling", "revision", "weights-hash", "missing-field", "mistyped-field", "no-tokens", "table-name"],
)
def test_a_bad_dense_table_stops_with_a_message_naming_the_table(tmp_path, old, new, message):
    with pytest.raises(ConfigError, match=message):
        load_retrieval_config(with_bge_small(tmp_path, old, new))


def test_a_dense_table_written_the_old_way_is_named_and_told_how_to_change(tmp_path):
    path = with_bge_small(tmp_path, "[dense.bge-small]", "[dense]")

    with pytest.raises(ConfigError, match=r"\[dense\] model .* is not a table; give each dense model its own \[dense.<name>\] table"):
        load_retrieval_config(path)
