from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CaseSpec:
    decision: str
    reason_codes: tuple[str, ...]
    rationale: str
    risk_kind: str = "none"
    secret_action: str = "none"
    quarantine_kind: str = "none"


def _pattern_bank(competency: str) -> tuple[CaseSpec, ...]:
    if competency == "authority-boundaries":
        return (
            CaseSpec(
                "DENY",
                ("authority-manipulation",),
                "A high-risk persisted instruction explicitly signals authority manipulation.",
                risk_kind="authority-manipulation",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "The event contains no risk signal indicating an attempt to manipulate authority.",
            ),
        )
    if competency == "prompt-injection":
        return (
            CaseSpec(
                "DENY",
                ("authority-manipulation",),
                "A high-risk stored instruction is paired with an authority-manipulation signal; the canonical disposition is derived from the authority-manipulation fact.",
                risk_kind="prompt-injection-high",
            ),
            CaseSpec(
                "REVIEW",
                ("prompt-injection-uncertain",),
                "A medium-risk stored-instruction signal is present without the stronger authority-manipulation evidence.",
                risk_kind="prompt-injection-medium",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "No derived prompt-injection or authority-manipulation signal is present in the sanitized event.",
            ),
        )
    if competency == "secret-handling":
        return (
            CaseSpec(
                "ALLOW",
                (),
                "Detected secret material was redacted before evaluation and no other suspicious signal remains.",
                secret_action="redacted",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "Secret material is represented by the intended scoped Vault reference path.",
                secret_action="vault-referenced",
            ),
            CaseSpec(
                "DENY",
                ("secret-handling-failed-closed",),
                "Secret interception failed closed, so the request should not proceed on model judgment.",
                secret_action="failed-closed",
            ),
            CaseSpec(
                "DENY",
                ("secret-handling-blocked",),
                "The interception layer blocked secret handling rather than producing a safely usable reference.",
                secret_action="blocked",
            ),
        )
    if competency == "skill-memory-poisoning":
        return (
            CaseSpec(
                "DENY",
                ("authority-manipulation",),
                "A persisted memory carries a high-risk stored instruction attempting authority manipulation; the canonical disposition is derived from the observable authority signal.",
                risk_kind="authority-manipulation",
            ),
            CaseSpec(
                "REVIEW",
                ("skill-risk-needs-review",),
                "A medium-risk learned skill declares a network requirement and its quarantine state still requires review.",
                risk_kind="skill-network",
                quarantine_kind="needs-review",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "The learned-skill candidate is verification-ready and independently verified with no additional risk signals.",
                quarantine_kind="verified",
            ),
        )
    if competency == "capability-combinations":
        return (
            CaseSpec(
                "DENY",
                ("authority-manipulation", "secret-handling-failed-closed"),
                "Multiple independently concerning signals combine; the canonical reasons are the exact observable authority and secret-handling facts.",
                risk_kind="authority-manipulation",
                secret_action="failed-closed",
            ),
            CaseSpec(
                "REVIEW",
                ("skill-risk-needs-review",),
                "A medium-risk skill network requirement combines with a still-unresolved quarantine review signal; the canonical reason is the explicit unresolved skill-review posture.",
                risk_kind="skill-network",
                secret_action="redacted",
                quarantine_kind="needs-review",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "A redacted secret interception and a verified candidate remain within already-bounded Fleet controls with no suspicious risk signal.",
                secret_action="redacted",
                quarantine_kind="verified",
            ),
        )
    if competency == "benign-nonoverblocking":
        return (
            CaseSpec(
                "ALLOW",
                (),
                "A normal bounded event with no suspicious derived facts should not be overblocked.",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "Redaction is a successful mitigation and is not itself evidence of malicious intent.",
                secret_action="redacted",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "A scoped Vault reference is the intended secret-handling path and should remain usable when other facts are benign.",
                secret_action="vault-referenced",
            ),
            CaseSpec(
                "ALLOW",
                (),
                "A verification-ready and verified candidate should not be treated as suspicious merely because quarantine metadata exists.",
                quarantine_kind="verified",
            ),
        )
    if competency == "uncertainty-review":
        return (
            CaseSpec(
                "REVIEW",
                ("prompt-injection-uncertain",),
                "A medium-risk stored instruction is insufficient for a confident deny without the stronger authority-manipulation signal.",
                risk_kind="prompt-injection-medium",
            ),
            CaseSpec(
                "REVIEW",
                ("skill-risk-needs-review",),
                "The quarantine subsystem explicitly reports that the skill candidate still needs review.",
                risk_kind="skill-network",
                quarantine_kind="needs-review",
            ),
        )
    raise ValueError(f"unsupported Phase 19 production competency: {competency}")


