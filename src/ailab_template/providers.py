"""LLM provider seam. No SDKs and no network here: real providers live in the lab repos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ailab_template.classifiers import KeywordClassifier


@runtime_checkable
class LLMProvider(Protocol):
    """The minimum a text-completion backend must offer.

    A real implementation wraps a vendor SDK or a local model server and reads
    its credentials from the environment. Keeping the protocol this narrow is
    what makes providers swappable and the eval reproducible.
    """

    model: str

    def complete(self, prompt: str) -> str: ...


class StubProvider:
    """Deterministic offline provider for tests, CI and demos.

    It answers classification prompts by delegating to the keyword baseline,
    so the full prompt -> completion -> parse path is exercised without a network.
    """

    model = "stub-keyword-v0"

    def __init__(self) -> None:
        self._baseline = KeywordClassifier()
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        text = prompt.rsplit("Text:", 1)[-1].strip()
        return f"Label: {self._baseline.predict(text)}"


PROMPT_TEMPLATE = (
    "Classify the support message into exactly one of: {labels}.\n"
    "Answer in the form 'Label: <label>'.\n"
    "Text: {text}"
)


class LLMClassifier:
    """Adapts any :class:`LLMProvider` into a :class:`~ailab_template.classifiers.Classifier`."""

    def __init__(self, provider: LLMProvider, labels: Sequence[str], fallback: str) -> None:
        if fallback not in labels:
            raise ValueError("fallback must be one of the labels")
        self.provider = provider
        self.labels = list(labels)
        self.fallback = fallback
        self.name = f"llm:{provider.model}"

    def build_prompt(self, text: str) -> str:
        return PROMPT_TEMPLATE.format(labels=", ".join(self.labels), text=text)

    def parse(self, completion: str) -> str:
        """Pull a known label out of free text; anything unparseable becomes the fallback."""
        answer = completion.strip().removeprefix("Label:").strip().lower()
        return answer if answer in self.labels else self.fallback

    def predict(self, text: str) -> str:
        return self.parse(self.provider.complete(self.build_prompt(text)))
