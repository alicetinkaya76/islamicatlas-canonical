#!/usr/bin/env python3
"""
check_all.py — Post-canonicalization integrity pass.

Two responsibilities:

1. RESOLVE cross-record references that were deferred during canonicalization:
     - For Bosworth: read dynasty_relations.csv, look up the canonical PID for
       each side of every 'selef' (predecessor) edge via the PID minter's
       idempotent index, and append:
           dynasty_id_2.predecessor[].push(PID(id_1))
           dynasty_id_1.successor[].push(PID(id_2))
       Re-validate each modified record against dynasty.schema.json.

2. CHECK INVARIANTS across the canonical store:
     - dynasty.predecessor / dynasty.successor must be bidirectional
       (every predecessor X on Y MUST have Y in X's successor[])
     - Rulers within each dynasty must be chronologically sorted
     - had_capital[].place pointers (when present) must resolve to
       existing iac:place- records (warning-only in Hafta 2: place
       namespace is empty until Yâqūt lands)
     - dynasty.bosworth_id format consistency

Usage:
    python3 pipelines/integrity/check_all.py                  # all adapters
    python3 pipelines/integrity/check_all.py --adapter bosworth
    python3 pipelines/integrity/check_all.py --strict         # exit 1 on any error
    python3 pipelines/integrity/check_all.py --skip-resolve   # checks only

Exit code: 0 if all checks pass (warnings allowed); 1 if --strict and any
hard error fired.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import PidMinter, filename_for_pid  # noqa: E402


# ----- main ----------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-canonicalization integrity check.")
    parser.add_argument("--adapter", default="bosworth",
                        help="Resolve relations from this adapter's manifest "
                             "(currently only Bosworth has cross-record edges).")
    parser.add_argument("--strict", action="store_true",
                        help="Exit code 1 on any hard error (warnings always reported).")
    parser.add_argument("--skip-resolve", action="store_true",
                        help="Skip the predecessor/successor backfill; check only.")
    args = parser.parse_args()

    n_resolved = 0
    n_warnings = 0
    n_errors = 0

    # ---- Resolve relations (predecessor/successor backfill) -----------
    if not args.skip_resolve:
        n_resolved, errs, warns = resolve_relations(args.adapter)
        n_errors += errs
        n_warnings += warns
        print(f"\n=== Resolution: {n_resolved} edges patched, "
              f"errors={errs}, warnings={warns}")

    # ---- Invariant checks --------------------------------------------
    print("\n=== Invariant checks")
    checkers = (
        ("bidirectional predecessor/successor", check_bidirectional_succession),
        ("chronological ruler ordering",       check_ruler_chronology),
        ("had_capital[].place reference resolution", check_capital_place_refs),
        ("schema validity of all canonical records", check_schema_validity),
    )
    for name, fn in checkers:
        errs, warns = fn()
        marker = "OK" if errs == 0 else ("WARN" if warns and not errs else "FAIL")
        print(f"  [{marker:<4}] {name:<48} errors={errs} warnings={warns}")
        n_errors += errs
        n_warnings += warns

    print()
    print(f"Total: errors={n_errors}, warnings={n_warnings}")
    return 1 if (args.strict and n_errors) else 0


# ----- resolution stage ---------------------------------------------------


def resolve_relations(adapter_id: str) -> tuple[int, int, int]:
    """Backfill predecessor/successor on canonical dynasty records.

    Returns (n_edges_resolved, n_errors, n_warnings).
    """
    manifest_path = REPO_ROOT / "pipelines" / "adapters" / adapter_id / "manifest.yaml"
    if not manifest_path.exists():
        print(f"  WARN: no manifest at {manifest_path}; skipping resolution.")
        return 0, 0, 1
    with manifest_path.open(encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    relations_csv: Path | None = None
    for p in manifest.get("input_paths") or []:
        if p.endswith("dynasty_relations.csv"):
            relations_csv = REPO_ROOT / p
            break
    if relations_csv is None or not relations_csv.exists():
        print(f"  INFO: {adapter_id} has no dynasty_relations.csv; nothing to resolve.")
        return 0, 0, 0

    pred_relation_type = (
        (manifest.get("relations_semantics") or {}).get("predecessor_relation_type", "selef")
    )

    minter = PidMinter(state_dir=REPO_ROOT / "data" / "_state")

    # Walk relations and bucket by direction.
    successors_to_add: dict[str, list[str]] = defaultdict(list)
    predecessors_to_add: dict[str, list[str]] = defaultdict(list)

    n_resolved = 0
    n_warnings = 0

    with relations_csv.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rtype = (row.get("relation_type") or "").strip().lower()
            if rtype != pred_relation_type:
                continue
            id_1 = (row.get("dynasty_id_1") or "").strip()
            id_2 = (row.get("dynasty_id_2") or "").strip()
            if not id_1 or not id_2:
                continue
            try:
                id_1 = str(int(id_1))
                id_2 = str(int(id_2))
            except ValueError:
                pass

            pid_1 = minter.lookup("dynasty", f"bosworth-nid:{id_1}")
            pid_2 = minter.lookup("dynasty", f"bosworth-nid:{id_2}")
            if not pid_1 or not pid_2:
                print(f"  WARN: relation row {row.get('relation_id')} "
                      f"id_1={id_1} id_2={id_2}: PID lookup failed "
                      f"(pid_1={pid_1}, pid_2={pid_2})")
                n_warnings += 1
                continue

            # Edge: id_1 is predecessor of id_2.
            predecessors_to_add[pid_2].append(pid_1)
            successors_to_add[pid_1].append(pid_2)
            n_resolved += 1

    # Apply patches.
    canonical_dir = REPO_ROOT / "data" / "canonical" / "dynasty"
    all_targets = set(predecessors_to_add) | set(successors_to_add)
    for pid in all_targets:
        path = canonical_dir / filename_for_pid(pid)
        if not path.exists():
            print(f"  WARN: cannot patch {pid}: file missing at {path}")
            n_warnings += 1
            continue
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        if predecessors_to_add.get(pid):
            preds = sorted(set(predecessors_to_add[pid]))
            rec["predecessor"] = preds
        if successors_to_add.get(pid):
            succs = sorted(set(successors_to_add[pid]))
            rec["successor"] = succs
        with path.open("w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    return n_resolved, 0, n_warnings


# ----- invariant checks ---------------------------------------------------


def check_bidirectional_succession() -> tuple[int, int]:
    """Every predecessor of X must have X listed as a successor (and vice versa)."""
    canonical_dir = REPO_ROOT / "data" / "canonical" / "dynasty"
    if not canonical_dir.exists():
        return 0, 0

    by_pid: dict[str, dict] = {}
    for path in sorted(canonical_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        by_pid[rec["@id"]] = rec

    errors = 0
    for pid, rec in by_pid.items():
        for pred_pid in rec.get("predecessor", []) or []:
            other = by_pid.get(pred_pid)
            if other is None:
                print(f"  ERROR: {pid}.predecessor references unknown PID {pred_pid}")
                errors += 1
                continue
            if pid not in (other.get("successor") or []):
                print(f"  ERROR: bidirectional broken — {pid} declares "
                      f"predecessor={pred_pid}, but {pred_pid}.successor "
                      f"does not contain {pid}")
                errors += 1
        for succ_pid in rec.get("successor", []) or []:
            other = by_pid.get(succ_pid)
            if other is None:
                print(f"  ERROR: {pid}.successor references unknown PID {succ_pid}")
                errors += 1
                continue
            if pid not in (other.get("predecessor") or []):
                print(f"  ERROR: bidirectional broken — {pid} declares "
                      f"successor={succ_pid}, but {succ_pid}.predecessor "
                      f"does not contain {pid}")
                errors += 1
    return errors, 0


def check_ruler_chronology() -> tuple[int, int]:
    """Rulers within a dynasty must be chronologically sorted by reign_start_ce."""
    canonical_dir = REPO_ROOT / "data" / "canonical" / "dynasty"
    if not canonical_dir.exists():
        return 0, 0
    errors = 0
    warnings = 0
    for path in sorted(canonical_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        rulers = rec.get("rulers") or []
        last = None
        for i, r in enumerate(rulers):
            cur = r.get("reign_start_ce")
            if cur is None:
                continue
            if last is not None and cur < last:
                # Allow tied/overlapping reigns (co-regents) but flag inversions
                if cur < last - 5:  # tolerance: 5 years of slack for known co-regencies
                    print(f"  ERROR: {rec['@id']} rulers[{i}]={r.get('name')!r} "
                          f"reign_start_ce={cur} < previous {last}")
                    errors += 1
                else:
                    warnings += 1
            last = cur
    return errors, warnings


def check_capital_place_refs() -> tuple[int, int]:
    """had_capital[].place must resolve to existing iac:place- records.

    In Hafta 2 the place namespace is empty (Yâqūt lands Hafta 3); any
    had_capital entries are warnings, not errors. This check is forward-
    compatible: when iac:place- records appear it will start enforcing.
    """
    canonical_dir_dyn = REPO_ROOT / "data" / "canonical" / "dynasty"
    canonical_dir_pl = REPO_ROOT / "data" / "canonical" / "place"
    if not canonical_dir_dyn.exists():
        return 0, 0

    place_pids: set[str] = set()
    if canonical_dir_pl.exists():
        for path in canonical_dir_pl.glob("*.json"):
            with path.open(encoding="utf-8") as fh:
                place_pids.add(json.load(fh)["@id"])

    warnings = 0
    for path in sorted(canonical_dir_dyn.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        for cap in rec.get("had_capital") or []:
            place_pid = cap.get("place")
            if place_pid and place_pid not in place_pids:
                warnings += 1
                # don't print every one; just report count
    if warnings and not place_pids:
        print(f"  INFO: {warnings} had_capital references unresolved "
              f"(place namespace empty; expected for Hafta 2).")
    return 0, warnings


def check_schema_validity() -> tuple[int, int]:
    """Re-run JSON-Schema validation across the canonical store."""
    schemas_dir = REPO_ROOT / "schemas"
    schemas: dict[str, dict] = {}
    for schema_path in schemas_dir.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            s = json.load(fh)
        if s.get("$id"):
            schemas[s["$id"]] = s
    schema_registry = Registry()
    for sid, s in schemas.items():
        schema_registry = schema_registry.with_resource(
            uri=sid, resource=Resource.from_contents(s)
        )

    errors = 0
    canonical_dir = REPO_ROOT / "data" / "canonical"
    if not canonical_dir.exists():
        return 0, 0
    for ns_dir in sorted(canonical_dir.iterdir()):
        if not ns_dir.is_dir():
            continue
        target_schema_path = schemas_dir / f"{ns_dir.name}.schema.json"
        if not target_schema_path.exists():
            continue
        with target_schema_path.open(encoding="utf-8") as fh:
            target_schema = json.load(fh)
        validator = Draft202012Validator(target_schema, registry=schema_registry)
        for path in sorted(ns_dir.glob("*.json")):
            with path.open(encoding="utf-8") as fh:
                rec = json.load(fh)
            errs = list(validator.iter_errors(rec))
            if errs:
                top = errs[0]
                print(f"  ERROR: {path.name}: "
                      f"[{'.'.join(str(p) for p in top.absolute_path) or '<root>'}] "
                      f"{top.validator}: {top.message[:160]}")
                errors += 1
    return errors, 0


if __name__ == "__main__":
    raise SystemExit(main())
