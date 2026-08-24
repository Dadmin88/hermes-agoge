from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path

from .askesis import prepare_run
from .spec import CurriculumSpec, SpecError, StudentSpec


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def cmd_validate(args: argparse.Namespace) -> int:
    student_path = Path(args.student)
    student = StudentSpec.load(student_path)
    curriculum = CurriculumSpec.load(student_path.parent / student.curriculum)
    _json(
        {
            "ok": True,
            "student_id": student.student_id,
            "student_hash": student.content_hash,
            "curriculum_id": curriculum.curriculum_id,
            "curriculum_hash": curriculum.content_hash,
            "base_model": student.base_model,
            "base_model_revision": student.base_model_revision,
        }
    )
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    student_path = Path(args.student)
    corpus_path = None
    if args.corpus:
        candidate = Path(args.corpus)
        corpus_path = candidate if candidate.is_absolute() else student_path.parent / candidate
    run = prepare_run(
        student_path,
        Path(args.out),
        corpus_path=corpus_path,
        split_strategy=args.split_strategy,
    )
    _json(run.manifest)
    return 0


def cmd_fleet_snapshot(args: argparse.Namespace) -> int:
    from .fleet_snapshot import write_fleet_contract_snapshot

    snapshot = write_fleet_contract_snapshot(
        student_path=Path(args.student),
        fleet_repo=Path(args.fleet_repo),
        out=Path(args.out),
    )
    _json(
        {
            "student_id": snapshot["student_id"],
            "student_hash": snapshot["student_hash"],
            "fleet_revision": snapshot["fleet_revision"],
            "snapshot_hash": snapshot["snapshot_hash"],
            "modules": sorted(snapshot["modules"]),
            "out": args.out,
        }
    )
    return 0


def cmd_academy_brief(args: argparse.Namespace) -> int:
    from .academy import AcademyFacultyBinding, build_faculty_prompt
    from .teacher import load_teacher_request

    request = load_teacher_request(Path(args.request))
    binding = AcademyFacultyBinding.from_dict(
        json.loads(Path(args.binding).read_text(encoding="utf-8"))
    )
    prompt = build_faculty_prompt(request, binding)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prompt + "\n", encoding="utf-8")
    _json(
        {
            "request_id": request.request_id,
            "faculty_id": binding.faculty_id,
            "teacher_id": binding.teacher_identity.teacher_id,
            "training_use": binding.training_use,
            "out": str(out),
        }
    )
    return 0


