from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .evaluation import Prediction, summarize

INVALID_DECISION = "__INVALID__"


@dataclass(frozen=True, slots=True)
class ParsedModelOutput:
    raw: str
    json_valid: bool
    contract_valid: bool
    decision: str | None
    reason_codes: tuple[str, ...]
    error: str | None


def parse_model_output(raw: str, contract: dict[str, Any]) -> ParsedModelOutput:
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        return ParsedModelOutput(raw, False, False, None, (), "invalid-json")
    if type(value) is not dict:
        return ParsedModelOutput(raw, True, False, None, (), "output-not-object")
    required = {"schema", "decision", "reason_codes"}
    if set(value) != required:
        return ParsedModelOutput(raw, True, False, None, (), "closed-schema-mismatch")
    if value.get("schema") != contract.get("schema"):
        return ParsedModelOutput(raw, True, False, None, (), "schema-mismatch")
    allowed = contract.get("decision")
    decision = value.get("decision")
    if type(allowed) is not list or decision not in allowed:
        return ParsedModelOutput(raw, True, False, None, (), "unsupported-decision")
    reason_codes = value.get("reason_codes")
    if (
        type(reason_codes) is not list
        or not all(type(item) is str and item for item in reason_codes)
        or len(reason_codes) != len(set(reason_codes))
    ):
        return ParsedModelOutput(raw, True, False, None, (), "invalid-reason-codes")
    required_for = contract.get("reason_codes_required_for", [])
    if decision in required_for and not reason_codes:
        return ParsedModelOutput(raw, True, False, None, (), "missing-reason-code")
    return ParsedModelOutput(
        raw=raw,
        json_valid=True,
        contract_valid=True,
        decision=decision,
        reason_codes=tuple(sorted(reason_codes)),
        error=None,
    )


def compare_exam_results(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    base_spec = base.get("exam_spec")
    candidate_spec = candidate.get("exam_spec")
    if type(base_spec) is not dict or type(candidate_spec) is not dict:
        raise RuntimeError("exam result is missing its exam_spec")
    for key in (
        "student_id",
        "student_hash",
        "corpus_hash",
        "base_model",
        "base_model_revision",
        "split",
    ):
        if base_spec.get(key) != candidate_spec.get(key):
            raise RuntimeError(f"exam comparison mismatch for {key}")
    base_summary = base.get("summary")
    candidate_summary = candidate.get("summary")
    if type(base_summary) is not dict or type(candidate_summary) is not dict:
        raise RuntimeError("exam result is missing its summary")
    rate_keys = (
        "json_valid_rate",
        "contract_valid_rate",
        "decision_accuracy",
        "reason_codes_exact_rate",
        "exact_match_rate",
    )
    deltas = {
        key: float(candidate_summary[key]) - float(base_summary[key]) for key in rate_keys
    }
    base_rows = {row["example_id"]: row for row in base.get("rows", [])}
    candidate_rows = {row["example_id"]: row for row in candidate.get("rows", [])}
    if set(base_rows) != set(candidate_rows):
        raise RuntimeError("exam comparison uses different example sets")
    transitions = {
        "json_valid_improved": 0,
        "json_valid_regressed": 0,
        "contract_valid_improved": 0,
        "contract_valid_regressed": 0,
        "decision_improved": 0,
        "decision_regressed": 0,
    }
    for example_id in sorted(base_rows):
        base_row = base_rows[example_id]
        candidate_row = candidate_rows[example_id]
        expected = base_row["expected"]["decision"]
        base_actual = base_row["actual"]
        candidate_actual = candidate_row["actual"]
        for field, prefix in (
            ("json_valid", "json_valid"),
            ("contract_valid", "contract_valid"),
        ):
            before = bool(base_actual[field])
            after = bool(candidate_actual[field])
            transitions[f"{prefix}_improved"] += int(not before and after)
            transitions[f"{prefix}_regressed"] += int(before and not after)
        base_correct = base_actual.get("decision") == expected
        candidate_correct = candidate_actual.get("decision") == expected
        transitions["decision_improved"] += int(not base_correct and candidate_correct)
        transitions["decision_regressed"] += int(base_correct and not candidate_correct)
    return {
        "schema": "agoge.exam-comparison.v1",
        "base_exam_id": base.get("exam_id"),
        "candidate_exam_id": candidate.get("exam_id"),
        "student_id": base_spec["student_id"],
        "split": base_spec["split"],
        "base_model_kind": base_spec.get("model_kind"),
        "candidate_model_kind": candidate_spec.get("model_kind"),
        "deltas": deltas,
        "transitions": transitions,
    }


def summarize_exam(rows: list[dict[str, Any]]) -> dict[str, Any]:
    predictions: list[Prediction] = []
    json_valid = 0
    contract_valid = 0
    exact_match = 0
    reason_codes_exact = 0
    for row in rows:
        expected = row["expected"]
        actual = row["actual"]
        json_valid += int(bool(actual["json_valid"]))
        contract_valid += int(bool(actual["contract_valid"]))
        actual_decision = actual["decision"] or INVALID_DECISION
        predictions.append(Prediction(expected["decision"], actual_decision))
        if actual["contract_valid"]:
            expected_reasons = tuple(sorted(expected["reason_codes"]))
            actual_reasons = tuple(actual["reason_codes"])
            reason_codes_exact += int(expected_reasons == actual_reasons)
            exact_match += int(
                expected["decision"] == actual["decision"]
                and expected_reasons == actual_reasons
            )
    decision_summary = summarize(predictions)
    total = len(rows)
    return {
        "total": total,
        "json_valid": json_valid,
        "json_valid_rate": json_valid / total if total else 0.0,
        "contract_valid": contract_valid,
        "contract_valid_rate": contract_valid / total if total else 0.0,
        "decision_correct": decision_summary.correct,
        "decision_accuracy": decision_summary.accuracy,
        "reason_codes_exact": reason_codes_exact,
        "reason_codes_exact_rate": reason_codes_exact / total if total else 0.0,
        "exact_match": exact_match,
        "exact_match_rate": exact_match / total if total else 0.0,
        "confusion": decision_summary.confusion,
    }
