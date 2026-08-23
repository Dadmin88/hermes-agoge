from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Prediction:
    expected: str
    actual: str


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    total: int
    correct: int
    accuracy: float
    confusion: dict[str, dict[str, int]]


def summarize(predictions: Iterable[Prediction]) -> EvaluationSummary:
    rows = list(predictions)
    labels = sorted({x.expected for x in rows} | {x.actual for x in rows})
    matrix: dict[str, Counter[str]] = {label: Counter() for label in labels}
    correct = 0
    for row in rows:
        matrix[row.expected][row.actual] += 1
        correct += int(row.expected == row.actual)
    total = len(rows)
    return EvaluationSummary(total=total, correct=correct, accuracy=(correct / total) if total else 0.0, confusion={expected: {actual: matrix[expected][actual] for actual in labels} for expected in labels})
