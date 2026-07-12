#!/usr/bin/env python3
"""
h10_002_work_pipeline_name_fix.py — 9.330 work kaydındaki jenerik
`generated_by.pipeline_name: "canonicalize_work"` değerini gerçek adapter
adıyla düzeltir (H10 Stage 12; PHASE0_CLOSEOUT §2 düşük-öncelik kalemi).

Kök neden (H9 S4'te teşhis): H5 koşusunda registry adapter_id'leri CLI
--id'yle eşleşmedi → run_adapter jenerik fallback bastı. Gerçek ad,
derived_from[0].source_id önekinden birebir türetilebilir:
    openiti:*        → canonicalize_work_openiti
    science-works:*  → canonicalize_work_science
İdempotent (jenerik olmayan atlanır); düzeltme record_history'ye yazılır.

Usage: python3 pipelines/migrations/h10_002_work_pipeline_name_fix.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = REPO_ROOT / "data" / "canonical" / "work"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"

PREFIX_TO_NAME = {
    "openiti": "canonicalize_work_openiti",
    "science-works": "canonicalize_work_science",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    n_fixed = n_noop = n_unknown = 0
    for path in sorted(WORK_DIR.glob("iac_work_*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        gen = rec.get("provenance", {}).get("generated_by", {})
        if gen.get("pipeline_name") != "canonicalize_work":
            n_noop += 1
            continue
        sid = (rec["provenance"].get("derived_from") or [{}])[0].get("source_id", "")
        prefix = sid.split(":", 1)[0]
        name = PREFIX_TO_NAME.get(prefix)
        if not name:
            n_unknown += 1
            print(f"  WARN unknown prefix {prefix!r} for {rec.get('@id')}")
            continue
        gen["pipeline_name"] = name
        rec["provenance"].setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"h10_002: generated_by.pipeline_name generic "
                     f"'canonicalize_work' → '{name}' (H5 registry-id "
                     f"mismatch correction; derived from source_id prefix)."),
        })
        rec["provenance"]["modified"] = now
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_fixed += 1

    print(f"[h10_002] fixed={n_fixed} already-ok={n_noop} unknown={n_unknown}"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_unknown == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
