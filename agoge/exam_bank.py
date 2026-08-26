from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import Example, read_jsonl
from .spec import CompetencySpec, SpecError, canonical_json, digest

_BANK_KINDS = {"fresh-transfer", "hidden-adversarial", "anchor-regression"}
_VISIBILITIES = {"reviewable", "external-hidden"}


@dataclass(frozen=True, slots=True)
class ExamCase:
    case_id: str
    competency: str
    prompt: dict[str, Any]
    expected: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> ExamCase:
        if type(value) is not dict:
            raise SpecError("exam case must be an object")
        required = {
            "schema",
            "case_id",
            "competency",
            "prompt",
            "expected",
            "provenance",
            "training_forbidden",
        }
        if set(value) != required or value.get("schema") != "agoge.exam-case.v1":
            raise SpecError("exam case has an invalid closed schema")
        if value.get("training_forbidden") is not True:
            raise SpecError("exam case must be permanently training-forbidden")
        for key in ("case_id", "competency"):
            if type(value[key]) is not str or not value[key].strip():
                raise SpecError(f"exam case {key} must be non-empty")
        for key in ("prompt", "expected", "provenance"):
            if type(value[key]) is not dict:
                raise SpecError(f"exam case {key} must be an object")
        return cls(
            case_id=value["case_id"],
            competency=value["competency"],
            prompt=value["prompt"],
            expected=value["expected"],
            provenance=value["provenance"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "agoge.exam-case.v1",
            "case_id": self.case_id,
            "competency": self.competency,
            "prompt": self.prompt,
            "expected": self.expected,
            "provenance": self.provenance,
            "training_forbidden": True,
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())

    @property
    def prompt_hash(self) -> str:
        return digest(self.prompt)


def read_exam_cases(path: Path) -> list[ExamCase]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SpecError(f"cannot read exam bank body {path}: {exc}") from exc
    cases: list[ExamCase] = []
    case_ids: set[str] = set()
    prompt_hashes: set[str] = set()
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SpecError(f"invalid exam-bank JSONL at {path}:{line_no}: {exc}") from exc
        case = ExamCase.from_dict(value)
        if case.case_id in case_ids:
            raise SpecError(f"duplicate exam case_id {case.case_id!r}")
        if case.prompt_hash in prompt_hashes:
            raise SpecError("exam bank contains duplicate prompt content")
        case_ids.add(case.case_id)
        prompt_hashes.add(case.prompt_hash)
        cases.append(case)
    if not cases:
        raise SpecError(f"exam bank is empty: {path}")
    return cases


def write_exam_cases(path: Path, cases: list[ExamCase]) -> None:
    if not cases:
        raise SpecError("cannot write an empty exam bank")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for case in cases:
            handle.write(canonical_json(case.to_dict()))
            handle.write(b"\n")


def exam_body_hash(cases: list[ExamCase]) -> str:
    return digest([case.to_dict() for case in cases])


def _training_prompt_hashes(corpus_paths: list[Path]) -> tuple[set[str], list[str]]:
    hashes: set[str] = set()
    corpus_hashes: list[str] = []
    for path in corpus_paths:
        examples = read_jsonl(path)
        corpus_hashes.append(digest([example.to_dict() for example in examples]))
        hashes.update(digest(example.prompt) for example in examples)
    return hashes, sorted(corpus_hashes)


def seal_exam_bank(
    *,
    competency_path: Path,
    body_path: Path,
    bank_id: str,
    kind: str,
    visibility: str,
    training_corpora: list[Path] | None = None,
) -> dict[str, Any]:
    if not bank_id.strip():
        raise SpecError("exam bank_id must be non-empty")
    if kind not in _BANK_KINDS:
        raise SpecError(f"unsupported exam bank kind: {kind}")
    if visibility not in _VISIBILITIES:
        raise SpecError(f"unsupported exam bank visibility: {visibility}")
    competency = CompetencySpec.load(competency_path)
    cases = read_exam_cases(body_path)
    prompt_hashes = [case.prompt_hash for case in cases]
    training_hashes, corpus_hashes = _training_prompt_hashes(training_corpora or [])
    overlap = sorted(set(prompt_hashes) & training_hashes)
    if overlap:
        raise SpecError(f"exam bank overlaps training corpus by {len(overlap)} exact prompt(s)")
    event_schemas = sorted(
        {
            str(case.prompt.get("schema"))
            for case in cases
            if type(case.prompt.get("schema")) is str and case.prompt.get("schema")
        }
    )
    manifest: dict[str, Any] = {
        "schema": "agoge.exam-bank.v1",
        "bank_id": bank_id,
        "kind": kind,
        "visibility": visibility,
        "competency_id": competency.competency_id,
        "competency_hash": competency.content_hash,
        "body_hash": exam_body_hash(cases),
        "case_count": len(cases),
        "event_schemas": event_schemas,
        "prompt_hashes": sorted(prompt_hashes),
        "training_forbidden": True,
        "immutable": True,
        "source_training_corpus_hashes": corpus_hashes,
        "exact_training_overlap_count": 0,
    }
    manifest["manifest_hash"] = digest(manifest)
    return manifest


def load_exam_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read exam bank manifest {path}: {exc}") from exc
    if type(value) is not dict:
        raise SpecError("exam bank manifest must be an object")
    required = {
        "schema",
        "bank_id",
        "kind",
        "visibility",
        "competency_id",
        "competency_hash",
        "body_hash",
        "case_count",
        "event_schemas",
        "prompt_hashes",
        "training_forbidden",
        "immutable",
        "source_training_corpus_hashes",
        "exact_training_overlap_count",
        "manifest_hash",
    }
    if set(value) != required or value.get("schema") != "agoge.exam-bank.v1":
        raise SpecError("exam bank manifest has an invalid closed schema")
    if value.get("kind") not in _BANK_KINDS or value.get("visibility") not in _VISIBILITIES:
        raise SpecError("exam bank manifest kind/visibility is invalid")
    if value.get("training_forbidden") is not True or value.get("immutable") is not True:
        raise SpecError("exam bank manifest must be immutable and training-forbidden")
    if type(value.get("prompt_hashes")) is not list or not all(
        type(item) is str and item.startswith("sha256:") for item in value["prompt_hashes"]
    ):
        raise SpecError("exam bank manifest prompt_hashes are invalid")
    expected_hash = value["manifest_hash"]
    unsigned = dict(value)
    del unsigned["manifest_hash"]
    if expected_hash != digest(unsigned):
        raise SpecError("exam bank manifest hash mismatch")
    return value


def verify_exam_body(manifest: dict[str, Any], cases: list[ExamCase]) -> None:
    if manifest.get("body_hash") != exam_body_hash(cases):
        raise SpecError("exam bank body hash does not match manifest")
    if manifest.get("case_count") != len(cases):
        raise SpecError("exam bank case count does not match manifest")
    prompt_hashes = sorted(case.prompt_hash for case in cases)
    if manifest.get("prompt_hashes") != prompt_hashes:
        raise SpecError("exam bank prompt fingerprint set does not match manifest")


def registered_exam_manifests(student_root: Path) -> list[dict[str, Any]]:
    exam_dir = student_root / "exams"
    if not exam_dir.is_dir():
        return []
    return [load_exam_manifest(path) for path in sorted(exam_dir.glob("*.manifest.json"))]


def assert_no_registered_exam_overlap(*, student_root: Path, examples: list[Example]) -> None:
    manifests = registered_exam_manifests(student_root)
    if not manifests:
        return
    protected: dict[str, str] = {}
    for manifest in manifests:
        for prompt_hash in manifest["prompt_hashes"]:
            protected[prompt_hash] = str(manifest["bank_id"])
    collisions = []
    for example in examples:
        prompt_hash = digest(example.prompt)
        bank_id = protected.get(prompt_hash)
        if bank_id is not None:
            collisions.append((example.example_id, bank_id))
    if collisions:
        formatted = ", ".join(f"{example_id}->{bank_id}" for example_id, bank_id in collisions)
        raise SpecError(f"training corpus overlaps registered exam bank: {formatted}")
