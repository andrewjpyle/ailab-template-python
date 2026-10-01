from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "fixtures" / "support_intents.jsonl"


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep host env vars from leaking into config-sensitive tests."""
    for var in (
        "AILAB_CONFIG",
        "AILAB_DATASET",
        "AILAB_CLASSIFIER",
        "AILAB_OUTPUT",
        "AILAB_MIN_ACCURACY",
        "AILAB_MIN_MACRO_F1",
        "AILAB_COMMIT",
        "GITHUB_SHA",
        "GITHUB_STEP_SUMMARY",
    ):
        monkeypatch.delenv(var, raising=False)
