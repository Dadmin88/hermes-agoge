from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from agoge.corpus import read_jsonl, write_jsonl
from agoge.spec import StudentSpec, digest

EXPECTED_SOURCES = (
    "phase19-security-events-v1",
    "phase23-learning-events-v1",
)
EXPECTED_SCHEMAS = {
    "fleet.security-event.v1",
    "fleet.learning-promotion-event.v1",
}


def _source_manifest(corpus_dir: Path, stem: str) -> dict[str, object]:
    path = corpus_dir / f"{stem}.manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise RuntimeError(f"source corpus manifest is invalid: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--student", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    student_path = Path(args.student).resolve()
    student = StudentSpec.load(student_path)
    student_root = student_path.parent
    corpus_dir = student_root / "corpus"

    examples = []
    sources = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for stem in EXPECTED_SOURCES:
        corpus_path = corpus_dir / f"{stem}.jsonl"
        rows = read_jsonl(corpus_path)
        manifest = _source_manifest(corpus_dir, stem)
        parsed_hash = digest([row.to_dict() for row in rows])
        if manifest.get("corpus_hash") != parsed_hash:
            raise RuntimeError(f"source corpus hash mismatch: {stem}")
        for row in rows:
            if row.example_id in seen_ids:
                raise RuntimeError(f"duplicate example id across source corpora: {row.example_id}")
            if row.content_hash in seen_hashes:
                raise RuntimeError(f"duplicate example content across source corpora: {row.content_hash}")
            seen_ids.add(row.example_id)
            seen_hashes.add(row.content_hash)
            examples.append(row)
        sources.append(
            {
                "path": corpus_path.relative_to(student_root).as_posix(),
                "manifest_path": (corpus_dir / f"{stem}.manifest.json")
                .relative_to(student_root)
                .as_posix(),
                "event_family": manifest.get("event_family"),
                "count": len(rows),
                "corpus_hash": parsed_hash,
            }
        )

    schemas = {row.prompt.get("schema") for row in examples}
    if schemas != EXPECTED_SCHEMAS:
        raise RuntimeError(f"combined Templar corpus has unexpected event schemas: {sorted(schemas)!r}")

    examples.sort(key=lambda row: (str(row.prompt.get("schema")), row.competency, row.example_id))
    out_path = Path(args.out).resolve()
    manifest_path = Path(args.manifest).resolve()
    write_jsonl(out_path, examples)

    schema_counts = Counter(str(row.prompt.get("schema")) for row in examples)
    fleet_revision = next(
        source.revision
        for source in student.sources
        if source.uri == "https://github.com/Dadmin88/hermes-fleet"
    )
    manifest = {
        "schema": "agoge.templar-runtime-foundation-corpus-manifest.v1",
        "student_id": student.student_id,
        "student_hash": student.content_hash,
        "fleet_revision": fleet_revision,
        "source_corpora": sources,
        "count": len(examples),
        "event_schema_counts": {key: schema_counts[key] for key in sorted(schema_counts)},
        "corpus_hash": digest([row.to_dict() for row in examples]),
        "status": "accepted-combined-foundation-curriculum-not-graduation-exam",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
