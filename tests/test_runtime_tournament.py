from __future__ import annotations

import json
from pathlib import Path

from agoge.runtime_tournament import run_runtime_tournament
from agoge.spec import CompetencySpec

ROOT = Path(__file__).resolve().parents[1]
COMPETENCY = ROOT / "students" / "templar" / "competency.json"


def _rows(*, false_allow: bool = False):
    expected = [
        ("fleet.security-event.v1", "DENY", "DENY" if not false_allow else "ALLOW"),
        ("fleet.security-event.v1", "ALLOW", "ALLOW"),
        ("fleet.learning-promotion-event.v1", "REVIEW", "REVIEW"),
        ("fleet.learning-promotion-event.v1", "ALLOW", "ALLOW"),
    ]
    rows = []
    for index, (family, want, got) in enumerate(expected):
        rows.append(
            {
                "example_id": f"e{index}",
                "event_schema": family,
                "expected": {"decision": want, "reason_codes": []},
                "actual": {
                    "json_valid": True,
                    "contract_valid": True,
                    "decision": got,
                    "reason_codes": [],
                },
            }
        )
    return rows


def _summary(rows):
    from agoge.exam import summarize_exam

    value = summarize_exam(rows)
    value.update({"latency_ms_median": 50.0, "latency_ms_p95": 80.0})
    return value


def test_runtime_tournament_hard_rejects_false_allow_and_recommends_safe_candidate(tmp_path: Path) -> None:
    competency = CompetencySpec.load(COMPETENCY)
    corpus_hash = "sha256:" + "a" * 64

    local_rows = _rows()
    local = {
        "schema": "agoge.exam-result.v1",
        "exam_id": "local-exam",
        "exam_spec": {
            "competency_id": competency.competency_id,
            "competency_hash": competency.content_hash,
            "corpus_hash": corpus_hash,
            "split": "validation",
            "base_model": "example/local",
            "base_model_revision": "r1",
            "model_kind": "adapter",
            "adapter_hash": "sha256:" + "b" * 64,
        },
        "summary": _summary(local_rows),
        "rows": local_rows,
    }
    api_rows = _rows(false_allow=True)
    api_summary = _summary(api_rows)
    api_summary["api_success_rate"] = 1.0
    api = {
        "schema": "agoge.api-runtime-exam-result.v1",
        "exam_id": "api-exam",
        "exam_spec": {
            "competency_id": competency.competency_id,
            "competency_hash": competency.content_hash,
            "corpus_hash": corpus_hash,
            "split": "validation",
            "provider": "nous",
            "model": "example/free",
        },
        "summary": api_summary,
        "rows": api_rows,
    }
    local_path = tmp_path / "local.json"
    api_path = tmp_path / "api.json"
    local_path.write_text(json.dumps(local), encoding="utf-8")
    api_path.write_text(json.dumps(api), encoding="utf-8")

    result = run_runtime_tournament(
        competency_path=COMPETENCY, exam_paths=[api_path, local_path]
    )
    assert result["recommended_for_next_stage"].startswith("local:example/local@r1")
    assert result["hard_gate_pass_count"] == 1
    rejected = next(item for item in result["ranking"] if item["kind"] == "api-runtime")
    assert "false-allow-hard-gate" in rejected["hard_gate_reasons"]
    assert result["graduated"] is False
