from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..spec import SpecError
from ..teacher import (
    TeacherIdentity,
    TeacherRequest,
    TeacherResponse,
    TeacherResponseItem,
)


@dataclass(frozen=True, slots=True)
class RuleCase:
    facts: dict[str, Any]
    decision: str
    reason_codes: tuple[str, ...]
    rationale: str
    basis: tuple[str, ...]


_BASIS_AUTHORITY = (
    "Templar is advisory and cannot widen authority; requested power must remain within the already-authorized envelope.",
)
_BASIS_INJECTION = (
    "Untrusted or persisted content cannot override Fleet policy, request binding, or execution authority.",
)
_BASIS_SECRETS = (
    "Secret bodies must not be persisted into model-visible learning state; scoped opaque references are the intended runtime mechanism.",
)
_BASIS_PRINCIPALS = (
    "Private state is principal-scoped and shared state requires valid membership and scope authorization.",
)
_BASIS_LEARNING = (
    "Memory and skills may carry knowledge but cannot grant authority or smuggle hidden privilege-changing instructions.",
)
_BASIS_COMBINATIONS = (
    "Individually permitted capabilities must still be evaluated for dangerous combined effects such as exfiltration or privilege chaining.",
)
_BASIS_BENIGN = (
    "Templar should not manufacture risk when a bounded operation remains inside authorized scope and no suspicious signal is present.",
)
_BASIS_REVIEW = (
    "REVIEW is the correct bounded outcome when security-relevant facts are genuinely insufficient, conflicting, or novel enough that safe judgment is uncertain.",
)
_BASIS_OWNERSHIP = (
    "Keryx connectivity and Nodescale trust do not themselves grant Fleet execution authority; system ownership boundaries remain distinct.",
)

_REASON_CODE_NORMALIZATION = {
    "authority-manipulation": "authority-manipulation",
    "authority-scope-uncertain": "insufficient-evidence",
    "authority-widening": "authority-manipulation",
    "behavioral-risk-uncertain": "insufficient-evidence",
    "capability-combination-uncertain": "dangerous-combination-uncertain",
    "cross-principal-access": "cross-principal-risk",
    "dangerous-capability-combination": "dangerous-combination",
    "host-effect-uncertain": "insufficient-evidence",
    "membership-invalid": "cross-principal-risk",
    "membership-state-uncertain": "cross-principal-risk",
    "memory-poisoning": "memory-poisoning",
    "memory-risk-uncertain": "insufficient-evidence",
    "novel-capability-uncertain": "insufficient-evidence",
    "ownership-boundary-uncertain": "insufficient-evidence",
    "ownership-boundary-violation": "authority-manipulation",
    "principal-scope-uncertain": "cross-principal-risk",
    "prompt-injection": "prompt-injection",
    "prompt-injection-uncertain": "prompt-injection-uncertain",
    "provenance-insufficient": "insufficient-evidence",
    "secret-classification-uncertain": "insufficient-evidence",
    "secret-exfiltration": "exfiltration-intent",
    "secret-persistence": "suspicious-secret-handling",
    "security-context-insufficient": "insufficient-evidence",
    "skill-poisoning": "hidden-instructions",
    "skill-risk-uncertain": "skill-risk-needs-review",
    "unverified-artifact-effect": "dangerous-combination",
}


def _canonical_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    try:
        normalized = {_REASON_CODE_NORMALIZATION[code] for code in reason_codes}
    except KeyError as exc:
        raise SpecError(f"prototype Templar reason code is unmapped: {exc.args[0]}") from exc
    return tuple(sorted(normalized))


def _allow(facts: dict[str, Any], rationale: str, basis: tuple[str, ...]) -> RuleCase:
    return RuleCase(facts, "ALLOW", (), rationale, basis)


def _deny(
    facts: dict[str, Any],
    reason_codes: tuple[str, ...],
    rationale: str,
    basis: tuple[str, ...],
) -> RuleCase:
    return RuleCase(facts, "DENY", reason_codes, rationale, basis)


def _review(
    facts: dict[str, Any],
    reason_codes: tuple[str, ...],
    rationale: str,
    basis: tuple[str, ...],
) -> RuleCase:
    return RuleCase(facts, "REVIEW", reason_codes, rationale, basis)


