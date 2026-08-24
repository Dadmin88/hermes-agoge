from __future__ import annotations

import json
from pathlib import Path

from agoge.base_benchmark import prepare_base_candidate_run
from agoge.spec import CompetencySpec, StudentSpec

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"
COMPETENCY = ROOT / "students" / "templar" / "competency.json"
CORPUS = ROOT / "students" / "templar" / "corpus" / "templar-runtime-foundation-v1.jsonl"


def test_base_candidate_run_preserves_capability_and_marks_artifact_non_promotable(
    tmp_path: Path,
) -> None:
    reference = StudentSpec.load(STUDENT)
    competency = CompetencySpec.load(COMPETENCY)
    run_dir = tmp_path / "candidate"
    manifest = prepare_base_candidate_run(
        reference_student_path=STUDENT,
        competency_path=COMPETENCY,
        corpus_path=CORPUS,
        model_id="example/test-base",
        revision="abc123",
        out_dir=run_dir,
        split_strategy="event-stratified",
    )
    candidate = StudentSpec.load(run_dir / "spec" / "student.json")
    assert candidate.base_model == "example/test-base"
    assert candidate.base_model_revision == "abc123"
    assert candidate.content_hash != reference.content_hash
    assert manifest["reference_student_hash"] == reference.content_hash
    assert manifest["competency_hash"] == competency.content_hash
    assert manifest["purpose"] == "base-model-benchmark-only-not-promotable"
    assert manifest["corpus_rebind_required_before_promotion"] is True
    assert manifest["counts"] == {"train": 414, "validation": 45, "test": 45}
    assert manifest["disposition_count"] == 16
    assert json.loads((run_dir / "spec" / "competency.json").read_text())["competency_id"] == competency.competency_id


def test_candidate_runs_use_the_same_deterministic_examples_across_bases(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    prepare_base_candidate_run(
        reference_student_path=STUDENT,
        competency_path=COMPETENCY,
        corpus_path=CORPUS,
        model_id="example/base-a",
        revision="one",
        out_dir=first,
    )
    prepare_base_candidate_run(
        reference_student_path=STUDENT,
        competency_path=COMPETENCY,
        corpus_path=CORPUS,
        model_id="example/base-b",
        revision="two",
        out_dir=second,
    )
    for split in ("train", "validation", "test"):
        assert (first / "data" / f"{split}.jsonl").read_bytes() == (
            second / "data" / f"{split}.jsonl"
        ).read_bytes()
    assert (first / "spec" / "dispositions.json").read_bytes() == (
        second / "spec" / "dispositions.json"
    ).read_bytes()
