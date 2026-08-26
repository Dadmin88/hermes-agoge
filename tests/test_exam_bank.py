from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.corpus import Example, read_jsonl, write_jsonl
from agoge.exam_bank import (
    ExamCase,
    assert_no_registered_exam_overlap,
    load_exam_manifest,
    seal_exam_bank,
    verify_exam_body,
    write_exam_cases,
)
from agoge.spec import SpecError

ROOT = Path(__file__).resolve().parents[1]
COMPETENCY = ROOT / "students" / "templar" / "competency.json"


def _case(case_id: str, prompt: dict[str, object]) -> ExamCase:
    return ExamCase(
        case_id=case_id,
        competency="benign-nonoverblocking",
        prompt=prompt,
        expected={
            "schema": "agoge.templar-model-output.v1",
            "decision": "ALLOW",
            "reason_codes": [],
        },
        provenance={"source": "test", "reviewed": True},
    )


def _example(example_id: str, prompt: dict[str, object]) -> Example:
    return Example(
        example_id=example_id,
        competency="benign-nonoverblocking",
        prompt=prompt,
        completion={
            "schema": "agoge.templar-model-output.v1",
            "decision": "ALLOW",
            "reason_codes": [],
        },
        provenance={"source": "test"},
    )


def test_exam_bank_seals_content_and_cannot_be_read_as_training_corpus(
    tmp_path: Path,
) -> None:
    body = tmp_path / "bank.jsonl"
    cases = [
        _case("fresh-1", {"schema": "fleet.security-event.v1", "facts": {"x": 1}}),
        _case(
            "fresh-2",
            {"schema": "fleet.learning-promotion-event.v1", "facts": {"x": 2}},
        ),
    ]
    write_exam_cases(body, cases)
    manifest = seal_exam_bank(
        competency_path=COMPETENCY,
        body_path=body,
        bank_id="templar-fresh-test",
        kind="fresh-transfer",
        visibility="reviewable",
    )
    manifest_path = tmp_path / "bank.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_exam_manifest(manifest_path)
    verify_exam_body(loaded, cases)
    assert loaded["case_count"] == 2
    assert loaded["training_forbidden"] is True
    assert loaded["immutable"] is True
    assert len(loaded["prompt_hashes"]) == 2
    with pytest.raises(SpecError, match="corpus example has an invalid closed schema"):
        read_jsonl(body)


def test_exam_bank_seal_rejects_training_overlap(tmp_path: Path) -> None:
    prompt = {"schema": "fleet.security-event.v1", "facts": {"same": True}}
    body = tmp_path / "bank.jsonl"
    write_exam_cases(body, [_case("fresh-overlap", prompt)])
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [_example("train-overlap", prompt)])
    with pytest.raises(SpecError, match="overlaps training corpus"):
        seal_exam_bank(
            competency_path=COMPETENCY,
            body_path=body,
            bank_id="templar-fresh-overlap",
            kind="fresh-transfer",
            visibility="reviewable",
            training_corpora=[corpus],
        )


def test_registered_exam_manifest_blocks_future_training_prompt(tmp_path: Path) -> None:
    student_root = tmp_path / "student"
    exam_dir = student_root / "exams"
    exam_dir.mkdir(parents=True)
    prompt = {"schema": "fleet.security-event.v1", "facts": {"protected": True}}
    body = tmp_path / "bank.jsonl"
    write_exam_cases(body, [_case("protected-1", prompt)])
    manifest = seal_exam_bank(
        competency_path=COMPETENCY,
        body_path=body,
        bank_id="protected-bank",
        kind="hidden-adversarial",
        visibility="external-hidden",
    )
    (exam_dir / "protected-bank.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SpecError, match="overlaps registered exam bank"):
        assert_no_registered_exam_overlap(
            student_root=student_root,
            examples=[_example("copied-exam-item", prompt)],
        )
    assert_no_registered_exam_overlap(
        student_root=student_root,
        examples=[
            _example(
                "distinct-correction",
                {"schema": "fleet.security-event.v1", "facts": {"protected": False}},
            )
        ],
    )


def test_exam_manifest_hash_fails_closed_on_tampering(tmp_path: Path) -> None:
    body = tmp_path / "bank.jsonl"
    write_exam_cases(
        body,
        [_case("fresh-1", {"schema": "fleet.security-event.v1", "facts": {"x": 1}})],
    )
    manifest = seal_exam_bank(
        competency_path=COMPETENCY,
        body_path=body,
        bank_id="tamper-bank",
        kind="fresh-transfer",
        visibility="reviewable",
    )
    manifest["case_count"] = 99
    path = tmp_path / "tampered.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SpecError, match="manifest hash mismatch"):
        load_exam_manifest(path)
