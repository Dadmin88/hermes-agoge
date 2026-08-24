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

## Current Templar status

`Qwen/Qwen3-0.6B` is the currently pinned Templar research base because it was selected manually for the initial local proof. It is not an Agoge default and should eventually compete through the same Base Model Audit and Student-local benchmark process as other candidates.