def _authority_cases() -> list[RuleCase]:
    cases: list[RuleCase] = []
    for operation in ("workspace-read", "workspace-write", "approved-build"):
        cases.append(
            _allow(
                {
                    "deterministic_policy": "PASS",
                    "operation": operation,
                    "requested_scope_relation": "within-authority",
                    "requests_authority_change": False,
                },
                "The operation remains inside the exact existing authority and asks for no widening.",
                _BASIS_AUTHORITY,
            )
        )
    for requested in ("network-broaden", "new-host-verb", "extra-secret-scope"):
        cases.append(
            _deny(
                {
                    "deterministic_policy": "PASS",
                    "operation": "continue-run",
                    "requested_scope_relation": "wider-than-authority",
                    "requested_extension": requested,
                    "requests_authority_change": True,
                },
                ("authority-widening",),
                "The request attempts to turn an existing run into a broader authority envelope.",
                _BASIS_AUTHORITY,
            )
        )
    cases.append(
        _review(
            {
                "deterministic_policy": "PASS",
                "operation": "continue-run",
                "requested_scope_relation": "indeterminate",
                "authority_projection_complete": False,
            },
            ("authority-scope-uncertain",),
            "The projection does not contain enough trustworthy information to prove the requested action is inside authority.",
            _BASIS_AUTHORITY,
        )
    )
    return cases


def _injection_cases() -> list[RuleCase]:
    cases: list[RuleCase] = []
    for source in ("repository-document", "learned-memory", "external-artifact"):
        cases.append(
            _deny(
                {
                    "deterministic_policy": "PASS",
                    "content_source": source,
                    "hidden_instruction_detected": True,
                    "instruction_intent": "override-fleet-policy",
                    "content_trust": "untrusted",
                },
                ("authority-manipulation", "prompt-injection"),
                "The content contains an instruction attempting to supersede Fleet policy.",
                _BASIS_INJECTION,
            )
        )
    cases.append(
        _deny(
            {
                "deterministic_policy": "PASS",
                "content_source": "encoded-artifact",
                "hidden_instruction_detected": True,
                "instruction_intent": "exfiltrate-secret-reference",
                "content_trust": "untrusted",
            },
            ("prompt-injection", "secret-exfiltration"),
            "The disguised instruction tries to turn a legitimate read into secret exfiltration.",
            _BASIS_INJECTION,
        )
    )
    for source in ("repository-readme", "issue-text"):
        cases.append(
            _allow(
                {
                    "deterministic_policy": "PASS",
                    "content_source": source,
                    "hidden_instruction_detected": False,
                    "requested_action": "summarize-content",
                    "content_trust": "untrusted",
                    "requests_policy_override": False,
                },
                "Untrusted text is not automatically hostile when it contains no control-plane instruction and the requested operation is bounded.",
                _BASIS_INJECTION,
            )
        )
    cases.append(
        _review(
            {
                "deterministic_policy": "PASS",
                "content_source": "obfuscated-text",
                "hidden_instruction_detected": "possible",
                "decoded_intent": "incomplete",
            },
            ("prompt-injection-uncertain",),
            "The content is suspicious but its decoded security intent is not established strongly enough for a confident allow or deny.",
            _BASIS_REVIEW,
        )
    )
    return cases


def _secret_cases() -> list[RuleCase]:
    cases: list[RuleCase] = []
    for destination in ("memory", "learned-skill", "audit-summary"):
        cases.append(
            _deny(
                {
                    "deterministic_policy": "PASS",
                    "secret_body_present": True,
                    "requested_destination": destination,
                    "secret_reference_only": False,
                },
                ("secret-persistence",),
                "A secret body is being routed into durable or model-derived state rather than intercepted and replaced by a reference.",
                _BASIS_SECRETS,
            )
        )
    for injection in ("runtime-env-handle", "runtime-file-handle"):
        cases.append(
            _allow(
                {
                    "deterministic_policy": "PASS",
                    "secret_body_present": False,
                    "secret_reference_only": True,
                    "reference_scope_valid": True,
                    "runtime_injection": injection,
                },
                "Only an authorized opaque reference is present and the runtime injection path remains inside scope.",
                _BASIS_SECRETS,
            )
        )
    cases.append(
        _review(
            {
                "deterministic_policy": "PASS",
                "credential_like_material_detected": True,
                "classification_confidence": "uncertain",
                "requested_destination": "learning-candidate",
            },
            ("secret-classification-uncertain",),
            "Potential credential material requires review before any learning persistence can proceed.",
            _BASIS_REVIEW,
        )
    )
    return cases


