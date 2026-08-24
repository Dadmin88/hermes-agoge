from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .api_runtime import invoke_hermes_api_batch
from .exam import parse_model_output, summarize_exam
from .exam_bank import load_exam_manifest, read_exam_cases, verify_exam_body
from .prompting import inference_messages
from .spec import CompetencySpec, SpecError, StudentSpec, digest
from .templar_projection import project_templar_event

BatchInvoker = Callable[..., list[dict[str, Any]]]


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def examine_api_bank(
    *,
    student_path: Path,
    competency_path: Path,
    manifest_path: Path,
    body_path: Path,
    provider: str,
    model: str,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    request_timeout_seconds: float = 30.0,
    workers: int = 2,
    out: Path | None = None,
    invoke_batch: BatchInvoker = invoke_hermes_api_batch,
) -> dict[str, Any]:
    if max_tokens < 1:
        raise SpecError("API bank Exam max_tokens must be positive")
    if not 0 < request_timeout_seconds <= 120:
        raise SpecError("API bank Exam request timeout must be between 0 and 120 seconds")

    student = StudentSpec.load(student_path)
    competency = CompetencySpec.load(competency_path)
    bank_manifest = load_exam_manifest(manifest_path)
    cases = read_exam_cases(body_path)
    verify_exam_body(bank_manifest, cases)
    if competency.student_id != student.student_id:
        raise SpecError("API bank Exam competency belongs to another Student")
    if bank_manifest.get("competency_id") != competency.competency_id:
        raise SpecError("API bank Exam competency ID mismatch")
    if bank_manifest.get("competency_hash") != competency.content_hash:
        raise SpecError("API bank Exam competency hash mismatch")
    if bank_manifest.get("training_forbidden") is not True:
        raise SpecError("API bank Exam requires a training-forbidden bank")

    requests = []
    for case in cases:
        projection = project_templar_event(case.prompt)
        requests.append(
            {
                "request_id": case.case_id,
                "model": model,
                "messages": inference_messages(projection, student.output_contract),
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout_seconds": request_timeout_seconds,
            }
        )
    api_results = invoke_batch(provider=provider, requests=requests, workers=workers)
    by_id = {item.get("request_id"): item for item in api_results if type(item) is dict}
    if set(by_id) != {case.case_id for case in cases}:
        raise RuntimeError("API bank Exam response IDs do not match requested cases")

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    api_success = 0
    prompt_tokens = completion_tokens = total_tokens = 0
    for case in cases:
        result = by_id[case.case_id]
        latency = result.get("latency_ms")
        if type(latency) in {int, float} and not isinstance(latency, bool):
            latencies.append(float(latency))
        if result.get("ok") is True:
            api_success += 1
            raw = result.get("content") if type(result.get("content")) is str else ""
            parsed = parse_model_output(raw, student.output_contract)
            usage = result.get("usage")
            if type(usage) is dict:
                prompt_tokens += int(usage.get("prompt_tokens") or 0)
                completion_tokens += int(usage.get("completion_tokens") or 0)
                total_tokens += int(usage.get("total_tokens") or 0)
            actual = {
                "raw": parsed.raw,
                "json_valid": parsed.json_valid,
                "contract_valid": parsed.contract_valid,
                "decision": parsed.decision,
                "reason_codes": list(parsed.reason_codes),
                "error": parsed.error,
                "api_ok": True,
                "provider_model": result.get("model"),
                "finish_reason": result.get("finish_reason"),
                "latency_ms": latency,
                "usage": usage,
            }
        else:
            actual = {
                "raw": "",
                "json_valid": False,
                "contract_valid": False,
                "decision": None,
                "reason_codes": [],
                "error": f"api-error:{result.get('error_type') or result.get('error') or 'unknown'}",
                "api_ok": False,
                "provider_model": None,
                "finish_reason": None,
                "latency_ms": latency,
                "usage": None,
            }
        rows.append(
            {
                "example_id": case.case_id,
                "example_hash": case.content_hash,
                "competency": case.competency,
                "event_schema": case.prompt.get("schema"),
                "expected": case.expected,
                "actual": actual,
            }
        )

    summary = summarize_exam(rows)
    summary.update(
        {
            "api_success": api_success,
            "api_errors": len(rows) - api_success,
            "api_success_rate": api_success / len(rows),
            "latency_ms_median": statistics.median(latencies) if latencies else None,
            "latency_ms_p95": _percentile(latencies, 0.95),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    )
    exam_spec = {
        "schema": "agoge.api-exam-bank-spec.v1",
        "purpose": "sealed-bank-runtime-candidate-benchmark-not-training-artifact",
        "bank_id": bank_manifest["bank_id"],
        "bank_manifest_hash": bank_manifest["manifest_hash"],
        "bank_body_hash": bank_manifest["body_hash"],
        "student_id": student.student_id,
        "reference_student_hash": student.content_hash,
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "provider": provider,
        "model": model,
        "transport": "hermes-credential-isolated-api-bridge-v1",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "request_timeout_seconds": request_timeout_seconds,
        "workers": workers,
        "training_forbidden": True,
    }
    result = {
        "schema": "agoge.api-exam-bank-result.v1",
        "exam_id": digest(exam_spec),
        "exam_spec": exam_spec,
        "performed_at_unix_ms": time.time_ns() // 1_000_000,
        "summary": summary,
        "rows": rows,
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
