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

1. closed student and curriculum specs;
2. provenance-bearing JSONL examples;
3. deterministic 80/10/10 corpus splitting;
4. immutable Askesis run snapshots/manifests;
5. a dry-run backend for plumbing tests;
6. an initial local CUDA QLoRA backend using Transformers/TRL/PEFT/bitsandbytes;
7. `agoge doctor`, `validate`, `prepare`, and `train` commands;
8. a Templar reference student pinned to a canonical Fleet revision;
9. a deliberately small deterministic seed corpus for pipeline validation.

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
```

The initial Templar base candidate is `Qwen/Qwen3-0.6B`. Model selection is an experiment, not an architectural commitment.

## Safety boundary

Agoge trains models. **Agoge models do not become authority.**

For Templar specifically, the model learns only the bounded advisory judgment payload. Fleet remains responsible for request/event/evaluation binding, deterministic hard denies, authorization, RunAuthority, and all execution decisions.

See `docs/ARCHITECTURE.md` and `docs/MASTER_PLAN.md`.
