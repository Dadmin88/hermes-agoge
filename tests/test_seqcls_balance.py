from __future__ import annotations

from collections import Counter

from agoge.backends.qlora_seqcls import _balance_key, _balance_rows


def _row(
    example_id: str,
    label: int,
    schema: str,
    competency: str,
    decision: str = "ALLOW",
) -> dict[str, object]:
    return {
        "text": example_id,
        "labels": label,
        "example_id": example_id,
        "event_schema": schema,
        "competency": competency,
        "decision": decision,
    }


def test_event_stratum_balancing_equalizes_runtime_learning_strata() -> None:
    rows = [
        _row("a1", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a2", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a3", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("b1", 1, "fleet.security-event.v1", "secret-handling"),
        _row("c1", 1, "fleet.learning-promotion-event.v1", "secret-handling"),
        _row("c2", 1, "fleet.learning-promotion-event.v1", "secret-handling"),
    ]
    balanced = _balance_rows(rows, seed=41, mode="event-stratum")
    counts = Counter(_balance_key(row, "event-stratum") for row in balanced)
    assert set(counts.values()) == {3}
    assert len(counts) == 3
    assert len(balanced) == 9


def test_hierarchical_balancing_equalizes_classes_and_spreads_each_class_across_strata() -> None:
    rows = [
        _row("a1", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a2", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a3", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a4", 0, "fleet.learning-promotion-event.v1", "benign-nonoverblocking"),
        _row("b1", 1, "fleet.security-event.v1", "secret-handling"),
        _row("c1", 1, "fleet.learning-promotion-event.v1", "secret-handling"),
    ]
    balanced = _balance_rows(rows, seed=41, mode="hierarchical")
    class_counts = Counter(int(row["labels"]) for row in balanced)
    assert class_counts == {0: 4, 1: 4}
    strata_counts = Counter(_balance_key(row, "hierarchical") for row in balanced)
    assert set(strata_counts.values()) == {2}


def test_decision_hierarchical_balancing_equalizes_decisions_then_reason_classes() -> None:
    rows = [
        _row("a1", 0, "fleet.security-event.v1", "benign-nonoverblocking", "ALLOW"),
        _row("a2", 0, "fleet.security-event.v1", "benign-nonoverblocking", "ALLOW"),
        _row("a3", 0, "fleet.learning-promotion-event.v1", "benign-nonoverblocking", "ALLOW"),
        _row("a4", 0, "fleet.learning-promotion-event.v1", "benign-nonoverblocking", "ALLOW"),
        _row("d1", 1, "fleet.security-event.v1", "secret-handling", "DENY"),
        _row("d2", 2, "fleet.learning-promotion-event.v1", "authority-boundaries", "DENY"),
        _row("r1", 3, "fleet.learning-promotion-event.v1", "uncertainty-review", "REVIEW"),
    ]
    balanced = _balance_rows(rows, seed=41, mode="decision-hierarchical")
    decision_counts = Counter(str(row["decision"]) for row in balanced)
    class_counts = Counter(int(row["labels"]) for row in balanced)
    assert decision_counts == {"ALLOW": 4, "DENY": 4, "REVIEW": 4}
    assert class_counts == {0: 4, 1: 2, 2: 2, 3: 4}


def test_balance_modes_are_deterministic_and_none_preserves_rows() -> None:
    rows = [
        _row("a1", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("a2", 0, "fleet.security-event.v1", "benign-nonoverblocking"),
        _row("b1", 1, "fleet.security-event.v1", "secret-handling"),
    ]
    first = _balance_rows(rows, seed=41, mode="class")
    second = _balance_rows(rows, seed=41, mode="class")
    assert first == second
    assert _balance_rows(rows, seed=41, mode="none") == rows
