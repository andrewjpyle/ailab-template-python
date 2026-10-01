from collections.abc import Callable
from typing import Any

import pytest

from ailab_template.metrics import accuracy, confusion_matrix, macro_f1, per_class


def test_perfect_predictions() -> None:
    y = ["a", "b", "c", "a"]
    assert accuracy(y, y) == 1.0
    assert macro_f1(y, y) == 1.0


def test_all_wrong() -> None:
    assert accuracy(["a", "b"], ["b", "a"]) == 0.0
    assert macro_f1(["a", "b"], ["b", "a"]) == 0.0


def test_known_values() -> None:
    gold = ["a", "a", "a", "b"]
    pred = ["a", "a", "b", "b"]
    # a: P=1, R=2/3, F1=0.8 ; b: P=1/2, R=1, F1=2/3
    scores = per_class(gold, pred)
    assert scores["a"].f1 == pytest.approx(0.8)
    assert scores["b"].f1 == pytest.approx(2 / 3)
    assert scores["a"].support == 3
    assert macro_f1(gold, pred) == pytest.approx((0.8 + 2 / 3) / 2)
    assert accuracy(gold, pred) == 0.75


def test_macro_f1_weights_classes_equally_unlike_accuracy() -> None:
    # 9 majority, 1 minority; always predicting the majority looks good on accuracy only.
    gold = ["maj"] * 9 + ["min"]
    pred = ["maj"] * 10
    assert accuracy(gold, pred) == 0.9
    assert macro_f1(gold, pred) == pytest.approx((2 * 0.9 * 1.0 / 1.9) / 2)


def test_invented_label_is_penalised() -> None:
    scores = per_class(["a", "a"], ["a", "zzz"])
    assert "zzz" in scores
    assert scores["zzz"].precision == 0.0
    assert scores["zzz"].support == 0


def test_zero_division_scores_zero() -> None:
    scores = per_class(["a"], ["b"])
    assert scores["a"].precision == 0.0  # never predicted: 0/0
    assert scores["b"].recall == 0.0  # never gold: 0/0
    assert scores["a"].f1 == scores["b"].f1 == 0.0


def test_confusion_matrix() -> None:
    matrix = confusion_matrix(["a", "a", "b"], ["a", "b", "b"])
    assert matrix == {"a": {"a": 1, "b": 1}, "b": {"a": 0, "b": 1}}


@pytest.mark.parametrize("fn", [accuracy, macro_f1, per_class, confusion_matrix])
def test_empty_input_raises(fn: Callable[[list[str], list[str]], Any]) -> None:
    with pytest.raises(ValueError, match="empty"):
        fn([], [])


@pytest.mark.parametrize("fn", [accuracy, macro_f1, per_class, confusion_matrix])
def test_length_mismatch_raises(fn: Callable[[list[str], list[str]], Any]) -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        fn(["a"], ["a", "b"])
