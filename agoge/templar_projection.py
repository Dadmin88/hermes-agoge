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
                "reason_codes": _sorted_strings(row.get("reason_codes"), "quarantine reason codes"),
                "verification_state": row.get("verification_state"),
                "verification_present": row.get("verification_digest") is not None,
            }
        )

    projection: dict[str, object] = {
        "schema": "agoge.templar-security-projection.v1",
        "source_schema": "fleet.security-event.v1",
        "request": {
            "principal_kind": principal.get("kind"),
            "requested_tools": _sorted_strings(request.get("requested_tools"), "requested tools"),
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


def _scope_kind(value: object, label: str) -> str:
    if type(value) is not dict:
        raise SpecError(f"Templar promotion projection {label} is malformed")
    for key in ("kind", "scope_kind"):
        candidate = value.get(key)
        if type(candidate) is str and candidate:
            return candidate
    raise SpecError(f"Templar promotion projection {label} kind is missing")


def _project_promotion_material(value: object) -> dict[str, object]:
    if type(value) is not dict or value.get("schema") != "fleet.promotion-evaluation-material.v1":
        raise SpecError("Templar promotion projection evaluation material is invalid")
    kind = value.get("kind")
    if kind == "memory":
        if set(value) != {"schema", "kind", "content_hash", "bytes", "text"}:
            raise SpecError("Templar promotion memory material has an invalid closed schema")
        text = value.get("text")
        if type(text) is not str:
            raise SpecError("Templar promotion memory text is invalid")
        return {"kind": "memory", "text": text}
    if kind == "skill":
        if set(value) != {"schema", "kind", "content_hash", "files"}:
            raise SpecError("Templar promotion skill material has an invalid closed schema")
        raw_files = value.get("files")
        if type(raw_files) is not list:
            raise SpecError("Templar promotion skill files are invalid")
        files: list[dict[str, str]] = []
        for item in raw_files:
            if type(item) is not dict or set(item) != {"path", "sha256", "bytes", "text"}:
                raise SpecError("Templar promotion skill file has an invalid closed schema")
            path = item.get("path")
            text = item.get("text")
            if type(path) is not str or type(text) is not str:
                raise SpecError("Templar promotion skill file text/path is invalid")
            files.append({"path": path, "text": text})
        return {"kind": "skill", "files": files}
    raise SpecError(f"Templar promotion material kind is unsupported: {kind!r}")


def _project_learning_promotion_event(event: dict[str, Any]) -> dict[str, object]:
    required = {
        "schema",
        "request_hash",
        "request",
        "evaluation_categories",
        "risk_signals",
        "authority",
    }
    if set(event) != required or event.get("schema") != "fleet.learning-promotion-event.v1":
        raise SpecError("Templar promotion projection requires a closed Fleet learning event")
    if event.get("authority") != "none":
        raise SpecError("Templar promotion event unexpectedly carries authority")
    request = event.get("request")
    if type(request) is not dict or request.get("schema") != "fleet.learning-promotion-request.v1":
        raise SpecError("Templar promotion projection request is invalid")
    request_required = {
        "schema",
        "subject_kind",
        "subject_key",
        "source_owner_principal_id",
        "agent_instance_id",
        "source_scope",
        "target_scope",
        "source_content_hash",
        "approved_content_hash",
        "candidate_hash",
        "administrator",
        "policy_digest",
        "sanitized",
        "evaluation_material",
        "verification_digest",
        "expected_current_promotion_id",
        "authority",
    }
    request_keys = set(request)
    current_request_required = request_required | {"source_execution_id"}
    if (
        request_keys not in (request_required, current_request_required)
        or request.get("authority") != "none"
    ):
        raise SpecError("Templar promotion projection request has an invalid closed schema")
    if "source_execution_id" in request:
        source_execution_id = request.get("source_execution_id")
        if type(source_execution_id) is not str or not source_execution_id:
            raise SpecError("Templar promotion projection source execution id is invalid")
    sanitized = request.get("sanitized")
    if type(sanitized) is not bool:
        raise SpecError("Templar promotion projection sanitized flag is invalid")
    administrator = request.get("administrator")
    if type(administrator) is not dict:
        raise SpecError("Templar promotion projection administrator is invalid")
    administrator_kind = administrator.get("kind")
    if type(administrator_kind) is not str or not administrator_kind:
        raise SpecError("Templar promotion projection administrator kind is invalid")
    subject_kind = request.get("subject_kind")
    if type(subject_kind) is not str or not subject_kind:
        raise SpecError("Templar promotion projection subject kind is invalid")
    categories = _sorted_strings(event.get("evaluation_categories"), "promotion categories")
    signals = _sorted_strings(event.get("risk_signals"), "promotion risk signals")
    return {
        "schema": "agoge.templar-learning-promotion-projection.v1",
        "source_schema": "fleet.learning-promotion-event.v1",
        "subject_kind": subject_kind,
        "source_scope_kind": _scope_kind(request.get("source_scope"), "source scope"),
        "target_scope_kind": _scope_kind(request.get("target_scope"), "target scope"),
        "administrator_kind": administrator_kind,
        "sanitized": sanitized,
        "verification_present": request.get("verification_digest") is not None,
        "expected_current_promotion_present": request.get("expected_current_promotion_id")
        is not None,
        "evaluation_categories": categories,
        "risk_signals": signals,
        "evaluation_material": _project_promotion_material(request.get("evaluation_material")),
    }


def project_templar_event(event: dict[str, Any]) -> dict[str, object]:
    schema = event.get("schema") if type(event) is dict else None
    if schema == "fleet.security-event.v1":
        return _project_security_event(event)
    if schema == "fleet.learning-promotion-event.v1":
        return _project_learning_promotion_event(event)
    raise SpecError(f"Templar model projection does not support event schema {schema!r}")
