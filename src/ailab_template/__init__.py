"""ailab_template: a small, eval-gated scaffold for Python AI lab repos."""

from ailab_template.classifiers import Classifier, KeywordClassifier, MajorityClassifier
from ailab_template.data import Example, load_jsonl
from ailab_template.metrics import accuracy, macro_f1
from ailab_template.providers import LLMClassifier, LLMProvider, StubProvider

__all__ = [
    "Classifier",
    "Example",
    "KeywordClassifier",
    "LLMClassifier",
    "LLMProvider",
    "MajorityClassifier",
    "StubProvider",
    "accuracy",
    "load_jsonl",
    "macro_f1",
]

__version__ = "0.1.0"
