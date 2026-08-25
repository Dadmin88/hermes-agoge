# Hermes Agoge Master Plan v0.2

## Current implementation status - 2026-08-24

- Phase 0: initial architecture/boundary contract implemented.
- Phase 1: closed Student, base-independent Competency, and Curriculum contracts are implemented; exact base-model/source revisions are pinned and new Askesis runs snapshot the Competency identity alongside the Student.
- Phase 2: provenance substrate and deterministic seed corpus implemented; production candidate lifecycle remains open.
- Phase 3: deterministic prototype split plus content-addressed, training-forbidden Exam banks are implemented. Templar has a 34-case reviewable fresh-transfer bank with exact contamination checks and a 20-case external-hidden adversarial bank held on Psalmbox; hidden bodies are transferred to Katana only transiently for authorized Exams and deleted afterward.
- Phase 4: immutable prepared-run snapshot/manifest implemented; full lifecycle state machine remains open.
- Phase 5: local QLoRA smoke proof complete on Katana RTX 4060; production tuning/OOM policy remains open.
- Phase 6: strict local and API Runtime Exams, base/adapter comparison, exact-disposition scoring, false-ALLOW/false-DENY metrics, contract validity, local/API latency measurements, sealed-bank evaluators, and a content-addressed closed-disposition calibration policy are implemented. Corrective Askesis plus validation-derived calibration now yields zero false-ALLOWs on internal validation, the reviewable fresh-transfer bank, and the first external-hidden adversarial bank; broader calibration evidence remains open.
- Phase 7: provider-neutral Teacher requests/responses, training-use provenance, deterministic Templar foundation teacher, independent candidate review, and conservative promotion partition implemented; provider-specific model adapters/disagreement adjudication remain open.
- Phase 8: Academy faculty binding/brief/import bridge implemented and proven live with `academy-cybersecurity-instructor`; Academy remains optional and generated content remains blocked from training when source terms are unknown.
- Phase 9: source-derived pinned Fleet contracts, runtime-oracle generators and independent reviewers for both supported Templar event families, closed disposition vocabularies, anti-curriculum-leakage rules, identity-free model projections, and separate 252-event accepted Phase 19/23 corpora are implemented. Those are combined into a content-addressed 504-event two-family runtime corpus with event-family-aware splitting. Two contamination-safe corrective curriculum cycles have now been completed. The current fresh adapter reaches 46/46 exact on internal validation, 33/34 raw exact on unchanged fresh transfer, and with the validation-derived calibration policy reaches 32/34 fresh-transfer exact with zero false-ALLOWs. On the first 20-case Psalmbox-held hidden adversarial bank it reaches 18/20 exact with zero false-ALLOWs and zero false-DENYs. A first real Fleet integration proof is also complete: Agoge can verify and answer bound `fleet.templar-evaluation-request.v1` documents, and a persistent mode-0600 Unix-socket runtime reduces warmed Fleet-to-model-to-Fleet latency to ~47 ms while preserving authority-free verdicts and Fleet fail-closed behavior. Templar remains non-graduated pending broader hidden/adversarial evidence, supported service lifecycle/configuration, and full production Fleet regression/integration.
- Phase 14-17: shared-base/profile specialization/continuing neural education/Agoge model-trainer operator profile are explicit future roadmap tracks. The Hugging Face Base Model Auditor, local sequence-classification compatibility probe, base-independent Competency Contract, non-promotable candidate-Student benchmark path, Hermes API-runtime catalog/inference bridge, mixed local/API Runtime Tournament, and equal-budget Base Adaptation Tournament are implemented. Live Nous discovery currently exposes 371 models with seven zero-priced models on the active catalog; the strongest three free API candidates were fully examined against Templar and all lost the foundation tournament to the locally trained specialist on hard safety/contract gates. Six compatible Hugging Face bases have now completed the same 100-step Templar adaptation budget; Qwen3-0.6B wins on capability while Qwen2.5-0.5B joins it on the capability/resource Pareto frontier. Generic Hermes API-key providers using `chat_completions` are supported by the credential-isolated bridge; native/non-chat protocols and provider-hosted fine-tuning adapters remain open.
- Phase 18-27: capability intervention routing, automated training-strategy selection, distillation, agent-environment RL, adapter composition, artifact genealogy, tournaments, Fleet-backed training placement, the Academy-to-Agoge closed loop, and the autonomous capability-factory challenge are now explicit roadmap tracks. These extend Agoge without changing its existing security boundaries or making every capability request a gradient-training request.

See `PROOFS.md` for bounded evidence. No current Templar model is production-ready.

## Architectural thesis - capability acquisition, not fine-tuning for its own sake

Hermes Agoge is a **capability acquisition system**.

Its north-star user intent is:

```text
Make this profile/model better at <capability>.
```

Agoge must determine the cheapest correct intervention rather than assuming that every weakness requires weight changes.

Canonical intervention ladder:

