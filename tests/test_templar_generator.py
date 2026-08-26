from __future__ import annotations

from pathlib import Path

import pytest

from agoge.generators.templar import generate_response
from agoge.spec import SpecError
from agoge.teacher import TeacherRequest, response_to_candidates

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def test_deterministic_generator_covers_every_templar_competency() -> None:
    competencies = (
        "authority-boundaries",
        "prompt-injection",
        "secret-handling",
        "cross-principal-isolation",
        "skill-memory-poisoning",
        "capability-combinations",
        "benign-nonoverblocking",
        "uncertainty-review",
        "architecture-ownership",
    )
    for competency in competencies:
        request = TeacherRequest.from_student(STUDENT, competency=competency, count=3)
        response = generate_response(request)
        assert response.teacher.kind == "deterministic"
        assert response.teacher.training_use == "allowed"
        candidates = response_to_candidates(request, response)
        assert len(candidates) == 3
        assert all(item.competency == competency for item in candidates)
        assert all(item.provenance["review_state"] == "generated-unreviewed" for item in candidates)


def test_prompt_injection_generator_includes_allow_deny_and_review() -> None:
    request = TeacherRequest.from_student(STUDENT, competency="prompt-injection", count=7)
    response = generate_response(request)
    decisions = {item.completion["decision"] for item in response.items}
    assert decisions == {"ALLOW", "DENY", "REVIEW"}


def test_deterministic_generator_refuses_duplicate_padding() -> None:
    request = TeacherRequest.from_student(STUDENT, competency="benign-nonoverblocking", count=100)
    with pytest.raises(SpecError, match="distinct cases"):
        generate_response(request)
