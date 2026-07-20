#!/usr/bin/env python3
"""
h22_003_person_dup_merge.py — aynı kişinin İKİ KAYNAKTAKİ ayrı kayıtlarını
birleştirir (H22 kuyruk eritme, kova A).

ÖLÇÜT (üç koşul birden): (1) aynı normalize Arapça prefLabel, (2) ölüm
tarihi HEM hicrî HEM miladi birebir aynı, (3) kaynak kümeleri AYRIK
(tipik: biri dia, diğeri el-alam) ve grup tam 2 kayıtlık.
EK SIKILAŞTIRMA: ad EN AZ İKİ KELİME olmalı. Tek kelimelik nisbeler
(الهذلي, الربعي, البرزلي sınıfı) DIŞARIDA bırakılır — aynı nisbeyi
taşıyan, aynı yıl ölmüş farklı kişiler olabilir; onlar kuyrukta kalır.

Kanıt örnekleri (ölçümle): İBNÜ'l-HÜMÂM(dia) = İbn el-Hemmâm(el-alam),
HAYVE b. ŞÜREYH = Hayye b. Şerîh, İBNÜ't-TİLMÎZ = İbn et-Telmîz —
transliterasyon farkı, aynı kişi. Bu küme xref↔store kopukluğunun
(H22 #3) diğer yüzüdür: aynı kişi iki kaynakta ayrı mint edilmiş.

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
  python3 pipelines/migrations/h22_003_person_dup_merge.py [--dry-run]
  python3 pipelines/migrations/h22_003_person_dup_merge.py --restore
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO / "data/canonical/person"
LEDGER = REPO / "data/_state/h22_person_dup_merge.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
    for f in sorted(PERSON_DIR.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        out[rec["@id"]] = (rec, f)
    return out


def find_groups(records):
    """Aynı norm(ar) + aynı (start_ah, start_ce); yalnız 2'li ve kaynakları
    ayrık gruplar; ad en az iki kelime."""
    buckets = defaultdict(list)
    for pid, (rec, _f) in records.items():
        prov = rec.get("provenance") or {}
        if prov.get("deprecated"):
            continue
        ar = ((rec.get("labels") or {}).get("prefLabel") or {}).get("ar")
        dt = rec.get("death_temporal") or {}
        ah, ce = dt.get("start_ah"), dt.get("start_ce")
        if not ar or ah is None or ce is None:
            continue
        key_ar = norm_ar(ar)
        if key_ar.count(" ") < 1:          # tek kelimelik nisbe → dışarıda
            continue
        srcs = frozenset((x.get("source_id") or "").split(":")[0]
                         for x in (prov.get("derived_from") or []))
        buckets[(key_ar, ah, ce)].append((pid, srcs))

    out = {}
    for k, v in buckets.items():
        if len(v) != 2:
            continue
        if set(v[0][1]) & set(v[1][1]):    # kaynaklar kesişiyorsa atla
            continue
        out[k] = sorted(p for p, _s in v)
    return out


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
                                          if "h22_003" not in (h.get("note") or "")]
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
        diff_src += 1

        for loser in losers:
            rec, f = records[loser]
            prov = rec.setdefault("provenance", {})
            prov["deprecated"] = True
            prov["deprecated_in_favor_of"] = winner
            hist = prov.setdefault("record_history", [])
            note = (f"h22_003 kişi-dublet birleştirme: aynı normalize Arapça ad "
                    f"{key[0]!r} + aynı ölüm ({key[1]} AH / {key[2]} CE) + ayrık "
                    f"kaynaklar; {winner} lehine emekli. "
                    f"PID korunur, geri alınabilir (h22_003 --restore).")
            if not any(h.get("note", "").startswith("h22_003") for h in hist):
                hist.append({"change_type": "deprecate", "note": note,
                             "changed_at": NOW, "changed_by": ATTRIBUTED_TO})
            if not args.dry_run:
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            n_losers += 1

        merges.append({"ad_ar": key[0], "olum_ah": key[1], "olum_ce": key[2],
                       "kazanan": winner, "kaybedenler": losers})

    if not args.dry_run and merges:
        LEDGER.write_text(json.dumps({
            "_doc": "H22 kova-A: aynı-kişi iki-kaynak dubletlerinin "
                    "birleştirme defteri (geri alma: h22_003 --restore).",
            "olcut": "aynı norm(ar prefLabel, ≥2 kelime) + aynı ölüm AH ve CE "
                     "+ ayrık kaynak kümeleri + tam 2 kayıtlık grup",
            "merged_at": NOW, "n_grup": len(merges), "n_emekli": n_losers,
            "merges": merges,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"grup={len(merges)} · emekli edilen={n_losers} (hepsi ayrık-kaynak)"
          + (" — DRY-RUN, yazılmadı" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
