from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .backends.hf_seqcls_exam import _imports
from .calibration import apply_calibration, load_calibration_policy
from .dispositions import disposition_for_class, validate_disposition_registry
from .prompting import user_content
from .spec import SpecError, digest
from .templar_projection import project_templar_event

REQUEST_SCHEMA = "fleet.templar-evaluation-request.v1"
RESPONSE_SCHEMA = "fleet.templar-backend-response.v1"
_REQUIRED_REQUEST_KEYS = {
    "schema",
    "evaluation_id",
    "request_hash",
    "event_hash",
    "fleet_policy_digest",
    "templar_policy",
    "evaluator",
    "issued_at_ms",
    "deadline_ms",
    "event",
}


def _validate_request(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REQUIRED_REQUEST_KEYS:
        raise SpecError("Fleet Templar evaluation request has an invalid closed schema")
    if value.get("schema") != REQUEST_SCHEMA:
        raise SpecError("Fleet Templar evaluation request schema is unsupported")
    event = value.get("event")
    if type(event) is not dict:
        raise SpecError("Fleet Templar event is invalid")
    if event.get("schema") not in {
        "fleet.security-event.v1",
        "fleet.learning-promotion-event.v1",
    }:
        raise SpecError("Fleet Templar event schema is unsupported")
    request_hash = value.get("request_hash")
    event_hash = value.get("event_hash")
    evaluation_id = value.get("evaluation_id")
    if type(request_hash) is not str or event.get("request_hash") != request_hash:
        raise SpecError("Fleet Templar request hash binding is invalid")
    if type(event_hash) is not str or digest(event) != event_hash:
        raise SpecError("Fleet Templar event hash binding is invalid")
    request_document = dict(value)
    request_document.pop("evaluation_id")
    if type(evaluation_id) is not str or digest(request_document) != evaluation_id:
        raise SpecError("Fleet Templar evaluation ID binding is invalid")
    request = event.get("request")
    if type(request) is not dict or request.get("policy_digest") != value.get(
        "fleet_policy_digest"
    ):
        raise SpecError("Fleet Templar policy binding is invalid")
    issued_at_ms = value.get("issued_at_ms")
    deadline_ms = value.get("deadline_ms")
    if (
        isinstance(issued_at_ms, bool)
        or type(issued_at_ms) is not int
        or isinstance(deadline_ms, bool)
        or type(deadline_ms) is not int
        or deadline_ms <= issued_at_ms
    ):
        raise SpecError("Fleet Templar request timing is invalid")
    if time.time_ns() // 1_000_000 >= deadline_ms:
        raise SpecError("Fleet Templar evaluation request is expired")
    return value


class TemplarRuntime:
    """One persistent, exact-run local Templar classifier."""

    def __init__(
        self,
        *,
        run_dir: Path,
        calibration_path: Path | None = None,
        max_length: int = 512,
        seed: int = 41,
    ) -> None:
        if max_length < 1:
            raise SpecError("Templar runtime max_length must be positive")
        self.run_dir = run_dir
        self.max_length = max_length
        self.seed = seed
        self.manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.registry = validate_disposition_registry(
            json.loads((run_dir / "spec" / "dispositions.json").read_text(encoding="utf-8"))
        )
        if self.registry["registry_hash"] != self.manifest.get("disposition_registry_hash"):
            raise SpecError("Askesis disposition registry does not match its manifest")
        self.policy = (
            None if calibration_path is None else load_calibration_policy(calibration_path)
        )

        lib = _imports()
        self.torch = lib["torch"]
        if not self.torch.cuda.is_available():
            raise RuntimeError("Templar local runtime requires CUDA")
        entries = self.registry["entries"]
        assert type(entries) is list
        self.entries = entries
        model_name = self.manifest["base_model"]
        model_revision = self.manifest["base_model_revision"]
        self.tokenizer = lib["AutoTokenizer"].from_pretrained(
            model_name, revision=model_revision, use_fast=True
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        compute_dtype = (
            self.torch.bfloat16 if self.torch.cuda.is_bf16_supported() else self.torch.float16
        )
        quantization = lib["BitsAndBytesConfig"](
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
        id2label = {index: str(entry["label_id"]) for index, entry in enumerate(entries)}
        label2id = {label: index for index, label in id2label.items()}
        self.torch.manual_seed(seed)
        self.torch.cuda.manual_seed_all(seed)
        model = lib["AutoModelForSequenceClassification"].from_pretrained(
            model_name,
            revision=model_revision,
            num_labels=len(entries),
            id2label=id2label,
            label2id=label2id,
            quantization_config=quantization,
            device_map={"": 0},
            dtype=compute_dtype,
        )
        model.config.pad_token_id = self.tokenizer.pad_token_id
        model.config.problem_type = "single_label_classification"
        adapter_dir = run_dir / "artifacts" / "seqcls-adapter"
        if not adapter_dir.is_dir():
            raise RuntimeError("Templar adapter directory is missing")
        self.model = lib["PeftModel"].from_pretrained(model, str(adapter_dir))
        self.model.eval()

    def warmup(self) -> None:
        """Prime the loaded classifier before the readiness socket is published."""

        encoded = self.tokenizer(
            "Templar local evaluator readiness warmup",
            return_tensors="pt",
            add_special_tokens=True,
            truncation=False,
        )
        encoded = {key: value.to(self.model.device) for key, value in encoded.items()}
        with self.torch.inference_mode():
            self.model(**encoded)
        self.torch.cuda.synchronize()

    def evaluate(self, request: object) -> dict[str, object]:
        request_doc = _validate_request(request)
        event = request_doc["event"]
        assert type(event) is dict
        projected = project_templar_event(event)
        text = user_content(projected)
        encoded_length = len(self.tokenizer(text, add_special_tokens=True)["input_ids"])
        if encoded_length > self.max_length:
            raise RuntimeError(
                "Templar local runtime max_length would truncate the Fleet projection"
            )
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=True,
            truncation=False,
        )
        encoded = {key: value.to(self.model.device) for key, value in encoded.items()}
        with self.torch.inference_mode():
            probabilities = self.torch.softmax(self.model(**encoded).logits[0].float(), dim=-1)
        class_index = int(self.torch.argmax(probabilities).item())
        disposition = disposition_for_class(self.registry, class_index)
        actual: dict[str, Any] = {
            "raw": disposition["label_id"],
            "decision": disposition["decision"],
            "reason_codes": list(disposition["reason_codes"]),
            "class_index": class_index,
            "label_id": disposition["label_id"],
            "confidence": float(probabilities[class_index].item()),
        }
        actual = apply_calibration(
            prompt=event,
            actual=actual,
            registry=self.registry,
            policy=self.policy,
        )
        return {
            "schema": RESPONSE_SCHEMA,
            "evaluation_id": request_doc["evaluation_id"],
            "request_hash": request_doc["request_hash"],
            "event_hash": request_doc["event_hash"],
            "decision": actual["decision"],
            "reason_codes": list(actual["reason_codes"]),
        }


def evaluate_request_once(
    *,
    run_dir: Path,
    request: object,
    calibration_path: Path | None = None,
    max_length: int = 512,
    seed: int = 41,
) -> dict[str, object]:
    runtime = TemplarRuntime(
        run_dir=run_dir,
        calibration_path=calibration_path,
        max_length=max_length,
        seed=seed,
    )
    return runtime.evaluate(request)
