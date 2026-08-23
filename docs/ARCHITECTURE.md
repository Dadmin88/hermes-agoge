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

## Execution roles

Agoge separates logical ownership from machine placement. One machine does not need to perform every part of an Askesis.

### Coordinator

The Coordinator owns the run/spec identities, accepted corpus state, lifecycle transitions, and artifact/evidence references. It does not need a GPU.

### Trainer

A Trainer performs gradient work against one exact prepared Askesis. It must consume the pinned base-model revision and immutable run snapshot, then return artifact and training evidence. Katana is the initial Trainer because its RTX 4060 has sufficient CUDA capacity for the first QLoRA students.

### Faculty/corpus worker

A Faculty/corpus worker performs CPU/network-oriented work such as deterministic generation, teacher-model calls, critique/adjudication jobs, provenance normalization, duplicate/contamination checks, corpus validation, and report generation. It cannot silently accept its own generated examples into the canonical corpus. Psalmbox is the initial always-on Faculty/corpus worker.

### Examiner

An Examiner executes a pinned model artifact against an immutable exam suite. The initial Hugging Face Examiner uses Katana's GPU, while CPU-side result validation/comparison may run anywhere.

These roles are capabilities, not trust escalation. A worker becoming reachable does not grant it authority to alter an accepted corpus, graduate a model, or deploy a consumer artifact.

## Local-first training

The initial backend targets CUDA QLoRA on consumer NVIDIA hardware using 4-bit NF4 base-model quantization plus PEFT LoRA adapters. Agoge may distribute non-gradient work to CPU workers without introducing a remote training-service dependency. CPU-only and alternative training backends may be added later behind the same training contract; neither is required by Agoge's architecture.
