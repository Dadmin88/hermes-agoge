from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .api_runtime import invoke_hermes_api_batch
from .corpus import (
    read_jsonl,
    stable_event_stratified_split,
    stable_split,
    stable_stratified_split,
)
from .exam import parse_model_output, summarize_exam
from .prompting import inference_messages
from .spec import CompetencySpec, SpecError, StudentSpec, digest
from .templar_projection import project_templar_event

BatchInvoker = Callable[..., list[dict[str, Any]]]


def _split(examples, strategy: str):
    if strategy == "stable":
        return stable_split(examples)
    if strategy == "stratified":
        return stable_stratified_split(examples)
    if strategy == "event-stratified":
        return stable_event_stratified_split(examples)
    raise SpecError(f"unsupported API Exam split strategy: {strategy}")


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def examine_api_runtime(
    *,
    student_path: Path,
    competency_path: Path,
    corpus_path: Path,
    provider: str,
    model: str,
    split: str = "validation",
    split_strategy: str = "event-stratified",
    max_tokens: int = 128,
    temperature: float = 0.0,
    request_timeout_seconds: float = 30.0,
    workers: int = 2,
    limit: int | None = None,
    out: Path | None = None,
    invoke_batch: BatchInvoker = invoke_hermes_api_batch,
) -> dict[str, Any]:
    if split not in {"train", "validation", "test"}:
        raise SpecError("API Exam split must be train, validation, or test")
    if max_tokens < 1:
        raise SpecError("API Exam max_tokens must be positive")
    if not 0 < request_timeout_seconds <= 120:
        raise SpecError("API Exam request_timeout_seconds must be between 0 and 120")
    student = StudentSpec.load(student_path)
    competency = CompetencySpec.load(competency_path)
    if competency.student_id != student.student_id:
        raise SpecError("API Exam competency belongs to another Student")
    examples = read_jsonl(corpus_path)
    splits = _split(examples, split_strategy)
    selected = splits[split]
    if not selected:
        raise SpecError("API Exam selected split is empty")
    if limit is not None:
        if limit < 1:
            raise SpecError("API Exam limit must be positive when supplied")
        selected = selected[:limit]

    requests = []
    for example in selected:
        projection = project_templar_event(example.prompt)
        requests.append(
            {
                "request_id": example.example_id,
                "model": model,
                "messages": inference_messages(projection, student.output_contract),
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout_seconds": request_timeout_seconds,
            }
        )
    api_results = invoke_batch(provider=provider, requests=requests, workers=workers)
    by_id = {item.get("request_id"): item for item in api_results if type(item) is dict}
    if set(by_id) != {example.example_id for example in selected}:
        raise RuntimeError("API Exam response IDs do not match requested examples")

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    api_success = 0
    empty_content = 0
    finish_length = 0
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    for example in selected:
        result = by_id[example.example_id]
        latency = result.get("latency_ms")
        if type(latency) in {int, float} and not isinstance(latency, bool):
            latencies.append(float(latency))
        if result.get("ok") is True:
            api_success += 1
            raw = result.get("content")
            raw = raw if type(raw) is str else ""
            empty_content += int(not raw.strip())
            finish_length += int(result.get("finish_reason") == "length")
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
                "example_id": example.example_id,
                "example_hash": example.content_hash,
                "competency": example.competency,
                "event_schema": example.prompt.get("schema"),
                "expected": example.completion,
                "actual": actual,
            }
        )

    summary = summarize_exam(rows)
    summary.update(
        {
            "api_success": api_success,
            "api_errors": len(rows) - api_success,
            "api_success_rate": api_success / len(rows),
            "empty_content": empty_content,
            "empty_content_rate": empty_content / len(rows),
            "finish_length": finish_length,
            "finish_length_rate": finish_length / len(rows),
            "latency_ms_median": statistics.median(latencies) if latencies else None,
            "latency_ms_p95": _percentile(latencies, 0.95),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    )
    exam_spec = {
        "schema": "agoge.api-runtime-exam-spec.v1",
        "purpose": "runtime-candidate-benchmark-not-training-artifact",
        "student_id": student.student_id,
        "reference_student_hash": student.content_hash,
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "corpus_hash": digest([example.to_dict() for example in examples]),
        "provider": provider,
        "model": model,
        "transport": "hermes-credential-isolated-api-bridge-v1",
        "split": split,
        "split_strategy": split_strategy,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "request_timeout_seconds": request_timeout_seconds,
        "workers": workers,
        "limit": limit,
    }
    result = {
        "schema": "agoge.api-runtime-exam-result.v1",
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
