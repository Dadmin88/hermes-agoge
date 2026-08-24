# Hermes Agoge

Hermes Agoge is a **capability-acquisition system for the Hermes ecosystem**.

Its job is not simply to fine-tune models. Given a bounded capability goal, Agoge is intended to determine which intervention is actually justified, perform it through the correct layer, and prove the result.

That may mean:

- no model change;
- a better Hermes skill or retrieval/memory path;
- Hermes Academy education for a persistent profile;
- selecting a better local base model;
- selecting an API-hosted runtime that already satisfies the goal;
- training a local adapter/model through Askesis;
- distillation, preference optimization, or bounded agent-environment training when later phases justify them.

**Academy teaches. Agoge forms capability.**

Academy remains independent. It may optionally provide faculty, curriculum design, instruction, critique, or assessment. Agoge owns capability contracts, training/runtime candidate evaluation, corpus provenance, Askesis runs, Exams, artifact lineage, and selection evidence.

The first reference student is **Templar**, Fleet's low-authority security evaluator. Templar is a proving ground, not a hard dependency or special case for Agoge core.

## Core language

- **Competency Contract**: base/runtime-independent statement of what capability must be demonstrated, under which conditions, with which anchors and measurements.
- **Student**: one exact base/model binding being formed or evaluated.
- **Curriculum**: competencies, taught material, and graduation gates.
- **Askesis**: one bounded train/evaluate/correct cycle.
- **Corpus**: accepted examples with provenance and review evidence.
- **Teacher**: deterministic generator, Academy faculty member, model, human, or other approved instructional source.
- **Exam**: held-out evaluation that cannot silently become training data.
- **Runtime candidate**: a local model/adapter or remote/API model competing to satisfy the same Competency Contract.
- **Artifact**: model/adapter output plus exact lineage and evaluation evidence.

## Current implementation

Agoge already implements a substantial end-to-end vertical slice:

1. closed Student, Competency Contract, and Curriculum specifications with content hashes;
2. provenance-bearing JSONL examples and conservative candidate review/promotion;
3. deterministic, disposition-stratified, and event-family-aware corpus splitting;
4. immutable Askesis snapshots/manifests, now including the exact Competency Contract;
5. local CUDA QLoRA backends for generative and closed sequence-classification experiments;
6. strict base/adapter Exams with false-ALLOW, false-DENY, latency, exact-disposition, and contract metrics;
7. provider-neutral Teacher contracts and an optional live-proven Hermes Academy faculty bridge;
8. source-derived snapshots of the pinned Fleet Templar contracts;
9. Fleet-runtime-oracle corpus generation and independent review for both supported Templar event families;
10. a combined accepted **504-event Templar runtime foundation corpus**, 252 `fleet.security-event.v1` and 252 `fleet.learning-promotion-event.v1` events;
11. identity-free model projections that strip Fleet-owned hashes/bindings while preserving the observable facts Templar actually receives;
12. a closed disposition classifier architecture in which the neural model cannot invent reason-code strings;
13. a provider-neutral Hugging Face Base Model Auditor;
14. local compatibility probes that verify tokenizer, native sequence-classification support, 4-bit loading, PEFT `SEQ_CLS`, CUDA fit, and a real forward pass before a candidate may benchmark;
15. non-promotable candidate-Student benchmark runs so alternative bases can compete against byte-identical data/splits without corrupting production provenance;
16. live Hermes provider catalog discovery and pricing/free-tier metadata for API-hosted runtime candidates;
17. credential-isolated API inference through short-lived Hermes subprocesses so Agoge never receives or persists provider credentials;
18. API Exams using the same Templar projection, closed contract, held-out split, false-ALLOW/false-DENY metrics, latency, and usage accounting as local candidates;
19. a normalized **Runtime Tournament** that compares local and API candidates under one Competency Contract and recommends only a next-stage candidate, never automatic graduation.

## First mixed-runtime proof

Templar's current combined Competency Contract covers both Fleet event families and requires **zero false-ALLOWs** before graduation can ever be considered.

A locally trained `Qwen/Qwen3-0.6B` QLoRA sequence-classification adapter was compared against the strongest currently free Nous Portal models surviving a live screen.

On the same 45-case validation split:

