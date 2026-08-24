from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spec import SpecError, canonical_json, digest


@dataclass(frozen=True, slots=True)
class Example:
    example_id: str
    competency: str
    prompt: dict[str, Any]
    completion: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> Example:
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


def stable_event_stratified_split(examples: Iterable[Example]) -> dict[str, list[Example]]:
    """Stratify by runtime event family plus competency and exact disposition.

    This is the foundation split for a Student that consumes multiple closed event
    schemas. It prevents one event family's examples from accidentally satisfying
    another family's held-out coverage merely because they share a decision/reason
    tuple.
    """

    groups: dict[tuple[str, str, str, tuple[str, ...]], list[Example]] = {}
    for example in examples:
        event_schema = example.prompt.get("schema")
        decision = example.completion.get("decision")
        reasons = example.completion.get("reason_codes")
        if type(event_schema) is not str or not event_schema.strip():
            raise SpecError("event-stratified split requires a closed prompt schema")
        if type(decision) is not str or type(reasons) is not list or not all(
            type(item) is str for item in reasons
        ):
            raise SpecError("event-stratified split requires closed decision/reason labels")
        key = (event_schema, example.competency, decision, tuple(sorted(reasons)))
        groups.setdefault(key, []).append(example)

    result = {"train": [], "validation": [], "test": []}
    for key in sorted(groups):
        rows = sorted(
            groups[key],
            key=lambda item: hashlib.sha256(item.example_id.encode()).hexdigest(),
        )
        count = len(rows)
        if count < 3:
            raise SpecError(
                "event-stratified split requires at least three examples per event/disposition family: "
                f"{key!r} has {count}"
            )
        holdout_each = max(1, count // 10)
        if holdout_each * 2 >= count:
            holdout_each = 1
        result["test"].extend(rows[:holdout_each])
        result["validation"].extend(rows[holdout_each : holdout_each * 2])
        result["train"].extend(rows[holdout_each * 2 :])

    for split in result.values():
        split.sort(key=lambda item: item.example_id)
    if not result["train"]:
        raise SpecError("event-stratified training split is empty")
    return result


def stable_stratified_split(examples: Iterable[Example]) -> dict[str, list[Example]]:
    """Deterministically retain each learned disposition family in validation/test.

    This is for foundation experiments, not the immutable graduation exam bank. A
    stratum is competency + decision + exact reason-code family so small corpora do
    not accidentally produce an all-ALLOW held-out split.
    """

    groups: dict[tuple[str, str, tuple[str, ...]], list[Example]] = {}
    for example in examples:
        decision = example.completion.get("decision")
        reasons = example.completion.get("reason_codes")
        if type(decision) is not str or type(reasons) is not list or not all(
            type(item) is str for item in reasons
        ):
            raise SpecError("stratified split requires closed decision/reason labels")
        key = (example.competency, decision, tuple(sorted(reasons)))
        groups.setdefault(key, []).append(example)

    result = {"train": [], "validation": [], "test": []}
    for key in sorted(groups):
        rows = sorted(
            groups[key],
            key=lambda item: hashlib.sha256(item.example_id.encode()).hexdigest(),
        )
        count = len(rows)
        if count < 3:
            raise SpecError(
                "stratified split requires at least three examples per disposition family: "
                f"{key!r} has {count}"
            )
        holdout_each = max(1, count // 10)
        if holdout_each * 2 >= count:
            holdout_each = 1
        result["test"].extend(rows[:holdout_each])
        result["validation"].extend(rows[holdout_each : holdout_each * 2])
        result["train"].extend(rows[holdout_each * 2 :])

    for split in result.values():
        split.sort(key=lambda item: item.example_id)
    if not result["train"]:
        raise SpecError("stratified training split is empty")
    return result
