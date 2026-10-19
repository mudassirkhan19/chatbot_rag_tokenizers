"""The retrieval config file (ADRs 0039, 0042, 0050, 0052, 0053, 0054 and 0055): BM25's table, the named dense tables, the
hybrids, the Collapsed ranking's pool and the chat table."""

import re
from pathlib import Path

import pytest

from chatbot_rag_tokenizers.chat.config import AnswerModelConfig, load_chat_config
from chatbot_rag_tokenizers.config import ConfigError
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config

RETRIEVAL_CONFIG = Path(__file__).parents[1] / "config" / "retrieval.toml"


def test_the_repo_config_names_bge_small_with_the_key_of_the_index_built_before_dense_tables_were_named():
    config = load_retrieval_config(RETRIEVAL_CONFIG)

    [dense] = [table for table in config.dense if table.name == "dense.bge-small"]
    assert (dense.pooling, dense.max_tokens) == ("cls", 512)
    # The key of the full-corpus index built as `dense` (data/eval/eval-report.md), so it isn't embedded again.
    assert dense.key == "dense-784e5a0da1b5"
    assert list(config.retrievers)[:4] == ["bm25", "dense.bge-small", "dense.bge-base", "dense.openscholar"]


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


def test_the_collapse_pool_must_be_at_least_one_chunk(tmp_path):
    config = RETRIEVAL_CONFIG.read_text()
    assert load_retrieval_config(RETRIEVAL_CONFIG).collapse_pool == 50
    path = tmp_path / "retrieval.toml"
    path.write_text(config.replace("pool = 50", "pool = 0"))

    with pytest.raises(ConfigError, match=r"\[collapse\] pool 0 must be at least 1"):
        load_retrieval_config(path)


def test_a_dense_table_written_the_old_way_is_named_and_told_how_to_change(tmp_path):
    path = with_bge_small(tmp_path, "[dense.bge-small]", "[dense]")

    with pytest.raises(ConfigError, match=r"\[dense\] model .* is not a table; give each dense model its own \[dense.<name>\] table"):
        load_retrieval_config(path)


def test_the_repo_config_fuses_bm25_with_each_dense_table():
    config = load_retrieval_config(RETRIEVAL_CONFIG)

    hybrids = {hybrid.name: hybrid for hybrid in config.hybrid}
    assert list(hybrids) == ["hybrid.bm25+bge-small", "hybrid.bm25+bge-base", "hybrid.bm25+openscholar"]
    bge_small = hybrids["hybrid.bm25+bge-small"]
    assert [member.name for member in bge_small.members] == ["bm25", "dense.bge-small"]
    assert (bge_small.k, bge_small.pool) == (60, 100)
    assert list(config.retrievers)[-3:] == list(hybrids)


def with_hybrid(tmp_path: Path, table: str) -> Path:
    """The repo's retrieval config with its hybrid tables replaced by this one."""
    config = re.sub(r"\n\[hybrid\.[^\n]*\]\n(?:[a-z][^\n]*\n)*", "\n", RETRIEVAL_CONFIG.read_text())
    assert "[hybrid." not in config
    path = tmp_path / "retrieval.toml"
    path.write_text(config + "\n" + table)
    return path


def test_the_chatbot_asks_the_dense_baseline_for_five_chunks_and_answers_with_the_pinned_gemma():
    chat = load_chat_config(RETRIEVAL_CONFIG)

    assert (chat.retriever.name, chat.k) == ("dense.bge-small", 5)
    assert chat.model == AnswerModelConfig(
        "gemma4:e2b-mlx", "e98b54fe1913178321e1d9cd007d12a465de77a8f8eae37af69d2501ca03c6b5@0.40.5", think=False, temperature=0.0
    )
    # The prompt asks for the fixed Abstention sentence word for word.
    assert chat.abstention in chat.system_prompt


def with_chat_line(tmp_path: Path, old: str, new: str) -> Path:
    config = RETRIEVAL_CONFIG.read_text()
    assert config.count(old) == 1
    path = tmp_path / "retrieval.toml"
    path.write_text(config.replace(old, new))
    return path


@pytest.mark.parametrize(
    "members, k, pool, message",
    [
        ('["bm25", "dense.missing"]', 60, 100, r"\[hybrid.test\] member 'dense.missing' is not a retriever in .*; it configures bm25, dense.bge-small"),
        ('["bm25", "hybrid.other"]', 60, 100, r"\[hybrid.test\] member 'hybrid.other' is not bm25 or a dense table"),
        ('["dense.bge-small", "dense.bge-base"]', 60, 100, r"\[hybrid.test\] fuses bm25 with one dense table, not dense.bge-small and dense.bge-base"),
        ('["bm25"]', 60, 100, r"\[hybrid.test\] fuses bm25 with one dense table, not bm25"),
        ('["bm25", "dense.bge-small"]', 0, 100, r"\[hybrid.test\] k 0 must be positive"),
        ('["bm25", "dense.bge-small"]', 60, -1, r"\[hybrid.test\] pool -1 must be positive"),
    ],
    ids=["unknown-member", "hybrid-member", "two-dense", "one-member", "k", "pool"],
)
def test_a_bad_hybrid_table_stops_with_a_message_naming_the_table(tmp_path, members, k, pool, message):
    other = "[hybrid.other]\nmembers = [\"bm25\", \"dense.bge-base\"]\nk = 60\npool = 100\n"
    table = f"[hybrid.test]\nmembers = {members}\nk = {k}\npool = {pool}\n"

    with pytest.raises(ConfigError, match=message):
        load_retrieval_config(with_hybrid(tmp_path, other + table))


@pytest.mark.parametrize(
    "old, new, message",
    [
        ('retriever = "dense.bge-small"', 'retriever = "dense.e5"', r"\[chat\] retriever 'dense.e5' is not a retriever .* configures: bm25, dense.bge-small"),
        ("k = 5", "k = 0", r"\[chat\] k 0 must be at least 1"),
        ('revision = "e98b54fe1913178321e1d9cd007d12a465de77a8f8eae37af69d2501ca03c6b5@0.40.5"', 'revision = "latest"', r"\[chat\] revision 'latest' is not pinned as <digest>@<Ollama version>"),
        ("think = false", 'think = "no"', r"\[chat\] think 'no' is not a bool"),
    ],
    ids=["unknown-retriever", "no-chunks", "unpinned", "mistyped"],
)
def test_a_bad_chat_table_stops_with_a_message_naming_it(tmp_path, old, new, message):
    with pytest.raises(ConfigError, match=message):
        load_chat_config(with_chat_line(tmp_path, old, new))
