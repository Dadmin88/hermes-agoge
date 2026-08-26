from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.base_tournament import BaseTournamentError, run_base_tournament
from agoge.exam import summarize_exam
from agoge.spec import CompetencySpec

ROOT = Path(__file__).resolve().parents[1]
COMPETENCY = ROOT / "students" / "templar" / "competency.json"


def _row(
    example_id: str,
    event_schema: str,
    expected_decision: str,
    expected_reasons: list[str],
    actual_decision: str,
    actual_reasons: list[str],
) -> dict[str, object]:
    return {
        "example_id": example_id,
        "example_hash": f"sha256:{example_id:0>64}",
        "competency": "benign-nonoverblocking",
        "event_schema": event_schema,
        "expected": {
            "schema": "agoge.templar-model-output.v1",
            "decision": expected_decision,
            "reason_codes": expected_reasons,
        },
        "actual": {
            "raw": "label",
            "json_valid": True,
            "contract_valid": True,
            "decision": actual_decision,
            "reason_codes": actual_reasons,
            "error": None,
        },
    }


def _write_run(
    root: Path,
    *,
    name: str,
    model: str,
    exact: bool,
    train_runtime: float,
    peak_cuda: int,
    latency: float,
    max_steps: int = 100,
    tamper_summary: bool = False,
) -> Path:
    competency = CompetencySpec.load(COMPETENCY)
    run = root / name
    run.mkdir()
    revision = f"rev-{name}"
    corpus_hash = "sha256:" + "c" * 64
    manifest = {
        "schema": "agoge.base-benchmark-run.v1",
        "purpose": "base-model-benchmark-only-not-promotable",
        "student_id": "templar-v1",
        "student_hash": "sha256:" + name[0] * 64,
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "base_model": model,
        "base_model_revision": revision,
        "corpus_hash": corpus_hash,
        "corpus_rebind_required_before_promotion": True,
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    training = {
        "schema": "agoge.training-result.v1",
        "status": "TRAINED",
        "backend": "qlora-seqcls",
        "student_id": "templar-v1",
        "base_model": model,
        "base_model_revision": revision,
        "cuda": {
            "device_name": "test-gpu",
            "max_memory_allocated_bytes": peak_cuda,
        },
        "metrics": {
            "train_runtime": train_runtime,
            "train_loss": 0.5,
            "train_samples_per_second": 10.0,
            "train_steps_per_second": 2.0,
        },
        "training": {
            "balance_mode": "class",
            "compute_dtype": "torch.bfloat16",
            "epochs": 1.0,
            "gradient_accumulation_steps": 1,
            "learning_rate": 5e-5,
            "lora_alpha": 32,
            "lora_r": 16,
            "max_length": 512,
            "max_steps": max_steps,
            "observed_max_tokens": 200,
            "per_device_train_batch_size": 8,
            "seed": 41,
        },
    }
    (run / "training-result-seqcls.json").write_text(json.dumps(training), encoding="utf-8")

    rows = [
        _row("1", "fleet.security-event.v1", "ALLOW", [], "ALLOW", []),
        _row(
            "2",
            "fleet.security-event.v1",
            "DENY",
            ["authority-manipulation"],
            "DENY",
            ["authority-manipulation"],
        ),
        _row(
            "3",
            "fleet.learning-promotion-event.v1",
            "REVIEW",
            ["hidden-instructions"],
            "REVIEW",
            ["hidden-instructions"],
        ),
        _row(
            "4",
            "fleet.learning-promotion-event.v1",
            "ALLOW",
            [],
            "ALLOW" if exact else "DENY",
            [] if exact else ["authority-manipulation"],
        ),
    ]
    summary = summarize_exam(rows)
    summary.update(
        {
            "latency_ms_median": latency,
            "latency_ms_p95": latency + 1.0,
            "runtime_device": "test-gpu",
        }
    )
    if tamper_summary:
        summary["exact_match_rate"] = 1.0
    exam = {
        "schema": "agoge.exam-result.v1",
        "exam_id": f"exam-{name}",
        "exam_spec": {
            "competency_id": competency.competency_id,
            "competency_hash": competency.content_hash,
            "corpus_hash": corpus_hash,
            "base_model": model,
            "base_model_revision": revision,
            "model_kind": "adapter",
            "adapter_hash": f"sha256:{name[-1] * 64}",
            "split": "validation",
        },
        "summary": summary,
        "rows": rows,
    }
    (run / "exam-seqcls-adapter-validation.json").write_text(json.dumps(exam), encoding="utf-8")
    return run


def test_base_tournament_prefers_capability_and_reports_resource_pareto_frontier(
    tmp_path: Path,
) -> None:
    stronger = _write_run(
        tmp_path,
        name="stronger",
        model="test/stronger",
        exact=True,
        train_runtime=10.0,
        peak_cuda=100,
        latency=5.0,
    )
    efficient = _write_run(
        tmp_path,
        name="efficient",
        model="test/efficient",
        exact=False,
        train_runtime=5.0,
        peak_cuda=50,
        latency=2.0,
    )
    result = run_base_tournament(
        competency_path=COMPETENCY,
        run_dirs=[efficient, stronger],
    )
    assert result["recommended_for_next_stage"].startswith("base:test/stronger@")
    assert result["hard_gate_pass_count"] == 2
    assert len(result["pareto_frontier"]) == 2
    assert result["graduated"] is False


def test_base_tournament_rejects_unequal_training_budgets(tmp_path: Path) -> None:
    first = _write_run(
        tmp_path,
        name="first",
        model="test/first",
        exact=True,
        train_runtime=10.0,
        peak_cuda=100,
        latency=5.0,
    )
    second = _write_run(
        tmp_path,
        name="second",
        model="test/second",
        exact=True,
        train_runtime=9.0,
        peak_cuda=90,
        latency=4.0,
        max_steps=99,
    )
    with pytest.raises(BaseTournamentError, match="different training budgets"):
        run_base_tournament(competency_path=COMPETENCY, run_dirs=[first, second])


def test_base_tournament_recomputes_exam_metrics(tmp_path: Path) -> None:
    good = _write_run(
        tmp_path,
        name="good",
        model="test/good",
        exact=True,
        train_runtime=10.0,
        peak_cuda=100,
        latency=5.0,
    )
    tampered = _write_run(
        tmp_path,
        name="tampered",
        model="test/tampered",
        exact=False,
        train_runtime=8.0,
        peak_cuda=80,
        latency=4.0,
        tamper_summary=True,
    )
    with pytest.raises(BaseTournamentError, match="stored validation summary disagrees"):
        run_base_tournament(competency_path=COMPETENCY, run_dirs=[good, tampered])
