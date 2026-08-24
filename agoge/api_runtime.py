from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .spec import digest


class ApiRuntimeError(RuntimeError):
    pass


def default_hermes_root() -> Path:
    configured = os.environ.get("HERMES_AGENT_ROOT")
    root = Path(configured).expanduser() if configured else Path.home() / ".hermes" / "hermes-agent"
    root = root.resolve()
    if not (root / "venv" / "bin" / "python").is_file():
        raise ApiRuntimeError(
            "Hermes Agent Python runtime was not found; set HERMES_AGENT_ROOT explicitly"
        )
    return root


def _bridge_path(name: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "tools" / name
    if not path.is_file():
        raise ApiRuntimeError(f"Agoge Hermes bridge is missing: {path}")
    return path


def _run_bridge(args: list[str], *, hermes_root: Path | None = None, timeout: int = 300) -> dict[str, Any]:
    root = (hermes_root or default_hermes_root()).resolve()
    python = root / "venv" / "bin" / "python"
    completed = subprocess.run(
        [str(python), *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        raise ApiRuntimeError(f"Hermes bridge failed: {detail[:1200]}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ApiRuntimeError("Hermes bridge returned invalid JSON") from exc
    if type(value) is not dict:
        raise ApiRuntimeError("Hermes bridge returned a non-object")
    return value


def discover_hermes_api_catalog(
    *,
    provider: str,
    free_only: bool = False,
    refresh: bool = False,
    hermes_root: Path | None = None,
) -> dict[str, Any]:
    provider = provider.strip().lower()
    if not provider:
        raise ApiRuntimeError("API catalog provider must be non-empty")
    args = [
        str(_bridge_path("hermes_provider_catalog_bridge.py")),
        "--hermes-root",
        str((hermes_root or default_hermes_root()).resolve()),
        "--provider",
        provider,
    ]
    if free_only:
        args.append("--free-only")
    if refresh:
        args.append("--refresh")
    bridged = _run_bridge(args, hermes_root=hermes_root)
    models = bridged.get("models")
    if type(models) is not list:
        raise ApiRuntimeError("Hermes catalog bridge did not return models")
    result = {
        "schema": "agoge.api-runtime-catalog.v1",
        "source": "hermes-provider-catalog",
        "provider": provider,
        "free_only": bool(free_only),
        "count": len(models),
        "models": models,
    }
    result["catalog_id"] = digest(result)
    return result


def invoke_hermes_api_batch(
    *,
    provider: str,
    requests: list[dict[str, Any]],
    workers: int = 2,
    hermes_root: Path | None = None,
    timeout: int = 600,
) -> list[dict[str, Any]]:
    provider = provider.strip().lower()
    if not provider:
        raise ApiRuntimeError("API inference provider must be non-empty")
    if not requests:
        raise ApiRuntimeError("API inference batch is empty")
    if workers < 1 or workers > 16:
        raise ApiRuntimeError("API inference workers must be between 1 and 16")
    root = (hermes_root or default_hermes_root()).resolve()
    payload = {"schema": "agoge.api-inference-batch.v1", "requests": requests}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        input_path = Path(handle.name)
    try:
        bridged = _run_bridge(
            [
                str(_bridge_path("hermes_api_inference_bridge.py")),
                "--hermes-root",
                str(root),
                "--provider",
                provider,
                "--input",
                str(input_path),
                "--workers",
                str(workers),
            ],
            hermes_root=root,
            timeout=timeout,
        )
    finally:
        input_path.unlink(missing_ok=True)
    results = bridged.get("results")
    if type(results) is not list or len(results) != len(requests):
        raise ApiRuntimeError("Hermes API bridge returned an invalid result batch")
    return results
