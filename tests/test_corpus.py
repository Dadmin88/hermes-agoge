from __future__ import annotations

from pathlib import Path

from agoge.corpus import read_jsonl, stable_split, stable_stratified_split

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "students" / "templar" / "seed_cases.jsonl"


def test_seed_corpus_has_unique_examples_and_all_decisions() -> None:
    examples = read_jsonl(CORPUS)
    assert len(examples) >= 20
    assert len({item.example_id for item in examples}) == len(examples)
    assert {item.completion["decision"] for item in examples} == {"ALLOW", "DENY", "REVIEW"}


def test_split_is_stable_and_nonempty() -> None:
    examples = read_jsonl(CORPUS)
    first = stable_split(examples)
    second = stable_split(reversed(examples))
    assert {k: [x.example_id for x in v] for k, v in first.items()} == {k: [x.example_id for x in v] for k, v in second.items()}
    assert first["train"] and first["validation"] and first["test"]


def test_stratified_split_is_stable_and_preserves_each_foundation_label_family() -> None:
    foundation = ROOT / "students" / "templar" / "corpus" / "phase19-security-events-v1.jsonl"
    examples = read_jsonl(foundation)
    first = stable_stratified_split(examples)
    second = stable_stratified_split(reversed(examples))
    assert {k: [x.example_id for x in v] for k, v in first.items()} == {k: [x.example_id for x in v] for k, v in second.items()}

    def strata(rows):
        return {
            (
                item.competency,
                item.completion["decision"],
                tuple(sorted(item.completion["reason_codes"])),
            )
            for item in rows
        }

    all_strata = strata(examples)
    assert strata(first["train"]) == all_strata
    assert strata(first["validation"]) == all_strata
    assert strata(first["test"]) == all_strata
