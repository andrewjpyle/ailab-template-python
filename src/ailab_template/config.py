"""Eval configuration: a TOML file, overridable by environment variables (12-factor)."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = "eval_config.toml"

#: environment variable -> EvalConfig attribute
ENV_OVERRIDES: dict[str, str] = {
    "AILAB_DATASET": "dataset",
    "AILAB_CLASSIFIER": "classifier",
    "AILAB_OUTPUT": "output",
    "AILAB_MIN_ACCURACY": "min_accuracy",
    "AILAB_MIN_MACRO_F1": "min_macro_f1",
}


class ConfigError(ValueError):
    """Raised for a missing or invalid configuration value."""


@dataclass(frozen=True, slots=True)
class EvalConfig:
    dataset: Path = Path("fixtures/support_intents.jsonl")
    classifier: str = "keyword"
    output: Path = Path("eval_results.json")
    min_accuracy: float = 0.0
    min_macro_f1: float = 0.0
    thresholds: dict[str, float] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("min_accuracy", "min_macro_f1"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"{name} must be within [0, 1], got {value}")
        object.__setattr__(
            self,
            "thresholds",
            {"accuracy": self.min_accuracy, "macro_f1": self.min_macro_f1},
        )


def _float(name: str, raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _from_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    section = data.get("eval", {})
    thresholds = data.get("thresholds", {})
    values: dict[str, Any] = {}
    if "dataset" in section:
        values["dataset"] = Path(section["dataset"])
    if "classifier" in section:
        values["classifier"] = str(section["classifier"])
    if "output" in section:
        values["output"] = Path(section["output"])
    if "accuracy" in thresholds:
        values["min_accuracy"] = _float("thresholds.accuracy", thresholds["accuracy"])
    if "macro_f1" in thresholds:
        values["min_macro_f1"] = _float("thresholds.macro_f1", thresholds["macro_f1"])
    return values


def _apply_env(config: EvalConfig, env: Mapping[str, str]) -> EvalConfig:
    updates: dict[str, Any] = {}
    for var, attr in ENV_OVERRIDES.items():
        raw = env.get(var)
        if raw is None or raw == "":
            continue
        if attr in ("dataset", "output"):
            updates[attr] = Path(raw)
        elif attr.startswith("min_"):
            updates[attr] = _float(var, raw)
        else:
            updates[attr] = raw
    return replace(config, **updates) if updates else config


def load_config(
    path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> EvalConfig:
    """Build the config: defaults <- TOML file <- environment variables.

    ``path`` defaults to ``$AILAB_CONFIG`` or ``eval_config.toml``. An explicitly
    requested file that does not exist is an error; the implicit default is optional.
    """
    env = os.environ if env is None else env
    explicit = path is not None or bool(env.get("AILAB_CONFIG"))
    config_path = Path(path or env.get("AILAB_CONFIG") or DEFAULT_CONFIG_PATH)

    values: dict[str, Any] = {}
    if config_path.is_file():
        with config_path.open("rb") as handle:
            try:
                values = _from_mapping(tomllib.load(handle))
            except tomllib.TOMLDecodeError as exc:
                raise ConfigError(f"{config_path}: invalid TOML ({exc})") from exc
    elif explicit:
        raise ConfigError(f"config file not found: {config_path}")

    return _apply_env(EvalConfig(**values), env)