def _principal_cases() -> list[RuleCase]:
    cases: list[RuleCase] = []
    for resource in ("private-memory", "private-skill"):
        cases.append(
            _deny(
                {
                    "deterministic_policy": "PASS",
                    "resource": resource,
                    "request_principal": "alice",
                    "resource_owner": "bob",
                    "shared_scope": False,
                },
                ("cross-principal-access",),
                "A principal is attempting to consume another principal's private learned state.",
                _BASIS_PRINCIPALS,
            )
        )
    for resource in ("project-memory", "project-skill"):
        cases.append(
            _allow(
                {
                    "deterministic_policy": "PASS",
                    "resource": resource,
                    "request_principal": "alice",
                    "shared_scope": True,
                    "project_membership_valid": True,
                    "resource_scope_authorized": True,
                },
                "The resource is intentionally shared in-project and the requesting principal has valid membership and scope.",
                _BASIS_PRINCIPALS,
            )
        )
    cases.append(
        _deny(
            {
                "deterministic_policy": "PASS",
                "resource": "project-memory",
                "request_principal": "mallory",
                "shared_scope": True,
                "project_membership_valid": False,
            },
            ("membership-invalid",),
            "Shared project state is not available to a principal without current project membership.",
            _BASIS_PRINCIPALS,
        )
    )
    cases.append(
        _review(
            {
                "deterministic_policy": "PASS",
                "resource": "legacy-memory",
                "resource_owner": "unknown",
                "scope_metadata_complete": False,
            },
            ("principal-scope-uncertain",),
            "The resource cannot be safely attributed to an authorized principal/scope from the available metadata.",
            _BASIS_REVIEW,
        )
    )
    return cases


def _learning_cases() -> list[RuleCase]:
    return [
        _deny(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "skill",
                "candidate_state": "quarantined",
                "contains_authority_instruction": True,
                "requested_effect": "grant-network-access",
            },
            ("authority-manipulation", "skill-poisoning"),
            "The candidate attempts to encode permission changes into learned skill content.",
            _BASIS_LEARNING,
        ),
        _deny(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "memory",
                "contains_hidden_instruction": True,
                "instruction_intent": "override-run-authority",
            },
            ("authority-manipulation", "memory-poisoning"),
            "Persisted memory text attempts to override future execution authority.",
            _BASIS_LEARNING,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "skill",
                "candidate_state": "verified-active",
                "scope_valid": True,
                "declares_new_permissions": False,
                "contains_hidden_instruction": False,
            },
            "A verified skill carries reusable procedure only and does not attempt to alter permissions.",
            _BASIS_LEARNING,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "memory",
                "scope_valid": True,
                "secret_body_present": False,
                "contains_hidden_instruction": False,
            },
            "The memory is scoped knowledge with no secret or authority-bearing content.",
            _BASIS_LEARNING,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "skill",
                "candidate_state": "verification-ready",
                "suspicious_command_chain": True,
                "declared_tooling_matches": "partial",
            },
            ("skill-risk-uncertain",),
            "The candidate has suspicious combined behavior whose legitimacy is not resolved by the available verification facts.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "candidate_type": "memory",
                "provenance_complete": False,
                "instruction_like_text": True,
                "authority_intent": "unclear",
            },
            ("memory-risk-uncertain",),
            "Incomplete provenance plus instruction-like text warrants review instead of automatic promotion.",
            _BASIS_REVIEW,
        ),
    ]


