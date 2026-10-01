import pytest

from ailab_template.classifiers import (
    Classifier,
    KeywordClassifier,
    MajorityClassifier,
    tokenize,
)
from ailab_template.data import Example
from ailab_template.providers import LLMClassifier, LLMProvider, StubProvider


def test_tokenize_lowercases_and_splits() -> None:
    assert tokenize("Refund MY card, please!") == ["refund", "my", "card", "please"]


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("Please refund the duplicate charge", "billing"),
        ("The app crashes on launch", "bug"),
        ("Reset my password", "account"),
        ("Love it, great work", "feedback"),
    ],
)
def test_keyword_classifier_predicts(text: str, label: str) -> None:
    assert KeywordClassifier().predict(text) == label


def test_keyword_classifier_falls_back_on_no_hits() -> None:
    assert KeywordClassifier(fallback="feedback").predict("zzz qqq") == "feedback"


def test_keyword_classifier_falls_back_on_tie() -> None:
    clf = KeywordClassifier({"x": ["alpha"], "y": ["beta"], "z": ["gamma"]}, fallback="z")
    assert clf.predict("alpha beta") == "z"
    assert clf.predict("alpha alpha beta") == "x"


def test_keyword_classifier_rejects_empty_keywords() -> None:
    with pytest.raises(ValueError, match="empty"):
        KeywordClassifier({})


def test_keyword_classifier_exposes_labels_and_scores() -> None:
    clf = KeywordClassifier({"x": ["alpha"], "y": ["beta"]})
    assert clf.labels == ["x", "y"]
    assert clf.scores("alpha alpha") == {"x": 2, "y": 0}


def test_majority_classifier() -> None:
    data = [Example("t", "b"), Example("t", "a"), Example("t", "b")]
    clf = MajorityClassifier.fit(data)
    assert clf.predict("anything") == "b"


def test_majority_classifier_tie_break_is_deterministic() -> None:
    data = [Example("t", "b"), Example("t", "a")]
    assert MajorityClassifier.fit(data).label == "a"


def test_majority_classifier_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        MajorityClassifier.fit([])


def test_all_classifiers_satisfy_protocol() -> None:
    llm = LLMClassifier(StubProvider(), labels=["a", "b"], fallback="a")
    for clf in (KeywordClassifier(), MajorityClassifier("a"), llm):
        assert isinstance(clf, Classifier)
    assert isinstance(StubProvider(), LLMProvider)


class _CannedProvider:
    model = "canned"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


def test_llm_classifier_builds_prompt_and_parses() -> None:
    provider = _CannedProvider("Label: Billing")
    clf = LLMClassifier(provider, labels=["billing", "bug"], fallback="bug")
    assert clf.predict("charged twice") == "billing"
    assert "billing, bug" in provider.prompts[0]
    assert provider.prompts[0].endswith("Text: charged twice")
    assert clf.name == "llm:canned"


@pytest.mark.parametrize("reply", ["I am not sure", "Label: refunds", ""])
def test_llm_classifier_unparseable_reply_uses_fallback(reply: str) -> None:
    clf = LLMClassifier(_CannedProvider(reply), labels=["billing", "bug"], fallback="bug")
    assert clf.predict("x") == "bug"


def test_llm_classifier_rejects_unknown_fallback() -> None:
    with pytest.raises(ValueError, match="fallback"):
        LLMClassifier(StubProvider(), labels=["a"], fallback="b")


def test_stub_provider_is_offline_and_counts_calls() -> None:
    provider = StubProvider()
    clf = LLMClassifier(
        provider, labels=["account", "billing", "bug", "feedback"], fallback="feedback"
    )
    assert clf.predict("I need a refund for this invoice") == "billing"
    assert provider.calls == 1
