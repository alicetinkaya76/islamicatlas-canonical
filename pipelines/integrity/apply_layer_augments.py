#!/usr/bin/env python3
"""
apply_layer_augments.py — JENERİK layer-augment uygulayıcısı (H10 Stage 8).

darp/evliya applier'larının üçüncü kopyası yerine parametrik tek script:
sidecar'daki eşleşme-olaylarını mevcut kayıtlara uygular —
    derived_from_layers += <layer>   (idempotent)
    provenance.record_history += update (olay kanıtı özetiyle)
Append-only; label/coords/temporal'a dokunmaz. Sidecar şekli: ya doğrudan
{pid: [event,...]} ya da {"augments": {pid: [...]}} (öntanımlı anahtar).

Usage:
  python3 pipelines/integrity/apply_layer_augments.py \
      --layer ibn-battuta \
      --sidecar data/_state/ibn_battuta_augment_pending.json \
      [--namespace place] [--augments-key augments] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True)
    ap.add_argument("--sidecar", required=True)
    ap.add_argument("--namespace", default="place")
    ap.add_argument("--augments-key", default="augments")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads((REPO_ROOT / args.sidecar).read_text(encoding="utf-8"))
    augments = data.get(args.augments_key)
    if augments is None:  # düz {pid: [...]} şekli
        augments = {k: v for k, v in data.items() if k.startswith("iac:")}
    ns_dir = REPO_ROOT / "data" / "canonical" / args.namespace

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_applied = n_skipped = n_missing = 0

    for pid, events in sorted(augments.items()):
        if not isinstance(events, list):
            events = [events]
        path = ns_dir / f"iac_{args.namespace}_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_missing += 1
            print(f"  WARN missing record for {pid}")
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        layers = list(rec.get("derived_from_layers") or [])
        if args.layer in layers:
            n_skipped += 1
            continue
        layers.append(args.layer)
        rec["derived_from_layers"] = layers

        confs = [round(e.get("confidence", 0), 2) for e in events]
        summary = {k: [e.get(k) for e in events][:4]
                   for k in ("stop_id", "darp_id", "evliya_id", "voyage_id",
                             "lestrange_id")   # H20 Dalga-3
                   if any(e.get(k) is not None for e in events)}
        rec.setdefault("provenance", {}).setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"{args.layer} augment: {len(events)} eşleşme-olayı "
                     f"(Tier-2 conf {confs}; kanıt {summary}).")[:1000],
        })
        rec["provenance"]["modified"] = now
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_layer_augments:{args.layer}] applied={n_applied} "
          f"already-done={n_skipped} missing={n_missing}"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
