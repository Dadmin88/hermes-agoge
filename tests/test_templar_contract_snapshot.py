from __future__ import annotations

import json
from pathlib import Path

from agoge.fleet_snapshot import fleet_revision_from_student
from agoge.spec import StudentSpec, digest

ROOT = Path(__file__).resolve().parents[1]
STUDENT_PATH = ROOT / "students" / "templar" / "student.json"
SNAPSHOT_PATH = ROOT / "students" / "templar" / "fleet-contract.json"
GOLDEN_PATH = ROOT / "students" / "templar" / "fixtures" / "security-event-golden.json"


def test_committed_fleet_snapshot_binds_current_student_and_revision() -> None:
    student = StudentSpec.load(STUDENT_PATH)
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot_hash = snapshot.pop("snapshot_hash")
    assert snapshot_hash == digest(snapshot)
    assert snapshot["student_hash"] == student.content_hash
    assert snapshot["fleet_revision"] == fleet_revision_from_student(student)
    supported = snapshot["modules"]["hermes_fleet/templar.py"]["constants"]
    assert supported["_SUPPORTED_EVENT_SCHEMAS"] == [
        "fleet.learning-promotion-event.v1",
        "fleet.security-event.v1",
    ]


def test_golden_security_event_is_one_supported_runtime_shape() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    supported = snapshot["modules"]["hermes_fleet/templar.py"]["constants"][
        "_SUPPORTED_EVENT_SCHEMAS"
    ]
    assert golden["fleet_revision"] == snapshot["fleet_revision"]
    assert golden["event_schema"] in supported
    assert golden["document"]["schema"] == "fleet.security-event.v1"
    assert golden["document"]["request_hash"] == golden["request_hash"]
    assert golden["event_hash"] == "sha256:" + golden["document_sha256"]
