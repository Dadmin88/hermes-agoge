# Hermes Agoge Proof Ledger

This ledger records bounded implementation proofs. A proof demonstrates one engineering property only; it must not be inflated into a claim that a student model is production-ready.

## 2026-08-23 - Local CUDA QLoRA smoke proof

### Purpose

Prove that Hermes Agoge can perform a real local gradient update on Katana without a remote training service.

### Bound inputs

- Student: `templar-v1`
- Base model: `Qwen/Qwen3-0.6B`
- Base model revision: `c1899de289a04d12100db370d81485cdf75e47ca`
- Fleet source revision: `591ea20bb1b7268254ddeaffaf16a5f853aa2db5`
- Academy source revision: `efd367a5b1f86afc641726a70a52b610e774efc7`
- Corpus: 24 deterministic seed examples, explicitly marked `seed-only-not-production-corpus`
- Split: 16 train / 2 validation / 6 test
- Backend: QLoRA, NF4, double quantization, PEFT LoRA `all-linear`
- Smoke bound: exactly one optimizer step, max length 256, gradient accumulation 1
- Compute dtype: BF16
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU

### Result

The pinned Qwen base loaded locally in 4-bit form, one real optimizer step completed, and a LoRA adapter was written successfully.

Observed smoke metrics from the corrected non-packing run:

- training runtime: approximately 1.33 seconds;
- peak CUDA allocation: approximately 1.55 GB;
- train loss: approximately 6.47.

These numbers are machine/proof observations, not model-quality targets.

### Correctness finding

The first smoke attempt used TRL packing. TRL warned that packing/padding-free behavior was not proven safe with the active attention implementation and could cross-contaminate samples. Agoge therefore disabled packing for the initial backend and repeated the smoke proof successfully.

### Base-versus-adapter Exam

The six held-out smoke examples were evaluated with strict closed-JSON parsing.

Untouched base model:

- JSON-valid: 0/6;
- contract-valid: 0/6;
- decision-correct: 0/6.

One-step adapter:

- JSON-valid: 6/6;
- contract-valid: 0/6;
- decision-correct: 0/6.

The adapter emitted the same incomplete JSON shape on all six cases, so this is not useful Templar behavior. It does, however, prove measurable behavioral movement from one local gradient step and proves that Agoge's Exam can distinguish syntax improvement from actual contract/competency improvement.

### What this proof does not establish

It does not establish:

- Templar competence;
- security suitability;
- production corpus quality;
- graduation;
- useful decision accuracy;
- reason-code accuracy;
- adversarial robustness;
- calibration;
- Fleet integration readiness.

Those remain later Agoge phases.

## 2026-08-23 - Provider-neutral Teacher and promotion proof

### Purpose

Prove that Agoge can generate useful training candidates through a Teacher interface without giving the Teacher direct write access to the accepted corpus.

### Bound request

- Student: `templar-v1`
- Competency: `prompt-injection`
- Count: 7
- Teacher request ID: `sha256:450227824787a5f4ac749459154e5a0134faec50d8648b8a66ab0c8760f258db`
- Teacher: `templar-foundation-rules-v1`
- Teacher kind: deterministic
- Teacher training use: allowed
- Teacher response hash: `sha256:18562384b8aaa05de923c67319ee7dce01c59fa454e9ce5374dff14e826e64ac`

### Candidate set

The deterministic Teacher produced seven semantically distinct candidates:

- three explicit hidden policy-override cases -> `DENY`;
- one disguised secret-exfiltration case -> `DENY`;
- two untrusted-but-benign summarization cases -> `ALLOW`;
- one incomplete obfuscated-control case -> `REVIEW`.

Every completion passed the Student's strict closed output contract and entered only the `generated-unreviewed` state.

### Independent review

The seven candidates were independently reviewed against the pinned Fleet/Templar ownership boundary by a separate reviewer identity, `gpt-5.6-sol-independent-reviewer`.

The reviewer is recorded with `training_use: unknown`. This does not block the candidates because the reviewer contributes review metadata only; the trainable prompt/completion content comes from the deterministic Teacher, whose training-use state is `allowed`. Training backends do not consume reviewer notes as training text.

### Promotion result

- accepted: 7;
- rejected: 0;
- quarantined: 0.

The promotion engine also has tests proving:

- a Teacher cannot independently accept its own candidate;
- a candidate from `training_use: unknown` cannot be accepted even with a positive review;
- any independent REJECT wins;
- disagreement/QUARANTINE prevents acceptance.

