
## Proof: Fleet can call a persistent local Agoge Templar without granting model authority

Agoge now exposes the prepared calibrated Templar adapter through two local runtime modes. `templar-evaluate` is a one-shot stdin evaluator used to prove the exact Fleet request/response binding. `templar-serve` keeps the exact prepared adapter loaded and listens on a mode-0600 Unix-domain socket for bound Fleet requests.

The Agoge runtime independently verifies the closed `fleet.templar-evaluation-request.v1` schema, supported event schema, request/event/policy bindings, canonical event hash, evaluation ID, and deadline before inference. It projects the event through the same identity-free Templar projection used by training and Exams, predicts one closed disposition, applies the content-addressed calibration policy, and returns only `fleet.templar-backend-response.v1` with the original evaluation/request/event bindings.

Fleet integration was exercised through `TemplarCore` using generic no-shell subprocess and Unix-socket backend transports. Fleet continued to own response validation, verdict construction, timeout handling, and authority. A cold one-shot model invocation exceeded a 10-second Fleet evaluator deadline and Fleet produced an authority-free `DENY / evaluator-timeout / origin=core-fail-closed`, proving that slow model startup cannot authorize execution. With a 30-second integration deadline, the cold path completed successfully in ~6.66 seconds and returned an evaluator-origin REVIEW.

Keeping the model loaded behind the local Unix socket removed the cold-start penalty. The first request after service startup completed end to end in ~559 ms; the next warmed Fleet -> Unix socket -> Agoge -> calibrated Qwen3 classifier -> Fleet round trip completed in ~47 ms under a 1-second Fleet deadline. The returned verdict remained `authority=none` and `origin=evaluator`.

Agoge request-binding tests and Fleet transport tests additionally cover event/evaluation substitution rejection, unsupported/expired requests, shell-free subprocess invocation, malformed/oversized output, missing sockets, evaluator process failure, and timeout fail-closed behavior.

This is an integration proof, not production graduation. Fleet still needs an explicit deployment/configuration factory for the local runtime, service lifecycle supervision, full repository CI with optional dependencies, and end-to-end execution/learning-gate regression evidence before the persistent evaluator becomes a supported production path.
