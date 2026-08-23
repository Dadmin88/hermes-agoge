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
    _json({"ok": True, "student_id": student.student_id, "student_hash": student.content_hash, "curriculum_id": curriculum.curriculum_id, "curriculum_hash": curriculum.content_hash, "base_model": student.base_model})
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    run = prepare_run(Path(args.student), Path(args.out))
    _json(run.manifest)
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run)
    if args.backend == "dry-run":
        from .backends.dryrun import train
    else:
        from .backends.qlora import train
    _json(train(run_dir))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    result: dict[str, object] = {"python": platform.python_version(), "platform": platform.platform(), "training_packages": {name: bool(importlib.util.find_spec(name)) for name in ("torch", "transformers", "datasets", "peft", "bitsandbytes", "trl")}}
    try:
        import torch
        result["cuda"] = {"available": torch.cuda.is_available(), "device_count": torch.cuda.device_count(), "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "bf16_supported": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False}
    except ImportError:
        result["cuda"] = {"available": False, "reason": "torch-not-installed"}
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
    train = subs.add_parser("train", help="execute a prepared Askesis training run")
    train.add_argument("--run", required=True)
    train.add_argument("--backend", choices=("dry-run", "qlora"), default="dry-run")
    train.set_defaults(func=cmd_train)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        return int(args.func(args))
    except (SpecError, RuntimeError) as exc:
        print(f"agoge: {exc}", file=sys.stderr)
        return 2