```text
information/retrieval gap
        -> memory / retrieval / source grounding

reusable procedural gap
        -> Hermes skill and/or Academy continuing education

stable behavioral or domain prior gap
        -> adapter / supervised fine-tuning

preference, ranking, or style-selection gap
        -> preference optimization when justified

mechanically verifiable interactive capability gap
        -> bounded agent-environment reinforcement learning when justified

strong teacher already demonstrates desired capability
        -> distillation when training rights and provenance permit it

underlying local base cannot support required capability efficiently
        -> audit/select a better trainable base model

existing API-hosted model already satisfies the capability better
        -> select that API model/runtime; no weight change required

remote model is strongest as a teacher rather than final runtime
        -> use it for curriculum/critique/distillation only when provenance and training-use rights permit

provider exposes an approved hosted fine-tuning path
        -> treat hosted training as a distinct versioned Training Strategy, not as ordinary inference

already competent or evidence too weak
        -> no model change
```

The intervention decision is evidence-driven and auditable. A GPU is never treated as the default answer to a capability problem.

### System boundary

```text
Hermes profile / user goal
        |
        v
Capability diagnosis
        |
        +------> Academy / native Hermes learning
        |           teaches the persistent agent
        |
        +------> Agoge Askesis
        |           changes model artifacts
        |
        +------> Local/base-model replacement
        |
        +------> API-hosted model/runtime selection
        |           may satisfy the goal with no weight change
        |
        v
Evaluation / fresh transfer / regression proof
        |
        v
Graduated capability or explicit rejection
```

- Academy teaches agents through normal Hermes conversation, goals, and skills.
- Agoge changes model artifacts through reproducible Askesis runs when weight-level learning is justified.
- API-hosted models are first-class runtime candidates and may satisfy a Competency Contract without any Askesis. Runtime-use rights, training-use rights, and hosted-fine-tuning rights are tracked separately.
- The same remote/API model may occupy different roles at different times: final inference runtime, Teacher/critic, distillation source, or provider-hosted training target. Those roles are never conflated implicitly.
- Evaluation proves capability transfer and catches regressions across local and API-hosted candidates using the same target/anchor evidence whenever the output/task contract permits a fair comparison.
- Fleet may eventually provide placement, reservations, isolation, and distributed compute for Agoge jobs, but Fleet does not choose educational/training semantics.
- Agoge core remains independent of Fleet, Keryx, Nodescale, and Academy runtime imports.
- Academy remains fully useful without Agoge.
- Training never grants execution authority.

The desired long-term outcome is not merely a collection of fine-tuning scripts. It is a system that can determine **what kind of learning is required**, perform it through the correct layer, prove the result, and preserve complete lineage.

## Phase 0 - Freeze identity, terminology, and boundaries

- Canonical project: Hermes Agoge.
- Canonical namespace/package: `agoge`.
- Canonical gradient/model-training cycle: Askesis.
- Canonical capability target: Competency Contract.
- Canonical pre-training decision: Intervention Plan.
- Canonical algorithm/backend decision: Training Strategy.
- Canonical durable model/adapter lineage surface: Artifact Registry.
- Academy is optional faculty, never a runtime dependency.
- Agoge is generic; Templar is the first reference student, not a hard dependency.
- No model output may grant authority merely because Agoge trained it.
- Not every capability-acquisition request produces an Askesis. Agoge may route to Academy/native Hermes learning, select another local base model, select an API-hosted runtime model, or conclude that no model change is justified.
- Model location is not a capability category. Local/downloadable weights, API-hosted inference, and provider-hosted training are execution/runtime modes that compete or cooperate under the same Competency Contract.
- Inference-use permission does not imply training-use permission; training-use permission does not imply hosted fine-tuning support; all three are explicit provider/model capabilities.

Acceptance: architecture contract and dependency direction are documented and tested by package structure.

## Phase 1 - Reproducible student, competency, and curriculum contracts

- closed `agoge.student.v1` schema;
- closed `agoge.competency.v1` schema;
- closed `agoge.curriculum.v1` schema;
- exact source revision references;
- content hashes;
- explicit output contract;
- target capabilities that should improve;
- anchor capabilities that must not materially regress;
- observable evaluation criteria;
- explicit graduation gates.

A Competency Contract should answer:

- what the Student must be able to do;
- under what conditions;
- what counts as successful transfer;
- which general/profile capabilities must remain intact;
- which measurements are authoritative enough for graduation;
- what evidence would prove that training is unnecessary or the selected base model is unsuitable.

Acceptance: invalid/extra fields fail closed; same content yields same identity; no Askesis can graduate against an undefined capability target.

## Phase 2 - Corpus and provenance substrate

- closed example schema;
- deterministic/programmatic examples;
- imported human examples;
- teacher-generated examples;
- corrected failure examples;
- preference-pair examples where justified;
- approved successful trajectory candidates where justified;
- provider/model/prompt/version provenance;
- source class: deterministic, human, Academy, teacher model, real Hermes execution, synthetic, failed eval, corrected failure, or other explicit origin;
- license/terms/training-use metadata where applicable;
- consent/usage basis where user-originated material is involved;
- secret/credential scanning;
- privacy/PII handling policy;
- duplicate/near-duplicate detection;
- contamination tracking;
- quality/review evidence;
- generated/reviewed/accepted/rejected/quarantined lifecycle.

