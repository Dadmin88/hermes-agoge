
## Proof: sealed fresh-transfer corrective Askesis closes most semantic generalization gap

The first reviewable Templar fresh-transfer bank contains 34 training-forbidden cases across both supported Fleet event families. Its body is content-addressed and resealed against each accepted training corpus; exact prompt contamination is rejected before the bank can be used as evidence.

The pre-corrective unified Qwen3 adapter scored 24/34 decision-correct and 23/34 exact dispositions on this bank, with seven dangerous false-ALLOWs. Failure analysis localized the main weakness to Phase 23 semantic paraphrase transfer for social engineering, hidden instructions, and suspicious secret handling.

Corrective Askesis did not copy failed exam prompts into training. Instead, Agoge broadened the corresponding curriculum families, regenerated Phase 23 events through the Student-pinned Fleet revision, independently reviewed every candidate, and refused corpus rebuilds whenever the reviewer found label ambiguity. The final regenerated Phase 23 source corpus admitted 252/252 candidates with zero rejects and zero quarantines. The resulting two-family runtime corpus remains 504 events and is content-addressed as `sha256:208d35eb8b4cad318cf8423d95a986aec753ce4ab46d4ba55238f923906244da`.

The unchanged 34-case bank body (`sha256:1e3808d7018deec7ffbfd23494bf6004ecd2c371e25f631ef76e5ea5da9c3850`) was resealed against that corrective corpus with zero contamination. A fresh Qwen3-0.6B adapter was then trained from base weights for 150 optimizer steps at batch 8, learning rate 5e-5, class balancing, and the same closed 16-disposition registry. Training completed in ~674.9 seconds with ~1.47 GB peak CUDA allocation.

Results:

| Exam | Exact | Decision | False ALLOW | False DENY | Median latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal validation (46) | **100%** | **100%** | **0** | **0** | ~44.8 ms |
| Internal test (46) | **100%** | **100%** | **0** | **0** | ~44.5 ms |
| Sealed fresh transfer (34) | **94.1% (32/34)** | **94.1% (32/34)** | **1** | **0** | ~43.0 ms |

The corrective cycle therefore reduced fresh-transfer false-ALLOWs from **7 to 1** and exact errors from **11 to 2** without changing the exam body or leaking it into training.

The two remaining transfer errors are both Phase 23 REVIEW-boundary cases: one hidden-instruction incident artifact is still incorrectly ALLOWed, and one suspicious-secret-handling ambiguity is over-escalated to a DENY reason from another family. Because Templar's hard safety gate requires zero false-ALLOWs, this model remains **not graduated**.

### What this proof establishes

Agoge has now demonstrated a full contamination-safe education loop: held-out transfer evaluation can expose apparent mastery, failures can be diagnosed by semantic family, corrective curriculum can be regenerated and independently admitted without copying exam items, a fresh adapter can be trained from base weights, and the unchanged sealed bank can measure whether the education transferred.

### Remaining blockers

Templar still requires zero false-ALLOW on fresh transfer, an external-hidden adversarial bank, calibration/REVIEW policy, production Fleet integration, and release-level regression evidence before graduation.
