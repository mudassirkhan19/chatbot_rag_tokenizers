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
