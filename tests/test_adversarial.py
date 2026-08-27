from __future__ import annotations

import json
from pathlib import Path

import pytest

from agoge.adversarial import (
    AdversarialCandidate,
    mutate_example,
    mutate_examples,
    mutate_prompt,
    mutation_families,
    read_adversarial_candidates,
    write_adversarial_candidates,
)
from agoge.corpus import Example, read_jsonl
from agoge.exam_bank import ExamCase, seal_exam_bank, write_exam_cases
from agoge.spec import SpecError, digest
from agoge.templar_projection import project_templar_event

ROOT = Path(__file__).resolve().parents[1]
STUDENT_ROOT = ROOT / "students" / "templar"
COMPETENCY = STUDENT_ROOT / "competency.json"
FOUNDATION = STUDENT_ROOT / "corpus" / "templar-runtime-foundation-v1.jsonl"


def _accepted_example(example_id: str, prompt: dict[str, object]) -> Example:
    return Example(
        example_id=example_id,
        competency="benign-nonoverblocking",
        prompt=prompt,
        completion={
            "schema": "agoge.templar-model-output.v1",
            "decision": "ALLOW",
            "reason_codes": [],
        },
        provenance={"review_state": "accepted", "training_use": "allowed", "source": "test"},
    )


def _learning_example() -> Example:
    for example in read_jsonl(FOUNDATION):
        if example.prompt.get("schema") == "fleet.learning-promotion-event.v1":
            return example
    raise AssertionError("foundation corpus has no learning-promotion event")


def _security_example_with_ordered_lists() -> Example:
    for example in read_jsonl(FOUNDATION):
        if example.prompt.get("schema") != "fleet.security-event.v1":
            continue
        request = example.prompt.get("request")
        if type(request) is not dict:
            continue
        requested_tools = request.get("requested_tools")
        if type(requested_tools) is list and len(requested_tools) > 1:
            return example
    raise AssertionError("foundation corpus has no suitable security event")


def test_adversarial_mutation_families_are_closed_and_stable() -> None:
    assert mutation_families() == (
        "irrelevant-noise",
        "layout-perturbation",
        "unordered-list-permutation",
    )
    with pytest.raises(SpecError, match="unsupported adversarial mutation family"):
        mutate_prompt({"schema": "fleet.learning-promotion-event.v1"}, family="invented")


def test_learning_noise_mutation_is_deterministic_and_candidate_only() -> None:
    source = _learning_example()
    first = mutate_example(source, family="irrelevant-noise", variant=2)
    second = mutate_example(source, family="irrelevant-noise", variant=2)
    assert first == second
    assert first.candidate_id.startswith("adversarial-")
    assert first.candidate_id == second.candidate_id
    assert first.expected == source.completion
    assert digest(first.prompt) != digest(source.prompt)
    assert first.to_dict()["training_eligible"] is False
    assert first.provenance["review_state"] == "generated"
    assert first.provenance["training_use"] == "candidate-only"
    assert first.provenance["runtime_binding"] == "requires-regeneration"
    assert first.provenance["source_example_hash"] == source.content_hash
    assert first.provenance["mutation"] == {
        "schema": "agoge.adversarial-mutation.v1",
        "family": "irrelevant-noise",
        "variant": 2,
        "generator": "hermes-agoge",
        "generator_version": "v1",
    }


def test_security_order_mutation_preserves_model_projection() -> None:
    source = _security_example_with_ordered_lists()
    mutant = mutate_example(source, family="unordered-list-permutation")
    assert digest(mutant.prompt) != digest(source.prompt)
    assert project_templar_event(mutant.prompt) == project_templar_event(source.prompt)
    assert mutant.expected == source.completion


def test_inapplicable_mutation_families_are_skipped_in_batch() -> None:
    source = _security_example_with_ordered_lists()
    mutants = mutate_examples(
        [source],
        student_root=STUDENT_ROOT,
        families=["irrelevant-noise", "unordered-list-permutation"],
    )
    assert len(mutants) == 1
    assert mutants[0].provenance["mutation"]["family"] == "unordered-list-permutation"


def test_adversarial_candidate_is_not_a_training_example(tmp_path: Path) -> None:
    candidate = mutate_example(_learning_example(), family="irrelevant-noise")
    path = tmp_path / "adversarial.jsonl"
    write_adversarial_candidates(path, [candidate])
    assert read_adversarial_candidates(path) == [candidate]
    with pytest.raises(SpecError, match="corpus example has an invalid closed schema"):
        read_jsonl(path)


def test_candidate_schema_rejects_training_eligible_tampering() -> None:
    candidate = mutate_example(_learning_example(), family="irrelevant-noise").to_dict()
    candidate["training_eligible"] = True
    with pytest.raises(SpecError, match="must not be directly training-eligible"):
        AdversarialCandidate.from_dict(candidate)


def test_registered_exam_prompt_cannot_be_used_as_mutation_source(tmp_path: Path) -> None:
    student_root = tmp_path / "templar"
    exam_dir = student_root / "exams"
    exam_dir.mkdir(parents=True)
    prompt = {"schema": "fleet.security-event.v1", "facts": {"sealed": True}}
    body = tmp_path / "hidden.jsonl"
    write_exam_cases(
        body,
        [
            ExamCase(
                case_id="sealed-source",
                competency="benign-nonoverblocking",
                prompt=prompt,
                expected={
                    "schema": "agoge.templar-model-output.v1",
                    "decision": "ALLOW",
                    "reason_codes": [],
                },
                provenance={"source": "external-hidden-test"},
            )
        ],
    )
    manifest = seal_exam_bank(
        competency_path=COMPETENCY,
        body_path=body,
        bank_id="sealed-source-bank",
        kind="hidden-adversarial",
        visibility="external-hidden",
    )
    (exam_dir / "sealed-source-bank.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(SpecError, match="overlaps registered exam bank"):
        mutate_examples(
            [_accepted_example("copied-hidden-source", prompt)],
            student_root=student_root,
            families=["unordered-list-permutation"],
        )


def test_batch_mutation_requires_accepted_training_approved_sources(tmp_path: Path) -> None:
    rejected = Example(
        example_id="not-reviewed",
        competency="benign-nonoverblocking",
        prompt={"schema": "fleet.learning-promotion-event.v1"},
        completion={
            "schema": "agoge.templar-model-output.v1",
            "decision": "ALLOW",
            "reason_codes": [],
        },
        provenance={"review_state": "generated", "training_use": "candidate-only"},
    )
    with pytest.raises(SpecError, match="is not an accepted example"):
        mutate_examples(
            [rejected],
            student_root=tmp_path,
            families=["irrelevant-noise"],
        )
