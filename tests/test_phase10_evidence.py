from __future__ import annotations

import json
from pathlib import Path

from agoge.spec import digest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "students" / "templar" / "evidence" / "phase10-adversarial-school-v1.json"


def test_phase10_evidence_manifest_is_content_addressed_and_non_graduating() -> None:
    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert value["schema"] == "agoge.templar-phase10-proof.v1"
    assert value["student_id"] == "templar-v1"
    assert value["phase"] == 10
    expected_hash = value["proof_hash"]
    unsigned = dict(value)
    del unsigned["proof_hash"]
    assert digest(unsigned) == expected_hash
    assert value["status"] == "PHASE10_VALIDATED_CANDIDATE_NOT_GRADUATED"


def test_phase10_selected_candidate_preserves_hard_safety_evidence() -> None:
    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    winner = value["winner"]
    assert winner["training"] == {
        "balance_mode": "class",
        "learning_rate": 1e-05,
        "seed": 41,
        "steps": 5,
    }
    assert winner["generated_adversarial"]["exact"] == "1008/1008"
    assert winner["fresh_transfer"]["exact"] == "34/34"
    assert winner["external_hidden"]["exact"] == "18/20"
    for key in ("generated_adversarial", "fresh_transfer", "external_hidden"):
        assert winner[key]["false_allow"] == 0
        assert winner[key]["false_deny"] == 0
    assert winner["external_hidden"]["body_persisted_on_katana"] is False
    assert value["failure_cluster"]["raw_prompt_body_reused"] is False


def test_phase10_rejected_strategies_are_preserved_as_evidence() -> None:
    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    trials = value["strategy_trials"]
    assert [trial["status"] for trial in trials] == [
        "REJECTED",
        "REJECTED",
        "REJECTED",
        "SELECTED_PHASE10_CANDIDATE",
    ]
    assert [trial["fresh_false_allow"] for trial in trials] == [1, 1, 1, 0]
