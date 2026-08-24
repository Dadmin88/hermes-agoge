from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..prompting import training_messages


class TrainingDependencyError(RuntimeError):
    pass


def _imports() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise TrainingDependencyError(
            "QLoRA dependencies are missing. Install with: pip install -e '.[train]'"
        ) from exc
    return {
        "torch": torch,
        "Dataset": Dataset,
        "LoraConfig": LoraConfig,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "SFTConfig": SFTConfig,
        "SFTTrainer": SFTTrainer,
    }


def _read_examples(path: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            item = json.loads(raw)
            rows.append(
                {
                    "messages": training_messages(
                        item["prompt"], item["completion"], contract
                    )
                }
            )
    return rows


def train(
    run_dir: Path,
    *,
    learning_rate: float = 2e-4,
    epochs: float = 1.0,
    max_steps: int | None = None,
    max_length: int = 1024,
    lora_r: int = 16,
    lora_alpha: int = 32,
    gradient_accumulation_steps: int = 8,
) -> dict[str, object]:
    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError(
            "QLoRA backend requires a CUDA GPU in the initial Agoge implementation"
        )
    if max_steps is not None and max_steps < 1:
        raise RuntimeError("max_steps must be a positive integer when supplied")
    if gradient_accumulation_steps < 1:
        raise RuntimeError("gradient_accumulation_steps must be positive")

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    student_document = json.loads(
        (run_dir / "spec" / "student.json").read_text(encoding="utf-8")
    )
    contract = student_document["output_contract"]
    model_name = manifest["base_model"]
    model_revision = manifest["base_model_revision"]
    dataset = lib["Dataset"].from_list(
        _read_examples(run_dir / "data" / "train.jsonl", contract)
    )
    artifact_dir = run_dir / "artifacts" / "adapter"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    compute_dtype = (
        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )
    quantization = lib["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    peft_config = lib["LoraConfig"](
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )

    torch.cuda.reset_peak_memory_stats(0)
    tokenizer = lib["AutoTokenizer"].from_pretrained(
        model_name,
        revision=model_revision,
        use_fast=True,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    token_lengths: list[int] = []
    for row in dataset:
        encoded = tokenizer.apply_chat_template(
            row["messages"], tokenize=True, return_dict=True
        )
        token_lengths.append(len(encoded["input_ids"]))
    max_observed_tokens = max(token_lengths)
    if max_observed_tokens > max_length:
        raise RuntimeError(
            "QLoRA max_length would truncate supervised assistant output: "
            f"configured={max_length}, observed_max={max_observed_tokens}. "
            "Increase max_length or deliberately reduce the model input projection."
        )
    model = lib["AutoModelForCausalLM"].from_pretrained(
        model_name,
        revision=model_revision,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=compute_dtype,
    )
    model.config.use_cache = False

    args = lib["SFTConfig"](
        output_dir=str(artifact_dir),
        learning_rate=learning_rate,
        num_train_epochs=epochs,
        max_steps=max_steps if max_steps is not None else -1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=gradient_accumulation_steps,
        logging_steps=1 if max_steps is not None else 5,
        save_strategy="no" if max_steps is not None else "epoch",
        max_length=max_length,
        packing=False,
        assistant_only_loss=True,
        report_to="none",
        bf16=bool(compute_dtype == torch.bfloat16),
        fp16=bool(compute_dtype == torch.float16),
    )
    trainer = lib["SFTTrainer"](
        model=model,
        args=args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    train_output = trainer.train()
    trainer.save_model(str(artifact_dir))

    result: dict[str, object] = {
        "schema": "agoge.training-result.v1",
        "backend": "qlora",
        "student_id": manifest["student_id"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "status": "TRAINED",
        "artifact_dir": str(artifact_dir),
        "training": {
            "epochs": epochs,
            "max_steps": max_steps,
            "max_length": max_length,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "compute_dtype": str(compute_dtype),
            "packing": False,
            "assistant_only_loss": True,
            "observed_max_tokens": max_observed_tokens,
        },
        "metrics": dict(train_output.metrics),
        "cuda": {
            "device_name": torch.cuda.get_device_name(0),
            "max_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
        },
    }
    (run_dir / "training-result.json").write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return result
