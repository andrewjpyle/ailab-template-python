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


SCHEMA_VERSION = 1


def current_commit() -> str | None:
    """Commit for the results record: env first (CI, Docker), then git, else None."""
    for var in ("GITHUB_SHA", "AILAB_COMMIT"):
        if sha := os.environ.get(var):
            return sha if sha != "unknown" else None
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _round(value: float) -> float:
    return round(value, 4)


def evaluate(config: EvalConfig) -> dict[str, Any]:
    """Run one eval and return the results record written to ``eval_results.json``.

    The top-level keys up to ``generated_at`` are a stable contract (``schema_version``
    1) that downstream tools may parse; the remaining keys are diagnostic extras.
    """
    examples = load_jsonl(config.dataset)
    classifier = build_classifier(config.classifier, examples)
    gold = [example.label for example in examples]
    predicted = [classifier.predict(example.text) for example in examples]

    scores = {"accuracy": accuracy(gold, predicted), "macro_f1": macro_f1(gold, predicted)}
    failures = [
        f"{metric} {scores[metric]:.4f} < threshold {floor:.4f}"
        for metric, floor in config.thresholds.items()
        if scores[metric] < floor
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "lab": config.lab,
        "dataset": config.dataset.stem,
        "provider": classifier.provider,
        "model": classifier.model,
        "primary_metric": config.primary_metric,
        "metrics": {**{key: _round(value) for key, value in scores.items()}, "n": len(examples)},
        "threshold": config.thresholds[config.primary_metric],
        "passed": not failures,
        "commit": current_commit(),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        # Diagnostic extras.
        "dataset_path": config.dataset.as_posix(),
        "thresholds": config.thresholds,
        "failures": failures,
        "per_class": {
            label: {key: _round(value) if isinstance(value, float) else value
                    for key, value in asdict(class_scores).items()}
            for label, class_scores in per_class(gold, predicted).items()
        },
        "confusion_matrix": confusion_matrix(gold, predicted),
    }  # fmt: skip


def markdown_rows(result: dict[str, Any]) -> str:
    """README "Eval results" rows, derived only from a results record."""
    commit = (result["commit"] or "unknown")[:7]
    dataset = f"{result['dataset']} (n={result['metrics']['n']})"
    note = "PASS" if result["passed"] else "FAIL"
    rows = [
        f"| {result['generated_at'][:10]} | {commit} | {result['model']} ({result['provider']}) "
        f"| {dataset} | {metric} | {result['metrics'][metric]:.4f} | "
        f"{note} (floor {floor:.2f}) |"
        for metric, floor in result["thresholds"].items()
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
    parser.add_argument(
        "--table-from",
        type=Path,
        metavar="RESULTS_JSON",
        help="print README table rows from an existing results file, without running",
    )
    return parser.parse_args(argv)  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.table_from is not None:
        try:
            record = json.loads(args.table_from.read_text(encoding="utf-8"))
            print(f"{TABLE_HEADER}\n{markdown_rows(record)}")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ailab-eval: error: cannot read {args.table_from}: {exc!r}", file=sys.stderr)
            return 2
        return 0
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
