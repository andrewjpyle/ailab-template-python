"""Tiny demo: classify a few messages with each bundled classifier, then run the eval."""

from __future__ import annotations

import os
from collections.abc import Sequence

from ailab_template.classifiers import Classifier, KeywordClassifier
from ailab_template.eval import main as eval_main
from ailab_template.providers import LLMClassifier, StubProvider

SAMPLES = (
    "I was billed twice for the same month, please refund one charge.",
    "The export button throws an error and the page goes blank.",
    "How do I change the email address on my profile?",
    "Would love a keyboard shortcut for archiving tickets.",
)


def main(argv: Sequence[str] | None = None) -> int:
    labels = ["account", "billing", "bug", "feedback"]
    classifiers: list[Classifier] = [
        KeywordClassifier(),
        LLMClassifier(StubProvider(), labels=labels, fallback="feedback"),
    ]
    greeting = os.environ.get("AILAB_DEMO_GREETING", "ailab-template demo")
    print(f"== {greeting} ==\n")
    for text in SAMPLES:
        predictions = ", ".join(f"{clf.name}={clf.predict(text)}" for clf in classifiers)
        print(f"- {text}\n    -> {predictions}")
    print("\n== eval ==\n")
    return eval_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
