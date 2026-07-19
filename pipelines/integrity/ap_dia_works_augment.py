#!/usr/bin/env python3
"""
ap_dia_works_augment.py — AP (dia_works), AUGMENT-ONLY icrası (H11 Stage 1).

Karar çerçevesi (H11 Karar 1; HAFTA10_AP_KICKOFF'un A1+B3 hattı):
  * ADR-009 DEĞİŞMEZ (A1): hiçbir DiA-only başlık mint edilmez — 42.449
    doğrulanmamış başlık dışarıda kalır. Katkıcı modellemesi ertelenir (B3).
  * AP = mevcut work kayıtlarının DiA-yüzü: H5 audit'inin başlık-eşleşmeleri
    BUGÜNKÜ tam yazar haritasıyla (Cat-A 3.309 + AN 2.261) yeniden doğrulanır;
    yazar-doğrulamalı eşleşmeler augment edilir:
        dia_slug = "<slug>:title_<i>"          (şema alanı; Hassâf emsali)
        derived_from += dia-rich:<slug>:title_<i>  (cilt+sayfa locator'ı
                        dia_chunks_rich'ten — AO'nun (c) teslimi)
        altLabel.tr += DiA başlık biçimi (yeniyse)
  * Çok-aday / yazar-doğrulamasız / dia_slug-çakışması → ap-dia-works-review
    kuyruğu (MINT YOK, AUGMENT YOK — tarihçi).

İdempotent: derived_from'da dia-rich:<slug>:title_<i> varsa no-op.

Usage: python3 pipelines/integrity/ap_dia_works_augment.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = REPO_ROOT / "data" / "canonical" / "work"
QUEUE = REPO_ROOT / "data" / "review_queue" / "ap-dia-works.jsonl"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _locator(rich_rec: dict, slug: str) -> str:
    parts = (rich_rec or {}).get("parts") or []
    for p in parts:
        if p.get("cilt"):
            s = f"TDV DİA cilt {p['cilt']}, s. {p['sayfa_baslangic']}"
            if p.get("sayfa_bitis"):
                s += f"-{p['sayfa_bitis']}"
            if p.get("baski_yili"):
                s += f" ({p['baski_yili']})"
            return s
    return f"https://islamansiklopedisi.org.tr/{slug} (web-only madde)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    audit = _load(REPO_ROOT / "data/_state/dia_works_h5_audit.json")["per_slug"]
    rich = _load(REPO_ROOT / "data/sources/dia_chunks_rich.json")["records"]
    cat_a = _load(REPO_ROOT / "data/_state/dia_slug_to_pid.json")["slug_to_pid"]
    an = {s: m["pid"] for s, m in
          _load(REPO_ROOT / "data/_state/an_cat_b_resolution.json")["matches"].items()}
    slug_to_scholar = {**an, **cat_a}   # Cat-A önceliği

    # Store'daki mevcut dia_slug sahipliği: aynı key'i İKİNCİ bir work'e
    # vermek = work-dublörü maskelenmesi (kanıt: hassaf:title_2 → el-mint
    # 9331 VE openiti-Hiyal 3591 aynı eser). Key sahipliyse öteki work
    # dup-adayı olarak kuyruğa gider, augment YAPILMAZ.
    slug_owner: dict[str, str] = {}
    for wp in WORK_DIR.glob("iac_work_*.json"):
        r = _load(wp)
        ds = r.get("dia_slug")
        if ds:
            slug_owner[ds] = r["@id"]

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    queued_keys = set()
    if QUEUE.exists():
        for line in QUEUE.read_text(encoding="utf-8").splitlines():
            try:
                queued_keys.add(json.loads(line)["key"])
            except Exception:
                pass

    stats = {"augmented": 0, "already": 0, "validated_multi": 0,
             "author_mismatch": 0, "no_scholar_pid": 0, "slug_conflict": 0,
             "work_missing": 0}
    q_new = []

    for slug, titles in sorted(audit.items()):
        scholar = slug_to_scholar.get(slug)
        for idx, t in enumerate(titles):
            matches = ((t.get("match_in_openiti_works") or []) +
                       (t.get("match_in_science_works") or []))
            if not matches:
                continue  # dia-only: ADR-009 gereği dokunulmaz (A1)
            key = f"{slug}:title_{idx}"
            if scholar is None:
                stats["no_scholar_pid"] += 1
                if key not in queued_keys:
                    q_new.append({"key": key, "reason": "scholar_unresolved",
                                  "title": t.get("title"), "matches": matches})
                continue
            validated = [m for m in matches if scholar in (m.get("authors") or [])]
            if not validated:
                stats["author_mismatch"] += 1
                if key not in queued_keys:
                    q_new.append({"key": key, "reason": "author_mismatch",
                                  "title": t.get("title"),
                                  "scholar": scholar, "matches": matches})
                continue
            if len(validated) > 1:
                stats["validated_multi"] += 1
                if key not in queued_keys:
                    q_new.append({"key": key, "reason": "multi_validated",
                                  "title": t.get("title"),
                                  "scholar": scholar, "matches": validated})
                continue

            wpid = validated[0]["pid"]
            owner = slug_owner.get(key)
            if owner and owner != wpid:
                stats["slug_conflict"] += 1
                if key not in queued_keys:
                    q_new.append({"key": key, "reason": "dia_slug_taken_work_dup_candidate",
                                  "owner": owner, "candidate": wpid,
                                  "title": t.get("title")})
                    queued_keys.add(key)
                continue
            wpath = WORK_DIR / f"iac_work_{wpid.rsplit('-', 1)[1]}.json"
            if not wpath.exists():
                stats["work_missing"] += 1
                continue
            rec = _load(wpath)
            sid = f"dia-rich:{key}"
            derived = rec.setdefault("provenance", {}).setdefault("derived_from", [])
            if any(d.get("source_id") == sid for d in derived):
                stats["already"] += 1
                continue
            existing_slug = rec.get("dia_slug")
            if existing_slug and existing_slug != key:
                stats["slug_conflict"] += 1
                if key not in queued_keys:
                    q_new.append({"key": key, "reason": "dia_slug_conflict",
                                  "work": wpid, "existing": existing_slug})
                continue

            rec["dia_slug"] = key
            derived.append({
                "source_id": sid,
                "source_type": "tertiary_reference",
                "page_or_locator": _locator(rich.get(slug), slug),
                "extraction_method": "structured_json",
                "edition_or_version": ("TDV İslâm Ansiklopedisi + AO rich "
                                       "locator (dia_chunks_rich.json)"),
            })
            dia_title = (t.get("title") or "").strip()
            labels = rec.setdefault("labels", {})
            all_vals = {v.casefold() for v in (labels.get("prefLabel") or {}).values()
                        if isinstance(v, str)}
            for arr in (labels.get("altLabel") or {}).values():
                if isinstance(arr, list):
                    all_vals.update(x.casefold() for x in arr if isinstance(x, str))
            if dia_title and dia_title.casefold() not in all_vals:
                labels.setdefault("altLabel", {}).setdefault("tr", []).append(dia_title)
            rec["provenance"].setdefault("record_history", []).append({
                "change_type": "update", "changed_at": NOW,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": (f"AP dia_works augment (H11 S1, A1+B3): dia_slug={key}; "
                         f"yazar-doğrulamalı ({scholar}); DiA locator eklendi."),
            })
            rec["provenance"]["modified"] = NOW
            if not args.dry_run:
                wpath.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
            stats["augmented"] += 1

    if q_new and not args.dry_run:
        with QUEUE.open("a", encoding="utf-8") as fh:
            for q in q_new:
                fh.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"[ap_augment] {stats} queued+={len(q_new)}"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