| Runtime | Exact disposition | False ALLOW | Contract valid | Median latency |
| --- | ---: | ---: | ---: | ---: |
| Local Qwen3-0.6B adapter | **97.8%** | **0** | 100% | **~48 ms** |
| Nous LongCat 2.0 free | 46.7% | 1 | 100% | ~3.3 s |
| Nous Laguna S 2.1 free | 33.3% | 0 | 97.8% | ~2.7 s |
| Nous Solar Pro4 free | 42.2% | 1 | 88.9% | ~1.5 s |

The tournament therefore recommends the local Qwen adapter for the **next stage only**. It is **not graduated**. Fresh-transfer, adversarial, calibration, and production-integration gates remain open.

The result is evidence-driven, not local-first dogma. For another profile or capability, a free Nous model, paid API model, different downloadable base, or no model change at all may be the correct answer.

## Model/runtime discovery

Agoge deliberately separates two related searches.

### Trainable local bases

`agoge model-audit` discovers Hugging Face candidates without assuming any family. The shortlist is then subjected to `agoge model-probe` on the actual training machine.

The first cross-family probe has already verified:

- `Qwen/Qwen3-0.6B` ✅
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` ✅
- `microsoft/phi-1_5` ✅
- `HuggingFaceTB/SmolLM2-1.7B-Instruct` ✅
- `microsoft/bitnet-b1.58-2B-4T` ❌ for the current sequence-classification backend because the installed Transformers stack exposes no compatible sequence-classification mapping.

Hub popularity never selects the winner. Candidate bases must earn selection on the target Competency Contract.

### API-hosted runtimes

`agoge api-model-audit` discovers live models through Hermes provider catalogs. Nous Portal is the first live-proven provider, including current free-tier pricing metadata. The inference bridge is provider-neutral for Hermes-supported OpenAI-compatible `chat_completions` providers; other API protocols require explicit adapters rather than being guessed.

An API model may be:

- the final selected runtime if it satisfies the Competency Contract best;
- a Teacher or critic when training-use terms permit;
- a distillation source where policy/rights allow;
- or rejected because of safety, contract, latency, cost, privacy, availability, or quota constraints.

Agoge does **not** assume that an inference API is a training endpoint.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

agoge validate --student students/templar/student.json
agoge doctor
```

For the local training stack:

```bash
pip install -e '.[train,dev]'

agoge prepare \
  --student students/templar/student.json \
  --corpus corpus/templar-runtime-foundation-v1.jsonl \
  --split-strategy event-stratified \
  --out runs/templar-runtime

agoge train \
  --run runs/templar-runtime \
  --backend qlora-seqcls \
  --max-length 512

agoge examine-seqcls --run runs/templar-runtime --model adapter --split validation --max-length 512
```

For discovery/evaluation:

```bash
# Hugging Face trainable-base discovery
agoge model-audit \
  --pipeline-tag text-generation \
  --min-parameters 400000000 \
  --max-parameters 2000000000 \
  --allow-license apache-2.0 \
  --allow-license mit \
  --out audit.json

# Live free API runtimes exposed by Hermes/Nous
agoge api-model-audit --provider nous --free-only --out nous-free.json
```

## Multi-machine roles

Agoge roles can be split across machines without pretending every machine is a trainer.

The current proving layout uses:

- **Katana**: GPU Trainer/Examiner and local model probing;
- **Psalmbox**: CPU/network-oriented faculty, corpus, provenance, and validation worker.

A future Fleet integration may schedule these roles across available nodes while leaving Agoge responsible for educational/training semantics.

## Safety boundary

Agoge may train or select intelligence. **It does not turn intelligence into authority.**

For Templar specifically:

- deterministic Fleet policy runs before and after Templar where required;
- Fleet owns request/event identity, authorization, RunAuthority, promotion authority, and execution;
- Templar receives a bounded projection of observable security facts;
- the classifier predicts only a closed disposition class;
- deterministic code maps that class to exact `ALLOW | DENY | REVIEW` plus canonical reason codes;
- malformed, stale, unsupported, or unbound results fail closed outside the model;
- runtime tournaments cannot waive graduation gates.

See `docs/ARCHITECTURE.md`, `docs/MASTER_PLAN.md`, `docs/BASE_MODEL_AUDIT.md`, and `docs/PROOFS.md` for the current architecture and evidence.
