from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.askesis import prepare_run
from agoge.backends.dryrun import train
from agoge.spec import SpecError

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def test_prepare_and_dry_run(tmp_path: Path) -> None:
    run = prepare_run(STUDENT, tmp_path / "run")
    assert run.manifest["state"] == "PREPARED"
    assert run.manifest["base_model_revision"] == "c1899de289a04d12100db370d81485cdf75e47ca"
    assert sum(run.manifest["counts"].values()) == 24
    assert (run.run_dir / "spec" / "student.json").exists()
    assert (run.run_dir / "spec" / "competency.json").exists()
    assert run.manifest["competency_id"] == "templar-runtime-judgment-v1"
    assert run.manifest["competency_hash"].startswith("sha256:")
    assert (run.run_dir / "data" / "train.jsonl").exists()
    result = train(run.run_dir)
    assert result["status"] == "DRY_RUN_COMPLETE"
    persisted = json.loads((run.run_dir / "training-result.json").read_text(encoding="utf-8"))
    assert persisted == result


def test_prepare_can_select_an_accepted_student_relative_corpus(tmp_path: Path) -> None:
    corpus = STUDENT.parent / "corpus" / "phase19-security-events-v1.jsonl"
    run = prepare_run(STUDENT, tmp_path / "foundation", corpus_path=corpus)
    assert run.manifest["corpus_source"] == "corpus/phase19-security-events-v1.jsonl"
    assert sum(run.manifest["counts"].values()) == 252


def test_prepare_rejects_a_corpus_outside_the_student_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside.jsonl"
    outside.write_text(
        (STUDENT.parent / "seed_cases.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(SpecError, match="inside the Student directory"):
        prepare_run(STUDENT, tmp_path / "run-outside", corpus_path=outside)