Raw Hermes conversations, raw production trajectories, private memories, unrelated user data, credentials, and arbitrary successful sessions are **not** training data merely because Agoge can observe them.

Production-derived material follows:

```text
raw evidence
   -> candidate example
   -> sanitize
   -> provenance bind
   -> secret/privacy scan
   -> deduplicate
   -> independent review/verification
   -> accepted corpus
```

Acceptance: no unprovenanced or unreviewed example can enter an accepted training set, and no private/secret material silently becomes weight data.

## Phase 3 - Exam isolation and transfer banks

- deterministic train/validation/test split for prototypes;
- named immutable exam suites for production;
- hidden adversarial exam bank;
- fresh transfer suites distinct from taught examples;
- target-capability Exam families;
- anchor/regression Exam families;
- contamination detector;
- rule preventing exam-to-training leakage;
- rule preventing a failed held-out item from being copied verbatim into corrective training.

A failed Exam may inspire a **new, distinct** training example. The original held-out item remains immutable.

Acceptance: a corpus rebuild cannot silently move a held-out exam into training, and success requires novel transfer rather than memorization of the lesson/example.

## Phase 4 - Askesis run lifecycle

- immutable prepared run manifest;
- base-model identity;
- Training Strategy identity;
- training config hash;
- corpus/split hashes;
- source revisions;
- target/anchor Competency Contract identity;
- lifecycle: PREPARED -> BASELINED -> TRAINING -> TRAINED -> EXAMINED -> GRADUATED/FAILED;
- explicit REJECTED artifact outcome when a trained candidate fails graduation even though training itself completed;
- resumable checkpoints without changing run identity.

Acceptance: every artifact can be reconstructed to exact inputs/config, and `TRAINED` is never confused with `GRADUATED`.

## Phase 5 - Local QLoRA backend and trainer abstraction

- CUDA readiness doctor;
- Qwen3 0.6B first smoke model;
- NF4 4-bit quantization;
- PEFT LoRA `all-linear` target;
- bounded batch/context defaults for 8 GB VRAM;
- checkpoints and adapter export;
- OOM diagnostics and safe config fallback;
- backend-neutral trainer interface around Agoge contracts;
- compare plain TRL/PEFT, Unsloth, Axolotl, or later compatible backends through pinned compatibility proofs rather than making any one project Agoge's identity;
- training backend must not weaken corpus provenance, Exam isolation, or artifact identity.

Acceptance: Katana completes a real adapter-training smoke run without remote training compute, and the Askesis manifest remains stable across supported backend implementations.

## Phase 6 - Evaluation engine and profile-native competency scoring

- strict output parser;
- task accuracy;
- per-competency metrics;
- confusion matrix;
- false-ALLOW / false-DENY / false-REVIEW metrics;
- latency and memory footprint;
- base-vs-trained A/B comparison;
- target-capability deltas;
- anchor/regression deltas;
- confidence/calibration experiment without trusting raw model confidence as authority;
- fresh transfer scoring;
- adversarial scoring where relevant;
- evaluation of the actual quantized/deployment artifact, not merely a training checkpoint;
- Sixcat/Hermes-native profile evaluations as the preferred signal for real profile suitability where such evals exist;
- optional generic benchmark bridges such as Lighteval when they provide useful standardized coverage, without letting generic leaderboard scores override profile-native evidence.

Model selection should be able to report profile-oriented results such as:

```text
candidate A
  Backend Engineer competency: 91%
  anchor/general capability: 88%

candidate B
  Backend Engineer competency: 84%
  anchor/general capability: 93%
```

rather than relying only on generic benchmark averages.

Acceptance: graduation is metric-gated, not vibes-gated, and the winning artifact demonstrably improves the target capability without unacceptable anchor regressions.

## Phase 7 - Teacher interface

Teacher sources may include:

- deterministic generators;
- ChatGPT/OpenAI models through available interfaces;
- Nous Portal models;
- local models;
- Academy faculty;
- human reviewers.

Implement provider-neutral teacher records before provider-specific adapters. Teacher disagreement is preserved as evidence rather than majority-voted away blindly.

Teacher outputs may include:

- curriculum proposals;
- explanations;
- demonstrations;
- critiques;
- corrected answers;
- preference comparisons;
- adversarial/counterexample generation;
- approved distillation trajectories;
- rubric/adjudication evidence.

The teacher interface records whether provider/model terms permit the proposed training use. A strong answer from a teacher does not automatically become lawful or acceptable training material.

Acceptance: one example can show who proposed it, who criticized it, who adjudicated it, why it was accepted, and whether its source permits the intended training use.

## Phase 8 - Academy bridge and synthetic curriculum faculty

