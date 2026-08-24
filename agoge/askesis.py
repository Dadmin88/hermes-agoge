from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
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
from .spec import CompetencySpec, CurriculumSpec, SpecError, StudentSpec, canonical_json, digest


@dataclass(frozen=True, slots=True)
class PreparedRun:
    run_dir: Path
    manifest: dict[str, Any]


def prepare_run(
    student_path: Path,
    out_dir: Path,
    *,
    corpus_path: Path | None = None,
    split_strategy: str = "stable",
) -> PreparedRun:
    student_path = student_path.resolve()
    student = StudentSpec.load(student_path)
    root = student_path.parent
    curriculum_path = (root / student.curriculum).resolve()
    curriculum = CurriculumSpec.load(curriculum_path)
    competency_path = (root / "competency.json").resolve()
    competency = CompetencySpec.load(competency_path) if competency_path.is_file() else None
    if competency is not None and competency.student_id != student.student_id:
        raise SpecError("Askesis competency belongs to another Student")
    selected_corpus = (corpus_path or (root / "seed_cases.jsonl")).resolve()
    try:
        corpus_source = selected_corpus.relative_to(root).as_posix()
    except ValueError as exc:
        raise SpecError("Askesis corpus must be inside the Student directory") from exc
    examples = read_jsonl(selected_corpus)
    assert_no_registered_exam_overlap(student_root=root, examples=examples)
    unknown = sorted({item.competency for item in examples} - set(curriculum.competencies))
    if unknown:
        raise SpecError(f"corpus references unknown competencies: {unknown}")
    if split_strategy == "stable":
        splits = stable_split(examples)
    elif split_strategy == "stratified":
        splits = stable_stratified_split(examples)
    elif split_strategy == "event-stratified":
        splits = stable_event_stratified_split(examples)
    else:
        raise SpecError(f"unsupported Askesis split strategy: {split_strategy}")
    if not splits["train"]:
        raise SpecError("training split is empty")
    out_dir.mkdir(parents=True, exist_ok=False)
    for split_name, split_examples in splits.items():
        write_jsonl(out_dir / "data" / f"{split_name}.jsonl", split_examples)
    snapshot_dir = out_dir / "spec"
    snapshot_dir.mkdir()
    shutil.copy2(student_path, snapshot_dir / "student.json")
    shutil.copy2(curriculum_path, snapshot_dir / "curriculum.json")
    if competency is not None:
        shutil.copy2(competency_path, snapshot_dir / "competency.json")
    disposition_registry = build_disposition_registry(examples, student_id=student.student_id)
    (snapshot_dir / "dispositions.json").write_bytes(
        canonical_json(disposition_registry) + b"\n"
    )
    manifest = {
        "schema": "agoge.askesis-run.v1",
        "student_id": student.student_id,
        "student_hash": student.content_hash,
        "curriculum_id": curriculum.curriculum_id,
        "curriculum_hash": curriculum.content_hash,
        "base_model": student.base_model,
        "base_model_revision": student.base_model_revision,
        "prepared_at_unix_ms": time.time_ns() // 1_000_000,
        "corpus_source": corpus_source,
        "corpus_hash": digest([item.to_dict() for item in examples]),
        "disposition_registry_hash": disposition_registry["registry_hash"],
        "disposition_count": len(disposition_registry["entries"]),
        "split_strategy": split_strategy,
        "counts": {name: len(items) for name, items in splits.items()},
        "sources": [item.to_dict() for item in student.sources],
        "state": "PREPARED",
    }
    if competency is not None:
        manifest["competency_id"] = competency.competency_id
        manifest["competency_hash"] = competency.content_hash
    (out_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return PreparedRun(out_dir, manifest)
