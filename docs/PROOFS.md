
## Proof: Fleet can call a persistent local Agoge Templar without granting model authority

Agoge now exposes the prepared calibrated Templar adapter through two local runtime modes. `templar-evaluate` is a one-shot stdin evaluator used to prove the exact Fleet request/response binding. `templar-serve` keeps the exact prepared adapter loaded and listens on a mode-0600 Unix-domain socket for bound Fleet requests.

The Agoge runtime independently verifies the closed `fleet.templar-evaluation-request.v1` schema, supported event schema, request/event/policy bindings, canonical event hash, evaluation ID, and deadline before inference. It projects the event through the same identity-free Templar projection used by training and Exams, predicts one closed disposition, applies the content-addressed calibration policy, and returns only `fleet.templar-backend-response.v1` with the original evaluation/request/event bindings.

Fleet integration was exercised through `TemplarCore` using generic no-shell subprocess and Unix-socket backend transports. Fleet continued to own response validation, verdict construction, timeout handling, and authority. A cold one-shot model invocation exceeded a 10-second Fleet evaluator deadline and Fleet produced an authority-free `DENY / evaluator-timeout / origin=core-fail-closed`, proving that slow model startup cannot authorize execution. With a 30-second integration deadline, the cold path completed successfully in ~6.66 seconds and returned an evaluator-origin REVIEW.

Keeping the model loaded behind the local Unix socket removed the cold-start penalty. The first request after service startup completed end to end in ~559 ms; the next warmed Fleet -> Unix socket -> Agoge -> calibrated Qwen3 classifier -> Fleet round trip completed in ~47 ms under a 1-second Fleet deadline. The returned verdict remained `authority=none` and `origin=evaluator`.

Agoge request-binding tests and Fleet transport tests additionally cover event/evaluation substitution rejection, unsupported/expired requests, shell-free subprocess invocation, malformed/oversized output, missing sockets, evaluator process failure, and timeout fail-closed behavior.

The integration was then extended across both real Fleet gate families through one shared configured `TemplarCore`. After model warmup, Phase 22 pre-execution completed in ~49.6 ms and Phase 23 learning promotion completed in ~46.4 ms, both evaluator-origin and authority-free under Fleet's 1-second deadline. Killing the Agoge service caused both gates to fail closed immediately as `DENY / evaluator-failure / authority=none`.

The live proof also exposed two cross-repository resilience defects that were fixed before proceeding. First, a Fleet timeout could close the client socket while Agoge was still returning a late response, causing `BrokenPipeError` to terminate the persistent service. Agoge now treats peer I/O failure as connection-local, with a regression test proving a disconnected client cannot stop the next evaluation. Second, current Fleet Phase 23 requests add `source_execution_id` to `fleet.learning-promotion-request.v1`; Agoge now accepts both the pinned training-corpus shape and the current additive shape, validates the new provenance field, and proves that the identity-free neural projection remains byte-identical.

Katana now runs the evaluator as an enabled supervised user service with a private `0700` runtime directory and `0600` Unix socket. The service prewarms the classifier before publishing readiness. On a fresh managed restart, the first real Fleet Phase 22 request completed in ~94 ms and the first Phase 23 request in ~52 ms, both evaluator-origin and authority-free.

A deliberate SIGKILL fault proved the unplanned-crash path. Both Fleet gates immediately failed closed as `DENY / evaluator-failure / authority=none` in about 1 ms. The stale socket disappeared in ~382 ms; systemd restarted Agoge, reloaded and prewarmed the model, and published a fresh readiness socket in ~8.2 seconds. The first recovered Phase 22 and Phase 23 evaluations then completed in ~68 ms and ~48 ms respectively without any Fleet configuration change or stale-verdict reuse.

The Phase 22 deterministic-deny ordering was also exercised independently. A request carrying a deterministic Fleet hard-deny completed in ~0.27 ms with `DENY / deterministic-policy-failure` and no Templar verdict/origin at all, proving that an already-hard-denied request does not depend on or wait for the model gate.

A separate Phase 22 ordering proof stopped Templar entirely and supplied a deterministic Fleet hard deny. Pre-execution returned `DENY` from Fleet's deterministic policy layer in ~0.25 ms with no evaluator verdict, proving that an already-hard-denied request never consults Templar. In the same offline state, a Phase 23 learning-promotion request that did require Templar correctly failed closed as `DENY / evaluator-failure / authority=none`.