- optional Agoge curriculum request contract;
- Academy Dean may route competencies to faculty;
- instructors generate lessons/exercises/counterexamples;
- instructors identify common misconceptions and likely failure modes;
- instructors produce increasing-difficulty practice;
- instructors produce novel transfer exercises rather than rephrasing the exact taught example;
- Academy assesses demonstrated gaps;
- Agoge converts accepted teaching artifacts into corpus candidates;
- Academy material passes the same provenance, review, license/terms, contamination, and promotion gates as every other source;
- Academy never calls gradient code or owns model artifacts.

Dependency direction:

```text
Agoge may request teaching from Academy.
Academy never requires Agoge.
```

The Academy Continuing Education lifecycle remains agent education. Agoge may learn from the curriculum or from sanitized, approved evidence of successful education, but Academy itself does not become a training framework.

Acceptance: Academy can assist model education while remaining fully usable without Agoge, and Academy-generated examples must still prove fresh transfer before they influence graduation.

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
- held-out human-designed attacks;
- counterexample generation targeted at discovered shallow heuristics;
- failure clusters converted into new corrective curriculum families rather than copied Exam items.

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
- target-capability improvement threshold;
- anchor/general-capability regression thresholds;
- model card and source/provenance manifest;
- reproducible adapter hash;
- exact base-model and deployment-artifact identity;
- explicit artifact lifecycle state;
- signed/tagged release artifact where ecosystem release policy requires it.

Artifact lifecycle states:

```text
experiment
candidate
validated
graduated
deprecated
rejected
```

`TRAINED`, `candidate`, or `validated` never imply production selection. Only a `graduated` artifact may become an approved default, and even then deployment remains an explicit consumer/operator decision.

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
- multiple independent adapters per base where the runtime supports it;
- deterministic adapter activation/switching and optional hotswap experiments where supported by the pinned runtime;
- immutable adapter manifests binding Student, Curriculum, Corpus, Askesis, Exams, and artifact hashes;
- deterministic adapter loading and fail-closed base/adapter mismatch rejection;
- evaluation of the actual quantized deployment artifact, not merely the training checkpoint;
- profile-facing base+adapter references without baking `SOUL.md`, skills, private memory, or secrets into model weights;
- explicit fallback behavior when a specialist artifact is unavailable or unhealthy.

The shared-base pattern is an optimization, not a dogma. A specialist may use another base model when evidence shows that it is materially better.

Acceptance: two independently trained specialist adapters can share one pinned local base model, load deterministically, remain provenance-isolated, and reproduce their respective Exam results without duplicating the base weights.

## Phase 15 - Hermes Profile neural specialization and Competency Contracts

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
- a profile Competency Contract that identifies target capabilities and anchor capabilities;
- role/jobs/skills extraction as **curriculum candidates**, never automatic ground truth;
- optional Academy-assisted curriculum decomposition;
- deterministic, teacher-generated, and human-reviewed role corpora through normal provenance gates;
- untuned-base baselines before any training;
- profile-specific held-out, transfer, and adversarial exams;
- cross-profile/general-capability regression checks so specialization does not destroy important baseline capability;
- profile suitability scores for candidate bases so Agoge can compare models in the context of the actual Hermes role;
- profile manifests that may select a local base+adapter while preserving normal SOUL/skill/memory/tool boundaries.

Acceptance: at least one non-Templar Hermes profile demonstrates a measurable held-out improvement from an Agoge adapter, with no material regression on its required general capabilities and with the adapter optional/removable at runtime.

## Phase 16 - Continuing neural education and failure harvesting

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
- successful trajectories are also candidates, not automatic training examples;
- failure clusters preserve the model's original bad output when safe/useful for diagnosis;
- corrected failures may produce supervised examples or preference pairs after review;
- an Exam failure may inspire a new distinct training example but the original held-out item remains immutable;
- Academy instructors may explain why the Student failed and construct new exercises targeting the misconception;
- new adapters never replace a production artifact merely because training completed;
- promotion requires the same graduation/regression gates as a fresh model release;
- old model/adapter versions remain reproducible and rollback-capable;
- Academy may diagnose/teach gaps, but Agoge alone owns weight-changing machinery.

Acceptance: a known weak capability can produce a corrective Askesis that improves a fresh transfer suite without contaminating the original Exam bank or silently modifying the deployed model.

## Phase 17 - Agoge model-trainer operator profile

Create a dedicated Hermes profile whose job is to operate Agoge for a user. The user should be able to describe the outcome they want in ordinary language, for example: "I want a small local model that reviews accessibility issues," "train an adapter for this profile," or simply "make this profile better at API security."

Working profile namespace/name: `agoge-model-trainer` until a better ecosystem name is chosen.

The profile is an **Agoge conductor**, not a source of authority and not a graduation bypass. It may automate the workflow but cannot waive provenance, review, Exam, or release gates.

Goal-driven workflow:

