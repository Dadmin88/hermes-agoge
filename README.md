# Hermes Agoge

Hermes Agoge is a local-first system for **forming small, purpose-built models for the Hermes ecosystem**.

Academy teaches. Agoge trains.

Agoge does not replace Hermes Academy and does not make Academy depend on model training. Academy may optionally provide curriculum design, instruction, critique, and assessment. Agoge owns the machine-learning side: corpus provenance, Askesis runs, local fine-tuning, checkpoints/adapters, evaluation, adversarial examination, and model artifacts.

The first reference student is **Templar**, Fleet's low-authority security evaluator. Templar is a consumer/reference target only; Agoge must remain independently usable for future students such as a Fleet orchestration model.

## Core language

- **Student**: the model being formed.
- **Curriculum**: explicit competencies and graduation gates.
- **Askesis**: one bounded train/evaluate/correct cycle.
- **Corpus**: accepted examples with provenance.
- **Teacher**: optional model, Academy faculty member, deterministic generator, or human source that contributes instruction/examples.
- **Exam**: held-out evaluation that may never be silently folded into training data.
- **Artifact**: adapter/model output plus exact provenance and evaluation evidence.

## Current vertical slice

The repository already implements:

- a provider-neutral Hugging Face **Base Model Auditor** that discovers and records candidate models by task, parameter range, architecture/config metadata, exact Hub revision, license/gating policy, and artifact metadata without assuming Qwen or any other model family; Hub audit produces a shortlist only, while local Student benchmarks choose the eventual base;

1. closed student and curriculum specs;
2. provenance-bearing JSONL examples;
3. deterministic 80/10/10 corpus splitting;
4. immutable Askesis run snapshots/manifests;
5. a dry-run backend for plumbing tests;
6. an initial local CUDA QLoRA backend using Transformers/TRL/PEFT/bitsandbytes;
7. strict held-out Exam inference with closed-JSON/contract validation;
8. base-versus-adapter Exam comparison and transition reporting;
9. `agoge doctor`, `validate`, `prepare`, `train`, `examine`, and `compare` commands;
10. a Templar reference student pinned to exact Fleet, Academy, and base-model revisions;
11. a deliberately small deterministic seed corpus for pipeline validation;
12. a successful local one-step QLoRA proof on an RTX 4060, documented in `docs/PROOFS.md`;
13. provider-neutral Teacher request/response contracts with explicit training-use provenance;
14. a deterministic Fleet-native Templar foundation Teacher across all nine current competencies;
15. independent candidate review and conservative accepted/rejected/quarantined promotion;
16. an optional Hermes Academy faculty bridge, live-proven with the Cybersecurity Instructor while keeping unknown-source output quarantined from training;
17. a source-derived snapshot of the Student's exact pinned Fleet Phase 19–23 contracts;
18. a golden `fleet.security-event.v1` fixture produced and round-trip-validated by the pinned Fleet implementation;
19. a runtime competency map that distinguishes what Templar can actually observe from what deterministic Fleet owns or withholds.

The seed corpus is **not** a production Templar training corpus. It exists to prove Agoge's data and training pipeline before we generate and independently verify a large Fleet-native corpus.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

agoge validate --student students/templar/student.json
agoge prepare --student students/templar/student.json --out runs/templar-smoke
agoge train --run runs/templar-smoke --backend dry-run
agoge doctor
```

For local QLoRA:

```bash
pip install -e '.[train,dev]'
agoge train --run runs/templar-smoke --backend qlora
agoge examine --run runs/templar-smoke --model base --split test
agoge examine --run runs/templar-smoke --model adapter --split test
agoge compare --run runs/templar-smoke --split test
```

Agoge roles may be split across machines. The initial layout uses Katana as Trainer/Examiner and Psalmbox as an always-on Faculty/corpus worker for CPU/network-oriented generation, teacher orchestration, provenance, and validation jobs.

The current Templar research base is `Qwen/Qwen3-0.6B`, pinned by exact Hub revision because it was selected manually for the first local proof. It is **not** an Agoge default. Future Students, including future Templar revisions, should use the Base Model Auditor plus local Student benchmarks to choose among viable Hugging Face candidates.

## Safety boundary

Agoge trains models. **Agoge models do not become authority.**

For Templar specifically, the model learns only the bounded advisory judgment payload. Fleet remains responsible for request/event/evaluation binding, deterministic hard denies, authorization, RunAuthority, and all execution decisions.

See `docs/ARCHITECTURE.md` and `docs/MASTER_PLAN.md`.
