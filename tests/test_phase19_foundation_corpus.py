from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

from agoge.corpus import read_jsonl
from agoge.reviewers.templar_phase19 import review_candidate
from agoge.spec import digest

ROOT = Path(__file__).resolve().parents[1]
STUDENT_DIR = ROOT / "students" / "templar"
CORPUS = STUDENT_DIR / "corpus" / "phase19-security-events-v1.jsonl"
MANIFEST = STUDENT_DIR / "corpus" / "phase19-security-events-v1.manifest.json"


def test_phase19_foundation_corpus_is_accepted_fleet_shaped_and_content_addressed() -> None:
    examples = read_jsonl(CORPUS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(examples) == manifest["count"] == 252
    assert manifest["corpus_hash"] == digest([item.to_dict() for item in examples])
    assert manifest["status"] == "accepted-foundation-curriculum-not-graduation-exam"
    counts = Counter(item.competency for item in examples)
    assert set(counts.values()) == {36}
    assert set(counts) == {
        "authority-boundaries",
        "prompt-injection",
        "secret-handling",
        "skill-memory-poisoning",
        "capability-combinations",
        "benign-nonoverblocking",
        "uncertainty-review",
    }
    assert {item.completion["decision"] for item in examples} == {
        "ALLOW",
        "DENY",
        "REVIEW",
    }
    ids: set[str] = set()
    hashes: set[str] = set()
    for item in examples:
        assert item.example_id not in ids
        ids.add(item.example_id)
        assert item.content_hash not in hashes
        hashes.add(item.content_hash)
        assert item.prompt["schema"] == "fleet.security-event.v1"
        assert item.prompt["request"]["schema"] == "fleet.security-request.v1"
        assert item.prompt["request_hash"] == digest(item.prompt["request"])
        event_hash = digest(item.prompt)
        assert any(
            ref == f"Fleet-validated fleet.security-event.v1 {event_hash}"
            for ref in item.provenance["basis_refs"]
        )
        assert item.prompt["policy_mismatches"] == []
        assert item.prompt["request"]["recipe"]["workflow_step_id"] == "templar-evaluation"
        assert item.competency not in json.dumps(item.prompt, sort_keys=True)
        assert item.provenance["review_state"] == "accepted"
        assert item.provenance["candidate_hash"].startswith("sha256:")
        reviewer_ids = {review["reviewer"]["teacher_id"] for review in item.provenance["reviews"]}
        assert reviewer_ids == {"templar-phase19-independent-rule-reviewer-v1"}
        assert item.provenance["teacher"]["teacher_id"] != next(iter(reviewer_ids))


def test_phase19_independent_reviewer_rejects_a_tampered_label() -> None:
    example = read_jsonl(CORPUS)[0]
    wrong = "ALLOW" if example.completion["decision"] != "ALLOW" else "DENY"
    tampered = replace(
        example,
        completion={
            "schema": "agoge.templar-model-output.v1",
            "decision": wrong,
            "reason_codes": [],
        },
    )
    review = review_candidate(tampered)
    assert review.decision == "REJECT"
    assert review.reason_codes == ("label-mismatch",)
