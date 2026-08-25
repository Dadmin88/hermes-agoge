from __future__ import annotations

from copy import deepcopy

import pytest

from agoge.spec import SpecError, digest
from agoge.templar_runtime import _validate_request


def _request() -> dict[str, object]:
    event: dict[str, object] = {
        "schema": "fleet.security-event.v1",
        "request_hash": "sha256:" + "1" * 64,
        "request": {"policy_digest": "sha256:" + "2" * 64},
    }
    request: dict[str, object] = {
        "schema": "fleet.templar-evaluation-request.v1",
        "request_hash": event["request_hash"],
        "event_hash": digest(event),
        "fleet_policy_digest": "sha256:" + "2" * 64,
        "templar_policy": {
            "policy_id": "templar",
            "policy_version": "v1",
            "policy_digest": "sha256:" + "3" * 64,
        },
        "evaluator": {
            "evaluator_id": "agoge",
            "implementation_version": "v1",
            "model_provider": "local",
            "model_name": "model",
            "model_version": "v1",
        },
        "issued_at_ms": 2_000_000_000_000,
        "deadline_ms": 2_000_000_010_000,
        "event": event,
    }
    request["evaluation_id"] = digest(request)
    return request


def test_validate_request_accepts_exact_bound_fleet_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agoge.templar_runtime.time.time_ns", lambda: 1_999_999_999_000_000_000)
    request = _request()
    assert _validate_request(request) == request


def test_validate_request_rejects_event_or_evaluation_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agoge.templar_runtime.time.time_ns", lambda: 1_999_999_999_000_000_000)
    event_swap = deepcopy(_request())
    assert isinstance(event_swap["event"], dict)
    event_swap["event"]["schema"] = "fleet.learning-promotion-event.v1"
    with pytest.raises(SpecError, match="event hash"):
        _validate_request(event_swap)

    evaluation_swap = _request()
    evaluation_swap["evaluation_id"] = "sha256:" + "f" * 64
    with pytest.raises(SpecError, match="evaluation ID"):
        _validate_request(evaluation_swap)


def test_validate_request_rejects_expired_or_unsupported_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    monkeypatch.setattr("agoge.templar_runtime.time.time_ns", lambda: 2_000_000_020_000_000_000)
    with pytest.raises(SpecError, match="expired"):
        _validate_request(request)

    unsupported = _request()
    assert isinstance(unsupported["event"], dict)
    unsupported["event"]["schema"] = "fleet.future-event.v1"
    with pytest.raises(SpecError, match="unsupported"):
        _validate_request(unsupported)
