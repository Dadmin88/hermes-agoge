from __future__ import annotations

import json
import statistics
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from .adversarial import AdversarialCandidate, read_adversarial_candidates
from .backends.hf_seqcls_exam import _imports, _percentile, _tree_digest
from .calibration import apply_calibration, load_calibration_policy
from .dispositions import disposition_for_class, registry_lookup, validate_disposition_registry
from .exam import summarize_exam
from .prompting import user_content
from .spec import SpecError, digest
from .teacher import TeacherRequest
from .templar_projection import project_templar_event


def cluster_adversarial_failures(result: dict[str, Any]) -> list[dict[str, Any]]:
    if result.get("schema") != "agoge.adversarial-exam-result.v1":
        raise SpecError("adversarial failure clustering requires an adversarial Exam result")
    rows = result.get("rows")
    if type(rows) is not list:
        raise SpecError("adversarial Exam result rows are invalid")
    grouped: dict[tuple[object, ...], list[dict[str, Any]]] = {}
    for row in rows:
        if type(row) is not dict:
            raise SpecError("adversarial Exam result row is invalid")
        expected = row.get("expected")
        actual = row.get("actual")
        if type(expected) is not dict or type(actual) is not dict:
            raise SpecError("adversarial Exam row expected/actual is invalid")
        expected_reasons = expected.get("reason_codes")
        actual_reasons = actual.get("reason_codes")
        if type(expected_reasons) is not list or type(actual_reasons) is not list:
            raise SpecError("adversarial Exam row reason codes are invalid")
        exact = expected.get("decision") == actual.get("decision") and sorted(
            expected_reasons
        ) == sorted(actual_reasons)
        if exact:
            continue
        neural_decision = actual.get("neural_decision", actual.get("decision"))
        key = (
            row.get("competency"),
            row.get("event_schema"),
            row.get("mutation_family"),
            expected.get("decision"),
            tuple(sorted(str(item) for item in expected_reasons)),
            actual.get("decision"),
            neural_decision,
        )
        grouped.setdefault(key, []).append(row)

    clusters: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda item: tuple(str(part) for part in item)):
        rows_for_cluster = grouped[key]
        (
            competency,
            event_schema,
            mutation_family,
            expected_decision,
            expected_reasons,
            actual_decision,
            neural_decision,
        ) = key
        body = {
            "schema": "agoge.adversarial-failure-cluster.v1",
            "competency": competency,
            "event_schema": event_schema,
            "mutation_family": mutation_family,
            "expected_decision": expected_decision,
            "expected_reason_codes": list(expected_reasons),
            "observed_decision": actual_decision,
            "observed_neural_decision": neural_decision,
            "failure_count": len(rows_for_cluster),
            "calibration_applied_count": sum(
                int(type(row["actual"].get("calibration")) is dict) for row in rows_for_cluster
            ),
            "source_example_hashes": sorted(
                {str(row.get("source_example_hash")) for row in rows_for_cluster}
            ),
            "candidate_hashes": sorted({str(row.get("example_hash")) for row in rows_for_cluster}),
            "safety_critical": bool(expected_decision != "ALLOW" and neural_decision == "ALLOW"),
            "raw_prompt_bodies_included": False,
        }
        body["cluster_id"] = digest(body)
        clusters.append(body)
    return clusters


def build_corrective_teacher_request(
    *, student_path: Path, cluster: dict[str, Any], count: int
) -> TeacherRequest:
    if cluster.get("schema") != "agoge.adversarial-failure-cluster.v1":
        raise SpecError("corrective request requires an adversarial failure cluster")
    competency = cluster.get("competency")
    if type(competency) is not str or not competency:
        raise SpecError("adversarial failure cluster competency is invalid")
    base = TeacherRequest.from_student(student_path, competency=competency, count=count)
    constraints = deepcopy(base.constraints)
    constraints["adversarial_focus"] = {
        "schema": "agoge.adversarial-corrective-focus.v1",
        "cluster_id": cluster.get("cluster_id"),
        "event_schema": cluster.get("event_schema"),
        "mutation_family": cluster.get("mutation_family"),
        "expected_decision": cluster.get("expected_decision"),
        "expected_reason_codes": cluster.get("expected_reason_codes"),
        "observed_decision": cluster.get("observed_decision"),
        "observed_neural_decision": cluster.get("observed_neural_decision"),
        "safety_critical": cluster.get("safety_critical"),
    }
    rules = constraints.get("rules")
    if type(rules) is not list:
        raise SpecError("teacher request rules are invalid")
    rules.extend(
        [
            "Generate new semantically distinct examples for the named failure family.",
            "Do not reproduce or paraphrase any failed adversarial case body.",
            "Include contrastive benign and uncertain controls when appropriate to avoid overblocking.",
            "All training candidates must be regenerated through the pinned source runtime and independently reviewed.",
        ]
    )
    return TeacherRequest(
        student_id=base.student_id,
        student_hash=base.student_hash,
        curriculum_id=base.curriculum_id,
        curriculum_hash=base.curriculum_hash,
        competency=base.competency,
        purpose=base.purpose,
        count=base.count,
        constraints=constraints,
        sources=base.sources,
    )


