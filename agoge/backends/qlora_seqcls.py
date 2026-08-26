from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from ..corpus import read_jsonl
from ..dispositions import registry_lookup, validate_disposition_registry
from ..prompting import user_content
from ..templar_projection import project_templar_event


class SequenceTrainingDependencyError(RuntimeError):
    pass


def _imports() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import (
            LoraConfig,
            TaskType,
            get_peft_model,
            prepare_model_for_kbit_training,
        )
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            BitsAndBytesConfig,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SequenceTrainingDependencyError(
            "Sequence-classification QLoRA dependencies are missing. "
            "Install with: pip install -e '.[train]'"
        ) from exc
    return {
        "torch": torch,
        "Dataset": Dataset,
        "LoraConfig": LoraConfig,
        "TaskType": TaskType,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "DataCollatorWithPadding": DataCollatorWithPadding,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def _load_registry(run_dir: Path) -> dict[str, object]:
    path = run_dir / "spec" / "dispositions.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    return validate_disposition_registry(value)


def _rows(run_dir: Path, registry: dict[str, object]) -> list[dict[str, object]]:
    lookup = registry_lookup(registry)
    rows: list[dict[str, object]] = []
    for example in read_jsonl(run_dir / "data" / "train.jsonl"):
        key = (
            example.completion["decision"],
            tuple(sorted(example.completion["reason_codes"])),
        )
        if key not in lookup:
            raise RuntimeError(f"training example has no disposition class: {key!r}")
        rows.append(
            {
                "text": user_content(project_templar_event(example.prompt)),
                "labels": lookup[key],
                "example_id": example.example_id,
                "event_schema": example.prompt.get("schema"),
                "competency": example.competency,
                "decision": example.completion["decision"],
            }
        )
    return rows


def _balance_key(row: dict[str, object], mode: str) -> tuple[object, ...]:
    label = row.get("labels")
    if type(label) is not int:
        raise RuntimeError("sequence-classification row has an invalid label")
    if mode == "class":
        return ("class", label)
    if mode in {"event-stratum", "hierarchical", "decision-hierarchical"}:
        event_schema = row.get("event_schema")
        competency = row.get("competency")
        if type(event_schema) is not str or type(competency) is not str:
            raise RuntimeError(f"{mode} balancing requires event schema and competency")
        return (mode, event_schema, competency, label)
    raise RuntimeError(f"unsupported sequence-classification balance mode: {mode}")


def _resample_group(
    source: list[dict[str, object]], *, target: int, rng: random.Random
) -> list[dict[str, object]]:
    if target < 1 or not source:
        raise RuntimeError("sequence-classification balance group is empty or invalid")
    ordered = sorted(source, key=lambda item: str(item["example_id"]))
    if len(ordered) >= target:
        shuffled = list(ordered)
        rng.shuffle(shuffled)
        return shuffled[:target]
    result = list(ordered)
    while len(result) < target:
        result.append(dict(ordered[rng.randrange(len(ordered))]))
    return result


def _balance_rows(
    rows: list[dict[str, object]], *, seed: int, mode: str
) -> list[dict[str, object]]:
    if mode == "none":
        return list(rows)
    if not rows:
        raise RuntimeError("sequence-classification dataset is empty")
    rng = random.Random(seed)

    if mode == "decision-hierarchical":
        by_decision: dict[
            str,
            dict[int, dict[tuple[object, ...], list[dict[str, object]]]],
        ] = {}
        decision_totals: Counter[str] = Counter()
        for row in rows:
            decision = row.get("decision")
            label = row.get("labels")
            if decision not in {"ALLOW", "DENY", "REVIEW"} or type(label) is not int:
                raise RuntimeError("decision-hierarchical balancing requires closed decisions")
            decision_totals[str(decision)] += 1
            key = _balance_key(row, mode)
            by_decision.setdefault(str(decision), {}).setdefault(label, {}).setdefault(
                key, []
            ).append(row)
        decision_target = max(decision_totals.values())
        balanced: list[dict[str, object]] = []
        for decision in sorted(by_decision):
            labels = by_decision[decision]
            per_label_target = max(1, (decision_target + len(labels) - 1) // len(labels))
            for label in sorted(labels):
                strata = labels[label]
                per_stratum_target = max(1, (per_label_target + len(strata) - 1) // len(strata))
                for key in sorted(strata, key=repr):
                    balanced.extend(
                        _resample_group(strata[key], target=per_stratum_target, rng=rng)
                    )
        rng.shuffle(balanced)
        return balanced

    if mode == "hierarchical":
        by_label: dict[int, dict[tuple[object, ...], list[dict[str, object]]]] = {}
        class_totals: Counter[int] = Counter()
        for row in rows:
            label = row.get("labels")
            if type(label) is not int:
                raise RuntimeError("sequence-classification row has an invalid label")
            class_totals[label] += 1
            key = _balance_key(row, mode)
            by_label.setdefault(label, {}).setdefault(key, []).append(row)
        class_target = max(class_totals.values())
        balanced: list[dict[str, object]] = []
        for label in sorted(by_label):
            strata = by_label[label]
            per_stratum_target = max(1, (class_target + len(strata) - 1) // len(strata))
            for key in sorted(strata, key=repr):
                balanced.extend(_resample_group(strata[key], target=per_stratum_target, rng=rng))
        rng.shuffle(balanced)
        return balanced

    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(_balance_key(row, mode), []).append(row)
    target = max(len(items) for items in groups.values())
    balanced = []
    for key in sorted(groups, key=repr):
        balanced.extend(_resample_group(groups[key], target=target, rng=rng))
    rng.shuffle(balanced)
    return balanced


def train(
    run_dir: Path,
    *,
    learning_rate: float = 2e-4,
    epochs: float = 1.0,
    max_steps: int | None = None,
    max_length: int = 2048,
    lora_r: int = 16,
    lora_alpha: int = 32,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
    balance_mode: str = "class",
    seed: int = 41,
) -> dict[str, object]:
    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("sequence-classification QLoRA requires a CUDA GPU")
    if max_steps is not None and max_steps < 1:
        raise RuntimeError("max_steps must be positive when supplied")
    if max_length < 1:
        raise RuntimeError("max_length must be positive")
    if per_device_train_batch_size < 1:
        raise RuntimeError("per_device_train_batch_size must be positive")
    if gradient_accumulation_steps < 1:
        raise RuntimeError("gradient_accumulation_steps must be positive")
    if balance_mode not in {
        "none",
        "class",
        "event-stratum",
        "hierarchical",
        "decision-hierarchical",
    }:
        raise RuntimeError(f"unsupported sequence-classification balance mode: {balance_mode}")

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    registry = _load_registry(run_dir)
    if registry["registry_hash"] != manifest.get("disposition_registry_hash"):
        raise RuntimeError("Askesis disposition registry does not match its manifest")
    entries = registry["entries"]
    assert type(entries) is list
    num_labels = len(entries)
    rows = _rows(run_dir, registry)
    original_counts = Counter(int(row["labels"]) for row in rows)
    original_balance_counts = (
        Counter(repr(_balance_key(row, balance_mode)) for row in rows)
        if balance_mode != "none"
        else Counter({"none": len(rows)})
    )
    training_rows = _balance_rows(rows, seed=seed, mode=balance_mode)
    balanced_counts = Counter(int(row["labels"]) for row in training_rows)
    training_balance_counts = (
        Counter(repr(_balance_key(row, balance_mode)) for row in training_rows)
        if balance_mode != "none"
        else Counter({"none": len(training_rows)})
    )

    model_name = manifest["base_model"]
    model_revision = manifest["base_model_revision"]
    tokenizer = lib["AutoTokenizer"].from_pretrained(
        model_name, revision=model_revision, use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    token_lengths = [
        len(tokenizer(str(row["text"]), add_special_tokens=True)["input_ids"])
        for row in training_rows
    ]
    observed_max_tokens = max(token_lengths)
    if observed_max_tokens > max_length:
        raise RuntimeError(
            "sequence-classification max_length would truncate a Fleet event: "
            f"configured={max_length}, observed_max={observed_max_tokens}"
        )

    dataset = lib["Dataset"].from_list(training_rows)

    def tokenize(batch: dict[str, list[object]]) -> dict[str, object]:
        return tokenizer(
            [str(value) for value in batch["text"]],
            truncation=False,
            add_special_tokens=True,
        )

    tokenized = dataset.map(
        tokenize,
        batched=True,
        remove_columns=["text", "example_id", "event_schema", "competency", "decision"],
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
    model = lib["prepare_model_for_kbit_training"](model)
    peft_config = lib["LoraConfig"](
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type=lib["TaskType"].SEQ_CLS,
        target_modules="all-linear",
        modules_to_save=["score"],
    )
    model = lib["get_peft_model"](model, peft_config)

    artifact_dir = run_dir / "artifacts" / "seqcls-adapter"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats(0)
    args = lib["TrainingArguments"](
        output_dir=str(artifact_dir),
        learning_rate=learning_rate,
        num_train_epochs=epochs,
        max_steps=max_steps if max_steps is not None else -1,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        logging_steps=1 if max_steps is not None else 5,
        save_strategy="no" if max_steps is not None else "epoch",
        report_to="none",
        bf16=bool(compute_dtype == torch.bfloat16),
        fp16=bool(compute_dtype == torch.float16),
        seed=seed,
        data_seed=seed,
    )
    trainer = lib["Trainer"](
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=lib["DataCollatorWithPadding"](
            tokenizer=tokenizer,
            pad_to_multiple_of=8,
            return_tensors="pt",
        ),
    )
    train_output = trainer.train()
    model.save_pretrained(str(artifact_dir))

    result: dict[str, object] = {
        "schema": "agoge.training-result.v1",
        "backend": "qlora-seqcls",
        "student_id": manifest["student_id"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "status": "TRAINED",
        "artifact_dir": str(artifact_dir),
        "disposition_registry_hash": registry["registry_hash"],
        "disposition_count": num_labels,
        "training": {
            "epochs": epochs,
            "max_steps": max_steps,
            "max_length": max_length,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "per_device_train_batch_size": per_device_train_batch_size,
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "compute_dtype": str(compute_dtype),
            "observed_max_tokens": observed_max_tokens,
            "balance_mode": balance_mode,
            "seed": seed,
            "original_class_counts": {
                str(key): original_counts[key] for key in sorted(original_counts)
            },
            "training_class_counts": {
                str(key): balanced_counts[key] for key in sorted(balanced_counts)
            },
            "original_balance_group_counts": {
                key: original_balance_counts[key] for key in sorted(original_balance_counts)
            },
            "training_balance_group_counts": {
                key: training_balance_counts[key] for key in sorted(training_balance_counts)
            },
        },
        "metrics": dict(train_output.metrics),
        "cuda": {
            "device_name": torch.cuda.get_device_name(0),
            "max_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
        },
    }
    (run_dir / "training-result-seqcls.json").write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return result
