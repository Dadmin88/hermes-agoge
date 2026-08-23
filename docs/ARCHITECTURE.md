# Hermes Agoge Architecture

## Purpose

Agoge is the model-formation layer of the Hermes ecosystem. It converts explicit competencies plus provenance-bearing examples into evaluated specialist model artifacts.

## Ownership

### Academy owns, when used

- pedagogy and curriculum assistance;
- faculty routing;
- teaching, critique, and assessment as an optional teacher source.

Academy has no runtime dependency on Agoge.

### Agoge owns

- student specifications;
- curriculum snapshots and hashes;
- corpus provenance;
- train/validation/test separation;
- teacher-output ingestion and review state;
- Askesis run identity and lifecycle;
- local training backends;
- checkpoints/adapters/model artifacts;
- evaluation and regression evidence;
- model cards/provenance manifests;
- graduation gates.

### Consumer systems own

The system consuming a trained model owns its own authority and runtime semantics. Agoge never grants production authority merely because a model graduated.

For Templar, Fleet remains authoritative for deterministic policy, exact request binding, verdict validation, RunAuthority, execution, and fail-closed behavior.

## Dependency direction

```text
Hermes Academy (optional)
        |
        v
    Hermes Agoge  <--- deterministic generators / API teachers / humans
        |
        v
  model artifact
        |
        +------> Fleet Templar adapter
        +------> future Fleet brain adapter
        +------> other bounded consumers
```

Agoge may know a student's exported contract through versioned source references. It must not import Fleet runtime modules into its core package.

## Askesis

An Askesis is one immutable learning cycle:

```text
student + curriculum + accepted corpus + training config
                         |
                         v
                   prepared run
                         |
                         v
                     baseline
                         |
                         v
                      train
                         |
                         v
                 held-out exams
                         |
             +-----------+-----------+
             |                       |
          graduate                 gaps
                                     |
                                     v
                         corrective curriculum
                                     |
                                     +--> next Askesis
```

Every Askesis records hashes for the student spec, curriculum, corpus, source revisions, training config, base model identity, output artifact, and exam results.

## Training data rule

Every example must carry provenance. Teacher output is not automatically trusted or accepted. Future corpus states are generated, reviewed, accepted, rejected, or quarantined.

Exam data is immutable and segregated. A failed exam example may inspire a new training example, but the original exam item must not silently migrate into training and invalidate the benchmark.

## Templar adapter rule

The Templar model should emit only:

```json
{"decision":"ALLOW|DENY|REVIEW","reason_codes":["..."]}
```

The model does not generate request hashes, event hashes, evaluation IDs, deadlines, policy identities, evaluator identities, or authority fields. A deterministic Fleet adapter reconstructs the canonical `fleet.templar-backend-response.v1` around the model output and Fleet's exact request.

This prevents neural generation from becoming the source of cryptographic/request binding.

## Local-first training

The initial backend targets CUDA QLoRA on consumer NVIDIA hardware using 4-bit NF4 base-model quantization plus PEFT LoRA adapters. CPU-only and remote backends may be added later behind the same training contract; neither is required by Agoge's architecture.
