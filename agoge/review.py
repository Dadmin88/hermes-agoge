from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import Example
from .spec import SpecError, digest
from .teacher import TeacherIdentity

REVIEW_DECISIONS = frozenset({"ACCEPT", "REJECT", "QUARANTINE"})


def _exact(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SpecError(f"{label} has an invalid closed schema")
    return value


def _codes(value: object) -> tuple[str, ...]:
    if (
        type(value) is not list
        or not value
        or not all(type(item) is str and item.strip() for item in value)
    ):
        raise SpecError("review reason_codes must be a non-empty string array")
    if len(value) != len(set(value)):
        raise SpecError("review reason_codes must be unique")
    return tuple(sorted(value))


@dataclass(frozen=True, slots=True)
class CandidateReview:
    candidate_hash: str
    reviewer: TeacherIdentity
    decision: str
    reason_codes: tuple[str, ...]
    notes: str

    def __post_init__(self) -> None:
        if type(self.candidate_hash) is not str or not self.candidate_hash.startswith("sha256:"):
            raise SpecError("review candidate_hash is invalid")
        if self.decision not in REVIEW_DECISIONS:
            raise SpecError("review decision is unsupported")
        if not self.reason_codes:
            raise SpecError("review reason_codes cannot be empty")
        if type(self.notes) is not str:
            raise SpecError("review notes must be a string")

    @classmethod
    def from_dict(cls, value: object) -> CandidateReview:
        item = _exact(
            value,
            {
                "schema",
                "review_id",
                "candidate_hash",
                "reviewer",
                "decision",
                "reason_codes",
                "notes",
            },
            "candidate review",
        )
        if item["schema"] != "agoge.candidate-review.v1":
            raise SpecError("candidate review schema is unsupported")
        review = cls(
            candidate_hash=item["candidate_hash"],
            reviewer=TeacherIdentity.from_dict(item["reviewer"]),
            decision=item["decision"],
            reason_codes=_codes(item["reason_codes"]),
            notes=item["notes"],
        )
        if item["review_id"] != review.review_id:
            raise SpecError("candidate review identity does not match its content")
        return review

    def document(self) -> dict[str, Any]:
        return {
            "schema": "agoge.candidate-review.v1",
            "candidate_hash": self.candidate_hash,
            "reviewer": self.reviewer.to_dict(),
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
        }

    @property
    def review_id(self) -> str:
        return digest(self.document())

    def to_dict(self) -> dict[str, Any]:
        return {**self.document(), "review_id": self.review_id}


def load_reviews(path: Path) -> list[CandidateReview]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SpecError(f"cannot read reviews {path}: {exc}") from exc
    reviews: list[CandidateReview] = []
    ids: set[str] = set()
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SpecError(f"invalid review JSONL at {path}:{line_no}: {exc}") from exc
        review = CandidateReview.from_dict(value)
        if review.review_id in ids:
            raise SpecError(f"duplicate review_id {review.review_id!r}")
        ids.add(review.review_id)
        reviews.append(review)
    if not reviews:
        raise SpecError(f"review set is empty: {path}")
    return reviews


def promote_candidates(
    candidates: list[Example], reviews: list[CandidateReview]
) -> tuple[list[Example], list[Example], list[Example]]:
    by_hash = {candidate.content_hash: candidate for candidate in candidates}
    if len(by_hash) != len(candidates):
        raise SpecError("candidate set contains duplicate content hashes")

    review_by_candidate: dict[str, list[CandidateReview]] = {}
    for review in reviews:
        if review.candidate_hash not in by_hash:
            raise SpecError("review references an unknown candidate")
        review_by_candidate.setdefault(review.candidate_hash, []).append(review)

    accepted: list[Example] = []
    rejected: list[Example] = []
    quarantined: list[Example] = []
    for candidate in candidates:
        candidate_reviews = review_by_candidate.get(candidate.content_hash, [])
        source_teacher = candidate.provenance.get("teacher")
        source_teacher_id = (
            source_teacher.get("teacher_id") if type(source_teacher) is dict else None
        )
        independent_reviews = [
            review
            for review in candidate_reviews
            if review.reviewer.teacher_id != source_teacher_id
        ]
        if not independent_reviews:
            quarantined.append(
                _with_review_state(
                    candidate,
                    "quarantined",
                    candidate_reviews,
                    "missing-independent-review",
                )
            )
            continue

        decisions = {review.decision for review in independent_reviews}
        if "REJECT" in decisions:
            rejected.append(
                _with_review_state(
                    candidate,
                    "rejected",
                    independent_reviews,
                    "independent-reject",
                )
            )
            continue
        if "QUARANTINE" in decisions or decisions != {"ACCEPT"}:
            quarantined.append(
                _with_review_state(
                    candidate,
                    "quarantined",
                    independent_reviews,
                    "review-disagreement-or-quarantine",
                )
            )
            continue

        training_use = candidate.provenance.get("training_use")
        if training_use != "allowed":
            quarantined.append(
                _with_review_state(
                    candidate,
                    "quarantined",
                    independent_reviews,
                    "teacher-training-use-not-allowed",
                )
            )
            continue
        accepted.append(
            _with_review_state(
                candidate,
                "accepted",
                independent_reviews,
                "independent-accept",
            )
        )
    return accepted, rejected, quarantined


def _with_review_state(
    candidate: Example,
    state: str,
    reviews: list[CandidateReview],
    disposition_reason: str,
) -> Example:
    provenance = dict(candidate.provenance)
    provenance["review_state"] = state
    provenance["disposition_reason"] = disposition_reason
    provenance["reviews"] = [review.to_dict() for review in reviews]
    provenance["candidate_hash"] = candidate.content_hash
    return Example(
        example_id=candidate.example_id,
        competency=candidate.competency,
        prompt=candidate.prompt,
        completion=candidate.completion,
        provenance=provenance,
    )