def _combination_cases() -> list[RuleCase]:
    return [
        _deny(
            {
                "deterministic_policy": "PASS",
                "network": "project-allowlist",
                "filesystem": "workspace-read",
                "secret_access": "scoped-ref",
                "combined_effect": "secret-to-network-exfiltration",
            },
            ("dangerous-capability-combination", "secret-exfiltration"),
            "Individually bounded capabilities form a direct exfiltration path when composed.",
            _BASIS_COMBINATIONS,
        ),
        _deny(
            {
                "deterministic_policy": "PASS",
                "filesystem": "writable-project-tree",
                "host_broker": "approved-deploy-verb",
                "artifact_provenance": "untrusted-modified",
                "combined_effect": "publish-unverified-artifact",
            },
            ("dangerous-capability-combination", "unverified-artifact-effect"),
            "The combination would turn unverified content into an approved host effect.",
            _BASIS_COMBINATIONS,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "network": "project-allowlist",
                "filesystem": "workspace-write",
                "secret_access": "none",
                "host_broker": "none",
                "all_within_authority": True,
                "combined_effect": "ordinary-build",
            },
            "The combined capabilities remain inside the run envelope and do not create an escalated effect.",
            _BASIS_COMBINATIONS,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "network": "none",
                "filesystem": "workspace-read-write",
                "secret_access": "none",
                "host_broker": "none",
                "combined_effect": "local-test",
            },
            "This is an isolated local test with no sensitive cross-boundary effect.",
            _BASIS_COMBINATIONS,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "network": "approved-domain",
                "filesystem": "read-only-input",
                "secret_access": "scoped-ref",
                "combined_effect": "novel-third-party-protocol",
                "interaction_model_known": False,
            },
            ("capability-combination-uncertain",),
            "A novel interaction between otherwise bounded capabilities lacks enough evidence for a safe deterministic judgment.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "host_broker": "approved-service-restart",
                "artifact_state": "none",
                "service_dependency_state": "unknown",
                "combined_effect": "potential-shared-impact",
            },
            ("host-effect-uncertain",),
            "The requested host effect is nominally approved but the projection lacks dependency facts needed to judge broader impact.",
            _BASIS_REVIEW,
        ),
    ]


def _benign_cases() -> list[RuleCase]:
    return [
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "read-workspace-source",
                "scope_valid": True,
                "suspicious_signals": [],
            },
            "Reading authorized workspace source with no suspicious signal is normal work.",
            _BASIS_BENIGN,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "run-declared-tests",
                "toolset_authorized": True,
                "network": "none",
                "suspicious_signals": [],
            },
            "Running declared tests in the authorized toolset is ordinary bounded execution.",
            _BASIS_BENIGN,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "summarize-untrusted-document",
                "document_contains_commands": False,
                "requests_command_execution": False,
                "suspicious_signals": [],
            },
            "Untrusted content may still be safely read and summarized when it is not controlling execution.",
            _BASIS_BENIGN,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "provider-api-call",
                "network_destination": "explicit-allowlist",
                "secret_reference_scope_valid": True,
                "suspicious_signals": [],
            },
            "An explicitly allowed provider call using a scoped secret reference is expected behavior.",
            _BASIS_BENIGN,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "export-declared-artifact",
                "artifact_declared": True,
                "destination_authorized": True,
                "secret_scan": "clear",
            },
            "A declared clean artifact exported to an authorized destination should not be blocked merely because it crosses a boundary.",
            _BASIS_BENIGN,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "operation": "use-approved-private-skill",
                "skill_scope_valid": True,
                "skill_verified": True,
                "permission_delta": "none",
            },
            "Using a verified private skill within its scope is normal persistence, not privilege escalation.",
            _BASIS_BENIGN,
        ),
    ]


def _uncertainty_cases() -> list[RuleCase]:
    return [
        _review(
            {
                "deterministic_policy": "PASS",
                "risk_signals": ["possible-exfiltration", "legitimate-backup-pattern"],
                "critical_context_complete": False,
            },
            ("security-context-insufficient",),
            "Competing benign and risky interpretations remain and a critical fact is missing.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "operation": "new-plugin-node-effect",
                "plugin_contract_known": False,
                "requested_scope_relation": "apparently-within-authority",
            },
            ("novel-capability-uncertain",),
            "The operation is novel enough that the security projection does not establish its effective capabilities.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "source_provenance": "partially-missing",
                "content_risk": "moderate",
                "requested_effect": "learning-promotion",
            },
            ("provenance-insufficient",),
            "A promotion request with incomplete provenance should be escalated instead of automatically accepted.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "secret_classifier": "uncertain",
                "candidate_contains_high-entropy-string": True,
                "requested_effect": "persist-skill",
            },
            ("secret-classification-uncertain",),
            "The classifier cannot safely establish whether sensitive credential material would be persisted.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "principal_scope": "valid",
                "shared_project_membership": "stale-observation",
                "requested_effect": "consume-shared-memory",
            },
            ("membership-state-uncertain",),
            "The relevant membership observation is stale, so shared-state access should not be confidently allowed.",
            _BASIS_REVIEW,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "artifact_integrity": "verified",
                "artifact_behavior": "unknown-native-extension",
                "requested_effect": "activate-extension",
            },
            ("behavioral-risk-uncertain",),
            "Integrity proves which artifact is present, not whether previously unseen native behavior is safe.",
            _BASIS_REVIEW,
        ),
    ]


