"""Dataset loading. A dataset is a JSONL file of ``{"text": ..., "label": ...}`` rows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Example:
    """One labelled example."""

    text: str
    label: str


class DatasetError(ValueError):
    """Raised when a dataset file is malformed."""


def load_jsonl(path: str | Path) -> list[Example]:
    """Load labelled examples from a JSONL file.

    Blank lines are skipped. Any other malformed line raises :class:`DatasetError`
    naming the file and line number, so a bad fixture fails loudly rather than
    silently shrinking the eval set.
    """
    path = Path(path)
    examples: list[Example] = []
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"{path}:{lineno}: invalid JSON ({exc.msg})") from exc
            if not isinstance(row, dict):
                raise DatasetError(f"{path}:{lineno}: expected a JSON object")
            text, label = row.get("text"), row.get("label")
            if not isinstance(text, str) or not isinstance(label, str) or not label:
                raise DatasetError(f"{path}:{lineno}: need string 'text' and non-empty 'label'")
            examples.append(Example(text=text, label=label))
    if not examples:
        raise DatasetError(f"{path}: dataset is empty")
    return examples