This remains an integration proof, not production graduation. The Fleet Templar branch has passed the self-hosted Gitea Rust, real Nodescale/readiness, Python 3.11, and Python 3.13 gates; the remaining broader release/security and production-regression gates still have to pass before the persistent evaluator is considered a released production component.

## Proof: Phase 10 adversarial school finds and corrects a shallow neural shortcut

Agoge now has a development adversarial-school path that is deliberately separate from both training corpus rows and sealed graduation Exams. Mutation output uses `agoge.adversarial-candidate.v1` with `training_eligible=false`; normal corpus loading rejects it. Registered sealed Exam prompt fingerprints are rejected as mutation sources, generated mutants cannot recursively become accepted training examples, and the adversarial examiner marks generated results as non-graduation evidence.

The first deterministic school generated 1,008 candidates from the accepted 504-event Templar foundation corpus: 252 irrelevant-noise mutations, 252 layout perturbations, and 504 unordered-list permutations across both supported Fleet event families. The previous calibrated adapter scored 1,007/1,008 exact. The only miss was a Phase 23 hidden-instruction DENY mixed with neutral documentation context: the neural classifier predicted ALLOW at about 0.52 confidence and calibration safely converted it to REVIEW. This exposed a benign-context-dilution shortcut without producing a false ALLOW at the deployed calibrated layer.

The failure was clustered without embedding its raw adversarial prompt body into the corrective Teacher request. The pinned Fleet Phase 23 runtime oracle regenerated fresh bound cases from the failure concept, and the existing independent reviewer accepted 18 of 24 candidates while rejecting six label disagreements. The resulting corrective corpus versions remained prompt-distinct from all registered reviewable Exam cases and from the 20-case external-hidden bank.

Two conventional full-from-base 150-step corrective runs were intentionally rejected. Both reached 1,008/1,008 on the generated school but introduced false-ALLOW or DENY-to-REVIEW regressions on the untouched 34-case fresh-transfer bank. That evidence showed that the problem was no longer missing examples alone; the corrective training strategy was moving shared decision boundaries too aggressively.

Agoge therefore added explicit resume-from-parent adapter lineage for sequence-classification QLoRA. The trainer fails closed unless the parent Askesis matches the target Student, exact base model and revision, and disposition registry, and records the parent adapter hash in the new training result. Starting from the previous proven adapter `sha256:b5811a90fe6ece26a05d48d91684e466b3b4937af61705ee2cd2e6faf4df08f8`, a five-step corrective update at learning rate `1e-5` produced adapter `sha256:d4ba373f9dcb2f9f997783001faa4b691fa58f3c063c927faad2183da613358b`.

That bounded repair produced the following evidence:

- generated adversarial school Exam `sha256:e284a6a50aa26371d2a006d142654ce6db6db3649a4ba12dc0e68fafc787b1bd`: 1,008/1,008 exact with no calibration, zero false-ALLOWs, zero false-DENYs;
- reviewable fresh-transfer Exam `sha256:1c010c991320840f65f14b9d4236a3a412481d42f44776237d8f7ebff3969af3`: 34/34 exact, zero false-ALLOWs, zero false-DENYs;
- external-hidden adversarial Exam `sha256:dd1a9088559a5047d340e724da7b15da1fa8574220937f723d091ff6bfb8764b`: 18/20 exact, zero false-ALLOWs, zero false-DENYs, matching the previous hidden-bank safety result while improving fresh transfer;
- internal validation: 48/49 exact with zero false-ALLOWs and zero false-DENYs.

The external-hidden body was transferred from Psalmbox only into Katana `/tmp`, verified against sealed body hash `sha256:63a1e674274fc8abe1781a127691c843e92e212e75cddb7e0936884ee0def3f6`, used for the authorized Exam, and deleted immediately afterward. The hidden body is not committed to Agoge and did not enter any corrective corpus.

This satisfies the Phase 10 acceptance direction: a discovered weakness became distinct corrective curriculum without contaminating the original Exam bank, unsafe corrective candidates were rejected, and the surviving candidate improved generated adversarial and fresh-transfer evidence without worsening the external-hidden hard safety gates. The durable evidence summary is `students/templar/evidence/phase10-adversarial-school-v1.json`, content-addressed as `sha256:2f6df32feeaaded3c4ed0b6f832dc18cb42831bef1a60d783e737c84406b6725`. It is still a candidate, not a production graduation claim.