def _validate_candidate_dispositions(
    candidates: list[AdversarialCandidate], registry: dict[str, Any]
) -> None:
    lookup = registry_lookup(registry)
    for candidate in candidates:
        decision = candidate.expected.get("decision")
        reasons = candidate.expected.get("reason_codes")
        if (
            type(decision) is not str
            or type(reasons) is not list
            or not all(type(item) is str and item for item in reasons)
        ):
            raise SpecError(
                f"adversarial candidate {candidate.candidate_id} has an invalid expected disposition"
            )
        if (decision, tuple(sorted(reasons))) not in lookup:
            raise SpecError(
                f"adversarial candidate {candidate.candidate_id} expects a disposition absent "
                "from the Student registry"
            )
        if candidate.provenance.get("review_state") != "generated":
            raise SpecError(
                f"adversarial candidate {candidate.candidate_id} is not in generated review state"
            )
        if candidate.provenance.get("training_use") != "candidate-only":
            raise SpecError(
                f"adversarial candidate {candidate.candidate_id} has invalid training-use state"
            )
        if candidate.provenance.get("runtime_binding") != "requires-regeneration":
            raise SpecError(
                f"adversarial candidate {candidate.candidate_id} has invalid runtime-binding state"
            )


def _group_summaries(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = str(row[key])
        groups.setdefault(value, []).append(row)
    return {name: summarize_exam(group) for name, group in sorted(groups.items())}


def examine_adversarial_seqcls(
    *,
    run_dir: Path,
    candidates_path: Path,
    model_kind: str = "adapter",
    max_length: int = 2048,
    seed: int = 41,
    calibration_path: Path | None = None,
    limit: int | None = None,
    out: Path | None = None,
) -> dict[str, Any]:
    if model_kind not in {"base", "adapter"}:
        raise SpecError("adversarial model_kind must be base or adapter")
    if max_length < 1:
        raise SpecError("adversarial max_length must be positive")
    if limit is not None and limit < 1:
        raise SpecError("adversarial limit must be positive")

    run_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    registry = validate_disposition_registry(
        json.loads((run_dir / "spec" / "dispositions.json").read_text(encoding="utf-8"))
    )
    if registry["registry_hash"] != run_manifest.get("disposition_registry_hash"):
        raise SpecError("Askesis disposition registry does not match its manifest")

    candidates = read_adversarial_candidates(candidates_path)
    if limit is not None:
        candidates = candidates[:limit]
    _validate_candidate_dispositions(candidates, registry)
    calibration = (
        load_calibration_policy(calibration_path) if calibration_path is not None else None
    )

    lib = _imports()
    torch = lib["torch"]
    if not torch.cuda.is_available():
        raise RuntimeError("adversarial sequence-classification exam requires CUDA")

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

    texts = [user_content(project_templar_event(candidate.prompt)) for candidate in candidates]
    lengths = [len(tokenizer(text, add_special_tokens=True)["input_ids"]) for text in texts]
    observed_max_tokens = max(lengths)
    if observed_max_tokens > max_length:
        raise RuntimeError(
            "adversarial max_length would truncate a projected case: "
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

    warmup = tokenizer(texts[0], return_tensors="pt", add_special_tokens=True, truncation=False)
    warmup = {key: value.to(model.device) for key, value in warmup.items()}
    with torch.inference_mode():
        model(**warmup)
    torch.cuda.synchronize()

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for candidate, text in zip(candidates, texts, strict=True):
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
        actual = {
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
        }
        actual = apply_calibration(
            prompt=candidate.prompt,
            actual=actual,
            registry=registry,
            policy=calibration,
        )
        mutation = candidate.provenance["mutation"]
        rows.append(
            {
                "example_id": candidate.candidate_id,
                "example_hash": candidate.content_hash,
                "competency": candidate.competency,
                "event_schema": candidate.prompt.get("schema"),
                "mutation_family": mutation["family"],
                "mutation_variant": mutation["variant"],
                "source_example_id": candidate.provenance["source_example_id"],
                "source_example_hash": candidate.provenance["source_example_hash"],
                "expected": candidate.expected,
                "actual": actual,
            }
        )

    candidate_hash = digest([candidate.to_dict() for candidate in candidates])
    exam_spec = {
        "schema": "agoge.adversarial-exam-spec.v1",
        "student_id": run_manifest["student_id"],
        "student_hash": run_manifest["student_hash"],
        "competency_id": run_manifest.get("competency_id"),
        "competency_hash": run_manifest.get("competency_hash"),
        "candidate_hash": candidate_hash,
        "candidate_count": len(candidates),
        "disposition_registry_hash": registry["registry_hash"],
        "base_model": model_name,
        "base_model_revision": model_revision,
        "model_kind": model_kind,
        "adapter_hash": adapter_hash,
        "max_length": max_length,
        "observed_max_tokens": observed_max_tokens,
        "seed": seed,
        "calibration_policy_hash": calibration["policy_hash"] if calibration is not None else None,
        "graduation_evidence": False,
        "candidate_training_eligible": False,
    }
    summary = summarize_exam(rows)
    summary.update(
        {
            "latency_ms_median": statistics.median(latencies) if latencies else None,
            "latency_ms_p95": _percentile(latencies, 0.95),
            "runtime_device": torch.cuda.get_device_name(0),
            "by_mutation_family": _group_summaries(rows, "mutation_family"),
            "by_event_schema": _group_summaries(rows, "event_schema"),
        }
    )
    result = {
        "schema": "agoge.adversarial-exam-result.v1",
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
