import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ailab_template.config import EvalConfig
from ailab_template.demo import main as demo_main
from ailab_template.eval import current_commit, evaluate, main
from tests.conftest import FIXTURE


def _no_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Run from an empty dir so only defaults + flags apply.
    monkeypatch.chdir(tmp_path)


def test_evaluate_keyword_baseline_on_fixture() -> None:
    result = evaluate(EvalConfig(dataset=FIXTURE, min_accuracy=0.8, min_macro_f1=0.8))
    assert result["passed"] is True
    assert result["metrics"]["n"] == 40
    assert result["metrics"]["accuracy"] >= 0.8
    assert set(result["per_class"]) == {"account", "billing", "bug", "feedback"}
    total = sum(sum(row.values()) for row in result["confusion_matrix"].values())
    assert total == 40


def test_gate_passes_and_writes_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_config(tmp_path, monkeypatch)
    monkeypatch.setenv("AILAB_COMMIT", "abc1234deadbeef00")
    out = tmp_path / "results.json"
    code = main(["--dataset", str(FIXTURE), "--output", str(out), "--min-accuracy", "0.5"])
    assert code == 0
    record = json.loads(out.read_text())
    assert record["passed"] is True
    assert record["commit"] == "abc1234deadbeef00"
    stdout = capsys.readouterr().out
    assert "| Date | Commit | Model/Provider | Dataset | Metric | Score | Notes |" in stdout
    assert (
        "| abc1234 | keyword-baseline-v1 (baseline) | support_intents (n=40) | accuracy |" in stdout
    )


def test_gate_fails_on_regression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_config(tmp_path, monkeypatch)
    out = tmp_path / "results.json"
    # The majority baseline scores 0.25 accuracy on a balanced 4-class set.
    code = main(
        ["--dataset", str(FIXTURE), "--output", str(out),
         "--classifier", "majority", "--min-accuracy", "0.8"]
    )  # fmt: skip
    assert code == 1
    record = json.loads(out.read_text())
    assert record["passed"] is False
    assert record["metrics"]["accuracy"] == 0.25
    assert "REGRESSION: accuracy" in capsys.readouterr().err


def test_gate_respects_env_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_config(tmp_path, monkeypatch)
    monkeypatch.setenv("AILAB_DATASET", str(FIXTURE))
    monkeypatch.setenv("AILAB_OUTPUT", str(tmp_path / "r.json"))
    monkeypatch.setenv("AILAB_MIN_MACRO_F1", "0.99")
    assert main([]) == 1


def test_llm_stub_classifier_runs_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_config(tmp_path, monkeypatch)
    out = tmp_path / "r.json"
    assert main(["--dataset", str(FIXTURE), "--output", str(out), "--classifier", "llm-stub"]) == 0
    record = json.loads(out.read_text())
    assert (record["provider"], record["model"]) == ("stub", "stub-keyword-v1")


def test_bad_dataset_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_config(tmp_path, monkeypatch)
    assert main(["--dataset", str(tmp_path / "nope.jsonl")]) == 2
    assert "error" in capsys.readouterr().err


def test_writes_github_step_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_config(tmp_path, monkeypatch)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert main(["--dataset", str(FIXTURE), "--output", str(tmp_path / "r.json")]) == 0
    assert "### Eval results" in summary.read_text()


def test_demo_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_config(tmp_path, monkeypatch)
    assert demo_main(["--dataset", str(FIXTURE), "--output", str(tmp_path / "r.json")]) == 0
    out = capsys.readouterr().out
    assert "keyword-baseline-v1=billing" in out
    assert "| macro_f1 |" in out


CONTRACT_KEYS: dict[str, type | tuple[type, ...]] = {
    "schema_version": int,
    "lab": str,
    "dataset": str,
    "provider": str,
    "model": str,
    "primary_metric": str,
    "metrics": dict,
    "threshold": float,
    "passed": bool,
    "commit": (str, type(None)),
    "generated_at": str,
}


def test_results_file_matches_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """eval_results.json is parsed by host applications; its shape is a contract."""
    _no_config(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_SHA", "f" * 40)
    out = tmp_path / "eval_results.json"
    assert main(["--dataset", str(FIXTURE), "--output", str(out), "--min-accuracy", "0.8"]) == 0
    record = json.loads(out.read_text())
    for key, kind in CONTRACT_KEYS.items():
        assert isinstance(record[key], kind), key
    assert record["schema_version"] == 1
    assert record["lab"] == "ailab-template-python"
    assert record["dataset"] == "support_intents"
    assert (record["provider"], record["model"]) == ("baseline", "keyword-baseline-v1")
    assert record["primary_metric"] == "accuracy"
    assert record["threshold"] == 0.8
    assert record["commit"] == "f" * 40
    assert set(record["metrics"]) >= {"accuracy", "macro_f1", "n"}
    assert all(isinstance(v, int | float) for v in record["metrics"].values())
    assert record["metrics"]["n"] == 40
    assert datetime.fromisoformat(record["generated_at"]).utcoffset() == timedelta(0)


def test_commit_is_null_when_unknown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))  # no git binary reachable
    assert current_commit() is None
    monkeypatch.setenv("AILAB_COMMIT", "unknown")
    assert current_commit() is None


def test_table_from_existing_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_config(tmp_path, monkeypatch)
    out = tmp_path / "r.json"
    assert main(["--dataset", str(FIXTURE), "--output", str(out)]) == 0
    first = capsys.readouterr().out
    assert main(["--table-from", str(out)]) == 0
    assert capsys.readouterr().out == first
    (tmp_path / "bad.json").write_text("{}")
    assert main(["--table-from", str(tmp_path / "bad.json")]) == 2
