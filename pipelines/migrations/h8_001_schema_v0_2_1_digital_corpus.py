#!/usr/bin/env python3
"""
H8 migration 001: schema v0.2.0 → v0.2.1 — digital_corpus enum extension

Companion to commit `Hafta 8 Stage 1: PE-1 remediation`. This migration
is **no-op for data**: it does not mutate any record. Its purpose is
to **re-validate** every canonical record against the patched schema
set and report a green/red ledger.

PE-1 root cause: H6 Stream 4 (schema v0.1.0 → v0.2.0) narrowed the
common provenance schema's source_type enum without re-validating
the existing H4 v2 person seed. 2,262 records carrying
source_type="digital_corpus" became schema-invalid silently. H8 Stage 1
re-admits the value to the enum (Option B1, ADR-010). This script
confirms the fix is complete and idempotent.

Idempotency: read-only; safe to re-run anytime.

Run:
    python3 pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py
    python3 pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py --verbose
    python3 pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py --entity person
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError as e:
    print(f"ERROR: missing dependency: {e}", file=sys.stderr)
    print("Install with: pip install jsonschema referencing", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
CANONICAL_DIR = REPO_ROOT / "data" / "canonical"

ENTITY_TYPES = ["person", "work", "place", "dynasty", "manuscript", "event"]


def build_registry():
    """Build a referencing.Registry from every *.schema.json file."""
    registry = Registry()
    for schema_path in SCHEMAS_DIR.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            s = json.load(fh)
        if not s.get("$id"):
            continue
        registry = registry.with_resource(
            uri=s["$id"], resource=Resource.from_contents(s)
        )
    return registry


def load_entity_validator(entity_type: str, registry: Registry) -> Draft202012Validator | None:
    schema_path = SCHEMAS_DIR / f"{entity_type}.schema.json"
    if not schema_path.exists():
        return None
    with schema_path.open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=registry)


def validate_entity_dir(entity_type: str, validator: Draft202012Validator, verbose: bool) -> dict:
    entity_dir = CANONICAL_DIR / entity_type
    if not entity_dir.exists():
        return {"entity": entity_type, "status": "no_directory", "passed": 0, "failed": 0}

    passed = 0
    failed = 0
    failure_types: Counter[str] = Counter()
    sample_failures: list[dict] = []

    files = sorted(entity_dir.glob(f"iac_{entity_type}_*.json"))
    for fp in files:
        try:
            with fp.open(encoding="utf-8") as fh:
                record = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            failed += 1
            failure_types[f"file_error:{type(e).__name__}"] += 1
            if len(sample_failures) < 5:
                sample_failures.append({"path": str(fp.name), "error": str(e)})
            continue

        errors = list(validator.iter_errors(record))
        if not errors:
            passed += 1
            continue

        failed += 1
        for e in errors:
            sig = f"{'.'.join(str(p) for p in e.absolute_path)}::{e.validator}"
            failure_types[sig] += 1
        if len(sample_failures) < 5:
            sample_failures.append({
                "path": str(fp.name),
                "errors": [{"path": list(e.absolute_path), "msg": e.message[:200]} for e in errors[:3]],
            })

    return {
        "entity": entity_type,
        "status": "checked",
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "failure_types": dict(failure_types.most_common(10)),
        "sample_failures": sample_failures if (failed and verbose) else [],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entity", choices=ENTITY_TYPES + ["all"], default="all")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--json-out", type=Path, help="Write the report to this path as JSON.")
    args = p.parse_args()

    registry = build_registry()
    targets = ENTITY_TYPES if args.entity == "all" else [args.entity]

    overall = {"migration": "h8_001_schema_v0_2_1_digital_corpus", "results": []}
    overall_passed = 0
    overall_failed = 0

    for et in targets:
        v = load_entity_validator(et, registry)
        if v is None:
            print(f"[{et}] no schema file at schemas/{et}.schema.json — skipped")
            continue
        result = validate_entity_dir(et, v, args.verbose)
        overall["results"].append(result)
        if result["status"] == "no_directory":
            print(f"[{et}] no canonical directory — skipped")
            continue
        overall_passed += result["passed"]
        overall_failed += result["failed"]

        marker = "OK " if result["failed"] == 0 else "FAIL"
        print(f"[{marker}] {et:11s} total={result['total']:>6} passed={result['passed']:>6} failed={result['failed']:>4}")

        if result["failed"] and args.verbose:
            print(f"       failure_types:")
            for sig, count in result["failure_types"].items():
                print(f"         {count:>5} × {sig}")
            for sf in result["sample_failures"]:
                print(f"       sample: {sf}")

    overall["passed_total"] = overall_passed
    overall["failed_total"] = overall_failed
    print()
    print(f"SUMMARY: passed={overall_passed} failed={overall_failed}")

    if args.json_out:
        args.json_out.write_text(json.dumps(overall, indent=2, ensure_ascii=False))
        print(f"Wrote JSON report to {args.json_out}")

    sys.exit(0 if overall_failed == 0 else 3)


if __name__ == "__main__":
    main()
