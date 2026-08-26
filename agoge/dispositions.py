from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .corpus import Example
from .spec import SpecError, digest


@dataclass(frozen=True, slots=True)
class Disposition:
    class_index: int
    label_id: str
    decision: str
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "class_index": self.class_index,
            "label_id": self.label_id,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
        }


def _key(decision: str, reason_codes: tuple[str, ...]) -> dict[str, object]:
    return {"decision": decision, "reason_codes": list(reason_codes)}


def disposition_label_id(decision: str, reason_codes: tuple[str, ...]) -> str:
    return "disp-" + digest(_key(decision, reason_codes)).removeprefix("sha256:")[:16]


def _completion_key(completion: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    decision = completion.get("decision")
    reasons = completion.get("reason_codes")
    if (
        type(decision) is not str
        or type(reasons) is not list
        or not all(type(item) is str and item for item in reasons)
    ):
        raise SpecError("disposition registry requires closed decision/reason labels")
    if len(reasons) != len(set(reasons)):
        raise SpecError("disposition registry rejects duplicate reason codes")
    return decision, tuple(sorted(reasons))


def build_disposition_registry(
    examples: Iterable[Example], *, student_id: str
) -> dict[str, object]:
    keys = {_completion_key(example.completion) for example in examples}
    if not keys:
        raise SpecError("disposition registry cannot be empty")
    ordered = sorted(
        (
            (disposition_label_id(decision, reasons), decision, reasons)
            for decision, reasons in keys
        ),
        key=lambda row: row[0],
    )
    entries = [
        Disposition(index, label_id, decision, reasons).to_dict()
        for index, (label_id, decision, reasons) in enumerate(ordered)
    ]
    document: dict[str, object] = {
        "schema": "agoge.disposition-registry.v1",
        "student_id": student_id,
        "entries": entries,
    }
    document["registry_hash"] = digest(document)
    return document


def validate_disposition_registry(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != {
        "schema",
        "student_id",
        "entries",
        "registry_hash",
    }:
        raise SpecError("disposition registry has an invalid closed schema")
    if value.get("schema") != "agoge.disposition-registry.v1":
        raise SpecError("unsupported disposition registry schema")
    student_id = value.get("student_id")
    entries = value.get("entries")
    registry_hash = value.get("registry_hash")
    if type(student_id) is not str or not student_id:
        raise SpecError("disposition registry student_id is invalid")
    if type(entries) is not list or not entries:
        raise SpecError("disposition registry entries are invalid")
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, tuple[str, ...]]] = set()
    for expected_index, entry in enumerate(entries):
        if type(entry) is not dict or set(entry) != {
            "class_index",
            "label_id",
            "decision",
            "reason_codes",
        }:
            raise SpecError("disposition registry entry has an invalid closed schema")
        if entry.get("class_index") != expected_index:
            raise SpecError("disposition registry class indices are not contiguous")
        label_id = entry.get("label_id")
        decision = entry.get("decision")
        reasons_value = entry.get("reason_codes")
        if type(label_id) is not str or not label_id.startswith("disp-"):
            raise SpecError("disposition registry label_id is invalid")
        if type(decision) is not str or not decision:
            raise SpecError("disposition registry decision is invalid")
        if type(reasons_value) is not list or not all(
            type(item) is str and item for item in reasons_value
        ):
            raise SpecError("disposition registry reason codes are invalid")
        reasons = tuple(sorted(reasons_value))
        if list(reasons) != reasons_value or len(reasons) != len(set(reasons)):
            raise SpecError("disposition registry reason codes are not canonical")
        if disposition_label_id(decision, reasons) != label_id:
            raise SpecError("disposition registry label_id does not match content")
        key = (decision, reasons)
        if label_id in seen_ids or key in seen_keys:
            raise SpecError("disposition registry contains duplicate labels")
        seen_ids.add(label_id)
        seen_keys.add(key)
    without_hash = dict(value)
    without_hash.pop("registry_hash")
    if registry_hash != digest(without_hash):
        raise SpecError("disposition registry hash is invalid")
    return value


def registry_lookup(value: dict[str, object]) -> dict[tuple[str, tuple[str, ...]], int]:
    validate_disposition_registry(value)
    result: dict[tuple[str, tuple[str, ...]], int] = {}
    entries = value["entries"]
    assert type(entries) is list
    for entry in entries:
        assert type(entry) is dict
        decision = entry["decision"]
        reasons = tuple(entry["reason_codes"])
        class_index = entry["class_index"]
        assert type(decision) is str and type(class_index) is int
        result[(decision, reasons)] = class_index
    return result


def disposition_for_class(value: dict[str, object], class_index: int) -> dict[str, object]:
    validate_disposition_registry(value)
    entries = value["entries"]
    assert type(entries) is list
    if not 0 <= class_index < len(entries):
        raise SpecError("disposition class index is out of range")
    entry = entries[class_index]
    assert type(entry) is dict
    return entry
