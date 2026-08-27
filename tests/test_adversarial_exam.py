from __future__ import annotations

from pathlib import Path

import pytest

from agoge.adversarial import AdversarialCandidate, mutate_example
from agoge.adversarial_exam import (
    _group_summaries,
    _validate_candidate_dispositions,
    build_corrective_teacher_request,
    cluster_adversarial_failures,
)
from agoge.corpus import Example, read_jsonl
from agoge.dispositions import build_disposition_registry
from agoge.spec import SpecError

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = ROOT / "students" / "templar" / "corpus" / "templar-runtime-foundation-v1.jsonl"


def _learning_example() -> Example:
    for example in read_jsonl(FOUNDATION):
        if example.prompt.get("schema") == "fleet.learning-promotion-event.v1":
            return example
    raise AssertionError("foundation corpus has no learning-promotion event")


def _registry() -> dict[str, object]:
    return build_disposition_registry(read_jsonl(FOUNDATION), student_id="templar")


def test_adversarial_candidate_disposition_is_checked_against_student_registry() -> None:
    candidate = mutate_example(_learning_example(), family="irrelevant-noise")
    _validate_candidate_dispositions([candidate], _registry())
    invalid = AdversarialCandidate(
        candidate_id=candidate.candidate_id,
        competency=candidate.competency,
        prompt=candidate.prompt,
        expected={
            "schema": "agoge.templar-model-output.v1",
            "decision": "DENY",
            "reason_codes": ["not-a-real-disposition"],
        },
        provenance=candidate.provenance,
    )
    with pytest.raises(SpecError, match="absent from the Student registry"):
        _validate_candidate_dispositions([invalid], _registry())


def test_adversarial_exam_rejects_candidate_promoted_by_metadata_only() -> None:
    candidate = mutate_example(_learning_example(), family="irrelevant-noise")
    provenance = dict(candidate.provenance)
    provenance["training_use"] = "allowed"
    tampered = AdversarialCandidate(
        candidate_id=candidate.candidate_id,
        competency=candidate.competency,
        prompt=candidate.prompt,
        expected=candidate.expected,
        provenance=provenance,
    )
    with pytest.raises(SpecError, match="invalid training-use state"):
        _validate_candidate_dispositions([tampered], _registry())


def test_adversarial_exam_group_summaries_preserve_family_failures() -> None:
    rows = [
        {
            "mutation_family": "irrelevant-noise",
            "event_schema": "fleet.learning-promotion-event.v1",
            "expected": {"decision": "DENY", "reason_codes": ["hidden-instructions"]},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "ALLOW",
                "reason_codes": [],
            },
        },
        {
            "mutation_family": "unordered-list-permutation",
            "event_schema": "fleet.security-event.v1",
            "expected": {"decision": "ALLOW", "reason_codes": []},
            "actual": {
                "json_valid": True,
                "contract_valid": True,
                "decision": "ALLOW",
                "reason_codes": [],
            },
        },
    ]
    grouped = _group_summaries(rows, "mutation_family")
    assert grouped["irrelevant-noise"]["false_allow"] == 1
    assert grouped["unordered-list-permutation"]["exact_match"] == 1


def test_failure_clustering_omits_prompt_bodies_and_preserves_neural_regression() -> None:
    result = {
        "schema": "agoge.adversarial-exam-result.v1",
        "rows": [
            {
                "example_hash": "sha256:candidate",
                "source_example_hash": "sha256:source",
                "competency": "prompt-injection",
                "event_schema": "fleet.learning-promotion-event.v1",
                "mutation_family": "irrelevant-noise",
                "expected": {"decision": "DENY", "reason_codes": ["hidden-instructions"]},
                "actual": {
                    "decision": "REVIEW",
                    "reason_codes": ["hidden-instructions"],
                    "neural_decision": "ALLOW",
                    "calibration": {"applied": True},
                },
            }
        ],
    }
    clusters = cluster_adversarial_failures(result)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["safety_critical"] is True
    assert cluster["observed_decision"] == "REVIEW"
    assert cluster["observed_neural_decision"] == "ALLOW"
    assert cluster["calibration_applied_count"] == 1
    assert cluster["raw_prompt_bodies_included"] is False
    assert "prompt" not in cluster
    assert str(cluster["cluster_id"]).startswith("sha256:")


def test_corrective_teacher_request_carries_only_failure_family_metadata() -> None:
    cluster = {
        "schema": "agoge.adversarial-failure-cluster.v1",
        "cluster_id": "sha256:cluster",
        "competency": "prompt-injection",
        "event_schema": "fleet.learning-promotion-event.v1",
        "mutation_family": "irrelevant-noise",
        "expected_decision": "DENY",
        "expected_reason_codes": ["hidden-instructions"],
        "observed_decision": "REVIEW",
        "observed_neural_decision": "ALLOW",
        "safety_critical": True,
    }
    request = build_corrective_teacher_request(
        student_path=ROOT / "students" / "templar" / "student.json",
        cluster=cluster,
        count=12,
    )
    focus = request.constraints["adversarial_focus"]
    assert focus["mutation_family"] == "irrelevant-noise"
    assert focus["observed_neural_decision"] == "ALLOW"
    assert "prompt" not in focus
    assert request.count == 12
    assert any("Do not reproduce" in rule for rule in request.constraints["rules"])
