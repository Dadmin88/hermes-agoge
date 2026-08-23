from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.spec import CurriculumSpec, SpecError, StudentSpec

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def test_templar_student_and_curriculum_validate() -> None:
    student = StudentSpec.load(STUDENT)
    curriculum = CurriculumSpec.load(STUDENT.parent / student.curriculum)
    assert student.student_id == "templar-v1"
    assert student.base_model == "Qwen/Qwen3-0.6B"
    assert set(curriculum.decisions) == {"ALLOW", "DENY", "REVIEW"}
    assert student.content_hash.startswith("sha256:")
    assert curriculum.content_hash.startswith("sha256:")


def test_student_schema_fails_closed_on_unknown_field(tmp_path: Path) -> None:
    value = json.loads(STUDENT.read_text(encoding="utf-8"))
    value["surprise"] = "nope"
    path = tmp_path / "student.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(SpecError, match="keys mismatch"):
        StudentSpec.load(path)
