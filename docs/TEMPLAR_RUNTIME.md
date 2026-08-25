# Templar Local Runtime

Agoge can serve a graduated-candidate Templar classifier as a persistent local evaluator for Hermes Fleet.

The runtime deliberately keeps model packaging outside Fleet. Fleet sends one bound `fleet.templar-evaluation-request.v1` over a private Unix socket. Agoge independently verifies the request/event/evaluation bindings, projects the supported Fleet event, runs the prepared sequence-classification adapter, applies the content-addressed calibration policy when configured, and returns only `fleet.templar-backend-response.v1`.

Fleet remains the authority boundary. An Agoge response never grants authority. Fleet validates the response binding again and its existing `TemplarCore` fails closed if the service is missing, slow, malformed, stale, or request-substituted.

## Start manually

```bash
python -m agoge templar-serve \
  --run /srv/hermes-agoge/runs/templar-runtime-transfer-corrective-v2 \
  --calibration /srv/hermes-agoge/students/templar/calibration.json \
  --socket /run/hermes/templar.sock
```

The model is loaded before the socket is created. Socket creation therefore acts as the readiness boundary. The socket is created with mode `0600` and removed on orderly SIGTERM/SIGINT shutdown.

## Supervisor shape

`deploy/systemd/hermes-templar.service.example` is an example systemd unit. Copy it into deployment configuration rather than installing it blindly. Paths, user/group ownership, and device visibility are operator policy.

The service should be supervised independently of Fleet. Fleet does not start or restart Templar and does not know adapter/model filesystem paths.

## Failure semantics

Expected Fleet behavior is conservative:

- evaluator available and valid: normal ALLOW/DENY/REVIEW advisory verdict;
- evaluator missing/crashed: Fleet `DENY`, reason `evaluator-failure`;
- evaluator exceeds Fleet deadline: Fleet `DENY`, reason `evaluator-timeout`;
- malformed or request-substituted response: Fleet fail-closed verdict;
- every Templar verdict has `authority=none`.

A warmed local Qwen3-0.6B corrective-v2 runtime has been measured at roughly 47-61 ms for the full Fleet -> Unix socket -> Agoge -> model -> Fleet round trip on Katana. Cold one-shot loading is intentionally not the production path.

## Current graduation status

This runtime is still a candidate, not a production-graduated model. Current evidence includes internal held-out, reviewable fresh-transfer, and Psalmbox-held external-hidden adversarial Exams with zero calibrated false-ALLOWs, but broader hidden evidence and full Fleet regression/integration remain required.