```text
user goal
   |
   v
define observable Competency Contract
   |
   v
run Capability Intervention Router
   |
   +----> Academy/skill/native Hermes learning when sufficient
   |
   +----> no model change when already competent
   |
   v
audit/benchmark candidate model runtimes
   |
   +----> API-hosted runtime wins -> no weight change required
   |
   +----> trainable/downloadable base wins -> continue below
   |
   v
choose Training Strategy
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
train locally or through authorized compute adapter
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
- natural-language goal intake converted into a bounded Competency Contract and Student/Curriculum proposal;
- automatic Intervention Plan before any training job is created;
- a provider-neutral **Model Runtime Auditor** with distinct candidate lanes for downloadable/trainable bases, API-hosted inference models, and provider-hosted training targets;
- a Hugging Face **Base Model Auditor** as the first downloadable/trainable discovery lane, using task, library, parameter-count, architecture, model-card metadata, repository/config evidence, exact revision, and artifact size;
- an API Runtime Auditor that discovers live provider catalogs through Hermes/provider adapters, with Nous Portal as the first live integration and OpenAI-compatible/custom providers supported through the same normalized candidate contract;
- live pricing/free-tier/quota/availability metadata where a provider exposes it; a currently free API model is a normal candidate rather than merely a Teacher;
- mandatory role-specific terms review: inference/runtime use, training-data use, distillation use, and hosted fine-tuning capability are separate fields and unknown/incompatible terms fail closed for the affected role rather than being guessed;
- hardware doctor and local-training feasibility scoring before choosing a local model size/backend, including VRAM/RAM/disk/context-length/quantization/architecture compatibility;
- API-runtime feasibility scoring covering endpoint health, context limits, structured-output/tool compatibility when required, latency, rate/quota limits, privacy/offline constraints, and expected cost;
- local compatibility probes plus bounded adaptation benchmarks for shortlisted trainable bases;
- untouched API-model baselines on the exact target/anchor Exams before any training is justified; an API candidate that already satisfies the Competency Contract may win immediately;
- recorded model/runtime selection evidence: every candidate considered, candidate role, rejection reason, exact Hub revision or provider/model identity, benchmark results, latency/resource/cost evidence, and why the winner was selected;
- no permanent preferred-family or preferred-provider rule: Qwen, Llama, Gemma, Mistral, SmolLM, Phi, a future open family, a free Nous model, an OpenAI/Codex model, or another permitted API model may win when evidence and user constraints support it;
- local-first is a preference only when it satisfies the Competency Contract and the user's privacy/offline/latency/cost constraints; it is never allowed to hide a materially better API-runtime option;
- when local training is selected, GPU workers handle gradients and CPU workers handle corpus/review/orchestration jobs where appropriate;
- optional Academy Dean/faculty routing for curriculum design without making Academy mandatory;
- provider-neutral Teacher orchestration across locally available models, Nous Portal, OpenAI/other permitted inference, deterministic generators, and human review;
- training-use/license/provenance checks before any generated material is allowed into weights;
- automatic selection among supported training strategies only after Phase 19 proves the selector;
- automatic baseline, Askesis, Exam, comparison, failure clustering, and corrective-curriculum loops;
- bounded budgets for iterations, inference use, disk, and training steps;
- resumable native Hermes goal/mission state for long model-development workflows;
- local artifact registry and clear final evidence/reporting;
- explicit user-controlled deployment/promotion step rather than silent replacement of an existing production model;
- no autonomous modification of Agoge's own graduation rules, held-out exams, or security boundaries.

The intended user experience is eventually as simple as:

```text
User: Make this profile better at <goal>.
Agoge Trainer: I will determine whether this needs teaching, a skill, a better
local base, an existing API-hosted model, an adapter, hosted tuning, preference
optimization, distillation, RL, or no model change; then I will prove the chosen
intervention against fresh transfer and regression checks and return the best
reproducible result with its evidence.
```

Acceptance: from one bounded natural-language user goal, the profile can autonomously produce the correct Intervention Plan and return the best evidence-backed runtime/intervention, including a no-training API-hosted model when it wins or a reproducible specialist artifact when weight training is justified, while surfacing only genuine blockers/decisions that require the user and never bypassing safety, provenance, privacy, or graduation policy.

## Phase 18 - Capability Intervention Router

Build the decision layer that prevents Agoge from treating every weakness as a fine-tuning task.

Inputs:

- user/profile capability goal;
- current profile identity;
- current model/runtime/base/adapter identity, including provider-hosted API runtime where applicable;
- profile Competency Contract;
- relevant existing skills/memory/retrieval capabilities;
- baseline evaluation evidence;
- hardware/resource constraints;
- privacy/offline/latency/cost requirements;
- available local bases and live API-provider/model catalogs, including free/quota-bearing options;
- provider runtime capabilities and separate inference/training/distillation/hosted-tuning usage rights;
- change-rate of required knowledge;
- training-data availability and usage rights.

Possible dispositions:

```text
NO_CHANGE
RETRIEVAL_OR_MEMORY
HERMES_SKILL
ACADEMY_EDUCATION
API_RUNTIME_SELECTION
BASE_MODEL_REPLACEMENT
SUPERVISED_TUNING
PREFERENCE_TUNING
DISTILLATION
AGENT_RL
NEEDS_REVIEW
INELIGIBLE
```

Rules:

- rapidly changing facts should normally remain outside weights;
- explicit reusable procedures should prefer skills when the model already has the underlying capability;
- Academy should be preferred for agent-level education when durable native Hermes learning is sufficient;
- adapter/tuning should require a stable measurable behavioral/domain gap;
- RL should require an environment with bounded, reproducible, mechanically meaningful rewards;
- distillation should require a demonstrably stronger teacher and acceptable training-use/distillation rights;
- an existing API-hosted model should be considered before weight training when it already satisfies the target/anchor contract within the user's privacy/offline/latency/cost constraints;
- a free API model may win on quality/cost but must still satisfy availability, quota/rate-limit, privacy, and regression gates;
- base-model replacement should be considered before attempting to force an unsuitable local base through increasingly expensive tuning;
- API_RUNTIME_SELECTION is a successful intervention outcome, not a failure to train;
- no intervention is a valid outcome when baseline evidence already satisfies the Competency Contract.

Every disposition carries deterministic reason codes and evidence references.

Acceptance: representative capability requests route to the correct layer, including cases where Agoge refuses to create an Askesis because a skill, Academy class, API-hosted runtime, different local base model, or no change is the better intervention.

## Phase 19 - Automated Training Strategy Planner

When Phase 18 selects a weight-changing intervention, choose the training method from evidence rather than user jargon.

Candidate strategies may include, subject to the exact pinned training stack:

- supervised fine-tuning;
- LoRA / QLoRA;
- full fine-tuning where genuinely justified;
- preference optimization such as DPO/KTO or other supported objectives;
- distillation;
- reward-model training where justified;
- GRPO or other supported agent/RL methods where reward semantics are deterministic enough;
- multi-stage strategies, for example SFT followed by preference optimization.

Decision signals:

```text
high-quality demonstrations available
        -> SFT candidate

