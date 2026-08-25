from __future__ import annotations

from agoge.calibration import apply_calibration
from agoge.dispositions import disposition_label_id
from agoge.spec import digest


def _registry() -> dict[str, object]:
    entries = [
        {
            "class_index": 0,
            "decision": "ALLOW",
            "reason_codes": [],
            "label_id": disposition_label_id("ALLOW", ()),
        },
        {
            "class_index": 1,
            "decision": "REVIEW",
            "reason_codes": ["hidden-instructions"],
            "label_id": disposition_label_id("REVIEW", ("hidden-instructions",)),
        },
    ]
    value: dict[str, object] = {
        "schema": "agoge.disposition-registry.v1",
        "student_id": "test-student",
        "entries": entries,
    }
    value["registry_hash"] = digest(value)
    return value


def _policy() -> dict[str, object]:
    return {
        "schema": "agoge.calibration-policy.v1",
        "policy_id": "test-policy",
        "policy_hash": "sha256:test",
        "phase23_risk_allow_min_confidence": 0.95,
        "review_reason_by_signal": {"hidden-instructions": ["hidden-instructions"]},
        "basis": ["test"],
    }


def test_low_confidence_risk_allow_routes_to_closed_review() -> None:
    actual = {
        "decision": "ALLOW",
        "reason_codes": [],
        "class_index": 0,
        "label_id": "allow",
        "raw": "allow",
        "confidence": 0.74,
    }
    result = apply_calibration(
        prompt={
            "schema": "fleet.learning-promotion-event.v1",
            "risk_signals": ["hidden-instructions"],
        },
        actual=actual,
        registry=_registry(),
        policy=_policy(),
    )
    assert result["decision"] == "REVIEW"
    assert result["reason_codes"] == ["hidden-instructions"]
    assert result["calibration"]["applied"] is True
    assert result["neural_decision"] == "ALLOW"


def test_high_confidence_risk_allow_is_unchanged() -> None:
    actual = {
        "decision": "ALLOW",
        "reason_codes": [],
        "class_index": 0,
        "label_id": "allow",
        "raw": "allow",
        "confidence": 0.997,
    }
    result = apply_calibration(
        prompt={
            "schema": "fleet.learning-promotion-event.v1",
            "risk_signals": ["hidden-instructions"],
        },
        actual=actual,
        registry=_registry(),
        policy=_policy(),
    )
    assert result["decision"] == "ALLOW"
    assert result["calibration"]["applied"] is False
