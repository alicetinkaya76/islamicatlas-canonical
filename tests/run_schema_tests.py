#!/usr/bin/env python3
"""
run_schema_tests.py — JSON Schema validation runner for islamicatlas-canonical Phase 0.

Loads every fixture listed in tests/test_manifest.json, validates it against the
declared schema, and asserts the outcome matches the manifest's expectation.

The schemas use absolute https://w3id.org/... $id values for portability. Since
those URIs aren't resolvable during local testing (the w3id PR happens in Hafta 6),
we build a Registry that maps each $id -> its on-disk schema, and use the
referencing library to resolve all $refs locally.

Usage:
    python3 tests/run_schema_tests.py
Exit code 0 = all tests pass; 1 = at least one test failed.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
TESTS_DIR = REPO_ROOT / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"
MANIFEST_PATH = TESTS_DIR / "test_manifest.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def discover_schemas(schemas_dir: Path) -> dict[str, dict]:
    """Walk schemas/ for *.schema.json files; return $id -> schema-dict mapping."""
    schemas: dict[str, dict] = {}
    for schema_path in schemas_dir.rglob("*.schema.json"):
        schema = load_json(schema_path)
        sid = schema.get("$id")
        if not sid:
            print(f"  WARN: {schema_path.relative_to(REPO_ROOT)} has no $id; skipping.")
            continue
        if sid in schemas:
            print(f"  WARN: duplicate $id {sid} (existing kept)")
            continue
        schemas[sid] = schema
    return schemas


def build_registry(schemas: dict[str, dict]) -> Registry:
    """Build a referencing.Registry holding every schema, keyed by its $id.

    Each schema declares "$schema": "https://json-schema.org/draft/2020-12/schema",
    so Resource.from_contents auto-detects the Draft 2020-12 specification.
    """
    registry = Registry()
    for sid, schema in schemas.items():
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(uri=sid, resource=resource)
    return registry


def validate_one(test: dict, schemas: dict[str, dict], registry: Registry) -> tuple[bool, str]:
    """Run one manifest test case. Return (passed, message)."""
    schema_relpath = test["schema"]
    schema_path = SCHEMAS_DIR / schema_relpath
    if not schema_path.exists():
        return False, f"schema file not found: {schema_relpath}"
    schema = load_json(schema_path)

    fixture_path = FIXTURES_DIR / test["fixture"]
    if not fixture_path.exists():
        return False, f"fixture file not found: {test['fixture']}"
    instance = load_json(fixture_path)

    validator = Draft202012Validator(schema, registry=registry)
    errors = list(validator.iter_errors(instance))

    expect = test["expect"]
    if expect == "valid":
        if errors:
            err_summary = "; ".join(
                f"[{'.'.join(str(p) for p in e.absolute_path) or '<root>'}] {e.validator}: {e.message[:120]}"
                for e in errors[:5]
            )
            return False, f"expected valid, got {len(errors)} error(s): {err_summary}"
        return True, "valid as expected"

    if expect == "invalid":
        if not errors:
            return False, "expected invalid, but instance validated cleanly"
        expected_keywords = set(test.get("expected_error_keywords", []))
        if not expected_keywords:
            return True, f"invalid as expected ({len(errors)} error(s); no keyword check requested)"
        observed_keywords = set()
        for err in errors:
            observed_keywords.add(err.validator)
            # Walk context (anyOf/allOf wrap nested errors)
            for ctx_err in err.context or []:
                observed_keywords.add(ctx_err.validator)
        if expected_keywords & observed_keywords:
            return True, (
                f"invalid as expected; observed keywords {sorted(observed_keywords)} "
                f"intersect expected {sorted(expected_keywords)}"
            )
        return False, (
            f"invalid as expected, but expected error keyword(s) {sorted(expected_keywords)} "
            f"not found among observed {sorted(observed_keywords)}"
        )

    return False, f"unknown expect value: {expect!r}"


def main() -> int:
    print(f"islamicatlas-canonical schema validator")
    print(f"  repo root: {REPO_ROOT}")
    print(f"  manifest:  {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print()

    schemas = discover_schemas(SCHEMAS_DIR)
    print(f"Discovered {len(schemas)} schema(s):")
    for sid in sorted(schemas):
        print(f"  - {sid}")
    print()

    registry = build_registry(schemas)

    manifest = load_json(MANIFEST_PATH)
    tests = manifest["tests"]
    print(f"Running {len(tests)} test(s):")

    n_pass = 0
    n_fail = 0
    failures: list[tuple[str, str]] = []
    for test in tests:
        ok, msg = validate_one(test, schemas, registry)
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {test['name']:<48} {msg}")
        if ok:
            n_pass += 1
        else:
            n_fail += 1
            failures.append((test["name"], msg))

    print()
    print(f"Summary: {n_pass}/{len(tests)} passed, {n_fail} failed.")
    if failures:
        print()
        print("Failures:")
        for name, msg in failures:
            print(f"  - {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
