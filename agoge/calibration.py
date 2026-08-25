from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dispositions import disposition_for_class, registry_lookup
from .spec import SpecError, digest

CALIBRATION_SCHEMA = "agoge.calibration-policy.v1"


def load_calibration_policy(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict or value.get("schema") != CALIBRATION_SCHEMA:
        raise SpecError("calibration policy schema is invalid")
    allowed = {
        "schema",
        "policy_id",
        "phase23_risk_allow_min_confidence",
        "review_reason_by_signal",
        "basis",
        "policy_hash",
    }
    if set(value) != allowed:
        raise SpecError("calibration policy is not a closed schema")
    policy_id = value.get("policy_id")
    threshold = value.get("phase23_risk_allow_min_confidence")
    mapping = value.get("review_reason_by_signal")
    basis = value.get("basis")
    if type(policy_id) is not str or not policy_id:
        raise SpecError("calibration policy_id is invalid")
    if type(threshold) is not float or not 0.0 <= threshold <= 1.0:
        raise SpecError("calibration confidence threshold is invalid")
    if type(mapping) is not dict or not mapping:
        raise SpecError("calibration review mapping is invalid")
    for signal, reasons in mapping.items():
        if type(signal) is not str or not signal:
            raise SpecError("calibration signal is invalid")
        if (
            type(reasons) is not list
            or not reasons
            or not all(type(item) is str and item for item in reasons)
        ):
            raise SpecError("calibration review reason tuple is invalid")
    if (
        type(basis) is not list
        or not basis
        or not all(type(item) is str and item for item in basis)
    ):
        raise SpecError("calibration basis is invalid")
    unsigned = {key: value[key] for key in allowed if key != "policy_hash"}
    if value.get("policy_hash") != digest(unsigned):
        raise SpecError("calibration policy hash mismatch")
    return value


def apply_calibration(
    *,
    prompt: dict[str, Any],
    actual: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    if policy is None:
        return actual
    result = dict(actual)
    result["calibration"] = {
        "policy_id": policy["policy_id"],
        "policy_hash": policy["policy_hash"],
        "applied": False,
    }
    if prompt.get("schema") != "fleet.learning-promotion-event.v1":
        return result
    if result.get("decision") != "ALLOW":
        return result
    confidence = result.get("confidence")
    if (
        type(confidence) is not float
        or confidence >= policy["phase23_risk_allow_min_confidence"]
    ):
        return result
    signals = prompt.get("risk_signals")
    if type(signals) is not list or not signals:
        return result
    mapping = policy["review_reason_by_signal"]
    selected: list[str] | None = None
    selected_signal: str | None = None
    for signal in signals:
        reasons = mapping.get(signal)
        if type(reasons) is list:
            selected = sorted(reasons)
            selected_signal = signal
            break
    if selected is None:
        return result
    lookup = registry_lookup(registry)
    review_index = lookup.get(("REVIEW", tuple(selected)))
    if review_index is None:
        raise SpecError("calibration fallback disposition is absent from the Student registry")
    entry = disposition_for_class(registry, review_index)
    result["neural_decision"] = actual["decision"]
    result["neural_reason_codes"] = list(actual["reason_codes"])
    result["neural_class_index"] = actual["class_index"]
    result["neural_label_id"] = actual["label_id"]
    result["decision"] = "REVIEW"
    result["reason_codes"] = list(entry["reason_codes"])
    result["class_index"] = entry["class_index"]
    result["label_id"] = entry["label_id"]
    result["raw"] = entry["label_id"]
    result["calibration"] = {
        "policy_id": policy["policy_id"],
        "policy_hash": policy["policy_hash"],
        "applied": True,
        "trigger": "phase23-risk-bearing-low-confidence-allow",
        "signal": selected_signal,
        "threshold": policy["phase23_risk_allow_min_confidence"],
    }
    return result
