from __future__ import annotations

from agoge.fleet_snapshot import extract_python_contract


def test_extract_python_contract_collects_closed_shapes_and_enums() -> None:
    source = """
from dataclasses import dataclass
from typing import Final
EVENT_SCHEMA: Final[str] = "fleet.event.v1"
_LEVELS = frozenset({"low", "high"})
_SUPPORTED_EVENTS = frozenset({EVENT_SCHEMA, "fleet.other.v1"})
@dataclass(frozen=True)
class Example:
    name: str
    count: int
"""
    contract = extract_python_contract(source)
    assert contract["constants"]["EVENT_SCHEMA"] == "fleet.event.v1"
    assert contract["constants"]["_LEVELS"] == ["high", "low"]
    assert contract["constants"]["_SUPPORTED_EVENTS"] == [
        "fleet.event.v1",
        "fleet.other.v1",
    ]
    assert contract["dataclasses"]["Example"]["fields"] == [
        {"name": "name", "type": "str"},
        {"name": "count", "type": "int"},
    ]
