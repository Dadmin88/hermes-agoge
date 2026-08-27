from __future__ import annotations

import json
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import Example
from .exam_bank import assert_no_registered_exam_overlap
from .spec import SpecError, canonical_json, digest

_MUTATION_FAMILIES = {
    "irrelevant-noise",
    "layout-perturbation",
    "unordered-list-permutation",
}

_NEUTRAL_NOISE = (
    "Context note: routine documentation synchronization.",
    "Context note: ordinary release bookkeeping follows.",
    "Context note: unrelated project metadata was attached.",
    "Context note: routine maintenance metadata is present.",
)


@dataclass(frozen=True, slots=True)
class AdversarialCandidate:
    candidate_id: str
    competency: str
    prompt: dict[str, Any]
    expected: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> AdversarialCandidate:
        if type(value) is not dict:
            raise SpecError("adversarial candidate must be an object")
        required = {
            "schema",
            "candidate_id",
            "competency",
            "prompt",
            "expected",
            "provenance",
            "training_eligible",
        }
        if set(value) != required or value.get("schema") != "agoge.adversarial-candidate.v1":
            raise SpecError("adversarial candidate has an invalid closed schema")
        if value.get("training_eligible") is not False:
            raise SpecError("adversarial candidate must not be directly training-eligible")
        for key in ("candidate_id", "competency"):
            if type(value[key]) is not str or not value[key].strip():
                raise SpecError(f"adversarial candidate {key} must be non-empty")
        for key in ("prompt", "expected", "provenance"):
            if type(value[key]) is not dict:
                raise SpecError(f"adversarial candidate {key} must be an object")
        return cls(
            candidate_id=value["candidate_id"],
            competency=value["competency"],
            prompt=value["prompt"],
            expected=value["expected"],
            provenance=value["provenance"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "agoge.adversarial-candidate.v1",
            "candidate_id": self.candidate_id,
            "competency": self.competency,
            "prompt": self.prompt,
            "expected": self.expected,
            "provenance": self.provenance,
            "training_eligible": False,
        }

    @property
    def content_hash(self) -> str:
        return digest(self.to_dict())


def read_adversarial_candidates(path: Path) -> list[AdversarialCandidate]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SpecError(f"cannot read adversarial candidate corpus {path}: {exc}") from exc
    candidates: list[AdversarialCandidate] = []
    ids: set[str] = set()
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SpecError(f"invalid adversarial JSONL at {path}:{line_no}: {exc}") from exc
        candidate = AdversarialCandidate.from_dict(value)
        if candidate.candidate_id in ids:
            raise SpecError(f"duplicate adversarial candidate_id {candidate.candidate_id!r}")
        ids.add(candidate.candidate_id)
        candidates.append(candidate)
    if not candidates:
        raise SpecError(f"adversarial candidate corpus is empty: {path}")
    return candidates


def write_adversarial_candidates(path: Path, candidates: Iterable[AdversarialCandidate]) -> None:
    rows = list(candidates)
    if not rows:
        raise SpecError("cannot write an empty adversarial candidate corpus")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for candidate in rows:
            handle.write(canonical_json(candidate.to_dict()))
            handle.write(b"\n")


def mutation_families() -> tuple[str, ...]:
    return tuple(sorted(_MUTATION_FAMILIES))


def _require_accepted_source(example: Example) -> None:
    provenance = example.provenance
    if provenance.get("review_state") != "accepted":
        raise SpecError(
            f"adversarial mutation source {example.example_id!r} is not an accepted example"
        )
    if provenance.get("training_use") != "allowed":
        raise SpecError(
            f"adversarial mutation source {example.example_id!r} is not approved for training use"
        )


def _mutate_text(text: str, family: str, variant: int) -> str:
    if family == "irrelevant-noise":
        note = _NEUTRAL_NOISE[variant % len(_NEUTRAL_NOISE)]
        return f"{text}\n\n{note}"
    if family == "layout-perturbation":
        if "\n" in text:
            return text.replace("\n", "\n\n")
        if ". " in text:
            return text.replace(". ", ".\n")
        return f"{text}\n"
    raise SpecError(f"text mutation family is unsupported: {family}")


def _mutate_learning_event(prompt: dict[str, Any], family: str, variant: int) -> dict[str, Any]:
    mutated = deepcopy(prompt)
    if family == "unordered-list-permutation":
        for key in ("evaluation_categories", "risk_signals"):
            value = mutated.get(key)
            if type(value) is list:
                value.reverse()
        return mutated

    request = mutated.get("request")
    if type(request) is not dict:
        raise SpecError("learning-event mutation requires a request object")
    material = request.get("evaluation_material")
    if type(material) is not dict:
        raise SpecError("learning-event mutation requires evaluation material")
    kind = material.get("kind")
    if kind == "memory":
        text = material.get("text")
        if type(text) is not str:
            raise SpecError("learning-event memory material text is invalid")
        material["text"] = _mutate_text(text, family, variant)
        return mutated
    if kind == "skill":
        files = material.get("files")
        if type(files) is not list or not files:
            raise SpecError("learning-event skill material files are invalid")
        for item in files:
            if type(item) is not dict or type(item.get("text")) is not str:
                raise SpecError("learning-event skill material file text is invalid")
            item["text"] = _mutate_text(item["text"], family, variant)
        return mutated
    raise SpecError(f"learning-event evaluation material kind is unsupported: {kind!r}")


def _reverse_list(value: object) -> None:
    if type(value) is list:
        value.reverse()


def _mutate_security_event(prompt: dict[str, Any], family: str, variant: int) -> dict[str, Any]:
    if family != "unordered-list-permutation":
        raise SpecError(
            f"security-event mutation family {family!r} cannot preserve the closed Fleet event semantics"
        )
    mutated = deepcopy(prompt)
    request = mutated.get("request")
    if type(request) is not dict:
        raise SpecError("security-event mutation requires a request object")
    _reverse_list(request.get("requested_tools"))
    _reverse_list(request.get("authorized_toolsets"))
    network = request.get("network")
    if type(network) is dict:
        destinations = network.get("destinations")
        _reverse_list(destinations)
        if type(destinations) is list:
            for destination in destinations:
                if type(destination) is dict:
                    _reverse_list(destination.get("ports"))
                    _reverse_list(destination.get("resolved_ips"))
    for key in (
        "memory_skill_risks",
        "secret_interceptions",
        "policy_mismatches",
        "quarantine_signals",
    ):
        rows = mutated.get(key)
        _reverse_list(rows)
        if type(rows) is list:
            for row in rows:
                if type(row) is dict:
                    for nested in ("signal_codes", "detected_kinds", "reason_codes"):
                        _reverse_list(row.get(nested))
    return mutated


def mutate_prompt(prompt: dict[str, Any], *, family: str, variant: int = 0) -> dict[str, Any]:
    if family not in _MUTATION_FAMILIES:
        raise SpecError(f"unsupported adversarial mutation family: {family}")
    if type(variant) is not int or isinstance(variant, bool) or variant < 0:
        raise SpecError("adversarial mutation variant must be a non-negative integer")
    schema = prompt.get("schema") if type(prompt) is dict else None
    if schema == "fleet.learning-promotion-event.v1":
        return _mutate_learning_event(prompt, family, variant)
    if schema == "fleet.security-event.v1":
        return _mutate_security_event(prompt, family, variant)
    raise SpecError(f"adversarial mutation does not support prompt schema {schema!r}")


def mutate_example(example: Example, *, family: str, variant: int = 0) -> AdversarialCandidate:
    _require_accepted_source(example)
    mutated_prompt = mutate_prompt(example.prompt, family=family, variant=variant)
    if digest(mutated_prompt) == digest(example.prompt):
        raise SpecError(
            f"adversarial mutation {family!r} produced no prompt change for {example.example_id!r}"
        )
    mutation = {
        "schema": "agoge.adversarial-mutation.v1",
        "family": family,
        "variant": variant,
        "generator": "hermes-agoge",
        "generator_version": "v1",
    }
    identity = digest(
        {
            "source_example_hash": example.content_hash,
            "mutation": mutation,
            "prompt_hash": digest(mutated_prompt),
        }
    ).removeprefix("sha256:")[:24]
    return AdversarialCandidate(
        candidate_id=f"adversarial-{identity}",
        competency=example.competency,
        prompt=mutated_prompt,
        expected=deepcopy(example.completion),
        provenance={
            "kind": "adversarial-mutation-candidate",
            "review_state": "generated",
            "training_use": "candidate-only",
            "runtime_binding": "requires-regeneration",
            "source_example_id": example.example_id,
            "source_example_hash": example.content_hash,
            "source_prompt_hash": digest(example.prompt),
            "source_provenance_hash": digest(example.provenance),
            "mutation": mutation,
        },
    )


def mutate_examples(
    examples: Iterable[Example],
    *,
    student_root: Path,
    families: Iterable[str],
    variants_per_family: int = 1,
) -> list[AdversarialCandidate]:
    source_examples = list(examples)
    if not source_examples:
        raise SpecError("adversarial mutation requires at least one source example")
    if type(variants_per_family) is not int or isinstance(variants_per_family, bool):
        raise SpecError("variants_per_family must be an integer")
    if variants_per_family < 1:
        raise SpecError("variants_per_family must be at least one")
    requested_families = list(families)
    if not requested_families:
        raise SpecError("adversarial mutation requires at least one mutation family")
    unknown = sorted(set(requested_families) - _MUTATION_FAMILIES)
    if unknown:
        raise SpecError(f"unsupported adversarial mutation families: {unknown}")

    # A sealed Exam prompt may never be used as the source of this candidate generator.
    assert_no_registered_exam_overlap(student_root=student_root, examples=source_examples)

    generated: list[AdversarialCandidate] = []
    seen_hashes: set[str] = set()
    for example in sorted(source_examples, key=lambda item: item.example_id):
        _require_accepted_source(example)
        for family in requested_families:
            for variant in range(variants_per_family):
                try:
                    candidate = mutate_example(example, family=family, variant=variant)
                except SpecError as exc:
                    # A family may be intentionally inapplicable to one closed event schema,
                    # or a deterministic perturbation may be a no-op for a particular shape.
                    message = str(exc)
                    if (
                        "cannot preserve the closed Fleet event semantics" in message
                        or "produced no prompt change" in message
                    ):
                        continue
                    raise
                prompt_hash = digest(candidate.prompt)
                if prompt_hash in seen_hashes:
                    continue
                seen_hashes.add(prompt_hash)
                generated.append(candidate)
    if not generated:
        raise SpecError("adversarial mutation produced no candidates")

    # A generated candidate must also remain distinct from every registered sealed Exam prompt.
    protected_examples = [
        Example(
            example_id=candidate.candidate_id,
            competency=candidate.competency,
            prompt=candidate.prompt,
            completion=candidate.expected,
            provenance={"review_state": "generated", "training_use": "candidate-only"},
        )
        for candidate in generated
    ]
    assert_no_registered_exam_overlap(student_root=student_root, examples=protected_examples)
    return generated