This proof establishes the candidate-control path, not production curriculum sufficiency.

## 2026-08-23 - Templar Phase 19 closed-class foundation proof

### Purpose

Prove that a small locally trained model can learn Templar's bounded Phase 19 Fleet-security disposition task from real Fleet-shaped events while eliminating free-form verdict/reason-code generation from the neural contract.

### Bound inputs

- Student: `templar-v1`
- Student hash: `sha256:eaabc2035dba64562530ccffcd938d53b4471997b7aceae92e656e84b2fcb8f1`
- Base model: `Qwen/Qwen3-0.6B`
- Base model revision: `c1899de289a04d12100db370d81485cdf75e47ca`
- Fleet source revision: `591ea20bb1b7268254ddeaffaf16a5f853aa2db5`
- Accepted Phase 19 corpus: 252 Fleet-runtime-oracle events
- Corpus hash: `sha256:74cc797f7b7e08fb59f8eb0205028e34802a27058cfc7ba869ae4be77e9203ce`
- Candidate admission: 252 accepted / 0 rejected / 0 quarantined after independent event-fact review
- Split strategy: deterministic disposition-family stratification
- Split: 214 train / 19 validation / 19 test
- Closed disposition registry: 7 classes
- Disposition registry hash: `sha256:8ab61f2172c012c020b228e883acff40309753a6f69c38a1556cb5ad58305c97`

### Runtime security projection

The sequence classifier does not receive the full serialized Fleet event. A deterministic Agoge/Fleet-facing projection removes unique identity/hash noise and retains bounded runtime security evidence such as risk levels/signals, secret-interception posture, quarantine state, requested tools, network posture, resource envelope, principal kind, and target source.

Across the 252-event corpus with the pinned Qwen tokenizer:

- raw Fleet-event median: 1,141 tokens;
- projected median: 163 tokens;
- raw maximum: 1,476 tokens;
- projected maximum: 210 tokens;
- median reduction: approximately 85.7%.

Projection tests require deterministic output and assert that `sha256:` identities are absent from the model-facing projection.

### Production-oriented classifier architecture

The model predicts one closed disposition class rather than generating JSON text. Deterministic code maps the class to the exact `ALLOW | DENY | REVIEW` plus canonical reason-code tuple. This removes invented reason-code spelling/synonym failure by construction.

Backend/configuration for the successful bounded run:

- backend: QLoRA sequence classification;
- base quantization: NF4 4-bit with double quantization;
- LoRA rank: 16;
- LoRA alpha: 32;
- classifier head persisted with the adapter;
- BF16 compute;
- class-balanced training rows;
- per-device batch size: 8;
- gradient accumulation: 1;
- learning rate: `5e-5`;
- max steps: 100;
- max length: 512;
- observed max projected tokens: 212;
- runtime: approximately 64.33 seconds;
- peak CUDA allocation: approximately 1.43 GB;
- train loss: approximately 0.546.

### Held-out foundation result

The 19-row test split contains unseen variants from each exact disposition family represented in the deterministic Phase 19 foundation corpus.

Untrained sequence-classification base/head:

- verdict accuracy: 6/19 = 31.6%;
- exact disposition/reason tuple: 1/19 = 5.3%.

Locally trained adapter:

- `ALLOW`: 8/8;
- `DENY`: 6/6;
- `REVIEW`: 5/5;
- verdict accuracy: 19/19 = 100%;
- exact disposition/reason tuple: 19/19 = 100%;
- deterministic output-contract validity: 19/19.

Base-versus-adapter comparison reports 13 improved decisions and zero decision regressions on this split.

Adapter tree hash recorded by the Exam: `sha256:1b87eb3a49ece539520171f7a20bfd54f73d505aa382b346f42c1e0bfcc0a2bc`.

### What this proof does not establish

This is a foundation-family proof, not Templar graduation. It does not establish:

- performance on an immutable human-designed adversarial bank;
- fresh semantic transfer outside the deterministic generator families;
- Phase 23 `fleet.learning-promotion-event.v1` competence;
- calibrated classifier probability/confidence;
- production Fleet adapter/sandbox integration;
- release-level false-ALLOW bounds;
- robustness to novel or malformed security signals.

Those remain required before any production claim.

## 2026-08-24 - Templar Phase 23 learning-promotion foundation proof

### Purpose

Prove that the same small local classifier architecture can learn Templar's other supported runtime event family, `fleet.learning-promotion-event.v1`, where semantic meaning of bounded memory/skill material matters beyond the mere presence of a Fleet-derived risk signal.

