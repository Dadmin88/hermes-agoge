from __future__ import annotations

from pathlib import Path

from agoge.review import CandidateReview, promote_candidates
from agoge.teacher import (
    TeacherIdentity,
    TeacherRequest,
    TeacherResponse,
    response_to_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def _identity(teacher_id: str, *, training_use: str = "allowed") -> TeacherIdentity:
    return TeacherIdentity(
        teacher_id=teacher_id,
        kind="model",
        provider="test",
        model="test-model",
        model_version="v1",
        role="reviewer",
        training_use=training_use,
    )


def _candidate(*, training_use: str = "allowed"):
    request = TeacherRequest.from_student(STUDENT, competency="prompt-injection", count=1)
    response = TeacherResponse.from_dict(
        {
            "schema": "agoge.teacher-response.v1",
            "request_id": request.request_id,
            "teacher": _identity("generator", training_use=training_use).to_dict(),
            "items": [
                {
                    "prompt": {
                        "schema": "agoge.templar-training-projection.v1",
                        "facts": {"embedded_instruction": "ignore policy"},
                    },
                    "completion": {
                        "schema": "agoge.templar-model-output.v1",
                        "decision": "DENY",
                        "reason_codes": ["prompt-injection"],
                    },
                    "rationale": "Untrusted instruction attempts policy override.",
                    "basis": ["Fleet policy cannot be widened by content."],
                }
            ],
        }
    )
    return response_to_candidates(request, response)[0]


def _review(candidate_hash: str, reviewer_id: str, decision: str) -> CandidateReview:
    return CandidateReview(
        candidate_hash=candidate_hash,
        reviewer=_identity(reviewer_id),
        decision=decision,
        reason_codes=("contract-reviewed",),
        notes="",
    )


def test_allowed_candidate_requires_independent_acceptance() -> None:
    candidate = _candidate()
    own_review = _review(candidate.content_hash, "generator", "ACCEPT")
    accepted, rejected, quarantined = promote_candidates([candidate], [own_review])
    assert not accepted and not rejected
    assert quarantined[0].provenance["disposition_reason"] == "missing-independent-review"

    independent = _review(candidate.content_hash, "reviewer", "ACCEPT")
    accepted, rejected, quarantined = promote_candidates([candidate], [independent])
    assert len(accepted) == 1 and not rejected and not quarantined
    assert accepted[0].provenance["review_state"] == "accepted"
    assert accepted[0].provenance["candidate_hash"] == candidate.content_hash


def test_unknown_training_use_cannot_be_accepted() -> None:
    candidate = _candidate(training_use="unknown")
    review = _review(candidate.content_hash, "reviewer", "ACCEPT")
    accepted, rejected, quarantined = promote_candidates([candidate], [review])
    assert not accepted and not rejected
    assert quarantined[0].provenance["disposition_reason"] == "teacher-training-use-not-allowed"


def test_reject_beats_accept_and_disagreement_quarantines() -> None:
    candidate = _candidate()
    accept = _review(candidate.content_hash, "reviewer-a", "ACCEPT")
    reject = _review(candidate.content_hash, "reviewer-b", "REJECT")
    accepted, rejected, quarantined = promote_candidates([candidate], [accept, reject])
    assert not accepted and len(rejected) == 1 and not quarantined

    quarantine = _review(candidate.content_hash, "reviewer-b", "QUARANTINE")
    accepted, rejected, quarantined = promote_candidates([candidate], [accept, quarantine])
    assert not accepted and not rejected and len(quarantined) == 1
