from __future__ import annotations

import json
from pathlib import Path

from agoge.api_exam import examine_api_runtime
from agoge.corpus import read_jsonl, stable_event_stratified_split

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"
COMPETENCY = ROOT / "students" / "templar" / "competency.json"
CORPUS = ROOT / "students" / "templar" / "corpus" / "templar-runtime-foundation-v1.jsonl"


def test_api_exam_uses_same_event_split_and_strict_templar_contract(tmp_path: Path) -> None:
    selected = stable_event_stratified_split(read_jsonl(CORPUS))["validation"]
    expected = {row.example_id: row.completion for row in selected}

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
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "latency_ms": 25.0,
            }
            for request in requests
        ]

    result = examine_api_runtime(
        student_path=STUDENT,
        competency_path=COMPETENCY,
        corpus_path=CORPUS,
        provider="nous",
        model="example/free-model:free",
        split="validation",
        workers=3,
        out=tmp_path / "exam.json",
        invoke_batch=fake_invoke,
    )
    summary = result["summary"]
    assert summary["total"] == 46
    assert summary["exact_match_rate"] == 1.0
    assert summary["false_allow_rate"] == 0.0
    assert summary["false_deny_rate"] == 0.0
    assert summary["api_success_rate"] == 1.0
    assert summary["total_tokens"] == 46 * 15
    assert result["exam_spec"]["provider"] == "nous"
    assert result["exam_spec"]["model"] == "example/free-model:free"


def test_api_exam_counts_transport_failure_and_dangerous_false_allow() -> None:
    selected = stable_event_stratified_split(read_jsonl(CORPUS))["validation"]
    expected = {row.example_id: row.completion for row in selected}
    deny_id = next(row.example_id for row in selected if row.completion["decision"] == "DENY")
    failed_id = next(row.example_id for row in selected if row.example_id != deny_id)

    def fake_invoke(*, provider, requests, workers):
        del provider, workers
        results = []
        for request in requests:
            request_id = request["request_id"]
            if request_id == failed_id:
                results.append(
                    {
                        "request_id": request_id,
                        "ok": False,
                        "error_type": "TimeoutError",
                        "latency_ms": 90000.0,
                    }
                )
                continue
            completion = dict(expected[request_id])
            if request_id == deny_id:
                completion = {
                    "schema": "agoge.templar-model-output.v1",
                    "decision": "ALLOW",
                    "reason_codes": [],
                }
            results.append(
                {
                    "request_id": request_id,
                    "ok": True,
                    "model": request["model"],
                    "content": json.dumps(completion, sort_keys=True),
                    "finish_reason": "stop",
                    "usage": None,
                    "latency_ms": 10.0,
                }
            )
        return results

    result = examine_api_runtime(
        student_path=STUDENT,
        competency_path=COMPETENCY,
        corpus_path=CORPUS,
        provider="nous",
        model="example/model",
        invoke_batch=fake_invoke,
    )
    summary = result["summary"]
    assert summary["api_errors"] == 1
    assert summary["false_allow"] == 1
    assert summary["false_allow_rate"] > 0.0
    assert summary["contract_valid_rate"] < 1.0
