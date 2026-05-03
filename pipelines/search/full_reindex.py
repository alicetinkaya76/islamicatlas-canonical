#!/usr/bin/env python3
"""
full_reindex.py — Walk the canonical store and project every record into
its Typesense-ready search document via the existing Projector. Validates
that every record projects cleanly.

Per the Hafta 2 acceptance contract (H2.7 default), the real Typesense
bootstrap is deferred to Hafta 6 — this CLI's job for now is to act as a
projection regression gate. If `--dry-run` is set (default), it prints
NDJSON to stdout (or to --out PATH) and a summary to stderr.

Usage:
    python3 pipelines/search/full_reindex.py --dry-run
    python3 pipelines/search/full_reindex.py --dry-run --out /tmp/proj.ndjson
    python3 pipelines/search/full_reindex.py --dry-run --namespace dynasty
    python3 pipelines/search/full_reindex.py --dry-run --quiet  # summary only

Exit code: 0 if every record projects without error; 1 if any projection
fails (which would also indicate a schema↔projection-rule drift to fix).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from search.projector import Projector, ProjectorError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project every canonical record into a Typesense search "
                    "document; validates the canonical-store ↔ projection-rule "
                    "contract."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Default in Hafta 2: emit NDJSON instead of "
                             "calling the Typesense bootstrap. Required until "
                             "Hafta 6 lands the live indexer.")
    parser.add_argument("--namespace", default=None,
                        help="Restrict projection to one namespace dir (e.g. "
                             "'dynasty'). Default: all namespaces present.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write NDJSON to this path. If omitted, stdout.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress NDJSON; print summary only.")
    args = parser.parse_args()

    if not args.dry_run:
        # Hard guard until Hafta 6.
        print(
            "ERROR: live Typesense indexing is deferred until Hafta 6. "
            "Re-run with --dry-run for projection validation only.",
            file=sys.stderr,
        )
        return 2

    projector = Projector(repo_root=REPO_ROOT)
    canonical_dir = REPO_ROOT / "data" / "canonical"
    if not canonical_dir.exists():
        print(f"ERROR: no canonical store found at {canonical_dir}.", file=sys.stderr)
        return 2

    targets: list[Path] = []
    for ns_dir in sorted(canonical_dir.iterdir()):
        if not ns_dir.is_dir():
            continue
        if args.namespace and ns_dir.name != args.namespace:
            continue
        targets.extend(sorted(ns_dir.glob("*.json")))

    if not targets:
        print("ERROR: no canonical records to project.", file=sys.stderr)
        return 2

    out_fh = None
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out_fh = args.out.open("w", encoding="utf-8")
    elif not args.quiet:
        out_fh = sys.stdout

    n_ok = 0
    n_fail = 0
    by_namespace: dict[str, int] = {}
    failures: list[tuple[str, str]] = []
    t0 = time.time()

    for record_path in targets:
        ns = record_path.parent.name
        with record_path.open(encoding="utf-8") as fh:
            record = json.load(fh)
        try:
            doc = projector.project(record)
            n_ok += 1
            by_namespace[ns] = by_namespace.get(ns, 0) + 1
            if out_fh is not None:
                out_fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        except ProjectorError as exc:
            n_fail += 1
            failures.append((str(record_path.relative_to(REPO_ROOT)), str(exc)))
            print(
                f"FAIL  {record_path.name}: {exc}",
                file=sys.stderr,
            )

    if args.out and out_fh is not None:
        out_fh.close()

    elapsed = time.time() - t0
    print(file=sys.stderr)
    print("=== Projection summary", file=sys.stderr)
    for ns, count in sorted(by_namespace.items()):
        print(f"  {ns:<20s}: {count} records projected", file=sys.stderr)
    print(f"  total ok:   {n_ok}", file=sys.stderr)
    print(f"  total fail: {n_fail}", file=sys.stderr)
    print(f"  elapsed:    {elapsed:.2f} s", file=sys.stderr)
    if args.out:
        try:
            out_display = args.out.relative_to(REPO_ROOT)
        except ValueError:
            out_display = args.out
        print(f"  ndjson out: {out_display}", file=sys.stderr)
    if failures:
        print(f"  first failure: {failures[0][0]} → {failures[0][1][:200]}",
              file=sys.stderr)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
