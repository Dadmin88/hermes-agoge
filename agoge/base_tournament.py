from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .exam import summarize_exam
from .spec import CompetencySpec, SpecError, digest


class BaseTournamentError(RuntimeError):
    pass


_BUDGET_KEYS = (
    "backend",
    "max_steps",
    "max_length",
    "learning_rate",
    "lora_r",
    "lora_alpha",
    "per_device_train_batch_size",
    "gradient_accumulation_steps",
    "balance_mode",
    "seed",
)


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaseTournamentError(f"cannot read base-tournament input {path}: {exc}") from exc
    if type(value) is not dict:
        raise BaseTournamentError(f"base-tournament input is not an object: {path}")
    return value


def _event_family_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family = row.get("event_schema")
        if type(family) is not str or not family:
            raise BaseTournamentError("base benchmark Exam row is missing event_schema")
        by_family.setdefault(family, []).append(row)
    return {family: summarize_exam(items) for family, items in sorted(by_family.items())}


def _training_budget(training_result: dict[str, Any]) -> dict[str, Any]:
    training = training_result.get("training")
    if type(training) is not dict:
        raise BaseTournamentError("training result is missing training configuration")
    budget: dict[str, Any] = {"backend": training_result.get("backend")}
    for key in _BUDGET_KEYS[1:]:
        if key not in training:
            raise BaseTournamentError(f"training result is missing budget field {key}")
        budget[key] = training[key]
    return budget


def _normalize_run(run_dir: Path, *, competency: CompetencySpec) -> dict[str, Any]:
    manifest = _load_object(run_dir / "manifest.json")
    training = _load_object(run_dir / "training-result-seqcls.json")
    exam = _load_object(run_dir / "exam-seqcls-adapter-validation.json")

    if manifest.get("schema") != "agoge.base-benchmark-run.v1":
        raise BaseTournamentError(f"run is not a base benchmark: {run_dir}")
    if manifest.get("purpose") != "base-model-benchmark-only-not-promotable":
        raise BaseTournamentError(f"run is not explicitly non-promotable: {run_dir}")
    if manifest.get("competency_id") != competency.competency_id:
        raise BaseTournamentError(f"run competency ID mismatch: {run_dir}")
    if manifest.get("competency_hash") != competency.content_hash:
        raise BaseTournamentError(f"run competency hash mismatch: {run_dir}")
    if manifest.get("corpus_rebind_required_before_promotion") is not True:
        raise BaseTournamentError(f"benchmark run does not require corpus rebinding: {run_dir}")
    if training.get("status") != "TRAINED" or training.get("backend") != "qlora-seqcls":
        raise BaseTournamentError(
            f"benchmark run is not a completed sequence-classification Askesis: {run_dir}"
        )
    if training.get("base_model") != manifest.get("base_model"):
        raise BaseTournamentError(f"training/model manifest mismatch: {run_dir}")
    if training.get("base_model_revision") != manifest.get("base_model_revision"):
        raise BaseTournamentError(f"training/revision manifest mismatch: {run_dir}")

    if exam.get("schema") != "agoge.exam-result.v1":
        raise BaseTournamentError(f"benchmark validation Exam has unsupported schema: {run_dir}")
    exam_spec = exam.get("exam_spec")
    summary = exam.get("summary")
    rows = exam.get("rows")
    if type(exam_spec) is not dict or type(summary) is not dict or type(rows) is not list:
        raise BaseTournamentError(f"benchmark validation Exam is incomplete: {run_dir}")
    if exam_spec.get("model_kind") != "adapter" or exam_spec.get("split") != "validation":
        raise BaseTournamentError(f"benchmark must use the adapted validation Exam: {run_dir}")
    for key in (
        "competency_id",
        "competency_hash",
        "corpus_hash",
        "base_model",
        "base_model_revision",
    ):
        expected = manifest.get(key)
        if exam_spec.get(key) != expected:
            raise BaseTournamentError(f"benchmark Exam/manifest mismatch for {key}: {run_dir}")

    computed_summary = summarize_exam(rows)
    for key, expected_value in computed_summary.items():
        if key in summary and summary[key] != expected_value:
            raise BaseTournamentError(
                f"stored validation summary disagrees with Exam rows for {key}: {run_dir}"
            )
    family_metrics = _event_family_metrics(rows)
    reasons: list[str] = []
    criteria = competency.transfer_criteria
    if criteria.get("both_event_families_required") is True and len(family_metrics) < 2:
        reasons.append("missing-required-event-family")
    if (
        criteria.get("zero_false_allow_required_for_graduation") is True
        and int(computed_summary.get("false_allow", 0)) != 0
    ):
        reasons.append("false-allow-hard-gate")
    if (
        criteria.get("reason_disposition_must_be_closed") is True
        and float(computed_summary.get("contract_valid_rate", 0.0)) < 1.0
    ):
        reasons.append("closed-contract-hard-gate")

    cuda = training.get("cuda")
    metrics = training.get("metrics")
    if type(cuda) is not dict or type(metrics) is not dict:
        raise BaseTournamentError(f"training result is missing resource evidence: {run_dir}")
    train_runtime = metrics.get("train_runtime")
    peak_cuda = cuda.get("max_memory_allocated_bytes")
    if type(train_runtime) not in {int, float} or isinstance(train_runtime, bool):
        raise BaseTournamentError(f"training result has invalid runtime evidence: {run_dir}")
    if type(peak_cuda) is not int or isinstance(peak_cuda, bool):
        raise BaseTournamentError(f"training result has invalid CUDA evidence: {run_dir}")

    return {
        "candidate_id": (
            f"base:{manifest['base_model']}@{manifest['base_model_revision']}:"
            f"adapter:{exam_spec.get('adapter_hash') or 'none'}"
        ),
        "model": manifest["base_model"],
        "revision": manifest["base_model_revision"],
        "student_hash": manifest["student_hash"],
        "exam_id": exam.get("exam_id"),
        "adapter_hash": exam_spec.get("adapter_hash"),
        "hard_gate_pass": not reasons,
        "hard_gate_reasons": reasons,
        "foundation_only": True,
        "training_budget": _training_budget(training),
        "capability": {
            key: computed_summary.get(key)
            for key in (
                "decision_accuracy",
                "exact_match_rate",
                "reason_codes_exact_rate",
                "contract_valid_rate",
                "false_allow",
                "false_allow_rate",
                "false_deny",
                "false_deny_rate",
            )
        },
        "resources": {
            "train_runtime_seconds": float(train_runtime),
            "peak_cuda_bytes": peak_cuda,
            "train_loss": metrics.get("train_loss"),
            "train_samples_per_second": metrics.get("train_samples_per_second"),
            "train_steps_per_second": metrics.get("train_steps_per_second"),
            "inference_latency_ms_median": summary.get("latency_ms_median"),
            "inference_latency_ms_p95": summary.get("latency_ms_p95"),
            "runtime_device": summary.get("runtime_device"),
        },
        "event_families": family_metrics,
    }


