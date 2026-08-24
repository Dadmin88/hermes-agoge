from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

from agoge.corpus import read_jsonl, write_jsonl
from agoge.spec import StudentSpec, digest

COMPETENCIES = (
    "authority-boundaries",
    "benign-nonoverblocking",
    "capability-combinations",
    "prompt-injection",
    "secret-handling",
    "skill-memory-poisoning",
    "uncertainty-review",
)


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _count_jsonl(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    python = repo / ".venv" / "bin" / "python"
    fleet_repo = repo.parent / "hermes-fleet"
    student_path = repo / "students" / "templar" / "student.json"
    student = StudentSpec.load(student_path)
    student_root = student_path.parent
    batch_root = student_root / "candidates" / "phase23-learning-events-v1"
    reviewed_root = student_root / "reviewed" / "phase23-learning-events-v1"
    corpus_path = student_root / "corpus" / "phase23-learning-events-v1.jsonl"
    corpus_manifest_path = student_root / "corpus" / "phase23-learning-events-v1.manifest.json"

    fleet_revision = next(
        source.revision
        for source in student.sources
        if source.uri == "https://github.com/Dadmin88/hermes-fleet"
    )

    competency_records: list[dict[str, object]] = []
    batch_records: list[dict[str, object]] = []
    accepted_examples = []
    teacher_ids: set[str] = set()
    reviewer_id = "templar-phase23-independent-rule-reviewer-v1"

    for competency in COMPETENCIES:
        request = batch_root / f"{competency}.request.json"
        response = batch_root / f"{competency}.response.json"
        candidates = batch_root / f"{competency}.candidates.jsonl"
        review_dir = reviewed_root / competency
        reviews = review_dir / "reviews.jsonl"
        review_dir.mkdir(parents=True, exist_ok=True)
        for stale_name in ("accepted.jsonl", "rejected.jsonl", "quarantined.jsonl"):
            stale_path = review_dir / stale_name
            if stale_path.exists():
                stale_path.unlink()

        _run(
            str(python),
            "tools/build_templar_learning_teacher.py",
            "--fleet-repo",
            str(fleet_repo),
            "--agoge-repo",
            str(repo),
            "--student",
            str(student_path),
            "--request",
            str(request),
            "--out",
            str(response),
            cwd=repo,
        )
        _run(
            str(python),
            "-m",
            "agoge",
            "teacher-import",
            "--request",
            str(request),
            "--response",
            str(response),
            "--out",
            str(candidates),
            cwd=repo,
        )
        _run(
            str(python),
            "-m",
            "agoge",
            "review-templar-phase23",
            "--candidates",
            str(candidates),
            "--out",
            str(reviews),
            cwd=repo,
        )
        _run(
            str(python),
            "-m",
            "agoge",
            "candidate-promote",
            "--candidates",
            str(candidates),
            "--reviews",
            str(reviews),
            "--out-dir",
            str(review_dir),
            cwd=repo,
        )

        accepted = review_dir / "accepted.jsonl"
        rejected = review_dir / "rejected.jsonl"
        quarantined = review_dir / "quarantined.jsonl"
        response_value = json.loads(response.read_text(encoding="utf-8"))
        teacher = response_value["teacher"]
        teacher_ids.add(str(teacher["teacher_id"]))
        generated = _count_jsonl(candidates)
        review_rows = [
            json.loads(line)
            for line in reviews.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        review_counts = Counter(str(row["decision"]) for row in review_rows)
        accepted_count = _count_jsonl(accepted)
        rejected_count = _count_jsonl(rejected) if rejected.exists() else 0
        quarantined_count = _count_jsonl(quarantined) if quarantined.exists() else 0
        if (generated, accepted_count, rejected_count, quarantined_count) != (36, 36, 0, 0):
            raise RuntimeError(
                f"Phase 23 admission failed for {competency}: "
                f"generated={generated}, accepted={accepted_count}, "
                f"rejected={rejected_count}, quarantined={quarantined_count}"
            )

        rows = read_jsonl(accepted)
        accepted_examples.extend(rows)
        competency_records.append(
            {
                "competency": competency,
                "generated": generated,
                "review_accept": review_counts.get("ACCEPT", 0),
                "review_reject": review_counts.get("REJECT", 0),
                "review_quarantine": review_counts.get("QUARANTINE", 0),
                "accepted": accepted_count,
                "rejected": rejected_count,
                "quarantined": quarantined_count,
            }
        )
        batch_records.append(
            {
                "competency": competency,
                "request_hash": digest(json.loads(request.read_text(encoding="utf-8"))),
                "response_hash": digest(response_value),
                "candidate_count": generated,
                "candidate_hash": digest([row.to_dict() for row in read_jsonl(candidates)]),
            }
        )

    if len(accepted_examples) != 252:
        raise RuntimeError(f"Phase 23 corpus must contain 252 accepted examples, got {len(accepted_examples)}")
    if len(teacher_ids) != 1:
        raise RuntimeError(f"Phase 23 corpus has inconsistent teacher identities: {sorted(teacher_ids)!r}")

    accepted_examples.sort(key=lambda row: (row.competency, row.example_id))
    write_jsonl(corpus_path, accepted_examples)
    corpus_hash = digest([row.to_dict() for row in accepted_examples])

    batch_manifest = {
        "schema": "agoge.templar-candidate-batch-manifest.v1",
        "student_id": student.student_id,
        "student_hash": student.content_hash,
        "fleet_revision": fleet_revision,
        "event_family": "fleet.learning-promotion-event.v1",
        "count": 252,
        "competencies": batch_records,
        "status": "generated-unreviewed-candidates",
    }
    (batch_root / "manifest.json").write_text(
        json.dumps(batch_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    corpus_manifest = {
        "schema": "agoge.templar-foundation-corpus-manifest.v1",
        "student_id": student.student_id,
        "fleet_revision": fleet_revision,
        "event_family": "fleet.learning-promotion-event.v1",
        "teacher_id": next(iter(teacher_ids)),
        "reviewer_id": reviewer_id,
        "candidate_batch_manifest": "students/templar/candidates/phase23-learning-events-v1/manifest.json",
        "competencies": competency_records,
        "count": len(accepted_examples),
        "corpus_hash": corpus_hash,
        "status": "accepted-foundation-curriculum-not-graduation-exam",
    }
    corpus_manifest_path.write_text(
        json.dumps(corpus_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(corpus_manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
