"""Eval runner and regression gate.

Usage::

    ailab-eval                      # or: python -m ailab_template.eval
    ailab-eval --classifier majority --min-accuracy 0.9

Exit codes: 0 = all metrics at or above threshold, 1 = regression, 2 = bad config/data.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ailab_template.classifiers import Classifier, KeywordClassifier, MajorityClassifier
from ailab_template.config import ConfigError, EvalConfig, load_config
from ailab_template.data import DatasetError, Example, load_jsonl
from ailab_template.metrics import accuracy, confusion_matrix, macro_f1, per_class
from ailab_template.providers import LLMClassifier, StubProvider

CLASSIFIERS = ("keyword", "majority", "llm-stub")
TABLE_HEADER = (
    "| Date | Commit | Model/Provider | Dataset | Metric | Score | Notes |\n"
    "|---|---|---|---|---|---|---|"
)


def build_classifier(name: str, examples: Sequence[Example]) -> Classifier:
    """Factory keyed by config name. Add new model families here."""
    if name == "keyword":
        return KeywordClassifier()
    if name == "majority":
        return MajorityClassifier.fit(examples)
    if name == "llm-stub":
        labels = sorted({example.label for example in examples})
        return LLMClassifier(StubProvider(), labels=labels, fallback=labels[0])
    raise ConfigError(f"unknown classifier {name!r}; choose one of {', '.join(CLASSIFIERS)}")


def current_commit() -> str:
    """Commit for the results record: env first (CI, Docker), then git, else 'unknown'."""
    for var in ("AILAB_COMMIT", "GITHUB_SHA"):
        if sha := os.environ.get(var):
            return sha[:7]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def evaluate(config: EvalConfig) -> dict[str, Any]:
    """Run one eval and return a JSON-serialisable results record."""
    examples = load_jsonl(config.dataset)
    classifier = build_classifier(config.classifier, examples)
    gold = [example.label for example in examples]
    predicted = [classifier.predict(example.text) for example in examples]

    metrics = {"accuracy": accuracy(gold, predicted), "macro_f1": macro_f1(gold, predicted)}
    failures = [
        f"{metric} {metrics[metric]:.4f} < threshold {floor:.4f}"
        for metric, floor in config.thresholds.items()
        if metrics[metric] < floor
    ]
    return {
        "date": datetime.now(UTC).date().isoformat(),
        "commit": current_commit(),
        "classifier": classifier.name,
        "dataset": config.dataset.as_posix(),
        "n_examples": len(examples),
        "metrics": {key: round(value, 4) for key, value in metrics.items()},
        "thresholds": config.thresholds,
        "passed": not failures,
        "failures": failures,
        "per_class": {
            label: {key: round(value, 4) if isinstance(value, float) else value
                    for key, value in asdict(scores).items()}
            for label, scores in per_class(gold, predicted).items()
        },
        "confusion_matrix": confusion_matrix(gold, predicted),
    }  # fmt: skip


def markdown_rows(result: dict[str, Any]) -> str:
    """One table row per gated metric, matching the README's Eval results table."""
    dataset = Path(result["dataset"]).name
    note = "PASS" if result["passed"] else "FAIL"
    rows = [
        f"| {result['date']} | {result['commit']} | {result['classifier']} | {dataset} "
        f"(n={result['n_examples']}) | {metric} | {score:.4f} | "
        f"{note} (floor {result['thresholds'][metric]:.2f}) |"
        for metric, score in result["metrics"].items()
    ]
    return "\n".join(rows)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ailab-eval", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--config", help="TOML config path (default: $AILAB_CONFIG or eval_config.toml)"
    )
    parser.add_argument("--dataset", type=Path, help="override the JSONL dataset")
    parser.add_argument("--classifier", choices=CLASSIFIERS, help="override the classifier")
    parser.add_argument("--output", type=Path, help="override the results JSON path")
    parser.add_argument("--min-accuracy", type=float, help="override the accuracy floor")
    parser.add_argument("--min-macro-f1", type=float, help="override the macro-F1 floor")
    return parser.parse_args(argv)  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        config = load_config(args.config)
        overrides = {
            key: value
            for key, value in {
                "dataset": args.dataset,
                "classifier": args.classifier,
                "output": args.output,
                "min_accuracy": args.min_accuracy,
                "min_macro_f1": args.min_macro_f1,
            }.items()
            if value is not None
        }
        config = replace(config, **overrides)
        result = evaluate(config)
    except (ConfigError, DatasetError, OSError) as exc:
        print(f"ailab-eval: error: {exc}", file=sys.stderr)
        return 2

    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    table = f"{TABLE_HEADER}\n{markdown_rows(result)}"
    print(table)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Eval results\n\n{table}\n\n")

    if not result["passed"]:
        for failure in result["failures"]:
            print(f"REGRESSION: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
