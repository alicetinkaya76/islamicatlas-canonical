#!/usr/bin/env python3
"""
H6 Stream 1 — Build `dia_slug_to_pid.json` from the H5 audit.

The DİA pipeline (Stream 2 in H6) needs a deterministic mapping from
slug (URL-friendly DİA scholar identifier, e.g. "hassaf", "lebli") to
canonical person PID (e.g. "iac:person-00003304"). H5 audit output
already encodes this in per_slug entries; this script extracts it as
a flat dictionary.

Usage (repo root):

    python pipelines/_lib/build_dia_slug_to_pid.py

Outputs:

    data/_state/dia_slug_to_pid.json

Idempotent — overwriting OK.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_AUDIT = Path("data/_state/dia_works_h5_audit.json")
DEFAULT_OUT = Path("data/_state/dia_slug_to_pid.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build slug→pid map from DİA audit.")
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if not args.audit_path.exists():
        print(f"FATAL: audit file not found: {args.audit_path}", file=sys.stderr)
        return 2
    audit = json.loads(args.audit_path.read_text(encoding="utf-8"))
    per_slug = audit.get("per_slug", {})
    if not per_slug:
        print(f"FATAL: audit has no per_slug section", file=sys.stderr)
        return 2

    slug_to_pid: dict[str, str] = {}
    unresolved: list[str] = []
    anomalies: list[dict] = []

    for slug, titles in per_slug.items():
        if not isinstance(titles, list):
            continue
        pids = {
            t.get("dia_scholar_pid")
            for t in titles
            if isinstance(t, dict) and t.get("dia_scholar_pid")
        }
        pids.discard(None)
        if not pids:
            unresolved.append(slug)
        elif len(pids) == 1:
            slug_to_pid[slug] = next(iter(pids))
        else:
            # Multiple distinct pids for one slug — flag for human review.
            anomalies.append({"slug": slug, "pids": sorted(pids)})

    out = {
        "schema_version": "1.0.0",
        "generated_by": "pipelines/_lib/build_dia_slug_to_pid.py",
        "source": str(args.audit_path),
        "slug_to_pid": slug_to_pid,
        "slugs_unresolved": unresolved,
        "anomalies_multi_pid": anomalies,
        "stats": {
            "total_slugs": len(per_slug),
            "resolved_count": len(slug_to_pid),
            "unresolved_count": len(unresolved),
            "anomaly_count": len(anomalies),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[build_dia_slug_to_pid] wrote {args.output}")
    print(f"  total_slugs:      {len(per_slug)}")
    print(f"  resolved:         {len(slug_to_pid)}")
    print(f"  unresolved:       {len(unresolved)}")
    print(f"  anomalies:        {len(anomalies)}")
    if anomalies:
        print(f"  anomalies sample: {anomalies[:3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
