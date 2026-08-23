from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .spec import SpecError, canonical_json, digest


@dataclass(frozen=True, slots=True)
class Example:
    example_id: str
    competency: str
    prompt: dict[str, Any]
    completion: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> "Example":
        if type(value) is not dict:
            raise SpecError("corpus example must be an object")
        required = {"schema", "example_id", "competency", "prompt", "completion", "provenance"}
        if set(value) != required or value.get("schema") != "agoge.example.v1":
            raise SpecError("corpus example has an invalid closed schema")
        if type(value["example_id"]) is not str or not value["example_id"].strip():
            raise SpecError("example_id must be non-empty")
        if type(value["competency"]) is not str or not value["competency"].strip():
            raise SpecError("competency must be non-empty")
        for key in ("prompt", "completion", "provenance"):
            if type(value[key]) is not dict:
                raise SpecError(f"{key} must be an object")
        return cls(value["example_id"], value["competency"], value["prompt"], value["completion"], value["provenance"])

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "agoge.example.v1", "example_id": self.example_id, "competency": self.competency, "prompt": self.prompt, "completion": self.completion, "provenance": self.provenance}

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())


def read_jsonl(path: Path) -> list[Example]:
    examples: list[Example] = []
    ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SpecError(f"cannot read corpus {path}: {exc}") from exc
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SpecError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
        example = Example.from_dict(value)
        if example.example_id in ids:
            raise SpecError(f"duplicate example_id {example.example_id!r}")
        ids.add(example.example_id)
        examples.append(example)
    if not examples:
        raise SpecError(f"corpus is empty: {path}")
    return examples


def write_jsonl(path: Path, examples: Iterable[Example]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for example in examples:
            handle.write(canonical_json(example.to_dict()))
            handle.write(b"\n")


def stable_split(examples: Iterable[Example]) -> dict[str, list[Example]]:
    result = {"train": [], "validation": [], "test": []}
    for example in sorted(examples, key=lambda item: item.example_id):
        bucket = int(hashlib.sha256(example.example_id.encode()).hexdigest()[:8], 16) % 100
        if bucket < 80:
            result["train"].append(example)
        elif bucket < 90:
            result["validation"].append(example)
        else:
            result["test"].append(example)
    return result