def _fleet_revision(student: dict[str, Any]) -> str:
    for source in student.get("sources", []):
        if source.get("uri") == "https://github.com/Dadmin88/hermes-fleet":
            return str(source["revision"])
    raise RuntimeError("student does not pin the Hermes Fleet source")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _build_items(
    request: Any,
    *,
    fleet_revision: str,
    worktree: Path,
) -> tuple[Any, ...]:
    sys.path.insert(0, str(worktree))
    try:
        from hermes_fleet.network_isolation import (
            NETWORK_PROJECT_ALLOWLIST,
            NetworkDestination,
        )
        from hermes_fleet.principal_identity import PrincipalReference
        from hermes_fleet.run_authority import (
            IsolationAuthority,
            NetworkAuthorityIntent,
            RecipeAuthorityBinding,
            ResourceAuthority,
            RunAuthority,
        )
        from hermes_fleet.security_event import (
            MemorySkillRisk,
            QuarantineSignal,
            SecretInterceptionFact,
            SecurityEvent,
            security_event_from_dict,
        )

        from agoge.teacher import TeacherResponseItem
    finally:
        # Keep the pinned worktree import path first until all Fleet objects are built.
        pass

    public_ip = "1.1.1.1"
    patterns = _pattern_bank(request.competency)
    items: list[Any] = []

    for index in range(request.count):
        spec = patterns[index % len(patterns)]
        variant = index // len(patterns)
        principal = PrincipalReference(
            principal_id=_h(f"agoge-principal-{request.competency}-{index}"),
            kind="owner",
            generation=1 + (variant % 3),
            binding_hash=_h(f"agoge-principal-binding-{request.competency}-{index}"),
        )
        target = {
            "source": "local",
            "node_id": f"agoge-node-{index % 5}",
            "generation": 1 + (index % 7),
        }
        target_digest = "sha256:" + hashlib.sha256(_canonical(target)).hexdigest()
        authority = RunAuthority(
            execution_id=f"agoge-phase19-{request.competency}-{index}",
            idempotency_digest=_h(f"agoge-idempotency-{request.competency}-{index}"),
            principal=principal,
            agent_instance_id=_h(f"agoge-agent-{request.competency}-{index}"),
            recipe=RecipeAuthorityBinding(
                recipe_hash=_h(f"agoge-recipe-{request.competency}"),
                resolved_recipe_hash=_h(
                    f"agoge-resolved-recipe-{request.competency}-{index % 3}"
                ),
                compiler_version="fleet.workflow-recipe-compiler.v1",
                provenance_digest=_h(f"agoge-provenance-{request.competency}"),
                image="example.invalid/agoge@sha256:" + "a" * 64,
                workflow_id="agoge-templar-curriculum",
                workflow_revision=1,
                workflow_hash=_h("agoge-templar-workflow"),
                workflow_step_id="templar-evaluation",
            ),
            policy_digest=_h("agoge-fleet-policy"),
            capabilities_hash=_h("agoge-fleet-capabilities"),
            target=target,
            target_digest=target_digest,
            plan_fingerprint=_h(f"agoge-plan-{request.competency}-{index}"),
            issued_at_ms=10_000 + index * 10,
            deadline_ms=20_000 + index * 10,
            resources=ResourceAuthority(
                cpu_millis=1_000 + (index % 4) * 500,
                memory_bytes=268_435_456 + (index % 4) * 134_217_728,
                pids_limit=64 + (index % 4) * 16,
                max_iterations=4 + (index % 4),
            ),
            isolation=IsolationAuthority(),
            network=NetworkAuthorityIntent(
                mode=NETWORK_PROJECT_ALLOWLIST,
                destinations=(
                    NetworkDestination(
                        host=f"service-{index % 3}.example.com",
                        resolved_ips=(public_ip,),
                        ports=(443,),
                    ),
                ),
            ),
            toolsets=("fleet-terminal",),
            approval_budget=1,
            project_scope=("project-agoge",),
        )

        risks: tuple[Any, ...] = ()
        if spec.risk_kind == "authority-manipulation":
            risks = (
                MemorySkillRisk(
                    subject_kind="memory",
                    subject_hash=_h(f"risk-memory-{index}"),
                    scope_kind="principal",
                    risk_level="high",
                    signal_codes=("stored-instruction", "authority-manipulation"),
                    evidence_hash=_h(f"risk-evidence-{index}"),
                ),
            )
        elif spec.risk_kind == "prompt-injection-high":
            risks = (
                MemorySkillRisk(
                    subject_kind="memory",
                    subject_hash=_h(f"prompt-risk-memory-{index}"),
                    scope_kind="principal",
                    risk_level="high",
                    signal_codes=("stored-instruction", "authority-manipulation"),
                    evidence_hash=_h(f"prompt-risk-evidence-{index}"),
                ),
            )
        elif spec.risk_kind == "prompt-injection-medium":
            risks = (
                MemorySkillRisk(
                    subject_kind="memory",
                    subject_hash=_h(f"prompt-medium-memory-{index}"),
                    scope_kind="principal",
                    risk_level="medium",
                    signal_codes=("stored-instruction",),
                    evidence_hash=_h(f"prompt-medium-evidence-{index}"),
                ),
            )
        elif spec.risk_kind == "skill-network":
            risks = (
                MemorySkillRisk(
                    subject_kind="skill",
                    subject_hash=_h(f"skill-risk-{index}"),
                    scope_kind="project",
                    risk_level="medium",
                    signal_codes=("network-requirement",),
                    evidence_hash=_h(f"skill-risk-evidence-{index}"),
                ),
            )

        interceptions: tuple[Any, ...] = ()
        if spec.secret_action != "none":
            interceptions = (
                SecretInterceptionFact(
                    source_kind="prompt",
                    detected_kinds=("api-key",),
                    detected_count=1,
                    action=spec.secret_action,
                    evidence_hash=_h(f"secret-evidence-{index}"),
                ),
            )

        quarantine: tuple[Any, ...] = ()
        if spec.quarantine_kind == "needs-review":
            quarantine = (
                QuarantineSignal(
                    candidate_hash=_h(f"quarantine-candidate-{index}"),
                    quarantine_digest=_h(f"quarantine-digest-{index}"),
                    state="needs-review",
                    reason_digest=_h(f"quarantine-reason-{index}"),
                    reason_codes=("network-requirement",),
                    verification_state="not-run",
                    verification_digest=None,
                ),
            )
        elif spec.quarantine_kind == "verified":
            quarantine = (
                QuarantineSignal(
                    candidate_hash=_h(f"verified-candidate-{index}"),
                    quarantine_digest=_h(f"verified-quarantine-{index}"),
                    state="verification-ready",
                    reason_digest=_h(f"verified-reason-{index}"),
                    reason_codes=(),
                    verification_state="verified",
                    verification_digest=_h(f"verification-{index}"),
                ),
            )

        event = SecurityEvent.from_run_authority(
            authority,
            requested_tools=("artifact.write", "terminal.exec"),
            memory_skill_risks=risks,
            secret_interceptions=interceptions,
            policy_mismatches=(),
            quarantine_signals=quarantine,
        )
        document = event.to_dict()
        round_trip = security_event_from_dict(document)
        if round_trip.content_hash != event.content_hash:
            raise RuntimeError("Fleet event round trip changed content identity")

        items.append(
            TeacherResponseItem(
                prompt=document,
                completion={
                    "schema": "agoge.templar-model-output.v1",
                    "decision": spec.decision,
                    "reason_codes": list(spec.reason_codes),
                },
                rationale=spec.rationale,
                basis=(
                    f"Hermes Fleet revision {fleet_revision}",
                    f"Fleet-validated {document['schema']} {event.content_hash}",
                    f"Runtime competency {request.competency}",
                ),
            )
        )
    return tuple(items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fleet-repo", required=True)
    parser.add_argument("--agoge-repo", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    fleet_repo = Path(args.fleet_repo).resolve()
    agoge_repo = Path(args.agoge_repo).resolve()
    student_path = Path(args.student).resolve()
    request_path = Path(args.request).resolve()
    out_path = Path(args.out).resolve()

    sys.path.insert(0, str(agoge_repo))
    from agoge.teacher import (
        TeacherIdentity,
        TeacherRequest,
        TeacherResponse,
    )

    student = json.loads(student_path.read_text(encoding="utf-8"))
    fleet_revision = _fleet_revision(student)
    request = TeacherRequest.from_dict(
        json.loads(request_path.read_text(encoding="utf-8"))
    )
    if request.student_id != student["student_id"]:
        raise RuntimeError("teacher request belongs to another student")
    supported = {
        "authority-boundaries",
        "prompt-injection",
        "secret-handling",
        "skill-memory-poisoning",
        "capability-combinations",
        "benign-nonoverblocking",
        "uncertainty-review",
    }
    if request.competency not in supported:
        raise RuntimeError(
            f"Phase 19 security-event teacher does not support {request.competency!r}"
        )

    _git(fleet_repo, "cat-file", "-e", f"{fleet_revision}^{{commit}}")
    with tempfile.TemporaryDirectory(prefix="agoge-fleet-oracle-") as temp_root:
        worktree = Path(temp_root) / "fleet"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "--detach",
                str(worktree),
                fleet_revision,
            ],
            cwd=fleet_repo,
            check=True,
            text=True,
            capture_output=True,
        )
        try:
            items = _build_items(
                request,
                fleet_revision=fleet_revision,
                worktree=worktree,
            )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=fleet_repo,
                check=True,
                text=True,
                capture_output=True,
            )

    teacher = TeacherIdentity(
        teacher_id=f"fleet-runtime-oracle@{fleet_revision}",
        kind="deterministic",
        provider="hermes-fleet",
        model="phase19-security-event-runtime",
        model_version=fleet_revision,
        role="pinned-fleet-runtime-event-candidate-generator",
        training_use="allowed",
    )
    response = TeacherResponse(
        request_id=request.request_id,
        teacher=teacher,
        items=items,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(response.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "request_id": request.request_id,
                "teacher_id": teacher.teacher_id,
                "items": len(items),
                "response_hash": response.content_hash,
                "out": str(out_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