good/bad or ranked responses available
        -> preference optimization candidate

strong teacher distribution/trajectory available
        -> distillation candidate

mechanically verifiable interactive outcome available
        -> RL candidate

limited VRAM / adapter-friendly architecture
        -> LoRA/QLoRA candidate

base incapable or inefficient
        -> return to base-model selection instead of forcing training
```

Requirements:

- strategy selection is represented in an immutable Training Strategy record;
- trainer/backend is distinct from learning objective;
- backend candidates such as TRL/PEFT, Axolotl, Unsloth, or future systems are replaceable implementations behind Agoge contracts;
- unsupported algorithms fail closed rather than being approximated silently;
- strategy planner estimates compute, storage, wall-clock bounds, and corpus requirements before launch;
- full fine-tuning is not chosen merely because hardware permits it;
- strategy selection is evaluated against a cheaper baseline/intervention whenever practical.

Acceptance: the same Competency Contract can produce different justified Training Strategies depending on the available evidence, teacher, model architecture, and hardware, with the rationale preserved.

## Phase 20 - Teacher distillation and approved trajectory factory

Allow a stronger permitted teacher to transfer bounded capability into a smaller/local Student.

Pipeline:

```text
Competency Contract
   -> teacher qualification
   -> task/curriculum generation
   -> teacher demonstrations/trajectories
   -> independent correctness review
   -> provenance/license/training-use gate
   -> sanitized accepted distillation corpus
   -> Student Askesis
   -> fresh transfer Exam
```

Trajectory records may include:

- task input;
- observable intermediate tool/action sequence where appropriate and lawful;
- final result;
- correction/retry information;
- deterministic execution evidence;
- evaluator verdict;
- teacher/provider/version identity.

Do not require or preserve private hidden chain-of-thought. Distillation focuses on outputs, tool/action trajectories, structured rationales where explicitly available, and verifiable behavior.

Requirements:

- compare teacher, base Student, and distilled Student on the same target/anchor contracts;
- never assume the teacher is correct because it is expensive or large;
- teacher failures are retained as negative evidence, not promoted;
- high-quality real Hermes task traces may become candidate material only after Phase 2 sanitation/review;
- allow multiple teachers and preserve disagreement;
- record the cost/performance tradeoff obtained by distillation.

Acceptance: a smaller/local Student measurably approaches or exceeds the target behavior of a stronger teacher on fresh transfer tasks while preserving provenance and required anchors.

## Phase 21 - Agent-environment reinforcement learning research track

Train Hermes-native interactive capability through bounded environments when success can be mechanically verified.

Example research environments:

### Software engineering

```text
isolated repository + task
   -> inspect
   -> edit
   -> run tests
   -> final repository state
   -> reward from objective test/evidence contract
```

### Research

```text
bounded source corpus
   -> retrieve
   -> synthesize
   -> cite
   -> reward citation/source correctness + task rubric
```

### Systems administration

```text
sandbox service topology
   -> diagnose
   -> repair
   -> health checks
   -> reward from bounded service/test state
