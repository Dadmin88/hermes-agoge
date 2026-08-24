from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.corpus import read_jsonl
from agoge.dispositions import (
    build_disposition_registry,
    disposition_for_class,
    registry_lookup,
    validate_disposition_registry,
)
from agoge.spec import SpecError

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "students" / "templar" / "corpus" / "phase19-security-events-v1.jsonl"


def test_phase19_registry_has_seven_content_derived_dispositions() -> None:
    examples = read_jsonl(CORPUS)
    registry = build_disposition_registry(examples, student_id="templar-v1")
    validate_disposition_registry(registry)
    assert len(registry["entries"]) == 7
    lookup = registry_lookup(registry)
    for example in examples:
        key = (
            example.completion["decision"],
            tuple(sorted(example.completion["reason_codes"])),
        )
        class_index = lookup[key]
        entry = disposition_for_class(registry, class_index)
        assert entry["decision"] == key[0]
        assert tuple(entry["reason_codes"]) == key[1]


def test_registry_hash_fails_closed_on_mutation() -> None:
    registry = build_disposition_registry(read_jsonl(CORPUS), student_id="templar-v1")
    mutated = json.loads(json.dumps(registry))
    mutated["entries"][0]["decision"] = "DENY"
    with pytest.raises(SpecError, match="label_id"):
        validate_disposition_registry(mutated)
