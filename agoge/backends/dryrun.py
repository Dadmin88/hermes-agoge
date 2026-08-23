from __future__ import annotations

import json
from pathlib import Path


def train(run_dir: Path) -> dict[str, object]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    result = {"schema": "agoge.training-result.v1", "backend": "dry-run", "student_id": manifest["student_id"], "base_model": manifest["base_model"], "status": "DRY_RUN_COMPLETE", "artifact_dir": None}
    (run_dir / "training-result.json").write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return result
