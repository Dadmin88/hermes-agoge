from __future__ import annotations

import gc
import json
import time
from pathlib import Path
from typing import Any

from .spec import digest


class ModelProbeDependencyError(RuntimeError):
    pass


def _imports() -> dict[str, Any]:
    try:
        import torch
        from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoConfig,
            AutoModelForSequenceClassification,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
    except ImportError as exc:
        raise ModelProbeDependencyError(
            "model probe dependencies are missing; install Agoge's training extra"
        ) from exc
    return {
        "torch": torch,
        "LoraConfig": LoraConfig,
        "TaskType": TaskType,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoConfig": AutoConfig,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
    }


def probe_sequence_classifier(
    *,
    model_id: str,
    revision: str,
    num_labels: int,
    out: Path | None = None,
) -> dict[str, Any]:
    if not model_id.strip() or not revision.strip():
        raise RuntimeError("model probe requires exact model id and revision")
    if num_labels < 2:
        raise RuntimeError("sequence-classification probe requires at least two labels")

    lib = _imports()
    torch = lib["torch"]
    started = time.perf_counter()
    result: dict[str, Any] = {
        "schema": "agoge.model-probe.v1",
        "model_id": model_id,
        "revision": revision,
        "task": "sequence-classification-qlora",
        "num_labels": num_labels,
        "cuda_required": True,
        "checks": {},
        "status": "rejected",
    }
    checks = result["checks"]
    assert type(checks) is dict

    config = lib["AutoConfig"].from_pretrained(model_id, revision=revision)
    model_class = lib["AutoModelForSequenceClassification"]._model_mapping.get(type(config), None)
    checks["auto_config"] = {
        "ok": True,
        "model_type": getattr(config, "model_type", None),
        "architectures": list(getattr(config, "architectures", None) or []),
    }
    if model_class is None:
        checks["sequence_classification_mapping"] = {"ok": False, "reason": "unsupported-config"}
        result["elapsed_seconds"] = time.perf_counter() - started
        result["probe_id"] = digest({k: v for k, v in result.items() if k != "probe_id"})
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    checks["sequence_classification_mapping"] = {
        "ok": True,
        "implementation": f"{model_class.__module__}.{model_class.__name__}",
    }

    tokenizer = lib["AutoTokenizer"].from_pretrained(model_id, revision=revision, use_fast=True)
    if tokenizer.pad_token_id is None:
        if tokenizer.eos_token_id is None:
            checks["tokenizer"] = {"ok": False, "reason": "no-pad-or-eos-token"}
            result["elapsed_seconds"] = time.perf_counter() - started
            result["probe_id"] = digest({k: v for k, v in result.items() if k != "probe_id"})
            if out is not None:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            return result
        tokenizer.pad_token = tokenizer.eos_token
    checks["tokenizer"] = {
        "ok": True,
        "class": type(tokenizer).__name__,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }

    if not torch.cuda.is_available():
        checks["cuda"] = {"ok": False, "reason": "cuda-unavailable"}
        result["elapsed_seconds"] = time.perf_counter() - started
        result["probe_id"] = digest({k: v for k, v in result.items() if k != "probe_id"})
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    checks["cuda"] = {
        "ok": True,
        "device": torch.cuda.get_device_name(0),
        "compute_dtype": str(compute_dtype),
    }
    quantization = lib["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)
    model = lib["AutoModelForSequenceClassification"].from_pretrained(
        model_id,
        revision=revision,
        num_labels=num_labels,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=compute_dtype,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.problem_type = "single_label_classification"
    checks["four_bit_load"] = {
        "ok": True,
        "model_class": type(model).__name__,
        "peak_cuda_bytes": int(torch.cuda.max_memory_allocated(0)),
    }

    model = lib["prepare_model_for_kbit_training"](model)
    peft_config = lib["LoraConfig"](
        r=8,
        lora_alpha=16,
        lora_dropout=0.0,
        bias="none",
        task_type=lib["TaskType"].SEQ_CLS,
        target_modules="all-linear",
        modules_to_save=["score"],
    )
    model = lib["get_peft_model"](model, peft_config)
    trainable, total = model.get_nb_trainable_parameters()
    checks["peft_seq_cls"] = {
        "ok": True,
        "trainable_parameters": int(trainable),
        "total_parameters": int(total),
    }

    sample = tokenizer("Agoge compatibility probe.", return_tensors="pt")
    sample = {key: value.to(model.device) for key, value in sample.items()}
    model.eval()
    with torch.inference_mode():
        logits = model(**sample).logits
    checks["forward_pass"] = {
        "ok": tuple(logits.shape) == (1, num_labels),
        "logits_shape": list(logits.shape),
    }
    if tuple(logits.shape) != (1, num_labels):
        raise RuntimeError(
            f"sequence-classification forward shape is invalid: {tuple(logits.shape)!r}"
        )

    result["status"] = "benchmark-compatible"
    result["elapsed_seconds"] = time.perf_counter() - started
    result["peak_cuda_bytes"] = int(torch.cuda.max_memory_allocated(0))
    result["probe_id"] = digest({k: v for k, v in result.items() if k != "probe_id"})
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    del model
    gc.collect()
    torch.cuda.empty_cache()
    return result