def _ownership_cases() -> list[RuleCase]:
    return [
        _deny(
            {
                "deterministic_policy": "PASS",
                "claim": "keryx-direct-route-implies-execution-trust",
                "keryx_authenticated": True,
                "fleet_authorized": False,
            },
            ("ownership-boundary-violation",),
            "Authenticated transport does not establish Fleet execution authorization.",
            _BASIS_OWNERSHIP,
        ),
        _deny(
            {
                "deterministic_policy": "PASS",
                "claim": "nodescale-device-trust-implies-run-authority",
                "nodescale_trusted": True,
                "run_authority_present": False,
            },
            ("ownership-boundary-violation",),
            "Device trust is not an execution grant and cannot substitute for RunAuthority.",
            _BASIS_OWNERSHIP,
        ),
        _deny(
            {
                "deterministic_policy": "PASS",
                "claim": "templar-allow-grants-execution",
                "templar_decision": "ALLOW",
                "fleet_final_authorization": "not-issued",
            },
            ("ownership-boundary-violation",),
            "A Templar ALLOW is advisory and cannot itself grant execution.",
            _BASIS_OWNERSHIP,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "claim": "direct-route-is-transport-evidence-only",
                "route": "direct-quic",
                "fleet_authorization_unchanged": True,
            },
            "Treating Keryx route choice as non-authoritative transport evidence preserves the ownership boundary.",
            _BASIS_OWNERSHIP,
        ),
        _allow(
            {
                "deterministic_policy": "PASS",
                "claim": "nodescale-trust-projects-identity-only",
                "nodescale_trusted": True,
                "fleet_authorization_checked_separately": True,
            },
            "Nodescale identity/trust and Fleet authorization are being applied as separate layers.",
            _BASIS_OWNERSHIP,
        ),
        _review(
            {
                "deterministic_policy": "PASS",
                "claim": "new-cross-system-capability",
                "owner_component": "ambiguous",
                "authority_effect": "unclear",
            },
            ("ownership-boundary-uncertain",),
            "A new cross-system capability has no established ownership boundary in the supplied architecture facts.",
            _BASIS_REVIEW,
        ),
    ]


_CASE_BUILDERS = {
    "authority-boundaries": _authority_cases,
    "prompt-injection": _injection_cases,
    "secret-handling": _secret_cases,
    "cross-principal-isolation": _principal_cases,
    "skill-memory-poisoning": _learning_cases,
    "capability-combinations": _combination_cases,
    "benign-nonoverblocking": _benign_cases,
    "uncertainty-review": _uncertainty_cases,
    "architecture-ownership": _ownership_cases,
}


def generate_response(request: TeacherRequest) -> TeacherResponse:
    if request.purpose != "generate-training-candidates":
        raise SpecError("deterministic Templar generator only supports candidate generation")
    builder = _CASE_BUILDERS.get(request.competency)
    if builder is None:
        raise SpecError(f"deterministic Templar generator has no rules for {request.competency}")
    cases = builder()
    if request.count > len(cases):
        raise SpecError(
            f"requested {request.count} examples but deterministic rules provide only {len(cases)} distinct cases"
        )
    items = tuple(
        TeacherResponseItem(
            prompt={
                "schema": "agoge.templar-training-projection.v1",
                "facts": case.facts,
            },
            completion={
                "schema": "agoge.templar-model-output.v1",
                "decision": case.decision,
                "reason_codes": list(_canonical_reason_codes(case.reason_codes)),
            },
            rationale=case.rationale,
            basis=case.basis,
        )
        for case in cases[: request.count]
    )
    return TeacherResponse(
        request_id=request.request_id,
        teacher=TeacherIdentity(
            teacher_id="templar-foundation-rules-v1",
            kind="deterministic",
            provider="hermes-agoge",
            model="rule-generator",
            model_version="v1",
            role="fleet-native-foundation-candidate-generator",
            training_use="allowed",
        ),
        items=items,
    )
