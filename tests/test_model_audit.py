from __future__ import annotations

from types import SimpleNamespace

import pytest

from agoge.model_audit import ModelAuditCriteria, audit_model_info
from agoge.spec import SpecError


def _info(*, license_name: str | None = "apache-2.0", gated: bool | str = False):
    card = {"license": license_name, "base_model": ["example/base"]} if license_name else {}
    return SimpleNamespace(
        id="example/model",
        sha="a" * 40,
        pipeline_tag="text-generation",
        library_name="transformers",
        gated=gated,
        private=False,
        downloads=123,
        likes=45,
        tags=["transformers", "safetensors"],
        safetensors=SimpleNamespace(total=750_000_000),
        card_data=SimpleNamespace(to_dict=lambda: card),
        config={"architectures": ["ExampleForCausalLM"], "model_type": "example"},
        siblings=[SimpleNamespace(rfilename="model.safetensors", size=1_500_000_000)],
    )


def test_audit_marks_known_allowed_candidate_benchmark_eligible() -> None:
    criteria = ModelAuditCriteria(
        pipeline_tag="text-generation",
        min_parameters=400_000_000,
        max_parameters=2_000_000_000,
        allowed_licenses=("apache-2.0",),
    )
    candidate = audit_model_info(_info(), criteria)
    assert candidate.status == "benchmark-eligible"
    assert candidate.reasons == ("metadata-policy-passed",)
    assert candidate.parameters == 750_000_000
    assert candidate.safetensors_bytes == 1_500_000_000
    assert candidate.revision == "a" * 40


def test_audit_fails_closed_on_gated_or_disallowed_license() -> None:
    criteria = ModelAuditCriteria(
        pipeline_tag="text-generation",
        min_parameters=400_000_000,
        max_parameters=2_000_000_000,
        allowed_licenses=("apache-2.0",),
    )
    gated = audit_model_info(_info(gated="manual"), criteria)
    assert gated.status == "rejected"
    assert "gated-model-not-allowed" in gated.reasons
    licensed = audit_model_info(_info(license_name="gemma"), criteria)
    assert licensed.status == "rejected"
    assert "license-not-allowed-by-audit-policy" in licensed.reasons


def test_audit_requires_license_policy_before_benchmarking() -> None:
    criteria = ModelAuditCriteria(
        pipeline_tag="text-generation",
        min_parameters=400_000_000,
        max_parameters=2_000_000_000,
    )
    candidate = audit_model_info(_info(), criteria)
    assert candidate.status == "review-required"
    assert "license-policy-not-specified" in candidate.reasons


def test_parameter_bounds_are_closed() -> None:
    with pytest.raises(SpecError, match="parameter bounds"):
        ModelAuditCriteria(
            pipeline_tag="text-generation",
            min_parameters=2_000_000_000,
            max_parameters=400_000_000,
        )
