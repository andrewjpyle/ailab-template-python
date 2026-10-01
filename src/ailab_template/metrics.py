"""Classification metrics, written out by hand so the maths is inspectable."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassScores:
    precision: float
    recall: float
    f1: float
    support: int


def _check(y_true: Sequence[str], y_pred: Sequence[str]) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError(f"length mismatch: {len(y_true)} gold vs {len(y_pred)} predicted")
    if not y_true:
        raise ValueError("cannot score an empty prediction set")


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    _check(y_true, y_pred)
    return sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def per_class(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, ClassScores]:
    """Precision/recall/F1 per label.

    Labels are the union of gold and predicted labels, so a model that invents
    a label is penalised (its precision for that label is 0) instead of ignored.
    Undefined ratios (0/0) are scored as 0.0, matching scikit-learn's
    ``zero_division=0`` convention.
    """
    _check(y_true, y_pred)
    scores: dict[str, ClassScores] = {}
    for label in sorted(set(y_true) | set(y_pred)):
        pairs = list(zip(y_true, y_pred, strict=True))
        tp = sum(t == label and p == label for t, p in pairs)
        fp = sum(t != label and p == label for t, p in pairs)
        fn = sum(t == label and p != label for t, p in pairs)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        scores[label] = ClassScores(precision, recall, f1, support=tp + fn)
    return scores


def macro_f1(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Unweighted mean of per-label F1: every class counts equally, however rare."""
    scores = per_class(y_true, y_pred)
    return sum(s.f1 for s in scores.values()) / len(scores)


def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, dict[str, int]]:
    """``matrix[gold][predicted] -> count`` over the union of labels."""
    _check(y_true, y_pred)
    labels = sorted(set(y_true) | set(y_pred))
    matrix = {gold: dict.fromkeys(labels, 0) for gold in labels}
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p] += 1
    return matrix
