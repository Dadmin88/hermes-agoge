from __future__ import annotations

import json
from pathlib import Path

from agoge.exam import (
    INVALID_DECISION,
    compare_exam_results,
    parse_model_output,
    summarize_exam,
)
from agoge.spec import StudentSpec

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def _contract() -> dict[str, object]:
    return StudentSpec.load(STUDENT).output_contract


def test_parse_model_output_accepts_closed_templar_output() -> None:
    raw = json.dumps(
        {
            "schema": "agoge.templar-model-output.v1",
            "decision": "DENY",
            "reason_codes": ["prompt-injection"],
        }
    )
    parsed = parse_model_output(raw, _contract())
    assert parsed.json_valid is True
    assert parsed.contract_valid is True
    assert parsed.decision == "DENY"
    assert parsed.reason_codes == ("prompt-injection",)


def test_parse_model_output_rejects_reason_code_outside_student_vocabulary() -> None:
    raw = json.dumps(
        {
            "schema": "agoge.templar-model-output.v1",
            "decision": "DENY",
            "reason_codes": ["invented-security-synonym"],
        }
    )
    parsed = parse_model_output(raw, _contract())
    assert parsed.json_valid is True
    assert parsed.contract_valid is False
    assert parsed.error == "unsupported-reason-code"


def test_parse_model_output_rejects_non_json_and_missing_reason() -> None:
    invalid = parse_model_output("DENY because it is bad", _contract())
    assert invalid.json_valid is False
    assert invalid.contract_valid is False
    missing_reason = parse_model_output(
        json.dumps(
            {
                "schema": "agoge.templar-model-output.v1",
                "decision": "REVIEW",
                "reason_codes": [],
            }
        ),
        _contract(),
    )
    assert missing_reason.contract_valid is False
    assert missing_reason.error == "missing-reason-code"


def test_summarize_exam_tracks_false_allow_and_false_deny_separately() -> None:
    rows = [
        {
            "expected": {"decision": "DENY", "reason_codes": ["x"]},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "ALLOW",
                "reason_codes": [],
            },
        },
        {
            "expected": {"decision": "ALLOW", "reason_codes": []},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "DENY",
                "reason_codes": ["x"],
            },
        },
        {
            "expected": {"decision": "REVIEW", "reason_codes": ["x"]},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "REVIEW",
                "reason_codes": ["x"],
            },
        },
    ]
    summary = summarize_exam(rows)
    assert summary["false_allow"] == 1
    assert summary["false_allow_rate"] == 0.5
    assert summary["false_deny"] == 1
    assert summary["false_deny_rate"] == 1.0


def test_summarize_exam_counts_invalid_output_as_wrong_decision() -> None:
    rows = [
        {
            "expected": {"decision": "ALLOW", "reason_codes": []},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "ALLOW",
                "reason_codes": [],
            },
        },
        {
            "expected": {"decision": "DENY", "reason_codes": ["x"]},
            "actual": {
                "json_valid": False,
                "contract_valid": False,
                "decision": None,
                "reason_codes": [],
            },
        },
    ]
    summary = summarize_exam(rows)
    assert summary["total"] == 2
    assert summary["decision_accuracy"] == 0.5
    assert summary["contract_valid_rate"] == 0.5
    assert summary["confusion"]["DENY"][INVALID_DECISION] == 1


def test_compare_exam_results_reports_improvement() -> None:
    common_spec = {
        "student_id": "templar-v1",
        "student_hash": "sha256:" + "1" * 64,
        "corpus_hash": "sha256:" + "2" * 64,
        "base_model": "Qwen/Qwen3-0.6B",
        "base_model_revision": "abc123",
        "split": "test",
    }
    base = {
        "exam_id": "base",
        "exam_spec": {**common_spec, "model_kind": "base"},
        "summary": {
            "json_valid_rate": 0.0,
            "contract_valid_rate": 0.0,
            "decision_accuracy": 0.0,
            "reason_codes_exact_rate": 0.0,
            "exact_match_rate": 0.0,
        },
        "rows": [
            {
                "example_id": "x",
                "expected": {"decision": "ALLOW"},
                "actual": {
                    "json_valid": False,
                    "contract_valid": False,
                    "decision": None,
                },
            }
        ],
    }
    candidate = {
        "exam_id": "candidate",
        "exam_spec": {**common_spec, "model_kind": "adapter"},
        "summary": {
            "json_valid_rate": 1.0,
            "contract_valid_rate": 1.0,
            "decision_accuracy": 1.0,
            "reason_codes_exact_rate": 1.0,
            "exact_match_rate": 1.0,
        },
        "rows": [
            {
                "example_id": "x",
                "expected": {"decision": "ALLOW"},
                "actual": {
                    "json_valid": True,
                    "contract_valid": True,
                    "decision": "ALLOW",
                },
            }
        ],
    }
    result = compare_exam_results(base, candidate)
    assert result["deltas"]["json_valid_rate"] == 1.0
    assert result["transitions"]["json_valid_improved"] == 1
    assert result["transitions"]["decision_improved"] == 1
