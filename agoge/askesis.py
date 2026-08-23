from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import read_jsonl, stable_split, write_jsonl
from .spec import CurriculumSpec, SpecError, StudentSpec, canonical_json, digest


@dataclass(frozen=True, slots=True)
class PreparedRun:
    run_dir: Path
    manifest: dict[str, Any]


def prepare_run(student_path: Path, out_dir: Path) -> PreparedRun:
    student_path = student_path.resolve()
    student = StudentSpec.load(student_path)
    root = student_path.parent
    curriculum_path = (root / student.curriculum).resolve()
    curriculum = CurriculumSpec.load(curriculum_path)
    examples = read_jsonl(root / "seed_cases.jsonl")
    unknown = sorted({item.competency for item in examples} - set(curriculum.competencies))
    if unknown:
        raise SpecError(f"corpus references unknown competencies: {unknown}")
    splits = stable_split(examples)
    if not splits["train"]:
        raise SpecError("training split is empty")
    out_dir.mkdir(parents=True, exist_ok=False)
    for split_name, split_examples in splits.items():
        write_jsonl(out_dir / "data" / f"{split_name}.jsonl", split_examples)
    snapshot_dir = out_dir / "spec"
    snapshot_dir.mkdir()
    shutil.copy2(student_path, snapshot_dir / "student.json")
    shutil.copy2(curriculum_path, snapshot_dir / "curriculum.json")
    manifest = {
        "schema": "agoge.askesis-run.v1",
        "student_id": student.student_id,
        "student_hash": student.content_hash,
        "curriculum_id": curriculum.curriculum_id,
        "curriculum_hash": curriculum.content_hash,
        "base_model": student.base_model,
        "prepared_at_unix_ms": time.time_ns() // 1_000_000,
        "corpus_hash": digest([item.to_dict() for item in examples]),
        "counts": {name: len(items) for name, items in splits.items()},
        "sources": [item.to_dict() for item in student.sources],
        "state": "PREPARED",
    }
    (out_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return PreparedRun(out_dir, manifest)
