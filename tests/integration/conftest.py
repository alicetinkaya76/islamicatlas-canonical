"""Shared, process-cached loaders for the integration suite (H9 Stage 3).

Why this exists — measured on the H9 store (46,702 records, suite 31.3 s):
the person store was loaded from disk 3×, the place store ~9× across modules
(module-scoped fixtures can't share) → ~9-10 s of pure re-reading. Module
fixtures now delegate to the lru_cached loaders below.

Deliberately NOT parallelized: a multiprocessing fan-out of the whole-store
validation was benchmarked and REJECTED — under macOS spawn, per-worker
interpreter + jsonschema-import overhead made the person pass slower
(5.5 s → 7.3 s in-suite). The full-store validation cost is the suite's core
guarantee; the fast inner loop is `-m "not slow_fullstore"` (see Makefile
`test-fast`).

Also centralizes DH-1 hardening: record files are globbed by the canonical
naming pattern (iac_<ns>_*.json), which AppleDouble droppings (._*) can never
match, instead of bare '*.json'.
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

# Honors the IAC_TEST_REPO_ROOT override that test_work_pilot documents (the
# review caught the first draft of this file silently breaking that contract
# by pinning its own root while STATE_DIR fixtures still honored the env).
_ENV_ROOT = os.environ.get("IAC_TEST_REPO_ROOT")
REPO_ROOT = Path(_ENV_ROOT).resolve() if _ENV_ROOT else Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CANONICAL_DIR = REPO_ROOT / "data" / "canonical"
SCHEMAS_DIR = REPO_ROOT / "schemas"


def record_files(namespace: str) -> list[Path]:
    """Canonical record files for a namespace, AppleDouble-proof (DH-1)."""
    ns_dir = CANONICAL_DIR / namespace
    if not ns_dir.exists():
        return []
    return sorted(ns_dir.glob(f"iac_{namespace}_*.json"))


@lru_cache(maxsize=None)
def load_records(namespace: str) -> tuple[dict, ...]:
    """All canonical records of a namespace, loaded once per test process.

    The tuple is shared across every consumer in the process — tests MUST
    treat records as read-only (grep-audited: no current test mutates them;
    a mutating test would poison every later reader)."""
    out = []
    for p in record_files(namespace):
        with p.open(encoding="utf-8") as fh:
            out.append(json.load(fh))
    return tuple(out)


@lru_cache(maxsize=1)
def schemas_registry():
    """referencing.Registry over every schema in schemas/, built once."""
    from referencing import Registry, Resource
    registry = Registry()
    for schema_path in SCHEMAS_DIR.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            schema = json.load(fh)
        if schema.get("$id"):
            registry = registry.with_resource(
                uri=schema["$id"], resource=Resource.from_contents(schema))
    return registry


@lru_cache(maxsize=None)
def validator_for(namespace: str):
    """Draft202012Validator for schemas/<namespace>.schema.json, cached."""
    from jsonschema import Draft202012Validator
    with (SCHEMAS_DIR / f"{namespace}.schema.json").open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=schemas_registry())


# ---- whole-store validation -------------------------------------------------

def validate_all(namespace: str, max_errors: int = 10) -> list[str]:
    """Validate every canonical record of a namespace against its schema,
    using the process-cached records + validator. Returns up to `max_errors`
    error strings (empty list == all valid)."""
    validator = validator_for(namespace)
    errors: list[str] = []
    for record in load_records(namespace):
        for err in validator.iter_errors(record):
            path = ".".join(str(x) for x in err.absolute_path) or "<root>"
            errors.append(f"{record.get('@id')}: [{path}] {err.message[:200]}")
            break  # first error per record is enough signal
        if len(errors) >= max_errors:
            break
    return errors
