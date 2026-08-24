from __future__ import annotations

import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from ..corpus import read_jsonl
from ..dispositions import disposition_for_class, validate_disposition_registry
from ..exam import summarize_exam
from ..prompting import user_content
from ..spec import digest
from ..templar_projection import project_templar_event


class SequenceExamDependencyError(RuntimeError):
    pass


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def _imports() -> dict[str, Any]:
    try:
        import torch
        from peft import PeftModel
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
    except ImportError as exc:
        raise SequenceExamDependencyError(
            "Sequence-classification Exam dependencies are missing. "
            "Install with: pip install -e '.[train]'"
        ) from exc
    return {
        "torch": torch,
        "PeftModel": PeftModel,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
    }


def _tree_digest(path: Path) -> str:
    if not path.is_dir():
        raise RuntimeError(f"adapter directory does not exist: {path}")
    hasher = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise RuntimeError(f"adapter directory is empty: {path}")
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        content = item.read_bytes()
        hasher.update(len(relative).to_bytes(8, "big"))
        hasher.update(relative)
        hasher.update(len(content).to_bytes(8, "big"))
        hasher.update(content)
    return "sha256:" + hasher.hexdigest()


def examine(
    run_dir: Path,
    *,
    model_kind: str,
    split: str = "test",
    max_length: int = 2048,
    seed: int = 41,
) -> dict[str, Any]:
    if model_kind not in {"base", "adapter"}:
        raise RuntimeError("model_kind must be 'base' or 'adapter'")
    if split not in {"train", "validation", "test"}:
        raise RuntimeError("split must be train, validation, or test")
    if max_length < 1:
        raise RuntimeError("max_length must be positive")

    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("sequence-classification Exam requires CUDA")

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    registry = validate_disposition_registry(
        json.loads((run_dir / "spec" / "dispositions.json").read_text(encoding="utf-8"))
    )
    if registry["registry_hash"] != manifest.get("disposition_registry_hash"):
        raise RuntimeError("Askesis disposition registry does not match its manifest")
    entries = registry["entries"]
    assert type(entries) is list
    num_labels = len(entries)
    examples = read_jsonl(run_dir / "data" / f"{split}.jsonl")

    model_name = manifest["base_model"]
    model_revision = manifest["base_model_revision"]
    tokenizer = lib["AutoTokenizer"].from_pretrained(
        model_name, revision=model_revision, use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    texts = [user_content(project_templar_event(example.prompt)) for example in examples]
    lengths = [
        len(tokenizer(text, add_special_tokens=True)["input_ids"]) for text in texts
    ]
    observed_max_tokens = max(lengths)
    if observed_max_tokens > max_length:
        raise RuntimeError(
            "sequence-classification Exam max_length would truncate a Fleet event: "
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

    # Warm the tokenizer/model path once so runtime latency excludes one-time CUDA
    # graph/kernel initialization while still including normal per-request tokenization.
    warmup = tokenizer(
        texts[0], return_tensors="pt", add_special_tokens=True, truncation=False
    )
    warmup = {key: value.to(model.device) for key, value in warmup.items()}
    with torch.inference_mode():
        model(**warmup)
    torch.cuda.synchronize()

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for example, text in zip(examples, texts, strict=True):
        torch.cuda.synchronize()
        started = time.perf_counter()
        encoded = tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=True,
            truncation=False,
        )
        encoded = {key: value.to(model.device) for key, value in encoded.items()}
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
                "example_id": example.example_id,
                "example_hash": example.content_hash,
                "competency": example.competency,
                "event_schema": example.prompt.get("schema"),
                "expected": example.completion,
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
                    "latency_ms": latency_ms,
                    "probabilities": {
                        str(entries[index]["label_id"]): float(probabilities[index].item())
                        for index in range(num_labels)
                    },
                },
            }
        )

    exam_spec = {
        "schema": "agoge.exam-spec.v1",
        "student_id": manifest["student_id"],
        "student_hash": manifest["student_hash"],
        "corpus_hash": manifest["corpus_hash"],
        "disposition_registry_hash": registry["registry_hash"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "inference_backend": "hf-seqcls",
        "model_kind": model_kind,
        "adapter_hash": adapter_hash,
        "split": split,
        "max_length": max_length,
        "seed": seed,
    }
    if manifest.get("competency_id") is not None:
        exam_spec["competency_id"] = manifest["competency_id"]
        exam_spec["competency_hash"] = manifest["competency_hash"]
    summary = summarize_exam(rows)
    summary.update(
        {
            "latency_ms_median": statistics.median(latencies) if latencies else None,
            "latency_ms_p95": _percentile(latencies, 0.95),
            "runtime_device": torch.cuda.get_device_name(0),
        }
    )
    result = {
        "schema": "agoge.exam-result.v1",
        "exam_id": digest(exam_spec),
        "exam_spec": exam_spec,
        "performed_at_unix_ms": time.time_ns() // 1_000_000,
        "summary": summary,
        "rows": rows,
    }
    output_path = run_dir / f"exam-seqcls-{model_kind}-{split}.json"
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
