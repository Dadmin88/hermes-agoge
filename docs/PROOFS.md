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
