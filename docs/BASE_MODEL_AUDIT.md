# Base Model Audit

Agoge must not assume Qwen, Llama, Gemma, Mistral, Phi, SmolLM, or any other model family. Base-model choice is an evidence-producing workflow.

## Stage 1: Hub discovery and metadata audit

The initial discovery source is Hugging Face Hub through its supported API client. Agoge records exact repository/revision identity and audits candidate metadata including:

- pipeline/task tag;
- parameter count;
- library and model architecture/config type;
- gated/private state;
- model-card license metadata;
- base-model lineage where declared;
- safetensors parameter and repository weight-size metadata;
- downloads/likes/tags as discovery context only, never correctness evidence.

A Hub audit is content-addressed and records both accepted-shortlist and rejection reasons. Missing or incompatible licensing/terms must not be guessed. Gated models require explicit policy. Unknown architecture/backend compatibility requires a later compatibility probe.

The Hub stage never chooses a winning model.

## Stage 2: Local backend/hardware compatibility probe

Shortlisted candidates are checked on the intended training node for the actual Agoge backend requirements. This includes, as applicable:

- Transformers architecture support;
- causal-LM or sequence-classification support;
- PEFT/LoRA compatibility;
- quantization/backend compatibility;
- context length required by the Student corpus;
- local VRAM/RAM/disk feasibility;
- model load and one-step training smoke tests.

A model that cannot be safely proven compatible does not proceed merely because its Hub metadata looked attractive.

## Stage 3: Student-local base benchmark

Only locally compatible candidates compete on the Student's actual untuned baseline/Exam tasks. The selection report records:

- all candidates considered;
- exact revisions and audit metadata;
- rejection reasons;
- local resource footprint and latency;
- untuned Student Exam results;
- any backend-specific limitations;
- why the selected base won for this Student.

Popularity, vendor, and model family are never selection criteria by themselves.

## Relationship to API/runtime selection

A **Base Model Audit** answers a narrower question: which downloadable/trainable base deserves an adaptation benchmark? It is not the full runtime-selection problem.

Agoge runtime selection is location/provider agnostic. A candidate runtime may be:

- a local untouched model;
- a local base plus Agoge adapter;
- an API-hosted inference model such as a Nous Portal model;
- a provider-hosted tuned artifact when an explicit training adapter and usage/provenance contract exist.

API-hosted candidates therefore use a separate provider/runtime lane:

```text
Hermes provider catalog
    -> availability / pricing / quota / protocol metadata
    -> credential-isolated API smoke screen
    -> same Competency Contract + target/anchor Exam
    -> latency / availability / contract / cost evidence
    -> mixed Runtime Tournament with local candidates
```

An API model is allowed to win without any weight training when it satisfies the user's privacy/offline/cost/latency constraints and beats the alternatives on the authoritative Competency measurements. Conversely, a local adapter is allowed to win even when a free API model is available. Agoge does not treat locality, vendor, price, or trainability as a proxy for competence.

Hermes owns provider credentials. Agoge's API benchmark path uses a short-lived Hermes subprocess/adapter that resolves credentials internally and returns only normalized model output, usage, latency, and error metadata. Credentials must not enter Agoge corpora, Exam reports, prompts, or model artifacts.

## Current Templar status

`Qwen/Qwen3-0.6B` remains the pinned Templar research base. It was originally selected manually, but its Competency-bound adapter has now also won the first mixed local/API foundation Runtime Tournament against the strongest three currently free Nous candidates. That does **not** complete the base-model audit: TinyLlama 1.1B, Phi-1.5, and SmolLM2 1.7B have already passed the exact local 4-bit/PEFT sequence-classification compatibility probe and still need equal-budget adaptation benchmarks before Qwen can be called the best trainable base for Templar. Microsoft BitNet passed Hub metadata policy but was rejected by the current backend because Transformers exposes no compatible sequence-classification mapping for that model type.
