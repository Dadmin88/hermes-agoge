# Hermes Agoge Master Plan v0.1

## Current implementation status - 2026-08-23

- Phase 0: initial architecture/boundary contract implemented.
- Phase 1: initial closed student/curriculum contracts implemented; exact base-model/source revisions are pinned.
- Phase 2: provenance substrate and deterministic seed corpus implemented; production candidate lifecycle remains open.
- Phase 3: deterministic prototype split implemented; named immutable production exam banks remain open.
- Phase 4: immutable prepared-run snapshot/manifest implemented; full lifecycle state machine remains open.
- Phase 5: local QLoRA smoke proof complete on Katana RTX 4060; production tuning/OOM policy remains open.
- Phase 6: strict base/adapter Exam plus comparison implemented; competency/security metrics remain open.
- Phase 7: provider-neutral Teacher requests/responses, training-use provenance, deterministic Templar foundation teacher, independent candidate review, and conservative promotion partition implemented; provider-specific model adapters/disagreement adjudication remain open.
- Phase 8: Academy faculty binding/brief/import bridge implemented and proven live with `academy-cybersecurity-instructor`; Academy remains optional and generated content remains blocked from training when source terms are unknown.
- Phase 9: source-derived pinned Fleet contract snapshot, Fleet-runtime-oracle Phase 19 generator, independent event-fact reviewer, canonical closed reason-code vocabulary, anti-curriculum-leakage rules, compact identity-free runtime security projection, seven-class disposition registry, and a 252-event independently accepted Phase 19 foundation corpus are implemented. A bounded local QLoRA sequence-classifier Askesis reached 19/19 exact dispositions on the deterministic held-out foundation-family test; this is a foundation proof only. Phase 23 production curriculum, fresh transfer, calibration, and immutable adversarial banks remain open.
- Phase 14-17: shared-base/profile specialization/continuing neural education/Agoge model-trainer operator profile are explicit future roadmap tracks, gated on Templar proving Agoge's production path. The provider-neutral Hugging Face Base Model Auditor is already implemented and live-smoke-proven as an early Phase 17 prerequisite; hardware/backend probes and Student-local shortlist benchmarking remain open.

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

## Phase 14 - Shared base-model and adapter substrate

Support a Hermes-native specialization pattern where many bounded roles can share one or a small number of pinned base models while carrying separate learned adapters.

Target layering:

```text
shared base model
        |
        v
Agoge specialist adapter
        |
        v
Hermes profile identity / SOUL
        |
        v
skills
        |
        v
memory
        |
        v
current task/context
```

The layers remain distinct: the base supplies general reasoning/language capability; the Agoge adapter supplies learned specialization; the profile supplies role/identity/boundaries; skills supply explicit procedures; memory supplies experience/continuity; current context supplies the immediate task.

Implement:

- provider-neutral base-model discovery/audit before registry admission; Hugging Face Hub is the initial discovery source, not a hard-coded family list;
- versioned base-model registry with exact revision/artifact hashes;
- adapter compatibility metadata binding each adapter to an exact base-model family/revision;
- local base-model caching so many adapters do not duplicate base weights;
- immutable adapter manifests binding Student, Curriculum, Corpus, Askesis, Exams, and artifact hashes;
- deterministic adapter loading and fail-closed base/adapter mismatch rejection;
- evaluation of the actual quantized deployment artifact, not merely the training checkpoint;
- profile-facing base+adapter references without baking `SOUL.md`, skills, private memory, or secrets into model weights;
- explicit fallback behavior when a specialist artifact is unavailable or unhealthy.

The shared-base pattern is an optimization, not a dogma. A specialist may use another base model when evidence shows that it is materially better.

Acceptance: two independently trained specialist adapters can share one pinned local base model, load deterministically, remain provenance-isolated, and reproduce their respective Exam results without duplicating the base weights.

## Phase 15 - Hermes Profile neural specialization program

After Templar proves Agoge can reliably form, evaluate, package, and deploy a specialist model, allow Hermes profiles to become optional Agoge Students.

Do **not** train an adapter merely because a profile exists. Neural specialization is justified when a role has enough of these properties:

- repeated specialized judgments or transformations;
- measurable competency and objective held-out evaluation;
- stable domain principles suitable for a learned prior;
- enough accepted examples to demonstrate transfer rather than memorization;
- meaningful local/privacy/offline benefits;
- meaningful latency or inference-cost benefits;
- a bounded enough role that a small specialist model can plausibly outperform its untuned base on the target task.

Profiles dominated by open-ended conversation, rapidly changing knowledge, or work already handled well by general inference plus explicit skills should remain normal profiles until evidence justifies weight specialization.

Candidate families may include code-review/software-quality specialists, security/policy auditors, accessibility reviewers, database/SQL specialists, Hermes troubleshooting/support specialists, and other bounded Agency/Academy/Profile Packs roles with clear competency evidence.

Implement:

- a versioned profile-to-Student binding referencing exact profile-distribution revisions without making Profile Packs a runtime dependency;
- role/jobs/skills extraction as **curriculum candidates**, never automatic ground truth;
- optional Academy-assisted curriculum decomposition;
- deterministic, teacher-generated, and human-reviewed role corpora through normal provenance gates;
- untuned-base baselines before any training;
- profile-specific held-out, transfer, and adversarial exams;
- cross-profile/general-capability regression checks so specialization does not destroy important baseline capability;
- profile manifests that may select a local base+adapter while preserving normal SOUL/skill/memory/tool boundaries.

