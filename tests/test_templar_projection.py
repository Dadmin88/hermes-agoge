from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.spec import SpecError, canonical_json
from agoge.templar_projection import project_templar_event

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "students" / "templar" / "corpus" / "phase19-security-events-v1.jsonl"


def _first_event() -> dict[str, object]:
    row = json.loads(CORPUS.read_text(encoding="utf-8").splitlines()[0])
    return row["prompt"]


def test_security_projection_is_deterministic_and_identity_free() -> None:
    event = _first_event()
    first = project_templar_event(event)
    second = project_templar_event(json.loads(json.dumps(event)))
    assert canonical_json(first) == canonical_json(second)
    payload = canonical_json(first).decode("utf-8")
    assert "sha256:" not in payload
    assert first["schema"] == "agoge.templar-security-projection.v1"
    assert first["source_schema"] == "fleet.security-event.v1"


def test_security_projection_preserves_security_signal_families() -> None:
    projected = project_templar_event(_first_event())
    assert set(projected) == {
        "schema",
        "source_schema",
        "request",
        "memory_skill_risks",
        "secret_interceptions",
        "policy_mismatches",
        "quarantine_signals",
    }
    request = projected["request"]
    assert isinstance(request, dict)
    assert "resources" in request
    assert "network" in request


def test_learning_projection_is_identity_free_and_preserves_bounded_material() -> None:
    corpus = ROOT / "students" / "templar" / "corpus" / "phase23-learning-events-v1.jsonl"
    row = json.loads(corpus.read_text(encoding="utf-8").splitlines()[0])
    projected = project_templar_event(row["prompt"])
    payload = canonical_json(projected).decode("utf-8")
    assert "sha256:" not in payload
    assert projected["schema"] == "agoge.templar-learning-promotion-projection.v1"
    assert projected["source_schema"] == "fleet.learning-promotion-event.v1"
    material = projected["evaluation_material"]
    assert isinstance(material, dict)
    assert material["kind"] in {"memory", "skill"}
    assert projected["risk_signals"] == sorted(projected["risk_signals"])


def test_learning_projection_accepts_current_fleet_source_execution_id_without_changing_model_input() -> (
    None
):
    corpus = ROOT / "students" / "templar" / "corpus" / "phase23-learning-events-v1.jsonl"
    row = json.loads(corpus.read_text(encoding="utf-8").splitlines()[0])
    legacy = row["prompt"]
    current = json.loads(json.dumps(legacy))
    current["request"]["source_execution_id"] = "execution-current-fleet"

    assert canonical_json(project_templar_event(current)) == canonical_json(
        project_templar_event(legacy)
    )


def test_learning_projection_rejects_invalid_source_execution_id() -> None:
    corpus = ROOT / "students" / "templar" / "corpus" / "phase23-learning-events-v1.jsonl"
    row = json.loads(corpus.read_text(encoding="utf-8").splitlines()[0])
    current = json.loads(json.dumps(row["prompt"]))
    current["request"]["source_execution_id"] = ""

    with pytest.raises(SpecError, match="source execution id"):
        project_templar_event(current)


def test_security_projection_fails_closed_on_non_event() -> None:
    with pytest.raises(SpecError, match="does not support event schema"):
        project_templar_event({"schema": "not-fleet"})
