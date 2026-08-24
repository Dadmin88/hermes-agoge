from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spec import SpecError, StudentSpec, digest

FLEET_CONTRACT_MODULES = (
    "hermes_fleet/security_event.py",
    "hermes_fleet/templar.py",
    "hermes_fleet/pre_execution_gate.py",
    "hermes_fleet/learning_promotion_gate.py",
)


@dataclass(frozen=True, slots=True)
class ExtractedClass:
    fields: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"fields": [{"name": name, "type": kind} for name, kind in self.fields]}


def _safe_value(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ValueError(node.id)
        return env[node.id]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [_safe_value(item, env) for item in node.elts]
        return values
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "set", "tuple"}
        and len(node.args) <= 1
        and not node.keywords
    ):
        if not node.args:
            return []
        value = _safe_value(node.args[0], env)
        if not isinstance(value, list):
            raise ValueError("collection argument")
        return sorted(value, key=lambda item: str(item))
    raise ValueError(type(node).__name__)


def extract_python_contract(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    env: dict[str, Any] = {}
    constants: dict[str, Any] = {}
    classes: dict[str, ExtractedClass] = {}

    for node in tree.body:
        target_name: str | None = None
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            target_name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        if target_name is not None and value_node is not None:
            try:
                value = _safe_value(value_node, env)
            except ValueError:
                pass
            else:
                env[target_name] = value
                if target_name.startswith("_SUPPORTED_") or target_name.endswith(
                    (
                        "_SCHEMA",
                        "_STATES",
                        "_LEVELS",
                        "_ACTIONS",
                        "_KINDS",
                        "_DECISIONS",
                    )
                ):
                    constants[target_name] = value

        if isinstance(node, ast.ClassDef):
            decorators = [ast.unparse(item) for item in node.decorator_list]
            if not any("dataclass" in item for item in decorators):
                continue
            fields: list[tuple[str, str]] = []
            for statement in node.body:
                if isinstance(statement, ast.AnnAssign) and isinstance(
                    statement.target, ast.Name
                ):
                    fields.append(
                        (statement.target.id, ast.unparse(statement.annotation))
                    )
            classes[node.name] = ExtractedClass(tuple(fields))

    return {
        "constants": constants,
        "dataclasses": {
            name: value.to_dict() for name, value in sorted(classes.items())
        },
    }


def _git_show(repo: Path, revision: str, path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SpecError(f"cannot read pinned Fleet source {revision}:{path}") from exc
    return result.stdout


def fleet_revision_from_student(student: StudentSpec) -> str:
    matches = [
        source
        for source in student.sources
        if source.kind == "git" and source.uri.rstrip("/").endswith("/hermes-fleet")
    ]
    if len(matches) != 1:
        raise SpecError("student must bind exactly one hermes-fleet Git source")
    return matches[0].revision


def build_fleet_contract_snapshot(
    *, student_path: Path, fleet_repo: Path
) -> dict[str, Any]:
    student = StudentSpec.load(student_path)
    revision = fleet_revision_from_student(student)
    modules: dict[str, Any] = {}
    for path in FLEET_CONTRACT_MODULES:
        source = _git_show(fleet_repo, revision, path)
        modules[path] = {
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            **extract_python_contract(source),
        }
    document = {
        "schema": "agoge.fleet-contract-snapshot.v1",
        "student_id": student.student_id,
        "student_hash": student.content_hash,
        "fleet_revision": revision,
        "modules": modules,
    }
    return {**document, "snapshot_hash": digest(document)}


def write_fleet_contract_snapshot(
    *, student_path: Path, fleet_repo: Path, out: Path
) -> dict[str, Any]:
    snapshot = build_fleet_contract_snapshot(
        student_path=student_path, fleet_repo=fleet_repo
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot
