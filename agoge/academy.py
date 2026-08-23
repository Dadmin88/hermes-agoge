from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .spec import SpecError
from .teacher import TeacherIdentity, TeacherRequest, TeacherResponse, TeacherResponseItem

ACADEMY_PAYLOAD_SCHEMA = "agoge.academy-faculty-payload.v1"


def _exact(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SpecError(f"{label} has an invalid closed schema")
    return value


@dataclass(frozen=True, slots=True)
class AcademyFacultyBinding:
    faculty_id: str
    faculty_distribution: str
    faculty_revision: str
    inference_provider: str
    inference_model: str
    inference_model_version: str
    training_use: str = "unknown"

    def __post_init__(self) -> None:
        for label, value in (
            ("faculty_id", self.faculty_id),
            ("faculty_distribution", self.faculty_distribution),
            ("faculty_revision", self.faculty_revision),
            ("inference_provider", self.inference_provider),
            ("inference_model", self.inference_model),
            ("inference_model_version", self.inference_model_version),
        ):
            if type(value) is not str or not value.strip():
                raise SpecError(f"Academy binding {label} must be non-empty")
        if self.training_use not in {"allowed", "unknown", "disallowed"}:
            raise SpecError("Academy binding training_use is unsupported")

    @classmethod
    def from_dict(cls, value: object) -> AcademyFacultyBinding:
        item = _exact(
            value,
            {
                "schema",
                "faculty_id",
                "faculty_distribution",
                "faculty_revision",
                "inference_provider",
                "inference_model",
                "inference_model_version",
                "training_use",
            },
            "Academy faculty binding",
        )
        if item["schema"] != "agoge.academy-faculty-binding.v1":
            raise SpecError("Academy faculty binding schema is unsupported")
        return cls(
            faculty_id=item["faculty_id"],
            faculty_distribution=item["faculty_distribution"],
            faculty_revision=item["faculty_revision"],
            inference_provider=item["inference_provider"],
            inference_model=item["inference_model"],
            inference_model_version=item["inference_model_version"],
            training_use=item["training_use"],
        )

    @property
    def teacher_identity(self) -> TeacherIdentity:
        return TeacherIdentity(
            teacher_id=(
                f"academy:{self.faculty_id}@{self.faculty_distribution}"
                f"+{self.faculty_revision}"
            ),
            kind="academy",
            provider=self.inference_provider,
            model=self.inference_model,
            model_version=self.inference_model_version,
            role=f"academy-faculty:{self.faculty_id}",
            training_use=self.training_use,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "schema": "agoge.academy-faculty-binding.v1",
            "faculty_id": self.faculty_id,
            "faculty_distribution": self.faculty_distribution,
            "faculty_revision": self.faculty_revision,
            "inference_provider": self.inference_provider,
            "inference_model": self.inference_model,
            "inference_model_version": self.inference_model_version,
            "training_use": self.training_use,
        }


@dataclass(frozen=True, slots=True)
class AcademyFacultyPayload:
    request_id: str
    items: tuple[TeacherResponseItem, ...]

    @classmethod
    def from_dict(cls, value: object) -> AcademyFacultyPayload:
        item = _exact(value, {"schema", "request_id", "items"}, "Academy payload")
        if item["schema"] != ACADEMY_PAYLOAD_SCHEMA:
            raise SpecError("Academy payload schema is unsupported")
        if type(item["request_id"]) is not str or not item["request_id"].strip():
            raise SpecError("Academy payload request_id must be non-empty")
        if type(item["items"]) is not list or not item["items"]:
            raise SpecError("Academy payload items must be non-empty")
        return cls(
            request_id=item["request_id"],
            items=tuple(TeacherResponseItem.from_dict(entry) for entry in item["items"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ACADEMY_PAYLOAD_SCHEMA,
            "request_id": self.request_id,
            "items": [item.to_dict() for item in self.items],
        }


def build_faculty_prompt(
    request: TeacherRequest,
    binding: AcademyFacultyBinding,
) -> str:
    output_contract = request.constraints["output_contract"]
    contract_schema = output_contract.get("schema")
    decisions = output_contract.get("decision")
    if type(contract_schema) is not str or type(decisions) is not list or not decisions:
        raise SpecError("Academy bridge requires a concrete closed-output contract")
    sample_decision = "DENY" if "DENY" in decisions else decisions[0]
    sample_reasons = ["bounded-reason-code"] if sample_decision in output_contract.get(
        "reason_codes_required_for", []
    ) else []
    payload_shape = {
        "schema": ACADEMY_PAYLOAD_SCHEMA,
        "request_id": request.request_id,
        "items": [
            {
                "prompt": {
                    "schema": "agoge.templar-training-projection.v1",
                    "facts": {"replace_with": "structured scenario facts"},
                },
                "completion": {
                    "schema": contract_schema,
                    "decision": sample_decision,
                    "reason_codes": sample_reasons,
                },
                "rationale": "why this exact judgment is correct",
                "basis": ["specific architecture/pedagogy basis"],
            }
        ],
    }
    brief = {
        "mode": "agoge-model-curriculum-contributor",
        "faculty_id": binding.faculty_id,
        "student_id": request.student_id,
        "student_hash": request.student_hash,
        "curriculum_id": request.curriculum_id,
        "curriculum_hash": request.curriculum_hash,
        "competency": request.competency,
        "objective": request.constraints["objective"],
        "count": request.count,
        "output_contract": request.constraints["output_contract"],
        "source_revisions": [source.to_dict() for source in request.sources],
    }
    return (
        "You are acting as Hermes Academy faculty for Hermes Agoge. This is NOT "
        "Academy Continuing Education for a Hermes profile. The learner is a small "
        "model being given curriculum candidates. Do not invoke /goal, /learn, "
        "message_agent, skill_manage, Fleet tools, or any persistence mechanism. "
        "Use Academy's minimum-sufficient pedagogy: target one observable competency, "
        "teach through concrete examples/counterexamples, include strange-but-benign "
        "cases so the learner does not overblock, and include ambiguity when REVIEW is "
        "the appropriate bounded judgment. Do not invent permissions or authority.\n\n"
        "Return ONLY one JSON object. No markdown fences and no prose outside JSON. "
        f"Return at most {request.count} semantically distinct items. The top-level "
        "object MUST have exactly the keys schema, request_id, and items. Copy the "
        "schema and request_id values shown below exactly. Each item MUST have exactly "
        "prompt, completion, rationale, and basis. Each completion is an INSTANCE of "
        "the Student output contract, not a copy of the contract descriptor: it MUST "
        "have exactly schema, decision, and reason_codes; decision MUST be one string "
        "from the allowed decisions, never an array. Do not add authority, note, "
        "reason_codes_required_for, identity, hashes, or other fields.\n\n"
        "Use this literal JSON skeleton as the syntax contract and replace only the "
        "scenario facts, judgment, reason codes, rationale, and basis content:\n"
        f"{json.dumps(payload_shape, sort_keys=True)}\n\n"
        "Agoge binds faculty/model identity itself.\n\n"
        f"Teaching brief:\n{json.dumps(brief, sort_keys=True)}"
    )


def parse_faculty_payload(
    raw: str,
    *,
    request: TeacherRequest,
    binding: AcademyFacultyBinding,
) -> TeacherResponse:
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        raise SpecError("Academy faculty returned invalid JSON") from exc
    payload = AcademyFacultyPayload.from_dict(value)
    if payload.request_id != request.request_id:
        raise SpecError("Academy faculty response is bound to another request")
    if len(payload.items) > request.count:
        raise SpecError("Academy faculty exceeded the requested item bound")
    return TeacherResponse(
        request_id=request.request_id,
        teacher=binding.teacher_identity,
        items=payload.items,
    )
