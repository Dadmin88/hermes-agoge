from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "students" / "templar" / "runtime-competencies.json"
SNAPSHOT = ROOT / "students" / "templar" / "fleet-contract.json"


def test_runtime_competency_map_binds_pinned_contract_and_supported_inputs() -> None:
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert mapping["fleet_revision"] == snapshot["fleet_revision"]
    assert mapping["fleet_contract_snapshot_hash"] == snapshot["snapshot_hash"]
    supported = snapshot["modules"]["hermes_fleet/templar.py"]["constants"][
        "_SUPPORTED_EVENT_SCHEMAS"
    ]
    assert mapping["model_input"]["supported_schemas"] == supported
    ids = [item["id"] for item in mapping["competencies"]]
    assert len(ids) == len(set(ids)) == 9
    assert (
        "raw user prompt merely because Templar is evaluating security"
        in mapping["unavailable_or_forbidden_model_inputs"]
    )
