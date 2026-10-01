from pathlib import Path

import pytest

from ailab_template.config import ConfigError, EvalConfig, load_config
from ailab_template.data import DatasetError, load_jsonl
from tests.conftest import FIXTURE


def test_bundled_fixture_is_balanced_and_valid() -> None:
    examples = load_jsonl(FIXTURE)
    assert 30 <= len(examples) <= 50
    labels = {example.label for example in examples}
    assert labels == {"account", "billing", "bug", "feedback"}
    counts = [sum(e.label == label for e in examples) for label in labels]
    assert len(set(counts)) == 1


def test_load_jsonl_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "d.jsonl"
    path.write_text('{"text": "a", "label": "x"}\n\n{"text": "b", "label": "y"}\n')
    assert [e.label for e in load_jsonl(path)] == ["x", "y"]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json\n", "invalid JSON"),
        ("[1, 2]\n", "JSON object"),
        ('{"text": "a"}\n', "label"),
        ('{"text": 3, "label": "x"}\n', "text"),
        ("\n\n", "empty"),
    ],
)
def test_load_jsonl_rejects_malformed(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(content)
    with pytest.raises(DatasetError, match=message):
        load_jsonl(path)


def test_config_defaults_when_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_config(env={}) == EvalConfig()


def test_config_file_then_env_override(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    cfg.write_text(
        '[eval]\ndataset = "d.jsonl"\nclassifier = "majority"\n'
        "[thresholds]\naccuracy = 0.5\nmacro_f1 = 0.4\n"
    )
    config = load_config(cfg, env={"AILAB_MIN_ACCURACY": "0.9", "AILAB_OUTPUT": "out/r.json"})
    assert config.classifier == "majority"
    assert config.dataset == Path("d.jsonl")
    assert config.min_accuracy == 0.9
    assert config.min_macro_f1 == 0.4
    assert config.output == Path("out/r.json")
    assert config.thresholds == {"accuracy": 0.9, "macro_f1": 0.4}
    assert config.lab == "ailab-template-python"


def test_config_lab_and_primary_metric(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    cfg.write_text('[eval]\nlab = "ailab-evals"\nprimary_metric = "macro_f1"\n')
    config = load_config(cfg, env={"AILAB_LAB": "ailab-rag"})
    assert (config.lab, config.primary_metric) == ("ailab-rag", "macro_f1")
    with pytest.raises(ConfigError, match="primary_metric"):
        load_config(cfg, env={"AILAB_PRIMARY_METRIC": "f2"})


def test_config_env_points_at_file(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    cfg.write_text('[eval]\nclassifier = "llm-stub"\n')
    assert load_config(env={"AILAB_CONFIG": str(cfg)}).classifier == "llm-stub"


def test_config_missing_explicit_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml", env={})


@pytest.mark.parametrize(
    ("env", "message"),
    [({"AILAB_MIN_ACCURACY": "high"}, "number"), ({"AILAB_MIN_MACRO_F1": "1.5"}, r"\[0, 1\]")],
)
def test_config_rejects_bad_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env: dict[str, str], message: str
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match=message):
        load_config(env=env)


def test_config_rejects_invalid_toml(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    cfg.write_text("[eval\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(cfg, env={})
