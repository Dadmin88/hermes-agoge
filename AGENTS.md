# AGENTS.md

Hermes Agoge is a model-training system, not an execution authority.

## Non-negotiable boundaries

- Keep Agoge core independent of Fleet, Keryx, Nodescale, and Academy runtime imports.
- Consumer systems own authority. Model output is never authority.
- Academy integration is optional and one-way: Agoge may request teaching; Academy must not depend on Agoge.
- Never place credentials, API keys, private prompts, secret bodies, or unrelated user data in training corpora.
- Never silently promote generated teacher output into accepted training data.
- Preserve source/model/provider/revision provenance for generated material.
- Preserve held-out exam isolation. Do not train on an exam because the model failed it.
- Do not claim a model is graduated or production-ready merely because training completed.
- Prefer deterministic generators for deterministic rules and model teachers for genuinely semantic/adversarial cases.

## Templar reference student

Templar remains low-authority and advisory. The trained model should return only decision/reason-code content. Fleet-owned deterministic code supplies request binding and retains all authorization semantics.
