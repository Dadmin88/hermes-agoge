from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ..corpus import read_jsonl
from ..exam import parse_model_output, summarize_exam
from ..prompting import inference_messages
from ..spec import StudentSpec, digest


class ExamDependencyError(RuntimeError):
    pass


def _imports() -> dict[str, Any]:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise ExamDependencyError(
            "Exam dependencies are missing. Install with: pip install -e '.[train]'"
        ) from exc
    return {
        "torch": torch,
        "PeftModel": PeftModel,
        "AutoModelForCausalLM": AutoModelForCausalLM,
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


def _generate(
    *,
    model: Any,
    tokenizer: Any,
    prompt: dict[str, Any],
    max_new_tokens: int,
    torch: Any,
) -> str:
    encoded = tokenizer.apply_chat_template(
        inference_messages(prompt),
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_tensors="pt",
        return_dict=True,
    )
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    input_length = encoded["input_ids"].shape[-1]
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = output[0, input_length:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def examine(
    run_dir: Path,
    *,
    model_kind: str,
    split: str = "test",
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    if model_kind not in {"base", "adapter"}:
        raise RuntimeError("model_kind must be 'base' or 'adapter'")
    if split not in {"train", "validation", "test"}:
        raise RuntimeError("split must be train, validation, or test")
    if max_new_tokens < 1:
        raise RuntimeError("max_new_tokens must be positive")

    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("Hugging Face Exam backend requires CUDA for this release")

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    student = StudentSpec.load(run_dir / "spec" / "student.json")
    examples = read_jsonl(run_dir / "data" / f"{split}.jsonl")
    model_name = manifest["base_model"]
    model_revision = manifest["base_model_revision"]
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = lib["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    tokenizer = lib["AutoTokenizer"].from_pretrained(
        model_name,
        revision=model_revision,
        use_fast=True,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = lib["AutoModelForCausalLM"].from_pretrained(
        model_name,
        revision=model_revision,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=compute_dtype,
    )

    adapter_hash: str | None = None
    if model_kind == "adapter":
        adapter_dir = run_dir / "artifacts" / "adapter"
        adapter_hash = _tree_digest(adapter_dir)
        model = lib["PeftModel"].from_pretrained(model, str(adapter_dir))
    model.eval()
    model.config.use_cache = True

    rows: list[dict[str, Any]] = []
    for example in examples:
        raw = _generate(
            model=model,
            tokenizer=tokenizer,
            prompt=example.prompt,
            max_new_tokens=max_new_tokens,
            torch=torch,
        )
        parsed = parse_model_output(raw, student.output_contract)
        rows.append(
            {
                "example_id": example.example_id,
                "example_hash": example.content_hash,
                "competency": example.competency,
                "expected": example.completion,
                "actual": {
                    "raw": parsed.raw,
                    "json_valid": parsed.json_valid,
                    "contract_valid": parsed.contract_valid,
                    "decision": parsed.decision,
                    "reason_codes": list(parsed.reason_codes),
                    "error": parsed.error,
                },
            }
        )

    exam_spec = {
        "schema": "agoge.exam-spec.v1",
        "student_id": manifest["student_id"],
        "student_hash": manifest["student_hash"],
        "corpus_hash": manifest["corpus_hash"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "model_kind": model_kind,
        "adapter_hash": adapter_hash,
        "split": split,
        "max_new_tokens": max_new_tokens,
    }
    result = {
        "schema": "agoge.exam-result.v1",
        "exam_id": digest(exam_spec),
        "exam_spec": exam_spec,
        "performed_at_unix_ms": time.time_ns() // 1_000_000,
        "summary": summarize_exam(rows),
        "rows": rows,
    }
    output_path = run_dir / f"exam-{model_kind}-{split}.json"
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
