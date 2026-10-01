"""Classifiers share one tiny interface so the eval loop never cares what's inside."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from ailab_template.data import Example

_TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens. Deliberately simple and deterministic."""
    return _TOKEN.findall(text.lower())


@runtime_checkable
class Classifier(Protocol):
    """Anything that maps text to one label.

    Swap in a fine-tuned model, an LLM, or a rules engine: if it identifies
    itself (``provider``, ``model``) and has ``predict``, the eval runner can score it.
    """

    provider: str  # who serves the model, e.g. "baseline", "stub", "openai"
    model: str  # stable model id recorded in eval results

    def predict(self, text: str) -> str: ...


# Keywords chosen by hand for the bundled support-intent fixture.
DEFAULT_KEYWORDS: Mapping[str, Sequence[str]] = {
    "billing": (
        "charge", "charged", "invoice", "refund", "bill", "billed", "payment",
        "card", "subscription", "price", "receipt", "plan",
    ),
    "bug": (
        "crash", "crashes", "error", "broken", "bug", "freezes", "blank",
        "fails", "failing", "stuck", "glitch", "500",
    ),
    "account": (
        "password", "login", "log", "email", "username", "account", "delete",
        "2fa", "locked", "profile", "sign",
    ),
    "feedback": (
        "love", "suggest", "suggestion", "wish", "great", "feature", "idea",
        "would", "nice", "thanks", "dark",
    ),
}  # fmt: skip


class KeywordClassifier:
    """Scores each label by keyword hits; ties and zero-hit inputs go to a fallback.

    This is the *baseline*: cheap, explainable, and the number any smarter
    model has to beat to justify its cost.
    """

    provider = "baseline"
    model = "keyword-baseline-v1"

    def __init__(
        self,
        keywords: Mapping[str, Sequence[str]] = DEFAULT_KEYWORDS,
        fallback: str = "feedback",
    ) -> None:
        if not keywords:
            raise ValueError("keywords must not be empty")
        self._keywords = {label: frozenset(words) for label, words in keywords.items()}
        self.fallback = fallback

    @property
    def labels(self) -> list[str]:
        return sorted(self._keywords)

    def scores(self, text: str) -> dict[str, int]:
        tokens = tokenize(text)
        return {
            label: sum(token in words for token in tokens)
            for label, words in self._keywords.items()
        }

    def predict(self, text: str) -> str:
        scores = self.scores(text)
        best = max(scores.values())
        if best == 0:
            return self.fallback
        winners = sorted(label for label, score in scores.items() if score == best)
        return winners[0] if len(winners) == 1 else self.fallback


class MajorityClassifier:
    """Always predicts the most common training label: the floor every model must clear."""

    provider = "baseline"
    model = "majority-baseline-v1"

    def __init__(self, label: str) -> None:
        self.label = label

    @classmethod
    def fit(cls, examples: Sequence[Example]) -> MajorityClassifier:
        if not examples:
            raise ValueError("cannot fit on an empty dataset")
        counts = Counter(example.label for example in examples)
        # Sort for a deterministic tie-break.
        label = max(sorted(counts), key=lambda key: counts[key])
        return cls(label)

    def predict(self, text: str) -> str:
        return self.label
