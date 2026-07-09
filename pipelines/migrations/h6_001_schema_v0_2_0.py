#!/usr/bin/env python3
"""
H6 Stream 4 — Migration h6_001: schema v0.1.0 → v0.2.0 SAME-AS structural field.

What this does
--------------
1. Reads the cluster sidecar (data/_state/work_same_as_clusters.json),
   produced by H5 Pass B.
2. For each cluster member work, adds the field
   `same_as_cluster_id: "<cluster-key>"` to the canonical work JSON
   (data/canonical/work/iac_work_*.json).
3. Validates each modified record against work.schema.json (post-Patch 1
   v0.2.0 schema must already be applied).
4. Writes back atomically (temp file + os.replace).
5. Emits a migration journal at
   data/_state/h6_migrations/h6_001_schema_v0_2_0_journal.json
   for audit/rollback.

Idempotency
-----------
- If a work already carries `same_as_cluster_id` matching its expected
  cluster, the file is not rewritten.
- If a work carries `same_as_cluster_id` for a *different* cluster than
  the sidecar reports, this is a fatal inconsistency and the migration
  aborts (cluster reassignment requires explicit human decision).

Flags
-----
  --dry-run        Print planned changes; do not write any files.
  --validate-only  Only run schema validation against the v0.2.0 schema
                   on all 9,330 records, do not modify anything.
  --repo-root PATH Override repo root (default: current directory).

Exit codes
----------
  0   Success (or dry-run completed cleanly).
  1   Inconsistency detected (e.g. conflicting same_as_cluster_id).
  2   Schema validation failed for one or more records.
  3   File I/O error.

Usage
-----
  python pipelines/migrations/h6_001_schema_v0_2_0.py --dry-run
  python pipelines/migrations/h6_001_schema_v0_2_0.py --validate-only
  python pipelines/migrations/h6_001_schema_v0_2_0.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

CLUSTER_SIDECAR_REL = Path("data/_state/work_same_as_clusters.json")
WORK_DIR_REL = Path("data/canonical/work")
SCHEMA_REL = Path("schemas/work.schema.json")
JOURNAL_DIR_REL = Path("data/_state/h6_migrations")
JOURNAL_NAME = "h6_001_schema_v0_2_0_journal.json"

MIGRATION_ID = "h6_001_schema_v0_2_0_same_as"
MIGRATION_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_to_filename(pid: str) -> str:
    """iac:work-00000006 → iac_work_00000006.json

    Both `:` and `-` separators are normalised to `_` to match the
    H5 canonical filename convention (verified against
    sample_works/iac_work_00000001.json shape).
    """
    if not pid.startswith("iac:work-"):
        raise ValueError(f"Unexpected PID shape: {pid!r}")
    return pid.replace(":", "_").replace("-", "_") + ".json"


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically (temp + rename) to avoid partial-write corruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_schema(schema_path: Path):
    """Load and compile the work schema validator with a local registry
    so that $ref links to schemas/_common/*.schema.json resolve from
    disk (not over the network)."""
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        from referencing import Registry, Resource  # type: ignore
    except ImportError as e:
        print(
            "FATAL: jsonschema/referencing not installed. "
            "Run: pip install jsonschema referencing",
            file=sys.stderr,
        )
        raise SystemExit(3) from e

    schemas_dir = schema_path.parent
    while schemas_dir != schemas_dir.parent and schemas_dir.name != "schemas":
        schemas_dir = schemas_dir.parent
    if schemas_dir.name != "schemas":
        schemas_dir = schema_path.parent

    registry = Registry()
    for sp in schemas_dir.rglob("*.schema.json"):
        try:
            s = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = s.get("$id")
        if sid:
            registry = registry.with_resource(
                uri=sid, resource=Resource.from_contents(s)
            )

    target = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(target)
    return Draft202012Validator(target, registry=registry)


# ---------------------------------------------------------------------------
# Core migration
# ---------------------------------------------------------------------------

def plan_migration(
    repo_root: Path,
) -> tuple[dict, dict[str, str]]:
    """
    Read the cluster sidecar and build a plan: dict of work_pid -> cluster_id.

    Returns
    -------
    (sidecar, plan) : tuple[dict, dict[str, str]]
        sidecar — full parsed JSON of work_same_as_clusters.json
        plan — flat map { "iac:work-00000006": "cluster-000001", ... }
    """
    sidecar_path = repo_root / CLUSTER_SIDECAR_REL
    if not sidecar_path.exists():
        raise FileNotFoundError(
            f"Cluster sidecar not found: {sidecar_path}\n"
            "Did Pass B run? Without clusters there is nothing to migrate."
        )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    clusters = sidecar.get("clusters", {})

    plan: dict[str, str] = {}
    for cluster_id, cluster_meta in clusters.items():
        for work_pid in cluster_meta.get("members", []):
            if work_pid in plan and plan[work_pid] != cluster_id:
                raise ValueError(
                    f"Work {work_pid} appears in two different clusters "
                    f"({plan[work_pid]} and {cluster_id}). Sidecar inconsistency; "
                    f"abort. Inspect work_same_as_clusters.json manually."
                )
            plan[work_pid] = cluster_id
    return sidecar, plan


def apply_to_record(
    work_path: Path,
    cluster_id: str,
    *,
    dry_run: bool,
) -> dict:
    """
    Add `same_as_cluster_id` to a single work record.

    Returns a per-record audit entry:
      { "pid", "path", "before_state", "after_state", "wrote" }

    where before/after_state ∈ {"absent", "present_correct", "present_conflict"}.
    """
    if not work_path.exists():
        return {
            "pid": work_path.stem.replace("iac_work_", "iac:work-"),
            "path": str(work_path),
            "error": "file_missing",
            "wrote": False,
        }

    data = json.loads(work_path.read_text(encoding="utf-8"))
    pid = data.get("@id")
    existing = data.get("same_as_cluster_id")

    if existing is None:
        before_state = "absent"
    elif existing == cluster_id:
        before_state = "present_correct"
    else:
        before_state = "present_conflict"

    if before_state == "present_conflict":
        return {
            "pid": pid,
            "path": str(work_path),
            "before_state": before_state,
            "existing_cluster_id": existing,
            "expected_cluster_id": cluster_id,
            "error": "cluster_id_conflict",
            "wrote": False,
        }

    if before_state == "present_correct":
        # Idempotent no-op
        return {
            "pid": pid,
            "path": str(work_path),
            "before_state": before_state,
            "after_state": "present_correct",
            "wrote": False,
        }

    # before_state == "absent" — apply the field
    data["same_as_cluster_id"] = cluster_id
    # Also bump the modified timestamp inside provenance, if that field exists.
    prov = data.get("provenance")
    if isinstance(prov, dict):
        prov["modified"] = _utc_now_iso()

    if not dry_run:
        _atomic_write_json(work_path, data)

    return {
        "pid": pid,
        "path": str(work_path),
        "before_state": before_state,
        "after_state": "present_correct",
        "wrote": (not dry_run),
    }


def validate_all_works(
    repo_root: Path,
    *,
    sample_size: int | None = None,
) -> tuple[int, int, list]:
    """
    Validate every work record against the schema. Used for --validate-only.

    Returns
    -------
    (n_total, n_invalid, invalid_samples)
    """
    validator = _load_schema(repo_root / SCHEMA_REL)
    work_dir = repo_root / WORK_DIR_REL
    if not work_dir.exists():
        raise FileNotFoundError(f"Work canonical dir not found: {work_dir}")

    n_total = 0
    n_invalid = 0
    samples: list[dict] = []
    for path in sorted(work_dir.glob("iac_work_*.json")):
        n_total += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            n_invalid += 1
            if len(samples) < 10:
                samples.append({"path": str(path), "error": f"parse: {e}"})
            continue
        errors = list(validator.iter_errors(data))
        if errors:
            n_invalid += 1
            if len(samples) < 10:
                samples.append(
                    {
                        "path": str(path),
                        "pid": data.get("@id"),
                        "errors": [
                            {"msg": err.message, "path": list(err.absolute_path)}
                            for err in errors[:3]
                        ],
                    }
                )
        if sample_size and n_total >= sample_size:
            break
    return n_total, n_invalid, samples


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(repo_root: Path, *, dry_run: bool, validate_only: bool) -> int:
    print(f"[h6_001] migration_id    = {MIGRATION_ID}")
    print(f"[h6_001] migration_version = {MIGRATION_VERSION}")
    print(f"[h6_001] repo_root       = {repo_root.resolve()}")
    print(f"[h6_001] dry_run         = {dry_run}")
    print(f"[h6_001] validate_only   = {validate_only}")
    print()

    if validate_only:
        print("[h6_001] Validating all work records against current schema...")
        n_total, n_invalid, samples = validate_all_works(repo_root)
        print(f"[h6_001]   total:   {n_total}")
        print(f"[h6_001]   invalid: {n_invalid}")
        if samples:
            print("[h6_001]   samples:")
            for s in samples[:5]:
                print(f"     {s}")
        return 2 if n_invalid else 0

    # Plan the migration from the sidecar
    sidecar, plan = plan_migration(repo_root)
    print(f"[h6_001] cluster_count   = {len(sidecar.get('clusters', {}))}")
    print(f"[h6_001] members_to_tag  = {len(plan)}")
    print()

    if not plan:
        print("[h6_001] Nothing to migrate (sidecar has no cluster members).")
        return 0

    # Compile the schema validator (catch v0.2.0 misapply early)
    validator = _load_schema(repo_root / SCHEMA_REL)

    # Sanity check: validator accepts a record with the new field
    test_doc = {
        "@id": "iac:work-99999999",
        "@type": ["iac:Work"],
        "same_as_cluster_id": "cluster-999999",
    }
    pre_errors = list(validator.iter_errors(test_doc))
    pre_complains_about_field = any(
        ".same_as_cluster_id" in str(list(e.absolute_path)) for e in pre_errors
    )
    if pre_complains_about_field:
        print(
            "[h6_001] FATAL: schema rejects same_as_cluster_id. "
            "Apply schemas/SCHEMA_v0_2_0_PATCH.md first.",
            file=sys.stderr,
        )
        return 2

    # Apply per-record
    work_dir = repo_root / WORK_DIR_REL
    audit_entries: list[dict] = []
    counts = {
        "wrote": 0,
        "noop_correct": 0,
        "absent_dry": 0,
        "conflict": 0,
        "missing": 0,
        "schema_invalid": 0,
    }

    for pid, cluster_id in sorted(plan.items()):
        work_path = work_dir / _pid_to_filename(pid)
        entry = apply_to_record(work_path, cluster_id, dry_run=dry_run)
        audit_entries.append(entry)

        if "error" in entry:
            if entry["error"] == "cluster_id_conflict":
                counts["conflict"] += 1
                print(
                    f"  CONFLICT {pid}: existing={entry['existing_cluster_id']} "
                    f"expected={entry['expected_cluster_id']}",
                    file=sys.stderr,
                )
            elif entry["error"] == "file_missing":
                counts["missing"] += 1
                print(f"  MISSING  {pid}: {entry['path']}", file=sys.stderr)
            continue

        if entry.get("wrote"):
            counts["wrote"] += 1
            # Re-validate after write
            data = json.loads(work_path.read_text(encoding="utf-8"))
            schema_errors = list(validator.iter_errors(data))
            if schema_errors:
                counts["schema_invalid"] += 1
                print(
                    f"  SCHEMA-INVALID {pid}: {[e.message for e in schema_errors[:2]]}",
                    file=sys.stderr,
                )
                entry["post_write_schema_errors"] = [
                    e.message for e in schema_errors[:5]
                ]
            print(f"  WROTE    {pid} -> same_as_cluster_id={cluster_id}")
        elif entry.get("before_state") == "present_correct":
            counts["noop_correct"] += 1
            print(f"  NOOP     {pid} (already tagged)")
        elif dry_run and entry.get("before_state") == "absent":
            counts["absent_dry"] += 1
            print(f"  DRY-RUN  {pid} -> would set same_as_cluster_id={cluster_id}")

    # Write journal
    journal = {
        "migration_id": MIGRATION_ID,
        "migration_version": MIGRATION_VERSION,
        "executed_at": _utc_now_iso(),
        "dry_run": dry_run,
        "summary": counts,
        "modified_pids": [
            e["pid"] for e in audit_entries if e.get("wrote")
        ],
        "noop_pids": [
            e["pid"]
            for e in audit_entries
            if e.get("before_state") == "present_correct"
        ],
        "errors": [
            e for e in audit_entries if "error" in e or e.get("post_write_schema_errors")
        ],
        "schema_path": str(SCHEMA_REL),
        "schema_target_version": "v0.2.0",
        "input_sidecar_stats": sidecar.get("stats", {}),
    }
    if not dry_run:
        journal_path = repo_root / JOURNAL_DIR_REL / JOURNAL_NAME
        _atomic_write_json(journal_path, journal)
        print()
        print(f"[h6_001] journal written: {journal_path}")
    else:
        print()
        print("[h6_001] (dry-run) journal not written")

    # Summary
    print()
    print("[h6_001] === SUMMARY ===")
    for k, v in counts.items():
        print(f"  {k:18s} {v}")

    if counts["conflict"] or counts["missing"] or counts["schema_invalid"]:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="H6 Stream 4 migration: SAME-AS structural field."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes; do not write any files.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate all 9,330 work records against the schema; no migration.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repo root (default: cwd).",
    )
    args = parser.parse_args(argv)
    if args.dry_run and args.validate_only:
        parser.error("Choose at most one of --dry-run / --validate-only.")
    return run(
        args.repo_root,
        dry_run=args.dry_run,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
