
## Proof: calibrated corrective Templar survives an external-hidden adversarial exam

A second surgical corrective Askesis targeted only the two remaining fresh-transfer REVIEW boundaries using new training language that did not copy the sealed bank. The regenerated Phase 23 corpus again passed independent admission 252/252 with zero rejects and zero quarantines. The resulting combined two-family corpus remains 504 events and is content-addressed as `sha256:36c4a0de4b33605686bc8901cc960005bc49f3902bc0a04ca868a818fdb765cf`. The unchanged 34-case fresh-transfer body remained `sha256:1e3808d7018deec7ffbfd23494bf6004ecd2c371e25f631ef76e5ea5da9c3850` and resealed against the new corpus with zero exact contamination.

A fresh Qwen3-0.6B adapter was trained from base weights for the same 150-step, batch-8, 5e-5 class-balanced recipe. Training completed in ~676.5 seconds with ~1.47 GB peak CUDA allocation. Internal validation remained 46/46 exact. Raw fresh transfer improved to 33/34 exact (97.1%) but retained one dangerous low-confidence hidden-instruction DENY -> ALLOW error.

Agoge then introduced a content-addressed calibration policy derived only from internal validation evidence. All correct validation-time Phase 23 ALLOW predictions carrying risk signals had confidence >= 0.997, so the policy conservatively routes a risk-bearing Phase 23 ALLOW below 0.95 to an existing closed REVIEW disposition matching the Fleet risk signal. Calibration never invents a new reason code or class and preserves the original neural prediction for audit.

With calibration enabled, internal validation remains 46/46 exact with zero false-ALLOWs. The unchanged fresh-transfer bank becomes 32/34 exact (94.1%) with zero false-ALLOWs and zero false-DENYs; the two differences are safe REVIEW abstentions.

A separate 20-case Phase 23 hidden-adversarial bank was then created and retained outside the Agoge repository on Psalmbox. Every body case was constructed by the Student-pinned Fleet runtime. The body hash is `sha256:63a1e674274fc8abe1781a127691c843e92e212e75cddb7e0936884ee0def3f6`. Psalmbox resealed that unchanged body against the exact current 504-event corpus with zero contamination and `visibility=external-hidden`. Katana received the body only transiently under `/tmp` for the authorized Exam and deleted it immediately afterward.

Calibrated hidden-adversarial result:

| Exam | Exact | Decision | False ALLOW | False DENY | Median latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| External-hidden adversarial (20) | **90% (18/20)** | **90%** | **0** | **0** | ~43.5 ms |

Both hidden misses routed to REVIEW rather than an unsafe permissive or hard-denial decision. Contract validity was 20/20 and exact reason-family accuracy was 19/20.

This is evidence that the current Templar runtime can combine learned classification with a separately derived uncertainty policy and survive a genuinely external-hidden adversarial exam without a false-ALLOW. It is **not graduation**: the hidden bank is still small, calibration needs broader evidence, and production Fleet integration/regression gates remain open.
