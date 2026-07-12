#!/usr/bin/env python3
"""
apply_darp_augments.py — apply the darp-islam Track-A augmentation sidecar
to existing place records (H10 Stage 2; mirrors the le-strange layer-append
pattern in place_integrity.py).

Per matched place PID (data/_state/darp_islam_augment_pending.json):
  * derived_from_layers += "darp-islam"  (idempotent — skip if present)
  * provenance.record_history += one update entry summarizing the mint
    evidence (ids, emission counts, nomisma URIs)
NO label/coords/temporal overwrite — append-only merge semantics (ADR-006
v1.1 / ADR-008). The `_review_skipped` key is reporting, not to apply.

Usage: python3 pipelines/integrity/apply_darp_augments.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIDECAR = REPO_ROOT / "data" / "_state" / "darp_islam_augment_pending.json"
PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SIDECAR.exists():
        print(f"ERROR: sidecar not found: {SIDECAR}")
        return 2
    with SIDECAR.open(encoding="utf-8") as fh:
        sidecar = json.load(fh)
    sidecar.pop("_review_skipped", None)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_applied = n_skipped = n_missing = 0

    for pid, events in sorted(sidecar.items()):
        if not isinstance(events, list):  # tolerate pre-fix single-dict shape
            events = [events]
        path = PLACE_DIR / f"iac_place_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_missing += 1
            print(f"  WARN missing record for {pid}")
            continue
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)

        layers = list(rec.get("derived_from_layers") or [])
        if "darp-islam" in layers:
            n_skipped += 1
            continue
        layers.append("darp-islam")
        rec["derived_from_layers"] = layers

        darp_ids = [e.get("darp_id") for e in events]
        emissions = sum(e.get("emission_count") or 0 for e in events)
        nomisma = [e["nomisma_uri"] for e in events if e.get("nomisma_uri")]
        note = (f"darp-islam augment (H10 Stage 2): mint kaydı "
                f"{darp_ids} (Tier-2 match, conf "
                f"{[round(e.get('confidence', 0), 2) for e in events]}); "
                f"{emissions} emisyon"
                + (f"; nomisma: {', '.join(nomisma[:3])}" if nomisma else "") + ".")
        rec.setdefault("provenance", {}).setdefault("record_history", []).append({
            "change_type": "update",
            "changed_at": now,
            "changed_by": ATTRIBUTED_TO,
            "release": "v0.1.0-phase0",
            "note": note[:1000],
        })
        rec["provenance"]["modified"] = now

        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_darp_augments] applied={n_applied} already-done={n_skipped} "
          f"missing={n_missing}{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
