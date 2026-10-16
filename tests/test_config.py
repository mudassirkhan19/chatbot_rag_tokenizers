from pathlib import Path

import pytest

from chatbot_rag_tokenizers.collection.config import ConfigError, load_config

REPO_CONFIG = Path(__file__).parents[1] / "config" / "scope.toml"


def test_repo_scope_config_loads_and_every_query_has_a_known_topic():
    config = load_config(REPO_CONFIG)
    assert config.queries
    assert {query.topic for query in config.queries} <= set(config.topics)


def test_query_with_unknown_topic_is_rejected(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(
        '[[topics]]\nid = "a"\ndescription = "A"\n'
        '[[queries]]\nid = "q"\nsource = "arxiv"\ntopic = "b"\nquery = "ti:x"\n'
    )
    with pytest.raises(ConfigError, match="unknown topic"):
        load_config(path)


def test_repo_scope_config_covers_every_topic_and_gives_every_seed_a_reason():
    config = load_config(REPO_CONFIG)
    assert {query.topic for query in config.queries} == set(config.topics)
    assert config.seeds
    assert all(seed.reason.strip() for seed in config.seeds)


@pytest.mark.parametrize(
    "seed, message",
    [
        ('id = "s"\npaper = "ARXIV:1"\ntopic = "b"\nreason = "R"\n', "unknown topic"),
        ('id = "s"\npaper = "ARXIV:1"\ntopic = "a"\nreason = " "\n', "no reason"),
    ],
    ids=["unknown-topic", "no-reason"],
)
def test_invalid_seed_is_rejected(tmp_path, seed, message):
    path = tmp_path / "scope.toml"
    path.write_text('[[topics]]\nid = "a"\ndescription = "A"\n[[seeds]]\n' + seed)
    with pytest.raises(ConfigError, match=message):
        load_config(path)
