# Hermes Academy Bridge

Hermes Academy is an optional faculty source for Hermes Agoge. The bridge reuses Academy's pedagogy without turning a model-training run into Academy Continuing Education and without making Academy depend on Agoge.

## Boundary

Academy Continuing Education teaches a Hermes profile. Its learner owns native `/goal`, `message_agent`, `/learn`, and learner-local skill persistence.

Agoge's learner is different: it is a model Student whose durable change is produced later by an Askesis gradient run.

Therefore an Agoge faculty brief explicitly uses `agoge-model-curriculum-contributor` mode and tells the Academy profile not to invoke:

- `/goal` or `/subgoal`;
- `/learn` or `skill_manage`;
- `message_agent`;
- Fleet tools;
- any persistence mechanism.

Academy supplies pedagogy, scenarios, counterexamples, critique, and assessment evidence only.

## Faculty binding

`agoge.academy-faculty-binding.v1` is supplied by Agoge/operator state rather than by faculty output. It records:

- faculty profile ID;
- faculty distribution version;
- exact faculty source revision;
- actual inference provider/model/version;
- training-use policy.

The faculty model cannot self-assert or replace this identity.

## Faculty payload

The Academy profile returns only `agoge.academy-faculty-payload.v1`:

```json
{
  "schema": "agoge.academy-faculty-payload.v1",
  "request_id": "sha256:...",
  "items": [
    {
      "prompt": {"schema": "...", "facts": {}},
      "completion": {
        "schema": "agoge.templar-model-output.v1",
        "decision": "ALLOW",
        "reason_codes": []
      },
      "rationale": "...",
      "basis": ["..."]
    }
  ]
}
```

No teacher identity, authority, evaluator binding, or consumer-system hashes are accepted from the model. Agoge wraps the payload in its provider-neutral `TeacherResponse` using the operator-supplied faculty binding.

## Training-use rule

Academy faculty output is not assumed to be legal/appropriate training material merely because it came from an installed Academy profile. The underlying inference provider/model still matters.

The bridge therefore defaults to `training_use: unknown` unless the relevant output/use terms have been explicitly established. Unknown/disallowed Academy output may still be used as curriculum advice, critique, red-team input, or review evidence, but the candidate-promotion engine will not admit it into trainable corpus content.

## Live bridge proof

On 2026-08-23 Agoge invoked the installed `academy-cybersecurity-instructor` profile on Katana:

- faculty distribution: `0.2.0`;
- faculty source revision: `4d93ed0eec730ac344546bba980ce844b2efbeed`;
- configured inference: Nous `xiaomi/mimo-v2.5-pro`;
- Agoge request ID: `sha256:5331c4c1cdafe389815762551c099f1b199e1e9ab49e0f3dff0540cbc12a4786`;
- competency: `prompt-injection`;
- requested items: 3.

The first faculty response understood the pedagogy but violated the closed machine schema. Agoge rejected it. The bridge prompt was corrected to distinguish an output-contract descriptor from an output instance and to require exact top-level/item/completion keys.

The second faculty response passed the bridge contract and produced:

- direct embedded injection -> `DENY`;
- quoted/educational injection language -> `ALLOW`;
- ambiguous template-engine/instruction syntax -> `REVIEW`.

The final wrapped Teacher response hash is:

`sha256:d518f8af3711a0c9a06e497bee272899e294549e1ed79c365d8409039b01fec0`

All three candidates passed independent curriculum review, but the promotion result was still:

- accepted: 0;
- rejected: 0;
- quarantined: 3.

Reason: the faculty binding remained `training_use: unknown`.

This proves Academy can materially teach Agoge while Agoge remains sovereign over provenance and weight-training admission.
