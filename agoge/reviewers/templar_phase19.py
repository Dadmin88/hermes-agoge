from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..corpus import Example, read_jsonl
from ..review import CandidateReview
from ..spec import digest
from ..teacher import TeacherIdentity

REVIEWER = TeacherIdentity(
    teacher_id="templar-phase19-independent-rule-reviewer-v1",
    kind="deterministic",
    provider="hermes-agoge",
    model="phase19-independent-rule-reviewer",
    model_version="v1",
    role="independent-fleet-event-label-reviewer",
    training_use="allowed",
)

_EVENT_KEYS = {
    "schema",
    "request_hash",
    "request",
    "memory_skill_risks",
    "secret_interceptions",
    "policy_mismatches",
    "quarantine_signals",
}


def _event_integrity(candidate: Example) -> tuple[bool, str]:
    prompt = candidate.prompt
    if set(prompt) != _EVENT_KEYS or prompt.get("schema") != "fleet.security-event.v1":
        return False, "event-shape-invalid"
    request = prompt.get("request")
    if type(request) is not dict or request.get("schema") != "fleet.security-request.v1":
        return False, "request-shape-invalid"
    if prompt.get("request_hash") != digest(request):
        return False, "request-hash-invalid"
    event_hash = digest(prompt)
    basis_refs = candidate.provenance.get("basis_refs")
    if type(basis_refs) is not list or not any(
        type(item) is str
        and item == f"Fleet-validated fleet.security-event.v1 {event_hash}"
        for item in basis_refs
    ):
        return False, "fleet-oracle-binding-missing"
    mismatches = prompt.get("policy_mismatches")
    if type(mismatches) is not list:
        return False, "phase19-policy-mismatch-shape-invalid"
    return True, "event-integrity-valid"


def _risk_rows(event: dict[str, Any]) -> list[dict[str, Any]]:
    value = event.get("memory_skill_risks")
    return value if type(value) is list else []


def _secret_actions(event: dict[str, Any]) -> set[str]:
    value = event.get("secret_interceptions")
    if type(value) is not list:
        return set()
    return {
        row.get("action")
        for row in value
        if type(row) is dict and type(row.get("action")) is str
    }


def _quarantine_rows(event: dict[str, Any]) -> list[dict[str, Any]]:
    value = event.get("quarantine_signals")
    return value if type(value) is list else []


def _has_signal(event: dict[str, Any], signal: str, *, levels: set[str] | None = None) -> bool:
    for row in _risk_rows(event):
        if type(row) is not dict:
            continue
        signals = row.get("signal_codes")
        level = row.get("risk_level")
        if type(signals) is list and signal in signals and (
            levels is None or level in levels
        ):
            return True
    return False


def _quarantine_state(event: dict[str, Any], state: str) -> bool:
    return any(
        type(row) is dict and row.get("state") == state
        for row in _quarantine_rows(event)
    )


def _verified_candidate(event: dict[str, Any]) -> bool:
    return any(
        type(row) is dict
        and row.get("state") == "verification-ready"
        and row.get("verification_state") == "verified"
        and type(row.get("verification_digest")) is str
        for row in _quarantine_rows(event)
    )


def _expected(candidate: Example) -> tuple[str, tuple[str, ...]]:
    """Derive one canonical disposition from observable Fleet facts only.

    Curriculum competency is intentionally ignored. Two semantically equivalent
    security events must receive the same label even if they were generated to
    exercise different teaching objectives.
    """

    event = candidate.prompt
    high_authority = _has_signal(
        event, "authority-manipulation", levels={"high", "critical"}
    )
    medium_stored = _has_signal(event, "stored-instruction", levels={"medium"})
    medium_network = _has_signal(event, "network-requirement", levels={"medium"})
    actions = _secret_actions(event)
    needs_review = _quarantine_state(event, "needs-review")

    deny_reasons: set[str] = set()
    if high_authority:
        deny_reasons.add("authority-manipulation")
    if "failed-closed" in actions:
        deny_reasons.add("secret-handling-failed-closed")
    if "blocked" in actions:
        deny_reasons.add("secret-handling-blocked")
    if deny_reasons:
        return "DENY", tuple(sorted(deny_reasons))

    review_reasons: set[str] = set()
    if medium_stored:
        review_reasons.add("prompt-injection-uncertain")
    if needs_review and medium_network:
        review_reasons.add("skill-risk-needs-review")
    if review_reasons:
        return "REVIEW", tuple(sorted(review_reasons))

    return "ALLOW", ()


def review_candidate(candidate: Example) -> CandidateReview:
    valid, integrity_reason = _event_integrity(candidate)
    if not valid:
        return CandidateReview(
            candidate_hash=candidate.content_hash,
            reviewer=REVIEWER,
            decision="QUARANTINE",
            reason_codes=(integrity_reason,),
            notes="Candidate could not be independently bound to a valid pinned Fleet event.",
        )

    expected_decision, expected_reasons = _expected(candidate)
    completion = candidate.completion
    actual_decision = completion.get("decision")
    actual_reasons_value = completion.get("reason_codes")
    actual_reasons = (
        tuple(sorted(actual_reasons_value))
        if type(actual_reasons_value) is list
        and all(type(item) is str for item in actual_reasons_value)
        else ()
    )
    if actual_decision != expected_decision or actual_reasons != expected_reasons:
        return CandidateReview(
            candidate_hash=candidate.content_hash,
            reviewer=REVIEWER,
            decision="REJECT",
            reason_codes=("label-mismatch",),
            notes=json.dumps(
                {
                    "expected_decision": expected_decision,
                    "expected_reason_codes": list(expected_reasons),
                    "actual_decision": actual_decision,
                    "actual_reason_codes": list(actual_reasons),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    return CandidateReview(
        candidate_hash=candidate.content_hash,
        reviewer=REVIEWER,
        decision="ACCEPT",
        reason_codes=("fleet-event-integrity-valid", "independent-label-match"),
        notes="Independent Phase 19 rule review matched the candidate disposition and reason codes.",
    )


def review_file(candidates_path: Path, out_path: Path) -> dict[str, int]:
    candidates = read_jsonl(candidates_path)
    reviews = [review_candidate(candidate) for candidate in candidates]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for review in reviews:
            handle.write(json.dumps(review.to_dict(), sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    counts = {"ACCEPT": 0, "REJECT": 0, "QUARANTINE": 0}
    for review in reviews:
        counts[review.decision] += 1
    return counts
