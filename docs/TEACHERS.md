# Hermes Agoge Teacher and Candidate Contract

Agoge treats teaching as a provenance-bearing proposal process, not as permission to mutate a training corpus.

## Teacher roles

A Teacher may be:

- deterministic rules owned by Agoge or a student project;
- a model/provider;
- Hermes Academy faculty;
- a human contributor.

Every Teacher has an immutable `agoge.teacher-identity.v1` record that binds its provider/model/version/role and a `training_use` state:

- `allowed`: output may become training content after independent review;
- `unknown`: output may be inspected or used as review/adjudication evidence, but cannot be promoted into trainable content;
- `disallowed`: output must not become training content.

`training_use` is provenance policy, not a claim about legal rights. Provider terms and source licenses still require their own review.

## Request

`agoge.teacher-request.v1` binds a Teacher assignment to:

- exact Student and Curriculum hashes;
- one named competency;
- one bounded purpose;
- maximum item count;
- output contract and teaching constraints;
- exact source revisions.

The request ID is content-addressed. A response for another request fails closed.

## Response

`agoge.teacher-response.v1` carries:

- the exact request ID;
- exact Teacher identity;
- bounded candidate items;
- per-item rationale and basis references.

A response is still only a proposal.

## Candidate import

`teacher-import` validates every proposed completion against the Student's closed output contract. Valid proposals become `agoge.example.v1` records with:

- deterministic candidate identity;
- Teacher identity;
- request ID;
- response hash;
- training-use state;
- `review_state: generated-unreviewed`.

Import does not add the candidate to the accepted training corpus.

## Independent review

`agoge.candidate-review.v1` binds one reviewer decision to one exact candidate hash.

Decisions are:

- `ACCEPT`;
- `REJECT`;
- `QUARANTINE`.

A source Teacher cannot independently approve its own candidate. At least one review from another identity is required.

Promotion rules are intentionally conservative:

- any independent `REJECT` wins;
- any independent `QUARANTINE`, or disagreement that does not resolve to all-ACCEPT, quarantines the candidate;
- an all-ACCEPT result still quarantines the candidate when its source Teacher is not `training_use: allowed`;
- only independently accepted candidates from an allowed source become accepted corpus examples.

Reviewer metadata is provenance. Agoge training backends consume accepted example prompts/completions, not reviewer prose.

## Deterministic Templar foundation teacher

`templar-foundation-rules-v1` is the first built-in deterministic teacher. It emits bounded cases from the pinned Fleet/Templar architecture for all current Templar competencies.

The generator intentionally does not model a request that already carries a deterministic Fleet hard deny as a normal Templar inference case. Fleet's real pre-execution ordering stops such requests before Templar. This avoids teaching the model an impossible runtime responsibility.

The deterministic generator has `training_use: allowed`, but its output still requires independent review before acceptance.

## CLI lifecycle

```bash
agoge teacher-request \
  --student students/templar/student.json \
  --competency prompt-injection \
  --count 7 \
  --out request.json

agoge teacher-deterministic \
  --request request.json \
  --out response.json

agoge teacher-import \
  --request request.json \
  --response response.json \
  --out candidates.jsonl

agoge candidate-promote \
  --candidates candidates.jsonl \
  --reviews reviews.jsonl \
  --out-dir reviewed
```

Provider-specific adapters should sit behind this contract rather than inventing provider-specific corpus formats.
