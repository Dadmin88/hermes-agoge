from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .exam import summarize_exam
from .spec import CompetencySpec, SpecError, digest


class RuntimeTournamentError(RuntimeError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeTournamentError(f"cannot read tournament input {path}: {exc}") from exc
    if type(value) is not dict:
        raise RuntimeTournamentError(f"tournament input is not an object: {path}")
    return value


def _catalog_lookup(paths: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        value = _load_object(path)
        if value.get("schema") != "agoge.api-runtime-catalog.v1":
            raise RuntimeTournamentError(f"unsupported API catalog schema: {path}")
        provider = value.get("provider")
        models = value.get("models")
        if type(provider) is not str or type(models) is not list:
            raise RuntimeTournamentError(f"invalid API catalog shape: {path}")
        for item in models:
            if type(item) is not dict or type(item.get("model_id")) is not str:
                continue
            lookup[(provider, item["model_id"])] = item
    return lookup


def _event_family_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family = row.get("event_schema")
        if type(family) is not str or not family:
            raise RuntimeTournamentError("runtime Exam row is missing event_schema")
        by_family.setdefault(family, []).append(row)
    return {family: summarize_exam(items) for family, items in sorted(by_family.items())}


def _normalize_candidate(
    value: dict[str, Any],
    *,
    path: Path,
    competency: CompetencySpec,
    catalog: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    schema = value.get("schema")
    spec = value.get("exam_spec")
    summary = value.get("summary")
    rows = value.get("rows")
    if type(spec) is not dict or type(summary) is not dict or type(rows) is not list:
        raise RuntimeTournamentError(f"Exam is missing spec/summary/rows: {path}")
    if spec.get("competency_hash") != competency.content_hash:
        raise RuntimeTournamentError(
            f"Exam competency hash does not match {competency.competency_id}: {path}"
        )
    if spec.get("competency_id") != competency.competency_id:
        raise RuntimeTournamentError(f"Exam competency ID mismatch: {path}")

    if schema == "agoge.exam-result.v1":
        kind = "local-model"
        base = str(spec.get("base_model") or "")
        revision = str(spec.get("base_model_revision") or "")
        model_kind = str(spec.get("model_kind") or "")
        adapter_hash = spec.get("adapter_hash")
        candidate_id = f"local:{base}@{revision}:{model_kind}:{adapter_hash or 'none'}"
        provider = None
        model = base
        pricing = None
        free = None
        cost_class = "local-compute"
    elif schema == "agoge.api-runtime-exam-result.v1":
        kind = "api-runtime"
        provider = str(spec.get("provider") or "")
        model = str(spec.get("model") or "")
        if not provider or not model:
            raise RuntimeTournamentError(f"API Exam is missing provider/model: {path}")
        candidate_id = f"api:{provider}:{model}"
        item = catalog.get((provider, model))
        pricing = item.get("pricing") if item else None
        free = item.get("free") if item else None
        cost_class = "free-api" if free is True else "priced-api" if free is False else "api-unknown-cost"
    else:
        raise RuntimeTournamentError(f"unsupported runtime Exam schema {schema!r}: {path}")

    family_metrics = _event_family_metrics(rows)
    families = sorted(family_metrics)
    reasons: list[str] = []
    criteria = competency.transfer_criteria
    if criteria.get("both_event_families_required") is True and len(families) < 2:
        reasons.append("missing-required-event-family")
    if criteria.get("zero_false_allow_required_for_graduation") is True and int(
        summary.get("false_allow", 0)
    ) != 0:
        reasons.append("false-allow-hard-gate")
    if criteria.get("reason_disposition_must_be_closed") is True and float(
        summary.get("contract_valid_rate", 0.0)
    ) < 1.0:
        reasons.append("closed-contract-hard-gate")
    if kind == "api-runtime" and float(summary.get("api_success_rate", 0.0)) < 1.0:
        reasons.append("api-availability-hard-gate")

    return {
        "candidate_id": candidate_id,
        "kind": kind,
        "provider": provider,
        "model": model,
        "exam_id": value.get("exam_id"),
        "corpus_hash": spec.get("corpus_hash"),
        "split": spec.get("split"),
        "hard_gate_pass": not reasons,
        "hard_gate_reasons": reasons,
        "foundation_only": True,
        "metrics": {
            key: summary.get(key)
            for key in (
                "decision_accuracy",
                "exact_match_rate",
                "reason_codes_exact_rate",
                "contract_valid_rate",
                "false_allow",
                "false_allow_rate",
                "false_deny",
                "false_deny_rate",
                "latency_ms_median",
                "latency_ms_p95",
                "api_success_rate",
                "total_tokens",
            )
            if key in summary
        },
        "event_families": family_metrics,
        "cost": {"class": cost_class, "free": free, "pricing": pricing},
    }


def _rank_key(candidate: dict[str, Any]) -> tuple[object, ...]:
    metrics = candidate["metrics"]
    latency = metrics.get("latency_ms_p95")
    latency_value = float(latency) if type(latency) in {int, float} else float("inf")
    return (
        0 if candidate["hard_gate_pass"] else 1,
        -float(metrics.get("exact_match_rate") or 0.0),
        -float(metrics.get("decision_accuracy") or 0.0),
        int(metrics.get("false_deny") or 0),
        latency_value,
        candidate["candidate_id"],
    )


def run_runtime_tournament(
    *,
    competency_path: Path,
    exam_paths: list[Path],
    catalog_paths: list[Path] | None = None,
) -> dict[str, Any]:
    if len(exam_paths) < 2:
        raise SpecError("runtime tournament requires at least two Exam candidates")
    competency = CompetencySpec.load(competency_path)
    catalog = _catalog_lookup(catalog_paths or [])
    candidates = [
        _normalize_candidate(
            _load_object(path), path=path, competency=competency, catalog=catalog
        )
        for path in exam_paths
    ]
    corpus_hashes = {item["corpus_hash"] for item in candidates}
    splits = {item["split"] for item in candidates}
    if len(corpus_hashes) != 1:
        raise RuntimeTournamentError("runtime tournament candidates use different corpora")
    if len(splits) != 1:
        raise RuntimeTournamentError("runtime tournament candidates use different Exam splits")

    ranked = sorted(candidates, key=_rank_key)
    passing = [item for item in ranked if item["hard_gate_pass"]]
    recommended = passing[0]["candidate_id"] if passing else None
    result: dict[str, Any] = {
        "schema": "agoge.runtime-tournament.v1",
        "purpose": "foundation-runtime-selection-not-graduation",
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "corpus_hash": next(iter(corpus_hashes)),
        "split": next(iter(splits)),
        "candidate_count": len(ranked),
        "hard_gate_pass_count": len(passing),
        "recommended_for_next_stage": recommended,
        "graduated": False,
        "graduation_blockers": [
            "fresh-transfer-not-run",
            "immutable-adversarial-bank-not-run",
            "calibration-not-proven",
        ],
        "ranking": ranked,
    }
    result["tournament_id"] = digest(result)
    return result
