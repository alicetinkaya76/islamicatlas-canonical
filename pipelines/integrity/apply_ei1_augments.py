#!/usr/bin/env python3
"""
apply_ei1_augments.py — apply EI1 Track-A augments to person/place/dynasty
records (H10 Stage 4). Gap-fill-only + provenance append; idempotency probe =
existing `ei1:*` in derived_from.

Per matched PID (sidecar maps `person` / `place` / `dynasty`):
    labels.description.{en,tr,ar} ← summary_*   (only if that lang is absent)
    labels.altLabel.en            += title      (if not present anywhere)
    place only: derived_from_layers += "ei1"
    always: derived_from += ei1:<id> (vol/page locator) + record_history

Usage: python3 pipelines/integrity/apply_ei1_augments.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIDECAR = REPO_ROOT / "data" / "_state" / "ei1_augment_pending.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def _all_label_strings(labels: dict) -> set[str]:
    out = set()
    for v in (labels.get("prefLabel") or {}).values():
        if isinstance(v, str):
            out.add(v.casefold())
    for arr in (labels.get("altLabel") or {}).values():
        if isinstance(arr, list):
            out.update(x.casefold() for x in arr if isinstance(x, str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with SIDECAR.open(encoding="utf-8") as fh:
        side = json.load(fh)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_applied = n_noop = n_missing = 0

    for ns in ("person", "place", "dynasty"):
        for pid, events in sorted((side.get(ns) or {}).items()):
            path = (REPO_ROOT / "data" / "canonical" / ns /
                    f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json")
            if not path.exists():
                n_missing += 1
                print(f"  WARN missing record for {pid}")
                continue
            rec = json.loads(path.read_text(encoding="utf-8"))
            derived = rec.setdefault("provenance", {}).setdefault("derived_from", [])
            if any(str(d.get("source_id", "")).startswith("ei1:") for d in derived):
                n_noop += 1
                continue

            ev = events[0]
            changed = []
            labels = rec.setdefault("labels", {})
            desc = labels.setdefault("description", {})
            for lang, key in (("en", "summary_en"), ("tr", "summary_tr"),
                              ("ar", "summary_ar")):
                if ev.get(key) and not desc.get(lang):
                    desc[lang] = ev[key]
                    changed.append(f"description.{lang}")
            if not desc:
                labels.pop("description", None)
            title = (ev.get("title") or "").strip()
            if title and title.casefold() not in _all_label_strings(labels):
                labels.setdefault("altLabel", {}).setdefault("en", []).append(title)
                changed.append("altLabel.en")
            if ns == "place":
                layers = list(rec.get("derived_from_layers") or [])
                if "ei1" not in layers:
                    layers.append("ei1")
                    rec["derived_from_layers"] = layers
                    changed.append("derived_from_layers")

            derived.append({
                "source_id": f"ei1:{ev['ei1_id']}",
                "source_type": "tertiary_reference",
                "page_or_locator": f"EI1 vol. {ev.get('vol')}, p. {ev.get('page')}",
                "extraction_method": "ocr",
                "edition_or_version": "Encyclopaedia of Islam, 1st ed. (Brill, 1913-1936)",
            })
            rec["provenance"].setdefault("record_history", []).append({
                "change_type": "update", "changed_at": now,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": (f"ei1 augment (H10 Stage 4, Tier-2 conf "
                         f"{round(ev.get('confidence', 0), 2)}): gap-filled "
                         f"{changed or 'nothing (provenance only)'}."),
            })
            rec["provenance"]["modified"] = now
            if not args.dry_run:
                path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            n_applied += 1

    print(f"[apply_ei1_augments] applied={n_applied} already-done={n_noop} "
          f"missing={n_missing}{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
