from __future__ import annotations

import json
from pathlib import Path

from agoge.askesis import prepare_run
from agoge.backends.dryrun import train

ROOT = Path(__file__).resolve().parents[1]
STUDENT = ROOT / "students" / "templar" / "student.json"


def test_prepare_and_dry_run(tmp_path: Path) -> None:
    run = prepare_run(STUDENT, tmp_path / "run")
    assert run.manifest["state"] == "PREPARED"
    assert run.manifest["base_model_revision"] == "c1899de289a04d12100db370d81485cdf75e47ca"
    assert sum(run.manifest["counts"].values()) == 24
    assert (run.run_dir / "spec" / "student.json").exists()
    assert (run.run_dir / "data" / "train.jsonl").exists()
    result = train(run.run_dir)
    assert result["status"] == "DRY_RUN_COMPLETE"
    persisted = json.loads((run.run_dir / "training-result.json").read_text(encoding="utf-8"))
    assert persisted == result
