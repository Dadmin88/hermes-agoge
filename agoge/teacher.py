from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import Example
from .exam import parse_model_output
from .spec import CurriculumSpec, SourceRef, SpecError, StudentSpec, digest

TEACHER_KINDS = frozenset({"deterministic", "model", "academy", "human"})
TRAINING_USE_STATES = frozenset({"allowed", "unknown", "disallowed"})
TEACHER_PURPOSES = frozenset(
    {"generate-training-candidates", "critique-candidate", "adjudicate-disagreement"}
)


def _exact(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SpecError(f"{label} has an invalid closed schema")
    return value


def _nonempty(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise SpecError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class TeacherIdentity:
    teacher_id: str
    kind: str
    provider: str
    model: str
    model_version: str
    role: str
    training_use: str

    def __post_init__(self) -> None:
        for label, value in (
            ("teacher_id", self.teacher_id),
            ("provider", self.provider),
            ("model", self.model),
            ("model_version", self.model_version),
            ("role", self.role),
        ):
            _nonempty(value, label)
        if self.kind not in TEACHER_KINDS:
            raise SpecError("teacher kind is unsupported")
        if self.training_use not in TRAINING_USE_STATES:
            raise SpecError("teacher training_use is unsupported")

    @classmethod
    def from_dict(cls, value: object) -> TeacherIdentity:
        item = _exact(
            value,
            {
                "schema",
                "teacher_id",
                "kind",
                "provider",
                "model",
                "model_version",
                "role",
                "training_use",
            },
            "teacher identity",
        )
        if item["schema"] != "agoge.teacher-identity.v1":
            raise SpecError("teacher identity schema is unsupported")
        return cls(
            teacher_id=item["teacher_id"],
            kind=item["kind"],
            provider=item["provider"],
            model=item["model"],
            model_version=item["model_version"],
            role=item["role"],
            training_use=item["training_use"],
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "schema": "agoge.teacher-identity.v1",
            "teacher_id": self.teacher_id,
            "kind": self.kind,
            "provider": self.provider,
            "model": self.model,
            "model_version": self.model_version,
            "role": self.role,
            "training_use": self.training_use,
        }


@dataclass(frozen=True, slots=True)
class TeacherRequest:
    student_id: str
    student_hash: str
    curriculum_id: str
    curriculum_hash: str
    competency: str
    purpose: str
    count: int
    constraints: dict[str, Any]
    sources: tuple[SourceRef, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("student_id", self.student_id),
            ("student_hash", self.student_hash),
            ("curriculum_id", self.curriculum_id),
            ("curriculum_hash", self.curriculum_hash),
            ("competency", self.competency),
        ):
            _nonempty(value, label)
        if self.purpose not in TEACHER_PURPOSES:
            raise SpecError("teacher request purpose is unsupported")
        if type(self.count) is not int or isinstance(self.count, bool) or not 1 <= self.count <= 1000:
            raise SpecError("teacher request count must be between 1 and 1000")
        if type(self.constraints) is not dict:
            raise SpecError("teacher request constraints must be an object")
        if not self.sources:
            raise SpecError("teacher request must retain source provenance")

    @classmethod
    def from_student(
        cls,
        student_path: Path,
        *,
        competency: str,
        count: int,
        purpose: str = "generate-training-candidates",
    ) -> TeacherRequest:
        student = StudentSpec.load(student_path)
        curriculum = CurriculumSpec.load(student_path.parent / student.curriculum)
        if competency not in curriculum.competencies:
            raise SpecError(f"unknown curriculum competency: {competency}")
        return cls(
            student_id=student.student_id,
            student_hash=student.content_hash,
            curriculum_id=curriculum.curriculum_id,
            curriculum_hash=curriculum.content_hash,
            competency=competency,
            purpose=purpose,
            count=count,
            constraints={
                "objective": curriculum.objective,
                "output_contract": student.output_contract,
                "rules": [
                    "Return bounded structured examples, not prose-only advice.",
                    "Do not invent authority or widen Fleet permissions.",
                    "Prefer semantically distinct cases over paraphrase-only duplicates.",
                    "Include strange-but-benign cases as well as risky cases.",
                    "Every proposed completion must obey the student's closed output contract.",
                ],
            },
            sources=student.sources,
        )

    def document(self) -> dict[str, Any]:
        return {
            "schema": "agoge.teacher-request.v1",
            "student_id": self.student_id,
            "student_hash": self.student_hash,
            "curriculum_id": self.curriculum_id,
            "curriculum_hash": self.curriculum_hash,
            "competency": self.competency,
            "purpose": self.purpose,
            "count": self.count,
            "constraints": self.constraints,
            "sources": [item.to_dict() for item in self.sources],
        }

    @property
    def request_id(self) -> str:
        return digest(self.document())

    def to_dict(self) -> dict[str, Any]:
        return {**self.document(), "request_id": self.request_id}

    @classmethod
    def from_dict(cls, value: object) -> TeacherRequest:
        item = _exact(
            value,
            {
                "schema",
                "request_id",
                "student_id",
                "student_hash",
                "curriculum_id",
                "curriculum_hash",
                "competency",
                "purpose",
                "count",
                "constraints",
                "sources",
            },
            "teacher request",
        )
        if item["schema"] != "agoge.teacher-request.v1":
            raise SpecError("teacher request schema is unsupported")
        sources = item["sources"]
        if type(sources) is not list:
            raise SpecError("teacher request sources must be an array")
        request = cls(
            student_id=item["student_id"],
            student_hash=item["student_hash"],
            curriculum_id=item["curriculum_id"],
            curriculum_hash=item["curriculum_hash"],
            competency=item["competency"],
            purpose=item["purpose"],
            count=item["count"],
            constraints=item["constraints"],
            sources=tuple(SourceRef.from_dict(source) for source in sources),
        )
        if item["request_id"] != request.request_id:
            raise SpecError("teacher request identity does not match its content")
        return request


@dataclass(frozen=True, slots=True)
class TeacherResponseItem:
    prompt: dict[str, Any]
    completion: dict[str, Any]
    rationale: str
    basis: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object) -> TeacherResponseItem:
        item = _exact(
            value, {"prompt", "completion", "rationale", "basis"}, "teacher item"
        )
        if type(item["prompt"]) is not dict or type(item["completion"]) is not dict:
            raise SpecError("teacher item prompt/completion must be objects")
        rationale = _nonempty(item["rationale"], "teacher item rationale")
        basis = item["basis"]
        if type(basis) is not list or not basis or not all(
            type(entry) is str and entry.strip() for entry in basis
        ):
            raise SpecError("teacher item basis must be a non-empty string array")
        return cls(item["prompt"], item["completion"], rationale, tuple(basis))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "rationale": self.rationale,
            "basis": list(self.basis),
        }


