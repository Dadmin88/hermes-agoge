# Hermes Agoge Master Plan v0.1

## Current implementation status - 2026-08-23

- Phase 0: initial architecture/boundary contract implemented.
- Phase 1: initial closed student/curriculum contracts implemented; exact base-model/source revisions are pinned.
- Phase 2: provenance substrate and deterministic seed corpus implemented; production candidate lifecycle remains open.
- Phase 3: deterministic prototype split implemented; named immutable production exam banks remain open.
- Phase 4: immutable prepared-run snapshot/manifest implemented; full lifecycle state machine remains open.
- Phase 5: local QLoRA smoke proof complete on Katana RTX 4060; production tuning/OOM policy remains open.
- Phase 6: strict base/adapter Exam plus comparison implemented; competency/security metrics remain open.
- Phase 7: next major implementation target.

See `PROOFS.md` for bounded evidence. No current Templar model is production-ready.

## Phase 0 - Freeze identity, terminology, and boundaries

- Canonical project: Hermes Agoge.
- Canonical namespace/package: `agoge`.
- Canonical training cycle: Askesis.
- Academy is optional faculty, never a runtime dependency.
- Agoge is generic; Templar is the first reference student, not a hard dependency.
- No model output may grant authority merely because Agoge trained it.

Acceptance: architecture contract and dependency direction are documented and tested by package structure.

## Phase 1 - Reproducible student and curriculum contracts

- closed `agoge.student.v1` schema;
- closed `agoge.curriculum.v1` schema;
- exact source revision references;
- content hashes;
- explicit output contract;
- explicit graduation gates.

Acceptance: invalid/extra fields fail closed; same content yields same identity.

## Phase 2 - Corpus and provenance substrate

- closed example schema;
- deterministic/programmatic examples;
- imported human examples;
- teacher-generated examples;
- provider/model/prompt/version provenance;
- license/terms metadata where applicable;
- duplicate/near-duplicate detection;
- contamination tracking;
- generated/reviewed/accepted/rejected/quarantined lifecycle.

Acceptance: no unprovenanced example can enter an accepted training set.

## Phase 3 - Exam isolation

- deterministic train/validation/test split for prototypes;
- named immutable exam suites for production;
- hidden adversarial exam bank;
- contamination detector;
- rule preventing exam-to-training leakage.

Acceptance: a corpus rebuild cannot silently move a held-out exam into training.

## Phase 4 - Askesis run lifecycle

- immutable prepared run manifest;
- base-model identity;
- training config hash;
- corpus/split hashes;
- source revisions;
- lifecycle: PREPARED -> BASELINED -> TRAINING -> TRAINED -> EXAMINED -> GRADUATED/FAILED;
- resumable checkpoints without changing run identity.

Acceptance: every artifact can be reconstructed to exact inputs/config.

## Phase 5 - Local QLoRA backend

- CUDA readiness doctor;
- Qwen3 0.6B first smoke model;
- NF4 4-bit quantization;
- PEFT LoRA `all-linear` target;
- bounded batch/context defaults for 8 GB VRAM;
- checkpoints and adapter export;
- OOM diagnostics and safe config fallback;
- later compare Unsloth backend against plain TRL/PEFT.

Acceptance: Katana completes a real adapter-training smoke run without remote training compute.

## Phase 6 - Evaluation engine

- strict output parser;
- task accuracy;
- per-competency metrics;
- confusion matrix;
- false-ALLOW / false-DENY / false-REVIEW metrics;
- latency and memory footprint;
- base-vs-trained A/B comparison;
- confidence/calibration experiment without trusting raw model confidence as authority.

Acceptance: graduation is metric-gated, not vibes-gated.

## Phase 7 - Teacher interface

Teacher sources may include:

- deterministic generators;
- ChatGPT/OpenAI models through available interfaces;
- Nous Portal models;
- local models;
- Academy faculty;
- human reviewers.

Implement provider-neutral teacher records before provider-specific adapters. Teacher disagreement is preserved as evidence rather than majority-voted away blindly.

Acceptance: one example can show who proposed it, who criticized it, who adjudicated it, and why it was accepted.

## Phase 8 - Academy bridge

- optional Agoge curriculum request contract;
- Academy Dean may route competencies to faculty;
- instructors generate lessons/exercises/counterexamples;
- Academy assesses demonstrated gaps;
- Agoge converts accepted teaching artifacts into corpus candidates;
- Academy never calls gradient code or owns model artifacts.

Acceptance: Academy can assist model education while remaining fully usable without Agoge.

## Phase 9 - Templar production curriculum

Build directly from pinned Fleet sources:

- Phase 19 security-event contract;
- Phase 20 Templar core;
- Phase 21 sandbox;
- Phase 22 pre-execution gate;
- Phase 23 learning/promotion gate;
- Fleet hard invariants and adversarial suites.

Generate canonical benign, deny, ambiguous REVIEW, prompt-injection, exfiltration, secret-handling, memory/skill poisoning, cross-principal, dangerous-combination, ownership-boundary, and strange-but-benign examples.

Acceptance: corpus is Fleet-native and independently reviewed, not generic cybersecurity prose.

## Phase 10 - Templar adversarial school

- mutation engine;
- paraphrase attacks;
- irrelevant-noise injection;
- semantic-preserving structure mutations;
- hidden instruction variants;
- multi-signal interaction cases;
- teacher-model red teams;
- held-out human-designed attacks.

Acceptance: newly discovered weaknesses become corrective curriculum without contaminating the original exam bank.

## Phase 11 - Templar integration adapter

- local model runner behind Phase 20 backend contract;
- deterministic Fleet-owned request/result binding;
- strict JSON output parser;
- timeout and malformed output fail closed;
- no tool access;
- Phase 21 sandbox compatibility;
- exact model/version identity in `TemplarEvaluatorIdentity`;
- frontier evaluator remains available as comparison/fallback experiment, not authority.

Acceptance: trained local Templar can replace an injected test evaluator without changing Fleet authority semantics.

## Phase 12 - Graduation and release

Required before production claim:

- zero authority-boundary violations in release exam;
- zero deterministic-hard-deny override errors;
- thresholded adversarial recall;
- bounded benign false-positive rate;
- REVIEW calibration evidence;
- fresh transfer suite;
- Fleet regression suite;
- sandbox/fail-closed suite;
- model card and source/provenance manifest;
- reproducible adapter hash;
- signed/tagged release artifact where ecosystem release policy requires it.

## Phase 13 - Fleet Brain research track

Only after Agoge proves itself with Templar:

- define Fleet planning/orchestration student contract;
- train proposals, never direct authority;
- placement/resource/workflow/recovery curriculum;
- exact deterministic validation around every proposal;
- separate model/evaluation family from Templar.

Templar and Fleet Brain must not collapse into one model simply because both know Fleet architecture.