```

Requirements:

- fresh disposable environment per rollout where required;
- no production credentials or unrestricted host access;
- reward logic outside the model;
- environment state and reward function versioned and hash-bound;
- no reward for bypassing safety/authority boundaries;
- tool calls/actions are bounded by the environment contract;
- success is determined by environment evidence, not self-report;
- use agent/RL methods only after deterministic supervised baselines exist;
- detect reward hacking and shortcut behavior with adversarial/held-out environment variants;
- route any real distributed execution through the future Fleet integration boundary rather than granting Agoge raw infrastructure authority.

Acceptance: at least one sandboxed Hermes-native task family shows improved interactive completion on held-out environment variants with no authority expansion or reward-hacking shortcut accepted as success.

## Phase 22 - Adapter composition, hierarchy, and profile runtime

Research whether reusable capability layers can be composed without destructive interference.

Possible hierarchy:

```text
base model
   +
Hermes/tool-use adapter
   +
pack/domain adapter
   +
profile-specialist adapter
```

This is a hypothesis, not an architectural assumption.

Implement:

- single-adapter baseline;
- multi-adapter activation where supported;
- ordering/composition experiments;
- deterministic activation manifests;
- hotswap/load-latency measurements where supported;
- target and anchor eval after every composition;
- interference detection;
- consolidation path that trains one combined adapter when stacking performs worse;
- explicit maximum composition depth until evidence supports deeper stacks;
- no hidden inheritance of permissions, SOUL, memory, or skills through adapter composition.

Potential runtime mapping:

```text
Hermes profile selection
   -> profile identity / SOUL
   -> skill + memory scopes
   -> approved base-model reference
   -> approved adapter set
   -> inference runtime
```

Acceptance: adapter composition is enabled only for combinations with reproducible evidence that they improve the target profile without unacceptable regressions relative to the best single-adapter alternative.

## Phase 23 - Model/adapter Artifact Registry and genealogy

Create a durable, content-addressed registry for every Agoge-produced or admitted model artifact.

Artifact record should include at least:

- artifact ID/version;
- lifecycle state;
- parent/base model identity and exact revision/hash;
- parent adapter/artifact identities where derived;
- Student;
- Competency Contract;
- Curriculum;
- corpus identity/digest;
- Askesis identity;
- Training Strategy;
- trainer/backend/version;
- hyperparameters;
- seed where applicable;
- hardware/environment identity;
- target baseline scores;
- final target scores;
- anchor/regression scores;
- transfer/adversarial results;
- quantization/deployment format;
- license/usage constraints;
- provenance manifest;
- creation/promote/deprecate/reject timestamps and reasons.

Genealogy should make a history reconstructible, for example:

```text
backend-engineer-v7
   <- backend-engineer-v6
   <- corrective curriculum api-auth-gap-14
   <- Askesis a_...
   <- base model hf:...@revision

change:
  +11.2 target capability
  -0.3 anchor/general score
  graduated because all gates passed
```

Registry invariants:

- mutable aliases such as `latest` never replace immutable artifact identity;
- rejected candidates remain auditable but cannot be selected as approved defaults;
- graduation evidence is immutable/content-addressed;
- rollback selects a prior graduated artifact, not an untracked local checkpoint;
- registry stores metadata and references without absorbing private corpus bodies unnecessarily.

Acceptance: any deployed specialist can be traced through exact base, corpus, teachers, training configuration, exams, and promotion decision, and an operator can reproduce or roll back the selected artifact.

## Phase 24 - Model and training-recipe tournaments

Allow Agoge to compare multiple candidate bases and training recipes under one Competency Contract.

Tournament entrants may vary:

- base model;
- untouched base versus tuned candidate;
- adapter rank/config;
- quantization;
- Training Strategy;
- teacher/curriculum family;
- training backend where semantics remain equivalent;
- resource budget.

Example:

```text
A: Base-1 untouched
B: Base-1 + QLoRA recipe A
C: Base-1 + QLoRA recipe B
D: Base-2 + QLoRA
E: Base-3 + distillation
```

Rules:

- identical target/anchor evaluation contracts across entrants;
- no entrant sees held-out tournament exams through training;
- resource/cost budgets are recorded;
- early elimination is allowed only from valid non-held-out evidence;
- winner selection can optimize a declared frontier such as capability, latency, VRAM, disk, or inference cost rather than raw score alone;
- a completely untuned base may win;
- the tournament may conclude that none of the trained candidates are worth promoting.

Acceptance: Agoge can select the best evidence-backed artifact for a bounded goal rather than merely returning the last model it trained.

## Phase 25 - Fleet-backed training execution contract

Integrate Agoge with Fleet only after the local training/evaluation contracts are stable.

Ownership:

### Agoge owns

- Student;
- Competency Contract;
- Curriculum/corpus;
- Training Strategy;
- Askesis identity;
- trainer command/Recipe requirements;
- checkpoints/artifact semantics;
- Exams and graduation.

### Fleet owns

- node capability observation;
- placement;
- CPU/RAM/GPU/VRAM/storage reservations;
- isolation;
- RunAuthority/Run Capsule where applicable;
- scheduling/queueing;
- remote execution transport through normal Fleet/Keryx boundaries;
- resource/deadline evidence.

Agoge must not become a second scheduler.

Training Recipe requirements should explicitly declare or resolve:

- CPU;
- RAM;
- GPU family/capability where relevant;
- VRAM;
- scratch storage;
- dataset/model/artifact sizes;
- network requirements;
- expected checkpoint behavior;
- bounded duration/step budget;
- required runtime/toolchain.

First-run unknown workloads may use Fleet's normal conservative requirement inference/probe concepts, but the resulting resource observations are execution evidence, not permission for Agoge to widen future authority.

The integration should support a user-level goal such as:

```text
Train the best local Backend Engineer specialist that can be produced
with the currently available authorized hardware.
```

Fleet may determine where the job runs. Agoge determines what experiment is being run and whether the result graduates.

Acceptance: the same immutable Askesis can run on an authorized compatible Fleet node without changing Student, corpus, Exam, Training Strategy, or graduation semantics, and remote placement cannot grant Agoge additional authority.

## Phase 26 - Academy -> Agoge -> Academy capability inheritance loop

Close the loop between agent education and model education while preserving the boundary between them.

Conceptual loop:

```text
Hermes profile fails or shows a weak capability
        |
        v
