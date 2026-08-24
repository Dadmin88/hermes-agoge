from __future__ import annotations

from typing import Any

from .spec import SpecError


def _sorted_strings(value: object, label: str) -> list[str]:
    if type(value) is not list or not all(type(item) is str for item in value):
        raise SpecError(f"Templar projection {label} is invalid")
    return sorted(value)


def _project_security_event(event: dict[str, Any]) -> dict[str, object]:
    required = {
        "schema",
        "request_hash",
        "request",
        "memory_skill_risks",
        "secret_interceptions",
        "policy_mismatches",
        "quarantine_signals",
    }
    if set(event) != required or event.get("schema") != "fleet.security-event.v1":
        raise SpecError("Templar security projection requires a closed Fleet security event")
    request = event.get("request")
    if type(request) is not dict or request.get("schema") != "fleet.security-request.v1":
        raise SpecError("Templar security projection request is invalid")

    principal = request.get("principal")
    target = request.get("target")
    network = request.get("network")
    resources = request.get("resources")
    if not all(type(value) is dict for value in (principal, target, network, resources)):
        raise SpecError("Templar security projection request facts are malformed")
    projected_resources = {
        "cpu_millis": resources.get("cpu_millis"),
        "memory_bytes": resources.get("memory_bytes"),
        "pids_limit": resources.get("pids_limit"),
        "max_iterations": resources.get("max_iterations"),
        "deadline_ms": resources.get("deadline_ms"),
    }
    target_body = target.get("target")
    if type(target_body) is not dict:
        raise SpecError("Templar security projection target is malformed")
    destinations = network.get("destinations")
    if type(destinations) is not list:
        raise SpecError("Templar security projection network destinations are malformed")

    risk_rows: list[dict[str, object]] = []
    raw_risks = event.get("memory_skill_risks")
    if type(raw_risks) is not list:
        raise SpecError("Templar security projection memory/skill risks are malformed")
    for row in raw_risks:
        if type(row) is not dict:
            raise SpecError("Templar security projection risk row is malformed")
        risk_rows.append(
            {
                "subject_kind": row.get("subject_kind"),
                "scope_kind": row.get("scope_kind"),
                "risk_level": row.get("risk_level"),
                "signal_codes": _sorted_strings(row.get("signal_codes"), "risk signal codes"),
            }
        )

    secret_rows: list[dict[str, object]] = []
    raw_secrets = event.get("secret_interceptions")
    if type(raw_secrets) is not list:
        raise SpecError("Templar security projection secret interceptions are malformed")
    for row in raw_secrets:
        if type(row) is not dict:
            raise SpecError("Templar security projection secret row is malformed")
        count = row.get("detected_count")
        if type(count) is not int or isinstance(count, bool):
            raise SpecError("Templar security projection secret count is malformed")
        secret_rows.append(
            {
                "source_kind": row.get("source_kind"),
                "detected_kinds": _sorted_strings(
                    row.get("detected_kinds"), "detected secret kinds"
                ),
                "detected_count": count,
                "action": row.get("action"),
            }
        )

    mismatch_rows: list[dict[str, object]] = []
    raw_mismatches = event.get("policy_mismatches")
    if type(raw_mismatches) is not list:
        raise SpecError("Templar security projection policy mismatches are malformed")
    for row in raw_mismatches:
        if type(row) is not dict:
            raise SpecError("Templar security projection mismatch row is malformed")
        mismatch_rows.append({"code": row.get("code"), "subject": row.get("subject")})

    quarantine_rows: list[dict[str, object]] = []
    raw_quarantine = event.get("quarantine_signals")
    if type(raw_quarantine) is not list:
        raise SpecError("Templar security projection quarantine signals are malformed")
    for row in raw_quarantine:
        if type(row) is not dict:
            raise SpecError("Templar security projection quarantine row is malformed")
        quarantine_rows.append(
            {
                "state": row.get("state"),
                "reason_codes": _sorted_strings(
                    row.get("reason_codes"), "quarantine reason codes"
                ),
                "verification_state": row.get("verification_state"),
                "verification_present": row.get("verification_digest") is not None,
            }
        )

    projection: dict[str, object] = {
        "schema": "agoge.templar-security-projection.v1",
        "source_schema": "fleet.security-event.v1",
        "request": {
            "principal_kind": principal.get("kind"),
            "requested_tools": _sorted_strings(
                request.get("requested_tools"), "requested tools"
            ),
            "authorized_toolsets": _sorted_strings(
                request.get("authorized_toolsets"), "authorized toolsets"
            ),
            "resources": projected_resources,
            "network": {
                "mode": network.get("mode"),
                "destination_count": len(destinations),
                "approval_present": network.get("approval_ref") is not None,
            },
            "target_source": target_body.get("source"),
        },
        "memory_skill_risks": sorted(
            risk_rows,
            key=lambda row: (
                str(row["subject_kind"]),
                str(row["scope_kind"]),
                str(row["risk_level"]),
                tuple(row["signal_codes"]),
            ),
        ),
        "secret_interceptions": sorted(
            secret_rows,
            key=lambda row: (
                str(row["source_kind"]),
                str(row["action"]),
                tuple(row["detected_kinds"]),
                int(row["detected_count"]),
            ),
        ),
        "policy_mismatches": sorted(
            mismatch_rows, key=lambda row: (str(row["code"]), str(row["subject"]))
        ),
        "quarantine_signals": sorted(
            quarantine_rows,
            key=lambda row: (
                str(row["state"]),
                str(row["verification_state"]),
                tuple(row["reason_codes"]),
            ),
        ),
    }
    return projection


def project_templar_event(event: dict[str, Any]) -> dict[str, object]:
    schema = event.get("schema") if type(event) is dict else None
    if schema == "fleet.security-event.v1":
        return _project_security_event(event)
    raise SpecError(f"Templar model projection does not support event schema {schema!r}")