def _rank_key(candidate: dict[str, Any]) -> tuple[object, ...]:
    capability = candidate["capability"]
    resources = candidate["resources"]
    return (
        0 if candidate["hard_gate_pass"] else 1,
        -float(capability.get("exact_match_rate") or 0.0),
        -float(capability.get("decision_accuracy") or 0.0),
        int(capability.get("false_deny") or 0),
        float(resources["train_runtime_seconds"]),
        int(resources["peak_cuda_bytes"]),
        float(resources.get("inference_latency_ms_p95") or float("inf")),
        candidate["candidate_id"],
    )


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Return True when left is no worse on all frontier axes and better on at least one."""
    left_cap = left["capability"]
    right_cap = right["capability"]
    left_res = left["resources"]
    right_res = right["resources"]
    left_values = (
        float(left_cap.get("exact_match_rate") or 0.0),
        -float(left_res["train_runtime_seconds"]),
        -float(left_res["peak_cuda_bytes"]),
        -float(left_res.get("inference_latency_ms_median") or float("inf")),
    )
    right_values = (
        float(right_cap.get("exact_match_rate") or 0.0),
        -float(right_res["train_runtime_seconds"]),
        -float(right_res["peak_cuda_bytes"]),
        -float(right_res.get("inference_latency_ms_median") or float("inf")),
    )
    return all(a >= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a > b for a, b in zip(left_values, right_values, strict=True)
    )


def _pareto_frontier(candidates: list[dict[str, Any]]) -> list[str]:
    passing = [item for item in candidates if item["hard_gate_pass"]]
    frontier = []
    for candidate in passing:
        if not any(other is not candidate and _dominates(other, candidate) for other in passing):
            frontier.append(candidate["candidate_id"])
    return sorted(frontier)


def run_base_tournament(
    *,
    competency_path: Path,
    run_dirs: list[Path],
) -> dict[str, Any]:
    if len(run_dirs) < 2:
        raise SpecError("base tournament requires at least two benchmark runs")
    competency = CompetencySpec.load(competency_path)
    candidates = [_normalize_run(path, competency=competency) for path in run_dirs]

    budgets = {digest(item["training_budget"]) for item in candidates}
    if len(budgets) != 1:
        raise BaseTournamentError("base tournament candidates use different training budgets")
    corpus_hashes = {_load_object(path / "manifest.json").get("corpus_hash") for path in run_dirs}
    if len(corpus_hashes) != 1:
        raise BaseTournamentError("base tournament candidates use different corpora")

    ranked = sorted(candidates, key=_rank_key)
    passing = [item for item in ranked if item["hard_gate_pass"]]
    result: dict[str, Any] = {
        "schema": "agoge.base-tournament.v1",
        "purpose": "equal-budget-base-selection-not-graduation",
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "corpus_hash": next(iter(corpus_hashes)),
        "training_budget": ranked[0]["training_budget"],
        "candidate_count": len(ranked),
        "hard_gate_pass_count": len(passing),
        "recommended_for_next_stage": passing[0]["candidate_id"] if passing else None,
        "pareto_frontier": _pareto_frontier(ranked),
        "graduated": False,
        "graduation_blockers": [
            "base-benchmark-corpus-rebinding-required-before-promotion",
            "fresh-transfer-not-run",
            "immutable-adversarial-bank-not-run",
            "calibration-not-proven",
        ],
        "ranking": ranked,
    }
    result["tournament_id"] = digest(result)
    return result
