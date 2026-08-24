# Templar Fleet Contract Snapshot

Templar production curriculum must match what the deployed Fleet evaluator can actually receive. Agoge therefore derives a contract snapshot from the Student's pinned Fleet Git revision instead of importing live Fleet modules or following moving `main`.

## Current pinned edition

- Student: `templar-v1`
- Fleet revision: `591ea20bb1b7268254ddeaffaf16a5f853aa2db5`
- Contract snapshot: `students/templar/fleet-contract.json`
- Snapshot hash: `sha256:14b1bc98ce7ad9844a209dec43dff556c48a7b1a065663727d669616f9a342b5`

The snapshot source-hashes and extracts closed dataclass fields/constants from:

- `hermes_fleet/security_event.py`;
- `hermes_fleet/templar.py`;
- `hermes_fleet/pre_execution_gate.py`;
- `hermes_fleet/learning_promotion_gate.py`.

Agoge does not import or execute those modules to build the snapshot.

## Actual Templar event families

The pinned Phase 20 core supports exactly:

- `fleet.security-event.v1`;
- `fleet.learning-promotion-event.v1`.

The Phase 19 security event contains the bounded run request plus four evaluator-facing fact families:

- `MemorySkillRisk`;
- `SecretInterceptionFact`;
- `PolicyMismatch`;
- `QuarantineSignal`.

The request carries principal, recipe, exact RunAuthority hash, target, requested/authorized tools, bounded resources/network posture, Fleet policy digest, and capability hash. Secret bodies and raw arbitrary prompt/memory/skill bodies are not part of this event contract.

## Templar-reachable distribution

Production corpus generation must model events Templar can actually receive. It must not treat an already hard-denied Fleet request as a normal model inference example: the Phase 22 gate stops after deterministic policy when a hard deny exists.

This is stricter than the original 24-example seed corpus, which intentionally exercised plumbing rather than a real runtime distribution. Seed/prototype examples remain valid only as development fixtures.

## Golden Phase 19 event

`students/templar/fixtures/security-event-golden.json` was produced by the pinned Fleet test fixture `tests/unit/test_security_event.py::event` through the real `SecurityEvent.from_run_authority(...)` implementation.

The resulting document was round-tripped through Fleet's own `security_event_from_dict(...)` parser before being copied into Agoge.

- request hash: `sha256:40dda288745ef2ee5e8512eddb5a545144d449448900b41fafadc73f846d8419`
- event/document hash: `sha256:5dcfa163d2276863469507ca25ab33f87ddc473d0a00915371aaf7743f888ba2`

The temporary detached Fleet worktree used to produce the fixture was removed immediately after validation.

## Model input boundary

The eventual Fleet backend adapter should keep request/evaluation binding deterministic outside the model. The specialist model does not need to generate or own:

- evaluation ID;
- request/event hash binding;
- Templar policy/evaluator identity;
- timestamps/deadlines;
- authority.

For the initial specialist design, the learned model's security input should be the supported sanitized Fleet event document, and its output remains only the bounded decision/reason-code payload. Fleet's Templar backend adapter reconstructs the exact `fleet.templar-backend-response.v1` around that learned judgment.

## Next production-curriculum step

Build event-family generators from the golden Fleet documents and validate generated variants against the pinned Fleet parsers. Training/exam partitioning must occur only after the generated examples have passed provenance, reachability, contract, independent review, and contamination checks.