@dataclass(frozen=True, slots=True)
class TeacherResponse:
    request_id: str
    teacher: TeacherIdentity
    items: tuple[TeacherResponseItem, ...]

    @classmethod
    def from_dict(cls, value: object) -> TeacherResponse:
        item = _exact(
            value, {"schema", "request_id", "teacher", "items"}, "teacher response"
        )
        if item["schema"] != "agoge.teacher-response.v1":
            raise SpecError("teacher response schema is unsupported")
        items = item["items"]
        if type(items) is not list or not items:
            raise SpecError("teacher response items must be a non-empty array")
        return cls(
            request_id=_nonempty(item["request_id"], "teacher response request_id"),
            teacher=TeacherIdentity.from_dict(item["teacher"]),
            items=tuple(TeacherResponseItem.from_dict(entry) for entry in items),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "agoge.teacher-response.v1",
            "request_id": self.request_id,
            "teacher": self.teacher.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())


def load_teacher_request(path: Path) -> TeacherRequest:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read teacher request {path}: {exc}") from exc
    return TeacherRequest.from_dict(value)


def load_teacher_response(path: Path) -> TeacherResponse:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read teacher response {path}: {exc}") from exc
    return TeacherResponse.from_dict(value)


def response_to_candidates(
    request: TeacherRequest, response: TeacherResponse
) -> list[Example]:
    if response.request_id != request.request_id:
        raise SpecError("teacher response is bound to another request")
    if len(response.items) > request.count:
        raise SpecError("teacher response exceeds the requested item bound")
    contract = request.constraints.get("output_contract")
    if type(contract) is not dict:
        raise SpecError("teacher request has no usable output contract")
    candidates: list[Example] = []
    for item in response.items:
        parsed = parse_model_output(
            json.dumps(item.completion, sort_keys=True, separators=(",", ":")), contract
        )
        if not parsed.contract_valid:
            raise SpecError(
                f"teacher proposed an invalid completion: {parsed.error or 'unknown'}"
            )
        candidate_material = {
            "request_id": request.request_id,
            "teacher": response.teacher.to_dict(),
            "prompt": item.prompt,
            "completion": item.completion,
            "rationale": item.rationale,
            "basis": list(item.basis),
        }
        candidate_id = "candidate-" + digest(candidate_material).split(":", 1)[1][:24]
        candidates.append(
            Example(
                example_id=candidate_id,
                competency=request.competency,
                prompt=item.prompt,
                completion=item.completion,
                provenance={
                    "kind": "teacher-generated-candidate",
                    "source": response.teacher.teacher_id,
                    "basis": item.rationale,
                    "basis_refs": list(item.basis),
                    "request_id": request.request_id,
                    "response_hash": response.content_hash,
                    "teacher": response.teacher.to_dict(),
                    "training_use": response.teacher.training_use,
                    "review_state": "generated-unreviewed",
                },
            )
        )
    return candidates