### Gate boundary

The pinned Phase 23 `LearningPromotionGate` rejects administrator mismatch, stale policy, unredacted credentials, invalid promotion policy, and missing Templar **before** model evaluation. Agoge therefore excludes those deterministic failures from normal Templar training. The model sees only structurally/policy-eligible promotion events containing bounded sanitized evaluation material.

### Bound inputs

- Student: `templar-v1`
- Student hash: `sha256:eaabc2035dba64562530ccffcd938d53b4471997b7aceae92e656e84b2fcb8f1`
- Base model: `Qwen/Qwen3-0.6B`
- Base model revision: `c1899de289a04d12100db370d81485cdf75e47ca`
- Fleet source revision: `591ea20bb1b7268254ddeaffaf16a5f853aa2db5`
- Accepted Phase 23 corpus: 252 Fleet-runtime-oracle promotion events
- Corpus hash: `sha256:7525c8b27a14b4017cb103adf42ba6c4f2c33f6a5dfa2b2aa7f652ad0738358f`
- Candidate admission: 252 accepted / 0 rejected / 0 quarantined after independent event/material review
- Split strategy: deterministic disposition-family stratification
- Split: 200 train / 26 validation / 26 test
- Closed disposition registry: 10 classes
- Disposition registry hash: `sha256:7b986dd2dfe5b31361e296383392ccc515e239dffc337dca46ef8ef6ab9c9cad`

### Semantic foundation design

Fleet derives the following bounded semantic categories from the exact promotion material:

- `hidden-instructions`;
- `social-engineering`;
- `exfiltration-intent`;
- `disguised-privilege-escalation`;
- `dangerous-combinations`;
- `suspicious-secret-handling`.

The corpus intentionally includes cases where the same derived signal maps to different safe outcomes based on the candidate text. In particular, `hidden-instructions`, `social-engineering`, and `suspicious-secret-handling` each appear in accepted `ALLOW`, `REVIEW`, and `DENY` examples. This prevents the learned task from collapsing into `signal present => deny`.

The initial multi-signal curriculum exposed one recurrent confusion on `dangerous-combinations`. Corrective Askesis added distinct compositions including social-engineering + exfiltration, hidden-instruction + credential persistence, privilege-bypass + credential persistence, and social-engineering + privilege bypass. Fleet itself verified the exact derived signal set for every new candidate before independent review.

### Model-facing promotion projection

The deterministic projection preserves:

- subject kind;
- source/target scope kinds;
- administrator kind;
- sanitized/verification posture;
- Fleet evaluation categories and derived risk signals;
- bounded memory text or skill file path/text.

It removes candidate/request hashes, principal IDs, policy digests, and other binding metadata owned by deterministic Fleet. Live proof over generated events confirmed the projection is identity-free while preserving both memory and skill evaluation material.

### Training configuration

- backend: QLoRA sequence classification;
- 10 closed dispositions;
- NF4 4-bit base with double quantization;
- LoRA rank: 16;
- LoRA alpha: 32;
- BF16 compute;
- class-balanced training;
- per-device batch size: 8;
- gradient accumulation: 1;
- learning rate: `5e-5`;
- max steps: 100;
- max length: 512;
- observed max projected tokens: 178;
- runtime: approximately 52.89 seconds;
- peak CUDA allocation: approximately 1.36 GB;
- train loss: approximately 1.031.

### Held-out foundation result

Untrained sequence-classification base/head on the 26-row test split:

- verdict accuracy: 8/26 = 30.8%;
- exact disposition/reason tuple: 3/26 = 11.5%.

Locally trained adapter:

- `ALLOW`: 8/8;
- `DENY`: 10/10;
- `REVIEW`: 8/8;
- verdict accuracy: 26/26 = 100%;
- exact disposition/reason tuple: 26/26 = 100%;
- validation split: 26/26 exact dispositions.

Base-versus-adapter comparison reports 18 improved decisions and zero decision regressions on the test split.

Adapter tree hash recorded by the Exam: `sha256:3999920a5226c6694d2e77d44a5be5c701a1ae05cf825144011e2686c1d4fb54`.

### What this proof does not establish

This remains a templated foundation-family proof. It does not establish:

- fresh teacher/human semantic transfer outside the deterministic material templates;
- immutable adversarial-bank performance;
- robustness to novel prompt-injection/social-engineering wording;
- calibrated probability/confidence;
- combined Phase 19 + Phase 23 competence in one adapter;
- production Fleet integration or release readiness.

Those remain subsequent Agoge gates.
