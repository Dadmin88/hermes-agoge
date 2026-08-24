from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from .corpus import (
    read_jsonl,
    stable_event_stratified_split,
    stable_split,
    stable_stratified_split,
    write_jsonl,
)
from .dispositions import build_disposition_registry
from .exam_bank import assert_no_registered_exam_overlap
from .spec import (
    CompetencySpec,
    CurriculumSpec,
    SpecError,
    StudentSpec,
    canonical_json,
    digest,
)


def _candidate_student(reference: StudentSpec, *, model_id: str, revision: str) -> dict[str, Any]:
    if not model_id.strip() or not revision.strip():
        raise SpecError("benchmark candidate model and revision must be non-empty")
    value = reference.to_dict()
    value["base_model"] = model_id
    value["base_model_revision"] = revision
    return value


def prepare_base_candidate_run(
    *,
    reference_student_path: Path,
    competency_path: Path,
    corpus_path: Path,
    model_id: str,
    revision: str,
    out_dir: Path,
    split_strategy: str = "event-stratified",
) -> dict[str, Any]:
    reference_student_path = reference_student_path.resolve()
    competency_path = competency_path.resolve()
    corpus_path = corpus_path.resolve()
    reference_student = StudentSpec.load(reference_student_path)
    competency = CompetencySpec.load(competency_path)
    if competency.student_id != reference_student.student_id:
        raise SpecError("benchmark competency belongs to another Student")
    curriculum_path = (reference_student_path.parent / reference_student.curriculum).resolve()
    curriculum = CurriculumSpec.load(curriculum_path)
    examples = read_jsonl(corpus_path)
    assert_no_registered_exam_overlap(
        student_root=reference_student_path.parent,
        examples=examples,
    )
    unknown = sorted({row.competency for row in examples} - set(curriculum.competencies))
    if unknown:
        raise SpecError(f"benchmark corpus references unknown competencies: {unknown}")

    if split_strategy == "stable":
        splits = stable_split(examples)
    elif split_strategy == "stratified":
        splits = stable_stratified_split(examples)
    elif split_strategy == "event-stratified":
        splits = stable_event_stratified_split(examples)
    else:
        raise SpecError(f"unsupported benchmark split strategy: {split_strategy}")
    if not splits["train"] or not splits["validation"] or not splits["test"]:
        raise SpecError("benchmark split must contain train, validation, and test rows")

    candidate_dict = _candidate_student(reference_student, model_id=model_id, revision=revision)
    candidate_path = out_dir / "spec" / "student.json"
    out_dir.mkdir(parents=True, exist_ok=False)
    candidate_path.parent.mkdir()
    candidate_path.write_bytes(canonical_json(candidate_dict) + b"\n")
    candidate_student = StudentSpec.load(candidate_path)
    shutil.copy2(curriculum_path, out_dir / "spec" / "curriculum.json")
    shutil.copy2(competency_path, out_dir / "spec" / "competency.json")
    for name, rows in splits.items():
        write_jsonl(out_dir / "data" / f"{name}.jsonl", rows)

    registry = build_disposition_registry(examples, student_id=reference_student.student_id)
    (out_dir / "spec" / "dispositions.json").write_bytes(canonical_json(registry) + b"\n")
    corpus_hash = digest([row.to_dict() for row in examples])
    manifest = {
        "schema": "agoge.base-benchmark-run.v1",
        "purpose": "base-model-benchmark-only-not-promotable",
        "prepared_at_unix_ms": time.time_ns() // 1_000_000,
        "student_id": reference_student.student_id,
        "reference_student_hash": reference_student.content_hash,
        "student_hash": candidate_student.content_hash,
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "curriculum_id": curriculum.curriculum_id,
        "curriculum_hash": curriculum.content_hash,
        "base_model": model_id,
        "base_model_revision": revision,
        "corpus_hash": corpus_hash,
        "corpus_provenance_student_hash": reference_student.content_hash,
        "corpus_rebind_required_before_promotion": True,
        "split_strategy": split_strategy,
        "counts": {name: len(rows) for name, rows in splits.items()},
        "disposition_registry_hash": registry["registry_hash"],
        "disposition_count": len(registry["entries"]),
        "sources": [item.to_dict() for item in reference_student.sources],
        "state": "BENCHMARK_PREPARED",
    }
    (out_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return manifest
