from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from agoge.corpus import read_jsonl
from agoge.reviewers.templar_phase23 import review_candidate

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "students" / "templar" / "corpus" / "phase23-learning-events-v1.jsonl"
MANIFEST = ROOT / "students" / "templar" / "corpus" / "phase23-learning-events-v1.manifest.json"


def test_phase23_foundation_corpus_is_accepted_and_fleet_shaped() -> None:
    rows = read_jsonl(CORPUS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(rows) == 252
    assert manifest["count"] == 252
    assert manifest["event_family"] == "fleet.learning-promotion-event.v1"
    assert all(row.prompt["schema"] == "fleet.learning-promotion-event.v1" for row in rows)
    assert all(row.provenance["review_state"] == "accepted" for row in rows)


def test_phase23_same_signal_can_have_allow_review_and_deny_semantics() -> None:
    decisions_by_signal: dict[str, set[str]] = defaultdict(set)
    for row in read_jsonl(CORPUS):
        for signal in row.prompt["risk_signals"]:
            decisions_by_signal[signal].add(row.completion["decision"])
    assert decisions_by_signal["hidden-instructions"] == {"ALLOW", "REVIEW", "DENY"}
    assert decisions_by_signal["social-engineering"] == {"ALLOW", "REVIEW", "DENY"}
    assert decisions_by_signal["suspicious-secret-handling"] == {"ALLOW", "REVIEW", "DENY"}


def test_phase23_independent_reviewer_accepts_committed_corpus() -> None:
    for row in read_jsonl(CORPUS):
        assert review_candidate(row).decision == "ACCEPT"
