#!/usr/bin/env python3
"""
h10_003_final_review_data_repairs.py — H10 final-review'un onayladığı beş
veri-bozulması sınıfının onarımı (H10 Stage 14). Her sınıf sayılır, dry-run
desteklenir, idempotenttir.

  R1  ei1 doğum-ölüm karışımı: kaynakta yalnız bc (doğum) olan ei1-mint
      person'larda death_temporal → birth_temporal taşınır (~58 kayıt).
  R2  AN çok-slug çakışması: aynı PID'e >1 slug match'lenen kayıtlarda
      (9 PID; Nûh II'ye Mansûr b. Nûh verisi bulaştığı kanıtlı) AN'in
      gap-fill'leri + dia-chunks:<slug> provenance'ı + history girdileri
      GERİ ALINIR; slug'lar an-cat-b-collisions.jsonl kuyruğuna.
  R3  ei1 çok-olay çakışması: aynı PID'e >1 EI1 makalesi (14 PID; 5166'da
      yanlış-kişi EN açıklaması kanıtlı) — ei1 fill'leri geri alınır,
      PID'ler ei1-collisions.jsonl kuyruğuna.
  R4  ibn-battuta koşu-içi mükerrer yer mintleri: aynı koordinat-yakınlığı
      (≤2 km) + isim-benzerliği ≥90 ile başka bir place'i ikileyen
      ibn-battuta mint'leri SİLİNİR (saatler önce bizim bug'ımızın ürettiği
      taze kayıtlar; PID rezerv kalır) + place-dedup listesine yazılır.
  R5  evliya temporal backfill: voyage_id → date_start_miladi yılından
      temporal_coverage.start_ce (kaynak veriden; 2.232 mint temporal'sızdı).

Usage: python3 pipelines/migrations/h10_003_final_review_data_repairs.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from rapidfuzz import fuzz  # noqa: E402

PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, rec, dry):
    if not dry:
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


def _hist(rec, note):
    rec.setdefault("provenance", {}).setdefault("record_history", []).append({
        "change_type": "update", "changed_at": NOW,
        "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
        "note": note[:1000]})
    rec["provenance"]["modified"] = NOW


def _revert_source_fills(rec, source_prefix, note_prefix):
    """Bir augment kaynağının gap-fill'lerini + provenance izini geri alır.
    History notlarındaki "gap-filled [...]" alan listesi parse edilir."""
    prov = rec.get("provenance") or {}
    hist = prov.get("record_history") or []
    reverted_fields = []
    kept_hist = []
    for h in hist:
        note = h.get("note") or ""
        if note.startswith(note_prefix):
            import re as _re
            m = _re.search(r"gap-filled \[([^\]]*)\]", note)
            if m:
                reverted_fields += [f.strip().strip("'\"")
                                    for f in m.group(1).split(",") if f.strip()]
            continue  # bu history girdisi düşer
        kept_hist.append(h)
    prov["record_history"] = kept_hist
    prov["derived_from"] = [d for d in (prov.get("derived_from") or [])
                            if not str(d.get("source_id", "")).startswith(source_prefix)]
    labels = rec.get("labels") or {}
    for f in reverted_fields:
        if f == "prefLabel.ar":
            (labels.get("prefLabel") or {}).pop("ar", None)
        elif f == "prefLabel.en":
            (labels.get("prefLabel") or {}).pop("en", None)
        elif f.startswith("description."):
            (labels.get("description") or {}).pop(f.split(".")[1], None)
        elif f == "altLabel.en":
            pass  # append'i güvenle ayıklayamayız — kuyruk kaydında not edilir
        elif f in ("kunya", "nisba", "laqab", "death_temporal"):
            rec.pop(f, None)
        elif f == "derived_from_layers":
            pass
    if not (labels.get("description") or {}):
        labels.pop("description", None)
    return reverted_fields


def r1_ei1_birth_death(dry) -> int:
    lite = {r["id"]: r for r in _load(REPO_ROOT / "data/sources/ei1/ei1_lite.json")}
    n = 0
    for path in sorted(PERSON_DIR.glob("iac_person_*.json")):
        rec = _load(path)
        gen = (rec.get("provenance") or {}).get("generated_by") or {}
        if gen.get("pipeline_name") != "canonicalize_person_ei1":
            continue
        sid = (rec["provenance"]["derived_from"][0].get("source_id") or "")
        try:
            eid = int(sid.split(":", 1)[1])
        except (IndexError, ValueError):
            continue
        src = lite.get(eid) or {}
        dc = str(src.get("dc") or "").strip()
        bc = str(src.get("bc") or "").strip()
        if dc or not bc:
            continue  # dc'liyse death doğru; bc'siz zaten mint edilmemeli
        dt = rec.get("death_temporal")
        if not dt:
            continue
        rec["birth_temporal"] = dt
        rec.pop("death_temporal", None)
        _hist(rec, "h10_003 R1: EI1 kaynak yalnız doğum yılı (bc) taşıyor — "
                   "death_temporal → birth_temporal taşındı (final-review).")
        _save(path, rec, dry)
        n += 1
    return n


def r2_an_collisions(dry) -> tuple[int, int]:
    res = _load(REPO_ROOT / "data/_state/an_cat_b_resolution.json")["matches"]
    from collections import Counter
    counts = Counter(m["pid"] for m in res.values())
    coll_pids = {p for p, c in counts.items() if c > 1}
    queue = REPO_ROOT / "data/review_queue/an-cat-b-collisions.jsonl"
    queue.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if queue.exists():
        for line in queue.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["slug"])
            except Exception:
                pass
    n_rec = n_slug = 0
    for pid in sorted(coll_pids):
        path = PERSON_DIR / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            continue
        rec = _load(path)
        if any((h.get("note") or "").startswith("h10_003 R2")
               for h in (rec.get("provenance", {}).get("record_history") or [])):
            continue  # idempotent
        fields = _revert_source_fills(rec, "dia-chunks:", "AN Cat-B enrichment")
        _hist(rec, f"h10_003 R2: çok-slug çakışması — AN katkıları geri alındı "
                   f"(reverted: {fields}); slug'lar collisions kuyruğunda.")
        _save(path, rec, dry)
        n_rec += 1
        if not dry:
            with queue.open("a", encoding="utf-8") as fh:
                for slug, m in sorted(res.items()):
                    if m["pid"] == pid and slug not in seen:
                        fh.write(json.dumps({"slug": slug, **m,
                                             "reverted_fields": fields},
                                            ensure_ascii=False) + "\n")
                        seen.add(slug)
                        n_slug += 1
    return n_rec, n_slug


def r3_ei1_collisions(dry) -> tuple[int, int]:
    side = _load(REPO_ROOT / "data/_state/ei1_augment_pending.json")
    queue = REPO_ROOT / "data/review_queue/ei1-collisions.jsonl"
    queue.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if queue.exists():
        for line in queue.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["pid"])
            except Exception:
                pass
    n_rec = n_ev = 0
    for ns in ("person", "place", "dynasty"):
        for pid, events in sorted((side.get(ns) or {}).items()):
            if not isinstance(events, list) or len(events) <= 1:
                continue
            path = (REPO_ROOT / "data" / "canonical" / ns /
                    f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json")
            if not path.exists():
                continue
            rec = _load(path)
            if any((h.get("note") or "").startswith("h10_003 R3")
                   for h in (rec.get("provenance", {}).get("record_history") or [])):
                continue  # idempotent
            fields = _revert_source_fills(rec, "ei1:", "ei1 augment")
            _hist(rec, f"h10_003 R3: çok-olaylı EI1 çakışması ({len(events)} "
                       f"makale aynı kayda) — ei1 katkıları geri alındı "
                       f"(reverted: {fields}); olaylar collisions kuyruğunda.")
            _save(path, rec, dry)
            n_rec += 1
            n_ev += len(events)
            if not dry and pid not in seen:
                with queue.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"pid": pid, "ns": ns, "events": events,
                                         "reverted_fields": fields},
                                        ensure_ascii=False) + "\n")
                seen.add(pid)
    return n_rec, n_ev


def r4_ibn_battuta_dupes(dry) -> int:
    def hav(a, b, c, d):
        p = math.pi / 180
        x = 0.5 - math.cos((c - a) * p) / 2 + \
            math.cos(a * p) * math.cos(c * p) * (1 - math.cos((d - b) * p)) / 2
        return 12742 * math.asin(math.sqrt(x))

    others, ibn = [], []
    for path in PLACE_DIR.glob("iac_place_*.json"):
        rec = _load(path)
        sid = ((rec.get("provenance") or {}).get("derived_from") or [{}])[0].get("source_id", "")
        c = rec.get("coords") or {}
        entry = (path, rec, c.get("lat"), c.get("lon"))
        (ibn if sid.startswith("ibn-battuta:") else others).append(entry)

    dedup_log = REPO_ROOT / "data/_state/place_dupes_removed_h10_003.json"
    removed = []
    review = []

    # İbn-İÇİ mükerrerler: güzergâh aynı şehre tekrar uğrar ("Kûlam (Dönüş)");
    # koşu-içi indeks tazeliği yüzünden her uğrayış ayrı mint olmuş. En düşük
    # pid tutulur, diğerleri silinir (≤2 km + isim ≥90).
    ibn_sorted = sorted(ibn, key=lambda e: e[1]["@id"])
    kept: list = []
    for path, rec, lat, lon in ibn_sorted:
        if lat is None:
            kept.append((path, rec, lat, lon))
            continue
        my_names = [v for v in (rec["labels"].get("prefLabel") or {}).values()]
        dup_of = None
        for _, krec, klat, klon in kept:
            if klat is None or abs(klat - lat) > 0.05:
                continue
            if hav(lat, lon, klat, klon) > 2.0:
                continue
            k_names = [v for v in (krec["labels"].get("prefLabel") or {}).values()]
            sim = max((fuzz.token_set_ratio(a.lower(), b.lower())
                       for a in my_names for b in k_names), default=0)
            if sim >= 90:
                dup_of = krec["@id"]
                break
        if dup_of:
            removed.append({"removed_pid": rec["@id"], "kept_pid": dup_of,
                            "name": my_names[:1], "kind": "intra-ibn"})
            if not dry:
                path.unlink()
        else:
            kept.append((path, rec, lat, lon))
    ibn = kept

    for path, rec, lat, lon in ibn:
        if lat is None:
            continue
        my_names = [v for v in (rec["labels"].get("prefLabel") or {}).values()]
        for _, orec, olat, olon in others:
            if olat is None or abs(olat - lat) > 0.05:
                continue
            if hav(lat, lon, olat, olon) > 2.0:
                continue
            o_names = [v for v in (orec["labels"].get("prefLabel") or {}).values()]
            sim = max((fuzz.token_set_ratio(a.lower(), b.lower())
                       for a in my_names for b in o_names), default=0)
            if sim >= 90:
                removed.append({"removed_pid": rec["@id"],
                                "kept_pid": orec["@id"],
                                "name": my_names[:1], "sim": sim,
                                "km": round(hav(lat, lon, olat, olon), 2),
                                "kind": "vs-store"})
                if not dry:
                    path.unlink()
                break
            elif sim >= 70:
                # Sınır vakası (ör. Sehwan↔Sadūsān 77): silme YOK — review.
                review.append({"ibn_pid": rec["@id"], "other_pid": orec["@id"],
                               "name": my_names[:1], "other_name": o_names[:1],
                               "sim": sim,
                               "km": round(hav(lat, lon, olat, olon), 2)})
    if not dry:
        dedup_log.write_text(json.dumps({
            "_meta": {"run_at": NOW,
                      "note": ("koşu-içi indeks-tazeliği bug'ının mint ettiği "
                               "mükerrerler; PID'ler rezerv kalır (idempotent "
                               "hash aynı pid'i döndürür — kayıt yeniden "
                               "yazılMAmalı, kept_pid kullanılmalı)")},
            "removed": removed,
            "borderline_review": review}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
    return len(removed)


def r5_evliya_temporal(dry) -> int:
    data = _load(REPO_ROOT / "data/sources/evliya-celebi/evliya_atlas_layer.json")
    vyear = {}
    for v in data.get("voyages", []):
        d = str(v.get("date_start_miladi") or "")[:4]
        if d.isdigit():
            vyear[v["id"]] = int(d)
    stops = {f"evliya-celebi:{p['id']}": p.get("voyage_id")
             for p in data.get("places", [])}
    n = 0
    for path in sorted(PLACE_DIR.glob("iac_place_*.json")):
        rec = _load(path)
        sid = ((rec.get("provenance") or {}).get("derived_from") or [{}])[0].get("source_id", "")
        if not sid.startswith("evliya-celebi:") or rec.get("temporal_coverage"):
            continue
        year = vyear.get(stops.get(sid))
        if not year:
            continue
        rec["temporal_coverage"] = {"start_ce": year, "note": "sefer başlangıç yılı (tanıklık)"}
        _hist(rec, f"h10_003 R5: temporal_coverage sefer yılından backfill "
                   f"({sid} → {year}; final-review).")
        _save(path, rec, dry)
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    d = args.dry_run
    r1 = r1_ei1_birth_death(d)
    r2r, r2s = r2_an_collisions(d)
    r3r, r3e = r3_ei1_collisions(d)
    r4 = r4_ibn_battuta_dupes(d)
    r5 = r5_evliya_temporal(d)
    print(f"[h10_003] R1 birth/death taşınan={r1} | R2 AN-revert kayıt={r2r} "
          f"slug-kuyruk={r2s} | R3 ei1-revert kayıt={r3r} olay={r3e} | "
          f"R4 mükerrer-yer silinen={r4} | R5 evliya-temporal={r5}"
          f"{' (dry-run)' if d else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
