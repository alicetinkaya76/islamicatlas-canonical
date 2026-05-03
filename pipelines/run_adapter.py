#!/usr/bin/env python3
"""
run_adapter.py — Orchestrator for content adapters.

CLI:
    python3 pipelines/run_adapter.py --id bosworth
    python3 pipelines/run_adapter.py --id bosworth --strict
    python3 pipelines/run_adapter.py --id bosworth --lenient
    python3 pipelines/run_adapter.py --id bosworth --limit 10
    python3 pipelines/run_adapter.py --id bosworth --recon-mode offline

Flow per adapter:
    1. Load registry → resolve adapter folder → load manifest.yaml.
    2. Resolve input_paths from manifest (relative to repo root).
    3. Construct PidMinter (state_dir = data/_state).
    4. Construct WikidataReconciler (cache + seed from manifest).
    5. Dynamically import adapter's extract.extract and canonicalize.canonicalize.
    6. For each canonical record: validate against schemas/<namespace>.schema.json.
       Write to data/canonical/<namespace>/iac_<namespace>_NNNNNNNN.json.
    7. Persist sidecar JSON (capital + territory pending data) to manifest path.
    8. Print summary stats (counts, reconciliation hit rates, validation failures).

Exit code 0 = success; 1 = at least one record failed validation in strict mode
or some other fatal error.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import PidMinter, filename_for_pid  # noqa: E402
from pipelines._lib.wikidata_reconcile import WikidataReconciler  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a content adapter end-to-end.")
    parser.add_argument("--id", dest="adapter_id", required=True,
                        help="Adapter id (matches a registry entry).")
    parser.add_argument("--strict", action="store_true",
                        help="Stop on first canonicalization or validation error.")
    parser.add_argument("--lenient", action="store_true",
                        help="Continue past errors; report at the end.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap the number of records canonicalized (for smoke runs).")
    parser.add_argument("--recon-mode", choices=("live", "offline", "auto"),
                        default=None,
                        help="Override manifest reconciliation.mode.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run extract+canonicalize but do not write canonical files.")
    args = parser.parse_args()

    if args.strict and args.lenient:
        print("ERROR: --strict and --lenient are mutually exclusive.", file=sys.stderr)
        return 2
    strict = args.strict or not args.lenient  # default: strict

    # Folder name is Python-package-friendly (underscore); adapter_id may use
    # hyphen for human-readability. Try both.
    candidate_dirs = [
        REPO_ROOT / "pipelines" / "adapters" / args.adapter_id,
        REPO_ROOT / "pipelines" / "adapters" / args.adapter_id.replace("-", "_"),
    ]
    adapter_dir = next((d for d in candidate_dirs if d.exists()), candidate_dirs[0])
    manifest_path = adapter_dir / "manifest.yaml"
    if not manifest_path.exists():
        print(f"ERROR: manifest.yaml not found for adapter {args.adapter_id!r} at {manifest_path}",
              file=sys.stderr)
        return 2
    with manifest_path.open(encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    namespace = (manifest.get("target_namespaces") or [None])[0]
    if not namespace:
        print("ERROR: manifest.target_namespaces is empty.", file=sys.stderr)
        return 2

    # ---- Resolve registry config (overrides manifest defaults) ---------
    registry_path = REPO_ROOT / "pipelines" / "adapters" / "registry.yaml"
    registry_config: dict = {}
    if registry_path.exists():
        with registry_path.open(encoding="utf-8") as fh:
            registry = yaml.safe_load(fh)
        for entry in (registry or {}).get("adapters") or []:
            if entry.get("adapter_id") == args.adapter_id:
                if not entry.get("enabled", True):
                    print(
                        f"WARNING: adapter {args.adapter_id!r} marked enabled=false in registry; "
                        f"continuing because --id was given explicitly.",
                        file=sys.stderr,
                    )
                registry_config = entry.get("config") or {}
                break

    # ---- Initialize state ---------------------------------------------
    state_dir = REPO_ROOT / "data" / "_state"
    pid_minter = PidMinter(state_dir=state_dir)

    recon_cfg = manifest.get("reconciliation", {}) or {}
    recon_mode = args.recon_mode or recon_cfg.get("mode", "auto")
    cache_path = REPO_ROOT / recon_cfg.get(
        "cache_path", "data/cache/wikidata_reconcile.sqlite"
    )
    seed_path_rel = recon_cfg.get("seed_path")
    seed_path = REPO_ROOT / seed_path_rel if seed_path_rel else None
    reconciler = None
    if recon_cfg.get("enabled", True):
        reconciler = WikidataReconciler(
            cache_path=cache_path,
            seed_path=seed_path,
            mode=recon_mode,
            threshold_auto_accept=recon_cfg.get("threshold_auto_accept", 0.85),
            threshold_review=recon_cfg.get("threshold_review", 0.70),
            verbose=True,
        )

    # ---- Resolve input paths ------------------------------------------
    input_paths = [REPO_ROOT / p for p in (manifest.get("input_paths") or [])]
    for p in input_paths:
        if not p.exists():
            print(f"ERROR: input path missing: {p.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 2

    # ---- Dynamically import adapter modules ---------------------------
    adapter_pkg = f"pipelines.adapters.{adapter_dir.name}"
    extract_mod = importlib.import_module(f"{adapter_pkg}.extract")
    canonicalize_mod = importlib.import_module(f"{adapter_pkg}.canonicalize")

    # ---- Load schemas + validator -------------------------------------
    schemas_dir = REPO_ROOT / "schemas"
    target_schema_path = schemas_dir / f"{namespace}.schema.json"
    if not target_schema_path.exists():
        print(f"ERROR: schema {target_schema_path} missing.", file=sys.stderr)
        return 2
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
    with target_schema_path.open(encoding="utf-8") as fh:
        target_schema = json.load(fh)
    validator = Draft202012Validator(target_schema, registry=schema_registry)

    # ---- Output dir ---------------------------------------------------
    out_dir = REPO_ROOT / "data" / "canonical" / namespace
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Sidecar handling (per-adapter pending data) -------------------
    sidecar_data: dict[str, dict] = {}   # key = sidecar name, value = dict to fill
    sidecar_paths: dict[str, Path] = {}  # key = sidecar name, value = output path
    sidecar_cfg = manifest.get("sidecar_pending") or {}
    for name, rel_path in sidecar_cfg.items():
        sidecar_paths[name] = REPO_ROOT / rel_path
        sidecar_data[name] = {}

    # ---- Canonicalize ------------------------------------------------
    options = {
        "strict_mode": strict,
        "namespace": namespace,
        "pipeline_name": registry_config.get("pipeline_name", f"canonicalize_{namespace}"),
        "pipeline_version": "v0.1.0",
        "reconciliation_type_qid": recon_cfg.get("type_qid"),
        # Backward-compat: legacy 'capital_sidecar' single key
        "capital_sidecar": sidecar_data.get("capital"),
        # New: per-name sidecar dicts addressable by adapters
        "parent_sidecar": sidecar_data.get("parent"),
        "persons_sidecar": sidecar_data.get("persons"),
        "events_sidecar": sidecar_data.get("events"),
        "yaqut_xref_sidecar": sidecar_data.get("yaqut_xref"),
        # Pass-through manifest options
        "recon_filter": recon_cfg.get("recon_filter") or {},
    }

    print(f"=== run_adapter: id={args.adapter_id} ns={namespace} mode={recon_mode} strict={strict}")
    print(f"    inputs: {[p.relative_to(REPO_ROOT) for p in input_paths]}")
    print(f"    output: {out_dir.relative_to(REPO_ROOT) if not args.dry_run else '(dry-run)'}")
    print()

    extracted_iter = extract_mod.extract(input_paths)
    if args.limit:
        extracted_iter = _take(extracted_iter, args.limit)

    canonical_iter = canonicalize_mod.canonicalize(
        extracted_iter, pid_minter, reconciler, options=options
    )

    n_written = 0
    n_validation_fail = 0
    failures: list[tuple[str, str]] = []
    t0 = time.time()

    for record in canonical_iter:
        pid = record.get("@id")
        if not pid:
            failures.append(("<no-pid>", "record missing @id"))
            n_validation_fail += 1
            if strict:
                break
            continue

        errors = list(validator.iter_errors(record))
        if errors:
            n_validation_fail += 1
            top = errors[0]
            err_msg = (
                f"[{'.'.join(str(p) for p in top.absolute_path) or '<root>'}] "
                f"{top.validator}: {top.message[:200]}"
            )
            failures.append((pid, err_msg))
            if strict:
                print(f"FAIL  {pid}  {err_msg}", file=sys.stderr)
                break
            else:
                print(f"WARN  {pid}  {err_msg}", file=sys.stderr)
                continue

        if not args.dry_run:
            out_path = out_dir / filename_for_pid(pid)
            # Preserve integrity-pass fields on overwrite (predecessor/successor,
            # had_capital, territory, located_in — these come from second-pass
            # backfills and shouldn't be wiped by a partial re-run).
            if out_path.exists():
                try:
                    with out_path.open(encoding="utf-8") as fh:
                        prior = json.load(fh)
                    for k in (
                        "predecessor", "successor", "had_capital", "territory",
                        "located_in", "had_capital_of", "falls_within_iqlim",
                    ):
                        if prior.get(k) and not record.get(k):
                            record[k] = prior[k]
                except (OSError, json.JSONDecodeError):
                    pass
            out_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        n_written += 1

    # ---- Persist sidecars --------------------------------------------
    if not args.dry_run:
        for name, payload in sidecar_data.items():
            if not payload:
                continue
            spath = sidecar_paths.get(name)
            if not spath:
                continue
            spath.parent.mkdir(parents=True, exist_ok=True)
            spath.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            print(
                f"\nSidecar written: {spath.relative_to(REPO_ROOT)} "
                f"({len(payload)} entries) [{name}]"
            )

    # ---- Summary -----------------------------------------------------
    elapsed = time.time() - t0
    print()
    print("=== Summary")
    print(f"  records written:     {n_written}")
    print(f"  validation failures: {n_validation_fail}")
    print(f"  elapsed:             {elapsed:.1f} s")
    if reconciler is not None:
        print(f"  reconcile counters:  {reconciler.counters}")
        reconciler.close()
    print(f"  PID counter state:   {pid_minter.stats()}")
    if failures and not strict:
        print()
        print(f"  First 5 of {len(failures)} validation failures:")
        for pid, msg in failures[:5]:
            print(f"    - {pid}: {msg}")

    return 0 if n_validation_fail == 0 else 1


def _take(it, n):
    for i, x in enumerate(it):
        if i >= n:
            return
        yield x


if __name__ == "__main__":
    raise SystemExit(main())
