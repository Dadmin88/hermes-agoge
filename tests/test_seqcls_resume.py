from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.backends.qlora_seqcls import _initial_adapter_info


def _write_source_run(tmp_path: Path) -> Path:
    run = tmp_path / "source-run"
    adapter = run / "artifacts" / "seqcls-adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text('{"peft_type":"LORA"}\n', encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"test-adapter-bytes")
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "student_id": "templar-v1",
                "base_model": "Qwen/Qwen3-0.6B",
                "base_model_revision": "rev-1",
                "corpus_hash": "sha256:source-corpus",
                "disposition_registry_hash": "sha256:registry",
            }
        ),
        encoding="utf-8",
    )
    (run / "training-result-seqcls.json").write_text(
        json.dumps(
            {
                "status": "TRAINED",
                "backend": "qlora-seqcls",
                "disposition_registry_hash": "sha256:registry",
            }
        ),
        encoding="utf-8",
    )
    return run


def _target_manifest() -> dict[str, object]:
    return {
        "student_id": "templar-v1",
        "base_model": "Qwen/Qwen3-0.6B",
        "base_model_revision": "rev-1",
    }


def test_initial_adapter_info_binds_exact_parent_run(tmp_path: Path) -> None:
    run = _write_source_run(tmp_path)
    info = _initial_adapter_info(
        run,
        target_manifest=_target_manifest(),
        registry_hash="sha256:registry",
    )
    assert info["run_dir"] == str(run)
    assert info["corpus_hash"] == "sha256:source-corpus"
    assert info["adapter_dir"] == str(run / "artifacts" / "seqcls-adapter")
    assert str(info["adapter_hash"]).startswith("sha256:")


def test_initial_adapter_info_rejects_base_or_registry_mismatch(tmp_path: Path) -> None:
    run = _write_source_run(tmp_path)
    bad_target = _target_manifest()
    bad_target["base_model_revision"] = "other-revision"
    with pytest.raises(RuntimeError, match="mismatch for base_model_revision"):
        _initial_adapter_info(
            run,
            target_manifest=bad_target,
            registry_hash="sha256:registry",
        )
    with pytest.raises(RuntimeError, match="disposition registry"):
        _initial_adapter_info(
            run,
            target_manifest=_target_manifest(),
            registry_hash="sha256:other-registry",
        )


def test_initial_adapter_info_requires_trained_seqcls_result(tmp_path: Path) -> None:
    run = _write_source_run(tmp_path)
    result_path = run / "training-result-seqcls.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["status"] = "FAILED"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not a trained sequence-classification adapter"):
        _initial_adapter_info(
            run,
            target_manifest=_target_manifest(),
            registry_hash="sha256:registry",
        )
