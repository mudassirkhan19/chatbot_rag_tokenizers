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


def test_settings_for_an_unknown_source_are_rejected(tmp_path):
    # A misspelt source name would otherwise leave the real source switched on without a word.
    path = tmp_path / "scope.toml"
    path.write_text('[sources.openalx]\nenabled = false\n[judge]\nmodel = "m"\nrevision = "r"\nthreshold = 0.5\nprompt = "{title} {abstract}"\n')
    with pytest.raises(ConfigError, match="unknown source 'openalx'"):
        load_config(path)


JUDGE = '[judge]\nmodel = "m"\nrevision = "r"\nthreshold = 0.5\nprompt = "{title} {abstract}"\n'


def test_judge_and_audit_models_name_their_backend(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(JUDGE + 'backend = "ollama"\n[[audit.models]]\nmodel = "a"\nrevision = "r"\n')
    config = load_config(path)
    assert config.judge.backend == "ollama"
    # Without one, a model is a Hugging Face model run with transformers.
    assert config.audit_models[0].backend == "transformers"


@pytest.mark.parametrize("section", ["judge", "audit-model"])
def test_an_unknown_judge_backend_is_rejected(tmp_path, section):
    path = tmp_path / "scope.toml"
    if section == "judge":
        path.write_text(JUDGE + 'backend = "llama.cpp"\n')
    else:
        path.write_text(JUDGE + '[[audit.models]]\nmodel = "a"\nrevision = "r"\nbackend = "llama.cpp"\n')
    with pytest.raises(ConfigError, match="unknown judge backend 'llama.cpp'"):
        load_config(path)


DECISION = '[judge.decision]\nstate = "{title} {abstract}"\ninstructions = "Q?"\ntrue = "T"\nfalse = "F"\n'


def test_a_decision_model_reads_its_question_from_judge_decision(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(JUDGE + 'backend = "ollama-decision"\n' + DECISION)
    question = load_config(path).judge.decision
    assert question is not None
    assert (question.state, question.instructions, question.true, question.false) == ("{title} {abstract}", "Q?", "T", "F")


def test_a_decision_model_without_a_question_is_rejected(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(JUDGE + '[[audit.models]]\nmodel = "a"\nrevision = "r"\nbackend = "ollama-decision"\n')
    with pytest.raises(ConfigError, match=r"needs a \[judge.decision\] question"):
        load_config(path)


def test_a_decision_state_without_the_abstract_is_rejected(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(JUDGE + DECISION.replace("{title} {abstract}", "{title}"))
    with pytest.raises(ConfigError, match=r"\[judge.decision\] state has no \{abstract\} placeholder"):
        load_config(path)
