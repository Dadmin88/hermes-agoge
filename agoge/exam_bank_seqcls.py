from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .backends.hf_seqcls_exam import _imports, _tree_digest
from .dispositions import disposition_for_class, registry_lookup, validate_disposition_registry
from .exam import summarize_exam
from .exam_bank import load_exam_manifest, read_exam_cases, verify_exam_body
from .prompting import user_content
from .spec import SpecError, digest
from .templar_projection import project_templar_event


def examine_seqcls_bank(
    *,
    run_dir: Path,
    manifest_path: Path,
    body_path: Path,
    model_kind: str = "adapter",
    max_length: int = 2048,
    seed: int = 41,
    out: Path | None = None,
) -> dict[str, Any]:
    if model_kind not in {"base", "adapter"}:
        raise SpecError("exam-bank model_kind must be base or adapter")
    if max_length < 1:
        raise SpecError("exam-bank max_length must be positive")

    run_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    bank_manifest = load_exam_manifest(manifest_path)
    cases = read_exam_cases(body_path)
    verify_exam_body(bank_manifest, cases)

    if run_manifest.get("competency_id") != bank_manifest.get("competency_id"):
        raise SpecError("exam bank competency ID does not match Askesis run")
    if run_manifest.get("competency_hash") != bank_manifest.get("competency_hash"):
        raise SpecError("exam bank competency hash does not match Askesis run")
    if bank_manifest.get("training_forbidden") is not True:
        raise SpecError("exam bank is not training-forbidden")

    registry = validate_disposition_registry(
        json.loads((run_dir / "spec" / "dispositions.json").read_text(encoding="utf-8"))
    )
    if registry["registry_hash"] != run_manifest.get("disposition_registry_hash"):
        raise SpecError("Askesis disposition registry does not match its manifest")
    lookup = registry_lookup(registry)
    for case in cases:
        decision = case.expected.get("decision")
        reasons = case.expected.get("reason_codes")
        if type(decision) is not str or type(reasons) is not list or not all(
            type(item) is str and item for item in reasons
        ):
            raise SpecError(f"exam case {case.case_id} has an invalid expected disposition")
        key = (decision, tuple(sorted(reasons)))
        if key not in lookup:
            raise SpecError(
                f"exam case {case.case_id} expects a disposition absent from the Student registry"
            )

    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("sequence-classification exam bank requires CUDA")

    entries = registry["entries"]
    assert type(entries) is list
    num_labels = len(entries)
    model_name = run_manifest["base_model"]
    model_revision = run_manifest["base_model_revision"]
    tokenizer = lib["AutoTokenizer"].from_pretrained(
        model_name, revision=model_revision, use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    texts = [user_content(project_templar_event(case.prompt)) for case in cases]
    lengths = [
        len(tokenizer(text, add_special_tokens=True)["input_ids"]) for text in texts
    ]
    observed_max_tokens = max(lengths)
    if observed_max_tokens > max_length:
        raise RuntimeError(
            "sequence-classification exam-bank max_length would truncate a case: "
            f"configured={max_length}, observed_max={observed_max_tokens}"
        )

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = lib["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    id2label = {index: str(entry["label_id"]) for index, entry in enumerate(entries)}
    label2id = {label: index for index, label in id2label.items()}
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    model = lib["AutoModelForSequenceClassification"].from_pretrained(
        model_name,
        revision=model_revision,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=compute_dtype,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.problem_type = "single_label_classification"

    adapter_hash: str | None = None
    if model_kind == "adapter":
        adapter_dir = run_dir / "artifacts" / "seqcls-adapter"
        adapter_hash = _tree_digest(adapter_dir)
        model = lib["PeftModel"].from_pretrained(model, str(adapter_dir))
    model.eval()

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case, text in zip(cases, texts, strict=True):
        encoded = tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=True,
            truncation=False,
        )
        encoded = {key: value.to(model.device) for key, value in encoded.items()}
        torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            logits = model(**encoded).logits[0].float()
            probabilities = torch.softmax(logits, dim=-1)
        torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        class_index = int(torch.argmax(probabilities).item())
        disposition = disposition_for_class(registry, class_index)
        sorted_probs = torch.sort(probabilities, descending=True).values
        confidence = float(sorted_probs[0].item())
        margin = float(
            (sorted_probs[0] - sorted_probs[1]).item()
            if len(sorted_probs) > 1
            else sorted_probs[0].item()
        )
        rows.append(
            {
                "example_id": case.case_id,
                "example_hash": case.content_hash,
                "competency": case.competency,
                "event_schema": case.prompt.get("schema"),
                "expected": case.expected,
                "actual": {
                    "raw": disposition["label_id"],
                    "json_valid": True,
                    "contract_valid": True,
                    "decision": disposition["decision"],
                    "reason_codes": list(disposition["reason_codes"]),
                    "error": None,
                    "class_index": class_index,
                    "label_id": disposition["label_id"],
                    "confidence": confidence,
                    "margin": margin,
                },
            }
        )

    summary = summarize_exam(rows)
    ordered_latency = sorted(latencies)
    p95_index = min(
        len(ordered_latency) - 1,
        max(0, round((len(ordered_latency) - 1) * 0.95)),
    )
    summary.update(
        {
            "latency_ms_median": ordered_latency[len(ordered_latency) // 2],
            "latency_ms_p95": ordered_latency[p95_index],
            "runtime_device": torch.cuda.get_device_name(0),
        }
    )
    exam_spec = {
        "schema": "agoge.exam-bank-exam-spec.v1",
        "bank_id": bank_manifest["bank_id"],
        "bank_kind": bank_manifest["kind"],
        "bank_manifest_hash": bank_manifest["manifest_hash"],
        "bank_body_hash": bank_manifest["body_hash"],
        "competency_id": bank_manifest["competency_id"],
        "competency_hash": bank_manifest["competency_hash"],
        "student_id": run_manifest["student_id"],
        "student_hash": run_manifest["student_hash"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "disposition_registry_hash": registry["registry_hash"],
        "model_kind": model_kind,
        "adapter_hash": adapter_hash,
        "case_count": len(cases),
        "max_length": max_length,
        "observed_max_tokens": observed_max_tokens,
        "seed": seed,
        "training_forbidden": True,
    }
    result = {
        "schema": "agoge.exam-bank-result.v1",
        "exam_id": digest(exam_spec),
        "exam_spec": exam_spec,
        "performed_at_unix_ms": time.time_ns() // 1_000_000,
        "summary": summary,
        "rows": rows,
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
