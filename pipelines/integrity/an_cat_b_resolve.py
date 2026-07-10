#!/usr/bin/env python3
"""
an_cat_b_resolve.py — AN: dia_chunks Cat B/C slug'larının Tier-2 çözümü
(H10 Stage 5; ADR-011 v1.1'in ertelediği iş, PHASE0_CLOSEOUT §3).

Cat B/C = dia_chunks'ta olup dia_slug_to_pid.slug_to_pid'de OLMAYAN 4,784
distinct slug (hükümdarlar, râviler, modern figürler + Cat C yer/kavram
karışık). Her slug person-uzayına karşı Tier-2'den geçirilir:

    match  → data/_state/an_cat_b_resolution.json altında `matches`:
             mevcut person'a v8-tarzı zenginleştirme adayı (aggregated
             narrative, prefLabel.ar, death_temporal) — application ayrı,
             journal'lı bir apply koşusudur (bu script store'a YAZMAZ).
    review → resolver kuyruğu (data/review_queue/an-cat-b.jsonl) + sayım.
    new    → MINT YOK (Cat C karışımı otomatik ayrıştırılamaz: bir slug'ın
             kişi mi yer mi kavram mı olduğuna makine karar vermez —
             North Star). `unmatched` altında sınıflandırma ipuçlarıyla
             (tarih var mı, Arapça var mı) triage havuzuna yazılır.

Usage: python3 pipelines/integrity/an_cat_b_resolve.py [--limit N]
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
    parse_death_paren_extended, build_temporal_from_parsed_d)
from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402

OUT = REPO_ROOT / "data" / "_state" / "an_cat_b_resolution.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    chunks = json.loads((REPO_ROOT / "data/sources/dia_chunks.json").read_text(encoding="utf-8"))
    s2p = json.loads((REPO_ROOT / "data/_state/dia_slug_to_pid.json").read_text(encoding="utf-8"))["slug_to_pid"]
    agg = aggregate_chunks_by_slug(chunks)
    cat_b = sorted(s for s in agg if s not in s2p)
    if args.limit:
        cat_b = cat_b[:args.limit]
    print(f"[an] Cat B/C evreni: {len(cat_b)} slug (dia_chunks {len(agg)} - Cat A {len(s2p)})")

    resolver = EntityResolver(REPO_ROOT)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    matches: dict = {}
    unmatched: dict = {}
    n_review = 0
    for slug in cat_b:
        a = agg[slug]
        title = (a.get("primary_n") or "").strip()
        labels = {"prefLabel": {"tr": title.title() if title.isupper() else title}}
        ar = (a.get("primary_a") or "").strip()
        if ar and classify_arabic_script(ar) == "arabic_primary":
            labels["prefLabel"]["ar"] = ar
        parsed = parse_death_paren_extended(a.get("primary_d") or "")
        temporal = build_temporal_from_parsed_d(parsed) or {}
        q_temporal = {"start_ce": temporal["start_ce"]} if temporal.get("start_ce") else {}

        d = resolver.resolve(entity_type="person", adapter_id="an-cat-b",
                             extracted_record_id=f"dia-chunks:{slug}",
                             labels=labels, temporal=q_temporal)
        if d.kind == "match":
            matches[slug] = {"pid": d.matched_pid, "confidence": d.confidence,
                             "tier": d.tier, "title": title,
                             "has_ar": "ar" in labels["prefLabel"],
                             "narrative_len": len(a.get("t_total") or ""),
                             "n_chunks": a.get("n_chunks")}
        elif d.kind == "review":
            n_review += 1
        else:
            unmatched[slug] = {"title": title,
                               "dated": bool(q_temporal),
                               "has_ar": "ar" in labels["prefLabel"],
                               "confidence": d.confidence}

    resolver.close()
    OUT.write_text(json.dumps({
        "_meta": {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "universe": len(cat_b), "matches": len(matches),
                  "review": n_review, "unmatched": len(unmatched),
                  "note": ("matches = v8-style enrichment candidates (apply is a "
                           "separate journaled run); unmatched = human triage pool "
                           "(person/place/concept split is NOT automated)")},
        "matches": matches, "unmatched": unmatched,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    dated_un = sum(1 for v in unmatched.values() if v["dated"])
    print(f"[an] match={len(matches)} review={n_review} unmatched={len(unmatched)} "
          f"(unmatched içinde tarihli: {dated_un})")
    print(f"[an] → {OUT.relative_to(REPO_ROOT)} + data/review_queue/an-cat-b.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
