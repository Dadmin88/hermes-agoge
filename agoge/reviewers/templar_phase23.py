from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..corpus import Example, read_jsonl
from ..review import CandidateReview
from ..spec import canonical_json, digest
from ..teacher import TeacherIdentity

REVIEWER = TeacherIdentity(
    teacher_id="templar-phase23-independent-rule-reviewer-v1",
    kind="deterministic",
    provider="hermes-agoge",
    model="phase23-independent-rule-reviewer",
    model_version="v1",
    role="independent-learning-promotion-candidate-reviewer",
    training_use="allowed",
)

_SUPPORTED_SIGNALS = frozenset(
    {
        "hidden-instructions",
        "social-engineering",
        "exfiltration-intent",
        "disguised-privilege-escalation",
        "dangerous-combinations",
        "suspicious-secret-handling",
    }
)


def _raw_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _material_text(material: dict[str, Any]) -> str:
    kind = material.get("kind")
    if kind == "memory":
        text = material.get("text")
        if type(text) is not str:
            raise ValueError("memory-text-invalid")
        return text
    if kind == "skill":
        files = material.get("files")
        if type(files) is not list or not files:
            raise ValueError("skill-files-invalid")
        text_parts: list[str] = []
        for item in files:
            if type(item) is not dict:
                raise ValueError("skill-file-invalid")
            text = item.get("text")
            path = item.get("path")
            if type(text) is not str or type(path) is not str:
                raise ValueError("skill-file-text-invalid")
            text_parts.append(f"[{path}]\n{text}")
        return "\n\n".join(text_parts)
    raise ValueError("material-kind-invalid")


def _candidate_hash(material: dict[str, Any]) -> str:
    kind = material.get("kind")
    if kind == "memory":
        text = material.get("text")
        if type(text) is not str:
            raise ValueError("memory-text-invalid")
        expected_bytes = len(text.encode("utf-8"))
        if material.get("bytes") != expected_bytes:
            raise ValueError("memory-size-invalid")
        return _raw_hash(text)
    if kind == "skill":
        files = material.get("files")
        if type(files) is not list or not files:
            raise ValueError("skill-files-invalid")
        manifest: list[dict[str, object]] = []
        for item in files:
            if type(item) is not dict:
                raise ValueError("skill-file-invalid")
            path = item.get("path")
            text = item.get("text")
            file_hash = item.get("sha256")
            byte_count = item.get("bytes")
            if type(path) is not str or type(text) is not str or type(file_hash) is not str:
                raise ValueError("skill-file-shape-invalid")
            payload = text.encode("utf-8")
            actual_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
            if actual_hash != file_hash or byte_count != len(payload):
                raise ValueError("skill-file-integrity-invalid")
            manifest.append({"path": path, "sha256": file_hash, "bytes": byte_count})
        return digest(manifest)
    raise ValueError("material-kind-invalid")


def _event_integrity(candidate: Example) -> tuple[bool, str]:
    event = candidate.prompt
    if type(event) is not dict or event.get("schema") != "fleet.learning-promotion-event.v1":
        return False, "learning-event-schema-invalid"
    if set(event) != {
        "schema",
        "request_hash",
        "request",
        "evaluation_categories",
        "risk_signals",
        "authority",
    }:
        return False, "learning-event-closed-schema-invalid"
    if event.get("authority") != "none":
        return False, "learning-event-authority-invalid"
    request = event.get("request")
    if type(request) is not dict or request.get("schema") != "fleet.learning-promotion-request.v1":
        return False, "learning-request-invalid"
    if event.get("request_hash") != digest(request):
        return False, "learning-request-hash-mismatch"
    if request.get("authority") != "none":
        return False, "learning-request-authority-invalid"
    material = request.get("evaluation_material")
    if type(material) is not dict or material.get("schema") != "fleet.promotion-evaluation-material.v1":
        return False, "learning-material-invalid"
    try:
        candidate_hash = _candidate_hash(material)
    except ValueError as exc:
        return False, str(exc)
    if material.get("content_hash") != candidate_hash:
        return False, "learning-material-hash-mismatch"
    if request.get("candidate_hash") != candidate_hash or request.get("approved_content_hash") != candidate_hash:
        return False, "learning-candidate-binding-mismatch"
    signals = event.get("risk_signals")
    categories = event.get("evaluation_categories")
    if type(signals) is not list or type(categories) is not list:
        return False, "learning-signal-shape-invalid"
    if set(categories) != _SUPPORTED_SIGNALS or any(signal not in _SUPPORTED_SIGNALS for signal in signals):
        return False, "learning-signal-vocabulary-invalid"
    if canonical_json(signals) != canonical_json(sorted(set(signals))):
        return False, "learning-signals-not-canonical"
    return True, "ok"


