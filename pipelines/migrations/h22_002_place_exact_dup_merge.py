#!/usr/bin/env python3
"""
h22_002_place_exact_dup_merge.py — BİREBİR aynı yer kayıtlarını birleştirir
(H22 kuyruk eritme, kova A; yer dublet kümelerinin en kesin alt kümesi).

ÖLÇÜT (kanıtı tartışmasız olan bant): aynı normalize Arapça prefLabel VE
koordinatlar 5 ondalık basamağa kadar BİREBİR aynı (≈1 metre). Farklı
koordinatlı adaşlar (Trablus Şam/Libya sınıfı) ve mesafe eşiği tartışması
BU SCRIPT'İN DIŞINDA — onlar tarihçi kuyruğunda kalır.

BİRLEŞTİRME = YUMUŞAK-SİLME + YÖNLENDİRME, silme değil:
  kazanan  : grubun en zengin kaydı (curie sayısı > alan sayısı > küçük pid)
  kaybeden : provenance.deprecated = true
             provenance.deprecated_in_favor_of = <kazanan pid>
             record_history'ye gerekçe
Kaybedenin PID'i yaşamaya devam eder (atıf istikrarı); tüketici
deprecated_in_favor_of ile kazanana yönlenir. search/projector zaten
deprecated kayıtlara -100 verir. Geri alma: --restore.

Referans göçü (başka kayıtların located_in/active_in_places alanları)
BU TURDA YAPILMAZ — eski pid canlı kaldığı için kırık bağ oluşmaz;
göç ayrı ve ölçülmüş bir adım olarak raporlanır.

Usage:
  python3 pipelines/migrations/h22_002_place_exact_dup_merge.py [--dry-run]
  python3 pipelines/migrations/h22_002_place_exact_dup_merge.py --restore
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PLACE_DIR = REPO / "data/canonical/place"
LEDGER = REPO / "data/_state/h22_place_dup_merge.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
COORD_PRECISION = 5          # ~1 m


def norm_ar(s: str) -> str:
    if not s:
        return ""
    out = []
    for ch in unicodedata.normalize("NFKD", s):
        if unicodedata.category(ch) == "Mn" or ch == "ـ":
            continue
        if ch in "أإآ":
            ch = "ا"
        elif ch == "ى":
            ch = "ي"
        elif ch == "ة":
            ch = "ه"
        out.append(ch)
    return "".join(out).strip()


def richness(rec: dict) -> tuple:
    prov = rec.get("provenance") or {}
    n_curie = len(prov.get("derived_from") or [])
    n_fields = sum(1 for k, v in rec.items() if v not in (None, [], {}, ""))
    return (n_curie, n_fields)


def load_all():
    out = {}
    for f in sorted(PLACE_DIR.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        out[rec["@id"]] = (rec, f)
    return out


def find_groups(records):
    groups = defaultdict(list)
    for pid, (rec, _f) in records.items():
        if (rec.get("provenance") or {}).get("deprecated"):
            continue
        ar = ((rec.get("labels") or {}).get("prefLabel") or {}).get("ar")
        c = rec.get("coords") or {}
        lat, lon = c.get("lat"), c.get("lon")
        if not ar or lat is None or lon is None:
            continue
        key = (norm_ar(ar), round(float(lat), COORD_PRECISION),
               round(float(lon), COORD_PRECISION))
        groups[key].append(pid)
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    records = load_all()

    if args.restore:
        if not LEDGER.exists():
            print("✗ defter yok")
            return 1
        led = json.loads(LEDGER.read_text(encoding="utf-8"))
        n = 0
        for m in led["merges"]:
            for loser in m["kaybedenler"]:
                rec, f = records.get(loser, (None, None))
                if not rec:
                    continue
                prov = rec.setdefault("provenance", {})
                prov["deprecated"] = False
                prov.pop("deprecated_in_favor_of", None)
                prov["record_history"] = [h for h in prov.get("record_history", [])
                                          if "h22_002" not in (h.get("note") or "")]
                if not args.dry_run:
                    f.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
                n += 1
        print(f"↩ geri alındı: {n} kayıt" + (" (DRY-RUN)" if args.dry_run else ""))
        return 0

    groups = find_groups(records)
    merges, n_losers = [], 0
    same_src = diff_src = 0

    for key, pids in sorted(groups.items()):
        ranked = sorted(pids, key=lambda p: (-richness(records[p][0])[0],
                                             -richness(records[p][0])[1], p))
        winner, losers = ranked[0], ranked[1:]
        srcs = {tuple(sorted({(x.get("source_id") or "").split(":")[0]
                              for x in ((records[p][0].get("provenance") or {})
                                        .get("derived_from") or [])}))
                for p in pids}
        (same_src, diff_src) = (same_src + 1, diff_src) if len(srcs) == 1 else (same_src, diff_src + 1)

        for loser in losers:
            rec, f = records[loser]
            prov = rec.setdefault("provenance", {})
            prov["deprecated"] = True
            prov["deprecated_in_favor_of"] = winner
            hist = prov.setdefault("record_history", [])
            note = (f"h22_002 birebir-dublet birleştirme: aynı normalize Arapça "
                    f"etiket {key[0]!r} + BİREBİR aynı koordinat "
                    f"({key[1]}, {key[2]}); {winner} lehine emekli. "
                    f"PID korunur, geri alınabilir (h22_002 --restore).")
            if not any(h.get("note", "").startswith("h22_002") for h in hist):
                hist.append({"change_type": "deprecate", "note": note,
                             "changed_at": NOW, "changed_by": ATTRIBUTED_TO})
            if not args.dry_run:
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            n_losers += 1

        merges.append({"etiket": key[0], "lat": key[1], "lon": key[2],
                       "kazanan": winner, "kaybedenler": losers})

    if not args.dry_run and merges:
        LEDGER.write_text(json.dumps({
            "_doc": "H22 kova-A: birebir aynı koordinat+etiket yer dubletlerinin "
                    "birleştirme defteri (geri alma: h22_002 --restore).",
            "olcut": f"aynı norm(ar prefLabel) + koordinat {COORD_PRECISION} "
                     f"ondalıkta birebir eşit (~1 m)",
            "merged_at": NOW, "n_grup": len(merges), "n_emekli": n_losers,
            "merges": merges,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"grup={len(merges)} · emekli edilen={n_losers} "
          f"(aynı-kaynak {same_src} grup, farklı-kaynak {diff_src} grup)"
          + (" — DRY-RUN, yazılmadı" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