Acceptance: at least one non-Templar Hermes profile demonstrates a measurable held-out improvement from an Agoge adapter, with no material regression on its required general capabilities and with the adapter optional/removable at runtime.

## Phase 16 - Continuing neural education

Extend the Academy/Agoge educational philosophy into explicit, versioned corrective model education.

Real-world profile use may produce failure evidence, but production models must never self-modify automatically. The loop is:

```text
profile/model works in the real world
        |
        v
bounded failure or weak-case evidence
        |
        v
competency-gap diagnosis
        |
        v
corrective curriculum candidates
        |
        v
normal Teacher/review/promotion gates
        |
        v
new Askesis
        |
        v
held-out + regression Exams
        |
        v
new versioned adapter candidate
```

Requirements:

- production telemetry/failure evidence is sanitized and provenance-bound before entering Agoge;
- private user data, secrets, raw conversations, and unrelated memory never become training data by default;
- an Exam failure may inspire a new distinct training example but the original held-out item remains immutable;
- new adapters never replace a production artifact merely because training completed;
- promotion requires the same graduation/regression gates as a fresh model release;
- old model/adapter versions remain reproducible and rollback-capable;
- Academy may diagnose/teach gaps, but Agoge alone owns weight-changing machinery.

Acceptance: a known weak capability can produce a corrective Askesis that improves a fresh transfer suite without contaminating the original Exam bank or silently modifying the deployed model.

## Phase 17 - Agoge model-trainer operator profile

Create a dedicated Hermes profile whose job is to operate Agoge for a user. The user should be able to describe the outcome they want in ordinary language, for example: "I want a small local model that reviews accessibility issues" or "train an adapter for this profile," and the profile should coordinate the remaining workflow locally whenever the available hardware permits it.

Working profile namespace/name: `agoge-model-trainer` until a better ecosystem name is chosen.

The profile is an **Agoge conductor**, not a source of authority and not a graduation bypass. It may automate the workflow but cannot waive provenance, review, Exam, or release gates.

Goal-driven workflow:

```text
user goal
   |
   v
define observable model competency
   |
   v
choose/benchmark candidate base model(s)
   |
   v
create Student + Curriculum
   |
   v
recruit deterministic / Academy / model / human Teachers
   |
   v
generate + review + promote corpus candidates
   |
   v
baseline untuned model
   |
   v
prepare Askesis
   |
   v
train locally
   |
   v
Exam + diagnose gaps
   |
   +----> corrective Askesis when needed
   |
   v
package adapter/model artifact
   |
   v
present graduation/deployment evidence to user
```

Implement:

- a Hermes profile with explicit SOUL/role/jobs and Agoge operating skills;
- natural-language goal intake converted into a bounded Student/Curriculum proposal;
- a provider-neutral **Base Model Auditor** that treats Hugging Face Hub as a discovery/catalog source rather than assuming Qwen or any other family;
- Hugging Face candidate discovery using task, library, parameter-count, architecture, model-card metadata, and repository/config evidence;
- mandatory license/usage/training-compatibility review before a candidate may enter benchmarking; unknown or incompatible terms fail closed rather than being guessed;
- hardware doctor and local-training feasibility scoring before choosing model size/backend, including VRAM/RAM/disk/context-length/quantization/architecture compatibility;
- local smoke benchmarks of shortlisted base models on the target Student's baseline/Exam tasks before selection;
- recorded base-model selection evidence: candidates considered, rejection reasons, benchmark results, exact Hub revision, artifact size/hash, and why the winner was selected;
- no permanent preferred-family rule: Qwen, Llama, Gemma, Mistral, SmolLM, Phi, or any future family may win when evidence supports it, and an unfamiliar architecture is rejected until Agoge proves backend compatibility;
- automatic preference for local compute, with Katana-like GPU workers handling gradients and CPU workers such as Psalmbox handling corpus/review/orchestration jobs when available;
- optional Academy Dean/faculty routing for curriculum design without making Academy mandatory;
- provider-neutral Teacher orchestration across locally available models, Nous Portal, OpenAI/other permitted inference, deterministic generators, and human review;
- training-use/license/provenance checks before any generated material is allowed into weights;
- automatic baseline, Askesis, Exam, comparison, failure clustering, and corrective-curriculum loops;
- bounded budgets for iterations, inference use, disk, and training steps;
- resumable native Hermes goal/mission state for long model-development workflows;
- local artifact registry and clear final evidence/reporting;
- explicit user-controlled deployment/promotion step rather than silent replacement of an existing production model;
- no autonomous modification of Agoge's own graduation rules, held-out exams, or security boundaries.

The intended user experience is eventually as simple as:

```text
User: Train me a small local specialist for <goal>.
Agoge Trainer: I will define the competency, build and review the curriculum,
benchmark candidate bases, train locally, test transfer, correct weaknesses,
and return the best reproducible artifact with its evidence.
```

Acceptance: from one bounded natural-language user goal, the profile can autonomously produce a reproducible local specialist adapter through Agoge's normal contracts and Exams, while surfacing only genuine blockers/decisions that require the user and never bypassing safety, provenance, or graduation policy.
