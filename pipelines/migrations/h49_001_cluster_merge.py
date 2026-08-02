#!/usr/bin/env python3
"""h49_001_cluster_merge.py — YARGILANMIŞ kişi kümelerini birleştirir.

H22'nin `h22_003_person_dup_merge.py` deseninin devamı; farkı ÖLÇÜT:
  H22 : otomatik (ad + tarih + kaynak ayrıklığı)
  H49 : **iki bağımsız merceğin yargısı** — prosopografi (isim/nesep/künye/
        nisbe çözümlemesi) + çürütme (ayrı kişi olduğunu göstermeye çalışan).
        Yalnız İKİSİ DE "aynı kişi" demiş kümeler birleşir.

NEDEN YARGI ŞART: küme ölçütü tek başına yetmiyor. Ölçüldü (664 karar):
    kesin  n=150 → 0 yanlış
    olası  n=484 → 72 yanlış (%14)
    zayıf  n= 30 → 15 yanlış (%50)
Yargı, otomatik ölçütün yakalayamadığı gerçek prosopografi hatalarını buldu:
  • Hz. Ali kümesine KIZI "Ümmü Külsûm bint Ali" karışmıştı
  • Halife el-Mehdî ile OĞLU el-Hâdî aynı kümedeydi
  • Filozof el-Kindî ile muhaddis Ebû Saîd el-Eşec el-Kindî — ortak olan
    yalnız KABİLE nisbesiydi
  • Sâlim mevlâ Ebî Huzeyfe ile EFENDİSİ Ebû Huzeyfe b. Utbe

BİRLEŞTİRME = YUMUŞAK-SİLME + YÖNLENDİRME (H22 deseni, aynen):
  kazanan  : kümenin EN ZENGİN kaydı (alan sayısı > kaynak sayısı > küçük pid)
  kaybeden : provenance.deprecated = true
             provenance.deprecated_in_favor_of = <kazanan pid>
             record_history'ye gerekçe + yargı kimliği
  Kaybedenin PID'İ YAŞAMAYA DEVAM EDER (atıf istikrarı); tüketici
  `deprecated_in_favor_of` ile kazanana yönlenir. projector zaten deprecated
  kayıtlara -100 verir, yani aramada mükerrer görünmez.

HİÇBİR ALAN SİLİNMEZ, hiçbir dosya kaldırılmaz. Referans göçü YAPILMAZ —
eski pid canlı kaldığı için kırık bağ oluşmaz (H22 kararı, aynen sürdürülür).

Geri alma: --restore (ledger'dan tam geri dönüş).

Usage:
  python3 pipelines/migrations/h49_001_cluster_merge.py --dry-run
  python3 pipelines/migrations/h49_001_cluster_merge.py
  python3 pipelines/migrations/h49_001_cluster_merge.py --restore
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERSON_DIR = REPO / "data" / "canonical" / "person"
JUDGE = REPO / "data" / "_state" / "person_cluster_judgments.json"
LEDGER = REPO / "data" / "_state" / "h49_cluster_merge.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def path_of(num: int) -> Path:
    return PERSON_DIR / f"iac_person_{num:08d}.json"


def load(num: int):
    p = path_of(num)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def save(num: int, rec) -> None:
    path_of(num).write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")


def zenginlik(rec) -> tuple:
    """Kazanan seçimi: en çok alan > en çok kaynak curie > küçük pid.

    'En zengin' ölçütü kasıtlı: kazanan, kaybedenin taşıdığı bilgiyi zaten
    büyük ölçüde içerir; böylece yönlendirme bilgi kaybı gibi görünmez.
    """
    alan = sum(1 for k, v in rec.items() if v not in (None, "", [], {}))
    curie = len((rec.get("provenance") or {}).get("source_curies") or [])
    if not curie:
        curie = len(rec.get("derived_from_layers") or [])
    return (alan, curie)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()

    if a.restore:
        if not LEDGER.is_file():
            print("ledger yok — geri alınacak bir şey yok")
            return
        led = json.loads(LEDGER.read_text(encoding="utf-8"))
        geri = 0
        for m in led["merges"]:
            for kayb in m["kaybedenler"]:
                num = int(kayb.rsplit("-", 1)[-1])
                rec = load(num)
                if not rec:
                    continue
                prov = rec.get("provenance") or {}
                prov.pop("deprecated", None)
                prov.pop("deprecated_in_favor_of", None)
                hist = prov.get("record_history") or []
                prov["record_history"] = [h for h in hist
                                          if "[h49_001]" not in (h.get("note") or "")]
                rec["provenance"] = prov
                save(num, rec)
                geri += 1
        LEDGER.unlink()
        print(f"geri alındı: {geri} kayıt · ledger silindi")
        return

    if not JUDGE.is_file():
        print("yargı defteri yok — önce küme yargısı koşulmalı")
        return
    yargi = json.loads(JUDGE.read_text(encoding="utf-8"))["kararlar"]

    merges = []
    atlanan = {"karar_evet_degil": 0, "dosya_yok": 0, "zaten_deprecated": 0}
    for kid, v in sorted(yargi.items()):
        if v.get("karar") != "evet":
            atlanan["karar_evet_degil"] += 1
            continue
        nums = [int(x) for x in kid.split("-")]
        kayitlar = {n: load(n) for n in nums}
        if any(r is None for r in kayitlar.values()):
            atlanan["dosya_yok"] += 1
            continue
        if any((r.get("provenance") or {}).get("deprecated") for r in kayitlar.values()):
            atlanan["zaten_deprecated"] += 1
            continue
        kazanan = max(nums, key=lambda n: (*zenginlik(kayitlar[n]), -n))
        kaybedenler = [n for n in nums if n != kazanan]
        merges.append({
            "kume_id": kid,
            "kazanan": f"iac:person-{kazanan:08d}",
            "kaybedenler": [f"iac:person-{n:08d}" for n in kaybedenler],
            "gerekce": v.get("gerekce_a") or v.get("gerekce_b"),
            "guven_girdi": v.get("guven_girdi"),
        })

    print(f"yargı defteri     : {len(yargi)} karar")
    print(f"birleştirilecek   : {len(merges)} küme")
    print(f"  yumuşak-silinen : {sum(len(m['kaybedenler']) for m in merges)} kayıt")
    print(f"  atlanan         : {atlanan}")
    if a.dry_run:
        for m in merges[:3]:
            print(f"    {m['kazanan']} ← {m['kaybedenler']}")
        print("(--dry-run: yazılmadı)")
        return

    yazilan = 0
    for m in merges:
        for kayb in m["kaybedenler"]:
            num = int(kayb.rsplit("-", 1)[-1])
            rec = load(num)
            prov = rec.setdefault("provenance", {})
            prov["deprecated"] = True
            prov["deprecated_in_favor_of"] = m["kazanan"]
            prov.setdefault("record_history", []).append({
                "change_type": "update",
                "changed_at": NOW,
                "changed_by": ATTRIBUTED_TO,
                # ŞEMA NOTU: record_history additionalProperties:false — özel alan
                # EKLENEMEZ. (H31'de aynı ders alınmıştı: `change_type: "repair"`
                # de reddedilmişti. Şemayı değiştirmek yerine bilgiyi note'a göm.)
                "note": (f"[h49_001] Aynı kişi kümesi ({m['kume_id']}) iki bağımsız mercekle "
                         f"(prosopografi + çürütme) yargılandı ve 'aynı kişi' kararı "
                         f"verildi; {m['kazanan']} lehine yumuşak-silindi. "
                         f"Gerekçe: {m['gerekce']}"),
            })
            save(num, rec)
            yazilan += 1

    # LEDGER KÜMÜLATİF: yeni tur öncekini EZMEZ. Ölçüldü — ikinci tur ledger'ı
    # üzerine yazınca ilk turun 468 birleştirmesi kaydı kayboldu ve --restore
    # onları geri alamaz hâle geldi. Geri alma yolu, kaydın bütünlüğüne bağlıdır.
    onceki = []
    if LEDGER.is_file():
        onceki = json.loads(LEDGER.read_text(encoding="utf-8")).get("merges", [])
    var = {m["kume_id"] for m in onceki}
    merges = onceki + [m for m in merges if m["kume_id"] not in var]

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps({
        "_doc": ("H49 küme birleştirmesi — YUMUŞAK-SİLME + YÖNLENDİRME. Kaybeden "
                 "pid'ler YAŞAMAYA DEVAM EDER (atıf istikrarı); yalnız deprecated "
                 "işaretlenir ve kazanana yönlendirilir. Geri alma: --restore."),
        "olcut": ("iki bağımsız merceğin (prosopografi + çürütme) mutabakatla "
                  "'aynı kişi' demesi. Ölçüm: kesin katmanda 150/150 doğru, "
                  "olası katmanda %14, zayıf katmanda %50 yanlış çıkmıştı — "
                  "yargı bu yüzden şart."),
        "merged_at": NOW,
        "n_kume": len(merges),
        "n_deprecated": yazilan,
        "merges": merges,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {yazilan} kayıt yumuşak-silindi · ledger {LEDGER.relative_to(REPO)}")
    print("sıradaki: make view-data (havuz/köprü/küme yeniden üretilmeli)")


if __name__ == "__main__":
    main()
