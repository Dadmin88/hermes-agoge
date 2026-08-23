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
