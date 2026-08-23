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
    run = prepare_run(Path(args.student), Path(args.out))
    _json(run.manifest)
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run)
    if args.backend == "dry-run":
        from .backends.dryrun import train

        result = train(run_dir)
    else:
        from .backends.qlora import train

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
    validate = subs.add_parser("validate", help="validate one student and curriculum contract")
    validate.add_argument("--student", required=True)
    validate.set_defaults(func=cmd_validate)
    prepare = subs.add_parser("prepare", help="prepare an immutable Askesis run snapshot")
    prepare.add_argument("--student", required=True)
    prepare.add_argument("--out", required=True)
    prepare.set_defaults(func=cmd_prepare)
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
    train = subs.add_parser("train", help="execute a prepared Askesis training run")
    train.add_argument("--run", required=True)
    train.add_argument("--backend", choices=("dry-run", "qlora"), default="dry-run")
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
