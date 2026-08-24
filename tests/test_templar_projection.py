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


def test_security_projection_fails_closed_on_non_event() -> None:
    with pytest.raises(SpecError, match="does not support event schema"):
        project_templar_event({"schema": "not-fleet"})