Academy teaches the individual profile
        |
        v
profile demonstrates the capability on novel transfer
        |
        v
sanitized/proven successful education evidence becomes Agoge candidates
        |
        v
Agoge distills/trains the reusable capability where justified
        |
        v
fresh profile instance begins with stronger inherited model prior
        |
        v
Academy moves on to harder gaps
```

This creates two distinct forms of learning:

### Acquired capability

- memories;
- skills;
- profile-specific continuing education;
- learned during the life of a persistent Hermes Agent Instance/profile.

### Inherited capability

- base-model selection;
- adapters;
- distilled/tuned weights;
- available to future instances once a graduated artifact is explicitly selected.

Rules:

- successful Academy learning is not automatically promoted into weights;
- only sanitized, reviewed, provenance-bound artifacts may enter Agoge;
- Academy does not mutate models;
- Agoge does not replace Academy as the preferred layer for fast-changing knowledge or explicit procedures;
- new inherited capability must still pass fresh transfer and anchor regression exams;
- a new inherited model should reduce repeated foundational teaching, allowing Academy to target more advanced gaps rather than repeating the same curriculum indefinitely.

Acceptance: one controlled profile capability can be taught through Academy, independently verified, converted into an Agoge training candidate set, trained into a new versioned artifact, and shown to improve a fresh profile's starting performance without bypassing any provenance or graduation gate.

## Phase 27 - Autonomous capability factory challenge

This is the end-to-end proof of the expanded Agoge vision.

User request:

```text
Make this Hermes profile better at <bounded capability>.
```

The Agoge model-trainer operator profile must, with no training jargon required from the user:

1. inspect the target profile/model and available evidence;
2. create a measurable Competency Contract;
3. baseline the current capability;
4. run the Capability Intervention Router;
5. if native Hermes/Academy learning is sufficient, perform/route that path and prove the result without creating an unnecessary Askesis;
6. if weight-level learning is justified, audit candidate base models rather than assuming a family;
7. benchmark shortlisted bases on profile-native tasks;
8. choose and record the Training Strategy;
9. source/build curriculum through deterministic generators, Academy, teachers, human material, and/or approved failure evidence;
10. sanitize, deduplicate, review, and provenance-bind all accepted corpus material;
11. execute the Askesis locally or through an authorized Fleet execution adapter;
12. evaluate target capability on fresh transfer tasks;
13. evaluate anchor/regression capability;
14. cluster failures and run bounded corrective iterations when useful;
15. optionally run a tournament when multiple plausible candidates exist;
16. package the winning artifact into the Artifact Registry with full genealogy;
17. reject the result if training made the model worse or failed to justify the complexity;
18. surface a clear final evidence report and require explicit deployment/promotion policy.

Required proof cases:

- a goal that routes to Academy/skill learning rather than weights;
- a goal where an untouched better base model wins;
- a goal where a LoRA/QLoRA adapter wins;
- a distillation case;
- an agent-environment RL research case when Phase 21 is proven;
- a failed training candidate that is explicitly rejected;
- an anchor-regression failure that blocks graduation despite target improvement;
- a corrected-failure loop that improves a distinct fresh transfer suite;
- a profile adapter sharing a base with another specialist;
- a rollback from a newly graduated artifact to a prior graduated version;
- a Fleet-backed remote training job whose placement does not alter Agoge semantics or authority.

Final acceptance:

From one natural-language capability goal, Hermes can determine **how the capability should be acquired**, perform the appropriate bounded workflow, and return a reproducible evidence-backed result. The user does not need to know whether the winning path involved Academy, a skill, model replacement, QLoRA, preference tuning, distillation, RL, a tournament, or no model change at all.

That is the definition of Hermes Agoge as a capability acquisition system.