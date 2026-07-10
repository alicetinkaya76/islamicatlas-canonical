#!/usr/bin/env python3
"""
apply_scholars_augments.py — apply the scholars Track-A sidecar to existing
person records (H10 Stage 3; person edition of apply_darp_augments).

Per matched person PID (data/_state/scholars_augment_pending.json):
  GAP-FILL ONLY (append-only semantics, v8 precedent — existing values are
  never overwritten):
    labels.prefLabel.en      ← preflabel_en        (if absent)
    labels.description.en    ← description_en      (if absent)
    labels.description.tr    ← description_tr      (if absent — v8 covered
                                                    dia slugs; science-layer
                                                    records may lack tr)
    kunya / nisba / laqab    ← card fields         (if absent)
  ALWAYS: provenance.record_history update entry + modified bump.
`_id_to_pid` and `_review_skipped` keys are bookkeeping, not applied.

Usage: python3 pipelines/integrity/apply_scholars_augments.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIDECAR = REPO_ROOT / "data" / "_state" / "scholars_augment_pending.json"
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
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
    sidecar.pop("_id_to_pid", None)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_applied = n_noop = n_missing = 0

    for pid, events in sorted(sidecar.items()):
        if not isinstance(events, list):
            events = [events]
        path = PERSON_DIR / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_missing += 1
            print(f"  WARN missing record for {pid}")
            continue
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)

        # Idempotency probe: scholars:* already in derived_from → done.
        derived = rec.setdefault("provenance", {}).setdefault("derived_from", [])
        if any(str(d.get("source_id", "")).startswith("scholars:") for d in derived):
            n_noop += 1
            continue

        ev = events[0]  # 49 distinct scholars → collisions not expected; [0] is the record
        changed_fields = []
        labels = rec.setdefault("labels", {})
        pref = labels.setdefault("prefLabel", {})
        if ev.get("preflabel_en") and not pref.get("en"):
            pref["en"] = ev["preflabel_en"]
            changed_fields.append("prefLabel.en")
        desc = labels.setdefault("description", {})
        for lang, key in (("en", "description_en"), ("tr", "description_tr")):
            if ev.get(key) and not desc.get(lang):
                desc[lang] = ev[key][:5000]
                changed_fields.append(f"description.{lang}")
        if not desc:
            labels.pop("description", None)
        if ev.get("kunya") and not rec.get("kunya"):
            rec["kunya"] = ev["kunya"][:200]
            changed_fields.append("kunya")
        for f in ("nisba", "laqab"):
            if ev.get(f) and not rec.get(f):
                rec[f] = ev[f]
                changed_fields.append(f)

        derived.append({
            "source_id": f"scholars:{ev['scholar_id']}",
            "source_type": "digital_corpus",
            "page_or_locator": f"scholars.csv scholar_id={ev['scholar_id']}",
            "extraction_method": "structured_json",
            "edition_or_version": "islamicatlas v1 scholars layer (v4.8.x)",
        })
        rec["provenance"].setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"scholars augment (H10 Stage 3, Tier-2 "
                     f"conf {round(ev.get('confidence', 0), 2)}): "
                     f"gap-filled {changed_fields or 'nothing (provenance only)'}."),
        })
        rec["provenance"]["modified"] = now

        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_scholars_augments] applied={n_applied} already-done={n_noop} "
          f"missing={n_missing}{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