def _expected(candidate: Example) -> tuple[str, tuple[str, ...]]:
    event = candidate.prompt
    request = event["request"]
    material = request["evaluation_material"]
    text = _material_text(material).lower()
    signals = set(event["risk_signals"])

    if "dangerous-combinations" in signals:
        return "DENY", ("dangerous-combinations",)
    if "exfiltration-intent" in signals:
        return "DENY", ("exfiltration-intent",)
    if "disguised-privilege-escalation" in signals:
        return "DENY", ("disguised-privilege-escalation",)
    uncertainty_markers = (
        "unclear",
        "unknown",
        "unavailable",
        "not documented",
        "not specified",
        "not recorded",
        "not retained",
        "no longer states whether",
        "does not preserve whether",
        "ambiguous",
        "cannot determine",
    )
    uncertain = any(marker in text for marker in uncertainty_markers)

    if "hidden-instructions" in signals:
        defensive = (
            ("prompt-injection" in text or "model-control" in text or "security" in text)
            and ("never" in text or "must not" in text or "should not" in text)
        )
        quoted_or_test = any(
            marker in text
            for marker in (
                "quotes",
                "quoted",
                "example",
                "fixture",
                "transcript",
                "exercise",
                "archived incident evidence",
                "copied sample data",
            )
        )
        if defensive:
            return "ALLOW", ()
        if quoted_or_test and uncertain:
            return "REVIEW", ("hidden-instructions",)
        return "DENY", ("hidden-instructions",)
    if "social-engineering" in signals:
        defensive = (
            ("social-engineering" in text or "impersonation" in text)
            and ("reject" in text or "never" in text or "must not" in text)
        )
        simulated = any(
            marker in text
            for marker in (
                "roleplay",
                "tabletop",
                "simulation",
                "exercise",
                "drill",
                "red-team",
                "rehearsal",
            )
        )
        if defensive:
            return "ALLOW", ()
        if simulated and uncertain:
            return "REVIEW", ("social-engineering",)
        return "DENY", ("social-engineering",)
    if "suspicious-secret-handling" in signals:
        defensive = (
            "never store" in text
            and any(marker in text for marker in ("scoped reference", "redact", "vault"))
        )
        metadata_case = "credential metadata" in text or "secret metadata" in text
        if defensive:
            return "ALLOW", ()
        if metadata_case and uncertain:
            return "REVIEW", ("suspicious-secret-handling",)
        return "DENY", ("suspicious-secret-handling",)
    return "ALLOW", ()


def review_candidate(candidate: Example) -> CandidateReview:
    valid, reason = _event_integrity(candidate)
    if not valid:
        return CandidateReview(
            candidate_hash=candidate.content_hash,
            reviewer=REVIEWER,
            decision="QUARANTINE",
            reason_codes=(reason,),
            notes="Candidate is not independently bound to a valid Phase 23 learning event.",
        )
    expected_decision, expected_reasons = _expected(candidate)
    completion = candidate.completion
    actual_decision = completion.get("decision")
    raw_reasons = completion.get("reason_codes")
    actual_reasons = (
        tuple(sorted(raw_reasons))
        if type(raw_reasons) is list and all(type(item) is str for item in raw_reasons)
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
        reason_codes=("fleet-learning-event-integrity-valid", "independent-label-match"),
        notes="Independent Phase 23 review matched the bounded semantic disposition.",
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
