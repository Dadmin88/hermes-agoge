from __future__ import annotations

import json
from pathlib import Path

from agoge.exam_bank import read_exam_cases
from agoge.exam_bank_api import examine_api_bank

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"
COMPETENCY = ROOT / "students" / "templar" / "competency.json"
BODY = ROOT / "students" / "templar" / "exams" / "templar-fresh-transfer-v1.jsonl"
MANIFEST = ROOT / "students" / "templar" / "exams" / "templar-fresh-transfer-v1.manifest.json"


def test_api_bank_exam_uses_sealed_cases_and_strict_contract(tmp_path: Path) -> None:
    cases = read_exam_cases(BODY)
    expected = {case.case_id: case.expected for case in cases}

    def fake_invoke(*, provider, requests, workers):
        assert provider == "nous"
        assert workers == 3
        return [
            {
                "request_id": request["request_id"],
                "ok": True,
                "model": request["model"],
                "content": json.dumps(expected[request["request_id"]], sort_keys=True),
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 5,
                    "total_tokens": 25,
                },
                "latency_ms": 12.5,
            }
            for request in requests
        ]

    result = examine_api_bank(
        student_path=STUDENT,
        competency_path=COMPETENCY,
        manifest_path=MANIFEST,
        body_path=BODY,
        provider="nous",
        model="example/free-runtime:free",
        workers=3,
        out=tmp_path / "exam.json",
        invoke_batch=fake_invoke,
    )
    summary = result["summary"]
    assert summary["total"] == 34
    assert summary["decision_accuracy"] == 1.0
    assert summary["exact_match_rate"] == 1.0
    assert summary["false_allow"] == 0
    assert summary["false_deny"] == 0
    assert summary["api_success_rate"] == 1.0
    assert result["exam_spec"]["bank_id"] == "templar-fresh-transfer-v1"
    assert result["exam_spec"]["training_forbidden"] is True
    assert (tmp_path / "exam.json").exists()
