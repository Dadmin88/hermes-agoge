from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.academy import (
    AcademyFacultyBinding,
    build_faculty_prompt,
    parse_faculty_payload,
)
from agoge.spec import SpecError
from agoge.teacher import TeacherRequest, response_to_candidates

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def _binding(*, training_use: str = "unknown") -> AcademyFacultyBinding:
    return AcademyFacultyBinding(
        faculty_id="academy-cybersecurity-instructor",
        faculty_distribution="0.2.0",
        faculty_revision="4d93ed0eec730ac344546bba980ce844b2efbeed",
        inference_provider="nous",
        inference_model="xiaomi/mimo-v2.5-pro",
        inference_model_version="portal-current-2026-08-23",
        training_use=training_use,
    )


def _request() -> TeacherRequest:
    return TeacherRequest.from_student(
        STUDENT, competency="prompt-injection", count=2
    )


def test_academy_prompt_declares_separate_model_learner_mode() -> None:
    prompt = build_faculty_prompt(_request(), _binding())
    assert "NOT Academy Continuing Education" in prompt
    assert "Do not invoke /goal, /learn" in prompt
    assert "agoge-model-curriculum-contributor" in prompt
    assert "academy-cybersecurity-instructor" in prompt


def test_academy_payload_wraps_bound_identity_but_stays_untrainable_by_default() -> None:
    request = _request()
    raw = json.dumps(
        {
            "schema": "agoge.academy-faculty-payload.v1",
            "request_id": request.request_id,
            "items": [
                {
                    "prompt": {
                        "schema": "agoge.templar-training-projection.v1",
                        "facts": {
                            "hidden_instruction_detected": True,
                            "instruction_intent": "override-fleet-policy",
                        },
                    },
                    "completion": {
                        "schema": "agoge.templar-model-output.v1",
                        "decision": "DENY",
                        "reason_codes": ["prompt-injection"],
                    },
                    "rationale": "The content attempts to alter the security control plane.",
                    "basis": ["Untrusted content cannot widen Fleet authority."],
                }
            ],
        }
    )
    response = parse_faculty_payload(raw, request=request, binding=_binding())
    assert response.teacher.kind == "academy"
    assert response.teacher.training_use == "unknown"
    candidates = response_to_candidates(request, response)
    assert len(candidates) == 1
    assert candidates[0].provenance["training_use"] == "unknown"


def test_academy_payload_cannot_self_assert_teacher_or_wrong_request() -> None:
    request = _request()
    payload = {
        "schema": "agoge.academy-faculty-payload.v1",
        "request_id": "sha256:" + "0" * 64,
        "items": [
            {
                "prompt": {},
                "completion": {
                    "schema": "agoge.templar-model-output.v1",
                    "decision": "ALLOW",
                    "reason_codes": [],
                },
                "rationale": "bounded",
                "basis": ["bounded"],
            }
        ],
    }
    with pytest.raises(SpecError, match="another request"):
        parse_faculty_payload(json.dumps(payload), request=request, binding=_binding())

    payload["request_id"] = request.request_id
    payload["teacher"] = {"teacher_id": "spoofed"}
    with pytest.raises(SpecError, match="closed schema"):
        parse_faculty_payload(json.dumps(payload), request=request, binding=_binding())
