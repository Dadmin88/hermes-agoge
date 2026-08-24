from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """A student or curriculum specification is invalid."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read JSON spec {path}: {exc}") from exc
    if type(value) is not dict:
        raise SpecError(f"spec must be a JSON object: {path}")
    return value


def _require_exact_keys(
    value: dict[str, Any], required: set[str], label: str
) -> None:
    actual = set(value)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise SpecError(f"{label} keys mismatch; missing={missing}, extra={extra}")


@dataclass(frozen=True, slots=True)
class SourceRef:
    kind: str
    uri: str
    revision: str
    purpose: str

    @classmethod
    def from_dict(cls, value: object) -> SourceRef:
        if type(value) is not dict:
            raise SpecError("source must be an object")
        _require_exact_keys(
            value, {"kind", "uri", "revision", "purpose"}, "source"
        )
        fields = [value[k] for k in ("kind", "uri", "revision", "purpose")]
        if not all(type(item) is str and item.strip() for item in fields):
            raise SpecError("source fields must be non-empty strings")
        return cls(
            value["kind"], value["uri"], value["revision"], value["purpose"]
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "uri": self.uri,
            "revision": self.revision,
            "purpose": self.purpose,
        }


@dataclass(frozen=True, slots=True)
class StudentSpec:
    schema: str
    student_id: str
    display_name: str
    description: str
    base_model: str
    base_model_revision: str
    task_type: str
    output_contract: dict[str, Any]
    sources: tuple[SourceRef, ...]
    curriculum: str

    @classmethod
    def load(cls, path: Path) -> StudentSpec:
        value = _load_json(path)
        _require_exact_keys(
            value,
            {
                "schema",
                "student_id",
                "display_name",
                "description",
                "base_model",
                "base_model_revision",
                "task_type",
                "output_contract",
                "sources",
                "curriculum",
            },
            "student spec",
        )
        if value["schema"] != "agoge.student.v1":
            raise SpecError("unsupported student schema")
        for key in (
            "student_id",
            "display_name",
            "description",
            "base_model",
            "base_model_revision",
            "task_type",
            "curriculum",
        ):
            if type(value[key]) is not str or not value[key].strip():
                raise SpecError(
                    f"student field {key!r} must be a non-empty string"
                )
        if type(value["output_contract"]) is not dict:
            raise SpecError("output_contract must be an object")
        if type(value["sources"]) is not list or not value["sources"]:
            raise SpecError("sources must be a non-empty array")
        return cls(
            value["schema"],
            value["student_id"],
            value["display_name"],
            value["description"],
            value["base_model"],
            value["base_model_revision"],
            value["task_type"],
            value["output_contract"],
            tuple(SourceRef.from_dict(item) for item in value["sources"]),
            value["curriculum"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "student_id": self.student_id,
            "display_name": self.display_name,
            "description": self.description,
            "base_model": self.base_model,
            "base_model_revision": self.base_model_revision,
            "task_type": self.task_type,
            "output_contract": self.output_contract,
            "sources": [item.to_dict() for item in self.sources],
            "curriculum": self.curriculum,
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CompetencySpec:
    schema: str
    competency_id: str
    student_id: str
    objective: str
    target_capabilities: tuple[str, ...]
    operating_conditions: tuple[str, ...]
    transfer_criteria: dict[str, Any]
    anchor_capabilities: tuple[str, ...]
    authoritative_measurements: tuple[str, ...]
    no_change_evidence: tuple[str, ...]
    candidate_unsuitable_evidence: tuple[str, ...]
    sources: tuple[SourceRef, ...]

    @staticmethod
    def _strings(value: object, label: str, *, nonempty: bool = False) -> tuple[str, ...]:
        if type(value) is not list or (nonempty and not value):
            raise SpecError(f"{label} must be {'a non-empty ' if nonempty else 'a '}string array")
        if not all(type(item) is str and item.strip() for item in value):
            raise SpecError(f"{label} must contain only non-empty strings")
        if len(value) != len(set(value)):
            raise SpecError(f"{label} must not contain duplicates")
        return tuple(value)

    @classmethod
    def load(cls, path: Path) -> CompetencySpec:
        value = _load_json(path)
        _require_exact_keys(
            value,
            {
                "schema",
                "competency_id",
                "student_id",
                "objective",
                "target_capabilities",
                "operating_conditions",
                "transfer_criteria",
                "anchor_capabilities",
                "authoritative_measurements",
                "no_change_evidence",
                "candidate_unsuitable_evidence",
                "sources",
            },
            "competency spec",
        )
        if value["schema"] != "agoge.competency.v1":
            raise SpecError("unsupported competency schema")
        for key in ("competency_id", "student_id", "objective"):
            if type(value[key]) is not str or not value[key].strip():
                raise SpecError(f"competency field {key!r} must be a non-empty string")
        if type(value["transfer_criteria"]) is not dict or not value["transfer_criteria"]:
            raise SpecError("transfer_criteria must be a non-empty object")
        if type(value["sources"]) is not list or not value["sources"]:
            raise SpecError("competency sources must be a non-empty array")
        return cls(
            value["schema"],
            value["competency_id"],
            value["student_id"],
            value["objective"],
            cls._strings(value["target_capabilities"], "target_capabilities", nonempty=True),
            cls._strings(value["operating_conditions"], "operating_conditions", nonempty=True),
            value["transfer_criteria"],
            cls._strings(value["anchor_capabilities"], "anchor_capabilities", nonempty=True),
            cls._strings(
                value["authoritative_measurements"],
                "authoritative_measurements",
                nonempty=True,
            ),
            cls._strings(value["no_change_evidence"], "no_change_evidence"),
            cls._strings(
                value["candidate_unsuitable_evidence"], "candidate_unsuitable_evidence"
            ),
            tuple(SourceRef.from_dict(item) for item in value["sources"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "competency_id": self.competency_id,
            "student_id": self.student_id,
            "objective": self.objective,
            "target_capabilities": list(self.target_capabilities),
            "operating_conditions": list(self.operating_conditions),
            "transfer_criteria": self.transfer_criteria,
            "anchor_capabilities": list(self.anchor_capabilities),
            "authoritative_measurements": list(self.authoritative_measurements),
            "no_change_evidence": list(self.no_change_evidence),
            "candidate_unsuitable_evidence": list(self.candidate_unsuitable_evidence),
            "sources": [item.to_dict() for item in self.sources],
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CurriculumSpec:
    schema: str
    curriculum_id: str
    objective: str
    competencies: tuple[str, ...]
    decisions: tuple[str, ...]
    graduation_gates: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> CurriculumSpec:
        value = _load_json(path)
        _require_exact_keys(
            value,
            {
                "schema",
                "curriculum_id",
                "objective",
                "competencies",
                "decisions",
                "graduation_gates",
            },
            "curriculum spec",
        )
        if value["schema"] != "agoge.curriculum.v1":
            raise SpecError("unsupported curriculum schema")
        if type(value["curriculum_id"]) is not str or not value[
            "curriculum_id"
        ].strip():
            raise SpecError("curriculum_id must be non-empty")
        if type(value["objective"]) is not str or not value["objective"].strip():
            raise SpecError("objective must be non-empty")
        if (
            type(value["competencies"]) is not list
            or not value["competencies"]
            or not all(
                type(item) is str and item.strip() for item in value["competencies"]
            )
        ):
            raise SpecError("competencies must be a non-empty string array")
        if type(value["decisions"]) is not list or not value["decisions"]:
            raise SpecError("decisions must be a non-empty array")
        if len(value["decisions"]) != len(set(value["decisions"])):
            raise SpecError("decisions must be unique")
        if type(value["graduation_gates"]) is not dict:
            raise SpecError("graduation_gates must be an object")
        return cls(
            value["schema"],
            value["curriculum_id"],
            value["objective"],
            tuple(value["competencies"]),
            tuple(value["decisions"]),
            value["graduation_gates"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "curriculum_id": self.curriculum_id,
            "objective": self.objective,
            "competencies": list(self.competencies),
            "decisions": list(self.decisions),
            "graduation_gates": self.graduation_gates,
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())