def cmd_academy_import(args: argparse.Namespace) -> int:
    from .academy import AcademyFacultyBinding, parse_faculty_payload
    from .teacher import load_teacher_request

    request = load_teacher_request(Path(args.request))
    binding = AcademyFacultyBinding.from_dict(
        json.loads(Path(args.binding).read_text(encoding="utf-8"))
    )
    raw = Path(args.payload).read_text(encoding="utf-8")
    response = parse_faculty_payload(raw, request=request, binding=binding)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(response.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _json(
        {
            "request_id": request.request_id,
            "response_hash": response.content_hash,
            "teacher_id": response.teacher.teacher_id,
            "training_use": response.teacher.training_use,
            "items": len(response.items),
            "out": str(out),
        }
    )
    return 0


def cmd_teacher_request(args: argparse.Namespace) -> int:
    from .teacher import TeacherRequest

    request = TeacherRequest.from_student(
        Path(args.student),
        competency=args.competency,
        count=args.count,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(request.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _json({"request_id": request.request_id, "out": str(out), "count": request.count})
    return 0


def cmd_teacher_deterministic(args: argparse.Namespace) -> int:
    from .generators.templar import generate_response
    from .teacher import load_teacher_request

    request = load_teacher_request(Path(args.request))
    response = generate_response(request)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(response.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _json(
        {
            "request_id": request.request_id,
            "response_hash": response.content_hash,
            "teacher_id": response.teacher.teacher_id,
            "items": len(response.items),
            "out": str(out),
        }
    )
    return 0


def cmd_teacher_import(args: argparse.Namespace) -> int:
    from .corpus import write_jsonl
    from .teacher import load_teacher_request, load_teacher_response, response_to_candidates

    request = load_teacher_request(Path(args.request))
    response = load_teacher_response(Path(args.response))
    candidates = response_to_candidates(request, response)
    out = Path(args.out)
    write_jsonl(out, candidates)
    _json(
        {
            "request_id": request.request_id,
            "response_hash": response.content_hash,
            "teacher_id": response.teacher.teacher_id,
            "training_use": response.teacher.training_use,
            "candidates": len(candidates),
            "out": str(out),
        }
    )
    return 0


def cmd_review_templar_phase19(args: argparse.Namespace) -> int:
    from .reviewers.templar_phase19 import review_file

    counts = review_file(Path(args.candidates), Path(args.out))
    _json({**counts, "out": args.out})
    return 0


def cmd_candidate_promote(args: argparse.Namespace) -> int:
    from .corpus import read_jsonl, write_jsonl
    from .review import load_reviews, promote_candidates

    candidates = read_jsonl(Path(args.candidates))
    reviews = load_reviews(Path(args.reviews))
    accepted, rejected, quarantined = promote_candidates(candidates, reviews)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if accepted:
        write_jsonl(out_dir / "accepted.jsonl", accepted)
    if rejected:
        write_jsonl(out_dir / "rejected.jsonl", rejected)
    if quarantined:
        write_jsonl(out_dir / "quarantined.jsonl", quarantined)
    _json(
        {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "quarantined": len(quarantined),
            "out_dir": str(out_dir),
        }
    )
    return 0


def cmd_model_audit(args: argparse.Namespace) -> int:
    from .model_audit import ModelAuditCriteria, audit_huggingface

    criteria = ModelAuditCriteria(
        pipeline_tag=args.pipeline_tag,
        min_parameters=args.min_parameters,
        max_parameters=args.max_parameters,
        limit=args.limit,
        search=args.search,
        require_library=args.require_library,
        allow_gated=args.allow_gated,
        allowed_licenses=tuple(sorted(set(args.allow_license or []))),
        sort=args.sort,
    )
    result = audit_huggingface(criteria)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _json(
        {
            "audit_id": result["audit_id"],
            "criteria_id": result["criteria_id"],
            "status_counts": result["status_counts"],
            "out": str(out),
        }
    )
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run)
    if args.backend == "dry-run":
        from .backends.dryrun import train

        result = train(run_dir)
    elif args.backend == "qlora":
        from .backends.qlora import train

        result = train(
            run_dir,
            max_steps=args.max_steps,
            max_length=args.max_length,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
        )
    else:
        from .backends.qlora_seqcls import train

        result = train(
            run_dir,
            max_steps=args.max_steps,
            max_length=args.max_length,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
        )
    _json(result)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from .exam import compare_exam_results

    run_dir = Path(args.run)
    base = json.loads(
        (run_dir / f"exam-base-{args.split}.json").read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (run_dir / f"exam-adapter-{args.split}.json").read_text(encoding="utf-8")
    )
    result = compare_exam_results(base, candidate)
    (run_dir / f"exam-comparison-{args.split}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _json(result)
    return 0


def cmd_examine(args: argparse.Namespace) -> int:
    from .backends.hf_exam import examine

    result = examine(
        Path(args.run),
        model_kind=args.model,
        split=args.split,
        max_new_tokens=args.max_new_tokens,
    )
    _json(result["summary"])
    return 0


def cmd_compare_seqcls(args: argparse.Namespace) -> int:
    from .exam import compare_exam_results

    run_dir = Path(args.run)
    base = json.loads(
        (run_dir / f"exam-seqcls-base-{args.split}.json").read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (run_dir / f"exam-seqcls-adapter-{args.split}.json").read_text(encoding="utf-8")
    )
    result = compare_exam_results(base, candidate)
    (run_dir / f"exam-seqcls-comparison-{args.split}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _json(result)
    return 0


def cmd_examine_seqcls(args: argparse.Namespace) -> int:
    from .backends.hf_seqcls_exam import examine

    result = examine(
        Path(args.run),
        model_kind=args.model,
        split=args.split,
        max_length=args.max_length,
    )
    _json(result["summary"])
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    package_names = (
        "torch",
        "transformers",
        "datasets",
        "peft",
        "bitsandbytes",
        "trl",
    )
    packages = {name: bool(importlib.util.find_spec(name)) for name in package_names}
    cuda_available = False
    cuda: dict[str, object]
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        cuda = {
            "available": cuda_available,
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0) if cuda_available else None,
            "bf16_supported": (
                torch.cuda.is_bf16_supported() if cuda_available else False
            ),
        }
    except ImportError:
        cuda = {"available": False, "reason": "torch-not-installed"}
    training_stack_ready = all(packages.values())
    result: dict[str, object] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "training_packages": packages,
        "cuda": cuda,
        "roles": {
            "coordinator": True,
            "faculty_corpus_worker": True,
            "trainer": training_stack_ready and cuda_available,
            "examiner": training_stack_ready and cuda_available,
        },
    }
    _json(result)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="agoge", description="Hermes Agoge model-training system")
    subs = root.add_subparsers(dest="command", required=True)
    doctor = subs.add_parser("doctor", help="inspect local training readiness")
    doctor.set_defaults(func=cmd_doctor)
    model_audit = subs.add_parser(
        "model-audit",
        help="audit Hugging Face Hub for base-model candidates without selecting a preferred family",
    )
    model_audit.add_argument("--pipeline-tag", default="text-generation")
    model_audit.add_argument("--min-parameters", type=int, required=True)
    model_audit.add_argument("--max-parameters", type=int, required=True)
    model_audit.add_argument("--limit", type=int, default=20)
    model_audit.add_argument("--search", default=None)
    model_audit.add_argument("--require-library", default="transformers")
    model_audit.add_argument("--allow-gated", action="store_true")
    model_audit.add_argument("--allow-license", action="append", default=[])
    model_audit.add_argument("--sort", default="likes")
    model_audit.add_argument("--out", required=True)
    model_audit.set_defaults(func=cmd_model_audit)
    validate = subs.add_parser("validate", help="validate one student and curriculum contract")
    validate.add_argument("--student", required=True)
    validate.set_defaults(func=cmd_validate)
    prepare = subs.add_parser("prepare", help="prepare an immutable Askesis run snapshot")
    prepare.add_argument("--student", required=True)
    prepare.add_argument(
        "--corpus",
        default=None,
        help="Student-relative accepted corpus JSONL; defaults to seed_cases.jsonl",
    )
    prepare.add_argument(
        "--split-strategy",
        choices=("stable", "stratified"),
        default="stable",
        help="deterministic split policy; stratified preserves disposition families in held-out sets",
    )
    prepare.add_argument("--out", required=True)
    prepare.set_defaults(func=cmd_prepare)
    fleet_snapshot = subs.add_parser(
        "fleet-snapshot",
        help="extract a source-derived Fleet contract snapshot from the Student's pinned revision",
    )
    fleet_snapshot.add_argument("--student", required=True)
    fleet_snapshot.add_argument("--fleet-repo", required=True)
    fleet_snapshot.add_argument("--out", required=True)
    fleet_snapshot.set_defaults(func=cmd_fleet_snapshot)
    academy_brief = subs.add_parser(
        "academy-brief",
        help="render one bounded Academy faculty prompt from an Agoge Teacher request",
    )
    academy_brief.add_argument("--request", required=True)
    academy_brief.add_argument("--binding", required=True)
    academy_brief.add_argument("--out", required=True)
    academy_brief.set_defaults(func=cmd_academy_brief)
    academy_import = subs.add_parser(
        "academy-import",
        help="wrap a bounded Academy faculty payload into the provider-neutral Teacher contract",
    )
    academy_import.add_argument("--request", required=True)
    academy_import.add_argument("--binding", required=True)
    academy_import.add_argument("--payload", required=True)
    academy_import.add_argument("--out", required=True)
    academy_import.set_defaults(func=cmd_academy_import)
    teacher_request = subs.add_parser(
        "teacher-request", help="create one bounded provider-neutral Teacher request"
    )
    teacher_request.add_argument("--student", required=True)
    teacher_request.add_argument("--competency", required=True)
    teacher_request.add_argument("--count", type=int, required=True)
    teacher_request.add_argument("--out", required=True)
    teacher_request.set_defaults(func=cmd_teacher_request)
    teacher_deterministic = subs.add_parser(
        "teacher-deterministic",
        help="fulfill one Teacher request with the Fleet-native deterministic Templar rule generator",
    )
    teacher_deterministic.add_argument("--request", required=True)
    teacher_deterministic.add_argument("--out", required=True)
    teacher_deterministic.set_defaults(func=cmd_teacher_deterministic)
    teacher_import = subs.add_parser(
        "teacher-import", help="validate one Teacher response into unreviewed corpus candidates"
    )
    teacher_import.add_argument("--request", required=True)
    teacher_import.add_argument("--response", required=True)
    teacher_import.add_argument("--out", required=True)
    teacher_import.set_defaults(func=cmd_teacher_import)
    phase19_review = subs.add_parser(
        "review-templar-phase19",
        help="independently review Fleet Phase 19 Templar candidates from event facts",
    )
    phase19_review.add_argument("--candidates", required=True)
    phase19_review.add_argument("--out", required=True)
    phase19_review.set_defaults(func=cmd_review_templar_phase19)
    candidate_promote = subs.add_parser(
        "candidate-promote",
        help="apply independent reviews and partition candidates into accepted/rejected/quarantined sets",
    )
    candidate_promote.add_argument("--candidates", required=True)
    candidate_promote.add_argument("--reviews", required=True)
    candidate_promote.add_argument("--out-dir", required=True)
    candidate_promote.set_defaults(func=cmd_candidate_promote)
    compare = subs.add_parser(
        "compare", help="compare base and adapter Exam results for one Askesis split"
    )
    compare.add_argument("--run", required=True)
    compare.add_argument(
        "--split", choices=("train", "validation", "test"), default="test"
    )
    compare.set_defaults(func=cmd_compare)
    examine = subs.add_parser(
        "examine", help="evaluate the base model or trained adapter on an Askesis split"
    )
    examine.add_argument("--run", required=True)
    examine.add_argument("--model", choices=("base", "adapter"), required=True)
    examine.add_argument(
        "--split", choices=("train", "validation", "test"), default="test"
    )
    examine.add_argument("--max-new-tokens", type=int, default=128)
    examine.set_defaults(func=cmd_examine)
    compare_seqcls = subs.add_parser(
        "compare-seqcls",
        help="compare untrained and adapted sequence-classification Exam results",
    )
    compare_seqcls.add_argument("--run", required=True)
    compare_seqcls.add_argument(
        "--split", choices=("train", "validation", "test"), default="test"
    )
    compare_seqcls.set_defaults(func=cmd_compare_seqcls)
    examine_seqcls = subs.add_parser(
        "examine-seqcls",
        help="evaluate the closed disposition sequence classifier on an Askesis split",
    )
    examine_seqcls.add_argument("--run", required=True)
    examine_seqcls.add_argument("--model", choices=("base", "adapter"), required=True)
    examine_seqcls.add_argument(
        "--split", choices=("train", "validation", "test"), default="test"
    )
    examine_seqcls.add_argument("--max-length", type=int, default=2048)
    examine_seqcls.set_defaults(func=cmd_examine_seqcls)
    train = subs.add_parser("train", help="execute a prepared Askesis training run")
    train.add_argument("--run", required=True)
    train.add_argument(
        "--backend",
        choices=("dry-run", "qlora", "qlora-seqcls"),
        default="dry-run",
    )
    train.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="bound QLoRA to an exact optimizer-step count; useful for hardware smoke tests",
    )
    train.add_argument("--max-length", type=int, default=1024)
    train.add_argument("--gradient-accumulation-steps", type=int, default=8)
    train.set_defaults(func=cmd_train)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        return int(args.func(args))
    except (SpecError, RuntimeError) as exc:
        print(f"agoge: {exc}", file=sys.stderr)
        return 2
