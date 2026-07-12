#!/usr/bin/env python3
"""
apply_an_cat_b.py — AN eşleşmelerinin v8-tarzı uygulanması (H10 Stage 5).

an_cat_b_resolution.json'daki her match (slug → mevcut person PID; tümü
Tier-2 conf ≥0.95 + çift-sinyal) için ADR-011 v1.1 patch-şekli:
    description.tr   ← aggregated chunk narrative (SADECE BOŞSA; 50K
                       sentence-boundary truncate, v8 fonksiyonuyla)
    prefLabel.ar     ← chunk.a (arabic_primary doğrulamalı; boşsa)
    death_temporal   ← extended parser (boşsa)
    derived_from    += dia-chunks:<slug> (web locator'lı) + record_history
İdempotency: derived_from'da `dia-chunks:<slug>` varsa no-op.

Usage: python3 pipelines/integrity/apply_an_cat_b.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.dia_enrichment_lib import (  # noqa: E402
    aggregate_chunks_by_slug, classify_arabic_script,
    parse_death_paren_extended, build_temporal_from_parsed_d,
    truncate_at_sentence_boundary)

RES = REPO_ROOT / "data" / "_state" / "an_cat_b_resolution.json"
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    matches = json.loads(RES.read_text(encoding="utf-8"))["matches"]
    # H10 final-review guard: aynı PID'e birden çok slug düştüyse (resolver
    # over-merge adayı) OTOMATİK UYGULANMAZ — 9 kayda yanlış-kişi verisi
    # bulaştığı kanıtlandı (Nûh II ← Mansûr b. Nûh Arapça etiketi). Bu
    # çakışmalar collisions kuyruğuna yazılır; karar tarihçinin.
    from collections import Counter
    pid_counts = Counter(m["pid"] for m in matches.values())
    collision_pids = {p for p, c in pid_counts.items() if c > 1}
    if collision_pids:
        coll_path = REPO_ROOT / "data" / "review_queue" / "an-cat-b-collisions.jsonl"
        coll_path.parent.mkdir(parents=True, exist_ok=True)
        existing = set()
        if coll_path.exists():
            for line in coll_path.read_text(encoding="utf-8").splitlines():
                try:
                    existing.add(json.loads(line)["slug"])
                except Exception:
                    pass
        with coll_path.open("a", encoding="utf-8") as fh:
            for slug, m in sorted(matches.items()):
                if m["pid"] in collision_pids and slug not in existing:
                    fh.write(json.dumps({"slug": slug, **m}, ensure_ascii=False) + "\n")
        n_skip_coll = sum(1 for m in matches.values() if m["pid"] in collision_pids)
        matches = {s: m for s, m in matches.items() if m["pid"] not in collision_pids}
        print(f"[apply_an] ÇAKIŞMA: {len(collision_pids)} PID / {n_skip_coll} slug "
              f"otomatik-uygulama DIŞI → {coll_path.name} (tarihçi)")
    chunks = json.loads((REPO_ROOT / "data/sources/dia_chunks.json").read_text(encoding="utf-8"))
    agg = aggregate_chunks_by_slug(chunks)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    n_applied = n_noop = n_missing = 0
    filled = {"description.tr": 0, "prefLabel.ar": 0, "death_temporal": 0}

    for slug, m in sorted(matches.items()):
        pid = m["pid"]
        path = PERSON_DIR / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_missing += 1
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        derived = rec.setdefault("provenance", {}).setdefault("derived_from", [])
        if any(str(d.get("source_id", "")) == f"dia-chunks:{slug}" for d in derived):
            n_noop += 1
            continue

        a = agg[slug]
        changed = []
        labels = rec.setdefault("labels", {})
        desc = labels.setdefault("description", {})
        if not desc.get("tr") and (a.get("t_total") or "").strip():
            text, _tr = truncate_at_sentence_boundary(a["t_total"].strip(), 50_000)
            desc["tr"] = text
            changed.append("description.tr")
            filled["description.tr"] += 1
        if not desc:
            labels.pop("description", None)
        ar = (a.get("primary_a") or "").strip()
        pref = labels.setdefault("prefLabel", {})
        if ar and not pref.get("ar") and classify_arabic_script(ar) == "arabic_primary":
            pref["ar"] = ar
            changed.append("prefLabel.ar")
            filled["prefLabel.ar"] += 1
        if not rec.get("death_temporal"):
            t = build_temporal_from_parsed_d(
                parse_death_paren_extended(a.get("primary_d") or ""))
            if t:
                rec["death_temporal"] = t
                changed.append("death_temporal")
                filled["death_temporal"] += 1

        derived.append({
            "source_id": f"dia-chunks:{slug}",
            "source_type": "tertiary_reference",
            "page_or_locator": f"https://islamansiklopedisi.org.tr/{slug}",
            "extraction_method": "structured_json",
            "edition_or_version": "TDV İslâm Ansiklopedisi (dia_chunks.json)",
        })
        rec["provenance"].setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"AN Cat-B enrichment (H10 Stage 5, Tier-2 conf "
                     f"{round(m.get('confidence', 0), 2)}): gap-filled "
                     f"{changed or 'nothing (provenance only)'}."),
        })
        rec["provenance"]["modified"] = now
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_an] applied={n_applied} noop={n_noop} missing={n_missing} "
          f"filled={filled}{' (dry-run)' if args.dry_run else ''}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
