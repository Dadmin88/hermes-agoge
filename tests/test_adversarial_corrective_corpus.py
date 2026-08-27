from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from agoge.corpus import read_jsonl
from agoge.exam_bank import assert_no_registered_exam_overlap
from agoge.reviewers.templar_phase23 import review_candidate
from agoge.spec import digest

ROOT = Path(__file__).resolve().parents[1]
STUDENT_ROOT = ROOT / "students" / "templar"
CORPUS = STUDENT_ROOT / "corpus" / "templar-runtime-adversarial-corrective-v1.jsonl"
MANIFEST = STUDENT_ROOT / "corpus" / "templar-runtime-adversarial-corrective-v1.manifest.json"
CORRECTIVE_REQUEST_ID = "sha256:ee1696135ce1e695169348755a34f9ab47667f35a07bf6ded180cc69e7c1c262"
CORPUS_V2 = STUDENT_ROOT / "corpus" / "templar-runtime-adversarial-corrective-v2.jsonl"
MANIFEST_V2 = STUDENT_ROOT / "corpus" / "templar-runtime-adversarial-corrective-v2.manifest.json"
ANCHOR_REQUEST_ID = "sha256:957788cfed72aa36f0bc6f49884751538b0e0914e45534a2019334ad6f6e05ff"


def test_adversarial_corrective_corpus_matches_manifest_and_stays_exam_clean() -> None:
    rows = read_jsonl(CORPUS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert len(rows) == manifest["count"] == 522
    assert digest([row.to_dict() for row in rows]) == manifest["corpus_hash"]
    assert Counter(row.prompt["schema"] for row in rows) == manifest["event_schema_counts"]
    assert_no_registered_exam_overlap(student_root=STUDENT_ROOT, examples=rows)
    assert manifest["failure_cluster"]["failed_exam_body_reused"] is False


def test_adversarial_corrective_partition_is_reviewed_and_fleet_valid() -> None:
    rows = read_jsonl(CORPUS)
    corrective = [row for row in rows if row.provenance.get("request_id") == CORRECTIVE_REQUEST_ID]

    assert len(corrective) == 18
    assert Counter(row.completion["decision"] for row in corrective) == {"DENY": 12, "ALLOW": 6}
    assert all(row.competency == "prompt-injection" for row in corrective)
    assert all(row.prompt["schema"] == "fleet.learning-promotion-event.v1" for row in corrective)
    assert all(row.provenance["review_state"] == "accepted" for row in corrective)
    assert all(row.provenance["training_use"] == "allowed" for row in corrective)
    assert all(review_candidate(row).decision == "ACCEPT" for row in corrective)


def test_adversarial_corrective_v2_adds_only_novel_reviewed_anchor_cases() -> None:
    parent = read_jsonl(CORPUS)
    rows = read_jsonl(CORPUS_V2)
    manifest = json.loads(MANIFEST_V2.read_text(encoding="utf-8"))
    parent_prompt_hashes = {digest(row.prompt) for row in parent}
    anchor = [row for row in rows if row.provenance.get("request_id") == ANCHOR_REQUEST_ID]

    assert len(rows) == manifest["count"] == 543
    assert digest([row.to_dict() for row in rows]) == manifest["corpus_hash"]
    assert Counter(row.prompt["schema"] for row in rows) == manifest["event_schema_counts"]
    assert_no_registered_exam_overlap(student_root=STUDENT_ROOT, examples=rows)
    assert manifest["corrective_addition"]["raw_failed_exam_body_copied_to_training"] is False
    assert manifest["corrective_addition"]["novel_prompt_count"] == 21
    assert len(anchor) == 21
    assert not (parent_prompt_hashes & {digest(row.prompt) for row in anchor})
    assert Counter(
        (row.completion["decision"], tuple(row.completion["reason_codes"])) for row in anchor
    ) == {
        ("DENY", ("disguised-privilege-escalation",)): 15,
        ("REVIEW", ("hidden-instructions",)): 4,
        ("ALLOW", ()): 2,
    }
    assert all(row.provenance["review_state"] == "accepted" for row in anchor)
    assert all(row.provenance["training_use"] == "allowed" for row in anchor)
    assert all(review_candidate(row).decision == "ACCEPT" for row in anchor)
