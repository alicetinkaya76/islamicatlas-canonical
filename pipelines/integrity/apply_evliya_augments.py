#!/usr/bin/env python3
"""
apply_evliya_augments.py — evliya-celebi Track-A augment'larını mevcut place
kayıtlarına uygular (H10 Stage 7; darp applier deseni).

Per matched place PID (data/_state/evliya_augment_pending.json → `augments`):
  * derived_from_layers += "evliya-celebi"  (idempotent)
  * provenance.record_history += update (kategori + sefer kanıtı)
Append-only; label/coords/temporal'a dokunulmaz.

Usage: python3 pipelines/integrity/apply_evliya_augments.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIDECAR = REPO_ROOT / "data" / "_state" / "evliya_augment_pending.json"
PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    augments = json.loads(SIDECAR.read_text(encoding="utf-8")).get("augments", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_applied = n_skipped = n_missing = 0

    for pid, events in sorted(augments.items()):
        path = PLACE_DIR / f"iac_place_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_missing += 1
            print(f"  WARN missing record for {pid}")
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        layers = list(rec.get("derived_from_layers") or [])
        if "evliya-celebi" in layers:
            n_skipped += 1
            continue
        layers.append("evliya-celebi")
        rec["derived_from_layers"] = layers

        ids = [e.get("evliya_id") for e in events]
        cats = sorted({e.get("category") for e in events if e.get("category")})
        voys = sorted({e.get("voyage_id") for e in events if e.get("voyage_id")})
        confs = [round(e.get("confidence", 0), 2) for e in events]
        note = (f"evliya-celebi augment (H10 Stage 7): Seyahatnâme konumu "
                f"{ids} (kategori {cats}; sefer {voys}; Tier-2 conf {confs}).")
        rec.setdefault("provenance", {}).setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": note[:1000],
        })
        rec["provenance"]["modified"] = now
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_evliya_augments] applied={n_applied} already-done={n_skipped} "
          f"missing={n_missing}{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
