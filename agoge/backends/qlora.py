from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TrainingDependencyError(RuntimeError):
    pass


def _imports() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise TrainingDependencyError("QLoRA dependencies are missing. Install with: pip install -e '.[train]'") from exc
    return {"torch": torch, "Dataset": Dataset, "LoraConfig": LoraConfig, "BitsAndBytesConfig": BitsAndBytesConfig, "SFTConfig": SFTConfig, "SFTTrainer": SFTTrainer}


def _read_examples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            item = json.loads(raw)
            rows.append({"messages": [
                {"role": "system", "content": "You are a bounded specialist evaluator. Return only the required closed JSON decision object. Never claim or grant authority."},
                {"role": "user", "content": json.dumps(item["prompt"], sort_keys=True, separators=(",", ":"))},
                {"role": "assistant", "content": json.dumps(item["completion"], sort_keys=True, separators=(",", ":"))},
            ]})
    return rows


def train(run_dir: Path, *, learning_rate: float = 2e-4, epochs: float = 1.0, max_length: int = 1024, lora_r: int = 16, lora_alpha: int = 32) -> dict[str, object]:
    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("QLoRA backend requires a CUDA GPU in the initial Agoge implementation")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    model_name = manifest["base_model"]
    dataset = lib["Dataset"].from_list(_read_examples(run_dir / "data" / "train.jsonl"))
    artifact_dir = run_dir / "artifacts" / "adapter"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = lib["BitsAndBytesConfig"](load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=compute_dtype)
    peft_config = lib["LoraConfig"](r=lora_r, lora_alpha=lora_alpha, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules="all-linear")
    args = lib["SFTConfig"](output_dir=str(artifact_dir), learning_rate=learning_rate, num_train_epochs=epochs, per_device_train_batch_size=1, gradient_accumulation_steps=8, logging_steps=5, save_strategy="epoch", max_length=max_length, packing=True, report_to="none")
    trainer = lib["SFTTrainer"](model=model_name, args=args, train_dataset=dataset, quantization_config=quantization, peft_config=peft_config)
    trainer.train()
    trainer.save_model(str(artifact_dir))
    result = {"schema": "agoge.training-result.v1", "backend": "qlora", "student_id": manifest["student_id"], "base_model": model_name, "status": "TRAINED", "artifact_dir": str(artifact_dir)}
    (run_dir / "training-result.json").write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return result
