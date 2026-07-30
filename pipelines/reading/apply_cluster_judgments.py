#!/usr/bin/env python3
"""Küme yargılarını kalıcı karar defterine işler (H48).

AKIŞ
    yargı turu (workflow) → bu script → data/_state/person_cluster_judgments.json
    → build_person_clusters.py → arayüz

NE YAPAR: yeni kararları mevcut deftere EKLER, çakışanları raporlar, kalibrasyon
sayımlarını yeniden hesaplar.

NE YAPMAZ: HİÇBİR KAYDI BİRLEŞTİRMEZ. Bu defter yalnız kümenin arayüzde
gösterilip gösterilmeyeceğini ve hangi etiketle gösterileceğini belirler.
Gerçek birleştirme (kazanan pid seçimi, alan taşıma, kaybeden pid'in
yumuşak-silinmesi) tarihçi oturumudur — ADR-008 Tier-3.

ÇAKIŞMA KURALI: aynı küme için önceki karar 'evet', yeni karar 'hayır' ise
(ya da tersi) karar SESSİZCE DEĞİŞTİRİLMEZ; çakışma raporlanır ve kayıt
'belirsiz'e düşer. İki bağımsız turun çeliştiği yerde kesinlik iddia edilemez.

Kullanım:
    python3 pipelines/reading/apply_cluster_judgments.py <workflow_output.json>
    python3 pipelines/reading/apply_cluster_judgments.py <dosya> --dry-run
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
JUDGE = REPO / "data" / "_state" / "person_cluster_judgments.json"

VALID = {"evet", "hayir", "belirsiz"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("kararlar", help="workflow çıktısı (sonuc alanı içeren JSON)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = json.loads(Path(a.kararlar).read_text(encoding="utf-8"))
    yeni = raw.get("sonuc") or raw.get("result", {}).get("sonuc") or {}
    if not yeni:
        print("HATA: girdi dosyasında 'sonuc' yok")
        return

    defter = {"_doc": "", "kararlar": {}}
    if JUDGE.is_file():
        defter = json.loads(JUDGE.read_text(encoding="utf-8"))
    mevcut = defter.setdefault("kararlar", {})

    eklenen = ayni = celisik = gecersiz = 0
    celiskiler = []
    for kid, v in yeni.items():
        karar = (v or {}).get("karar")
        if karar not in VALID:
            gecersiz += 1
            continue
        onceki = (mevcut.get(kid) or {}).get("karar")
        if onceki is None:
            mevcut[kid] = v
            eklenen += 1
        elif onceki == karar:
            ayni += 1
        else:
            # İki tur çelişti → kesinlik iddia edilemez, 'belirsiz'e düşer.
            celisik += 1
            celiskiler.append(f"{kid}: {onceki} → {karar}")
            mevcut[kid] = {**v, "karar": "belirsiz",
                           "basis": f"turlar çelişti ({onceki} vs {karar})"}

    # Kalibrasyonu yeniden hesapla — eşiğin gerekçesi budur, bayatlamamalı.
    kalib = {}
    for v in mevcut.values():
        g = v.get("guven_girdi")
        if not g:
            continue
        kalib.setdefault(g, {"evet": 0, "hayir": 0, "belirsiz": 0})
        kalib[g][v["karar"]] += 1
    defter["guven_isabeti"] = kalib
    defter["toplam_karar"] = len(mevcut)
    defter["_doc"] = ("Kişi kümesi yargıları — iki bağımsız mercek (prosopografi + "
                      "çürütme), mutabakat yoksa 'belirsiz'. BİRLEŞTİRME DEĞİLDİR; "
                      "yalnız kümenin arayüzde gösterimini belirler. "
                      "Üretici: apply_cluster_judgments.py")

    print(f"yeni karar dosyası : {Path(a.kararlar).name} ({len(yeni)} kayıt)")
    print(f"  eklenen          : {eklenen}")
    print(f"  zaten aynı       : {ayni}")
    if celisik:
        print(f"  ÇELİŞEN          : {celisik} → 'belirsiz'e düşürüldü")
        for c in celiskiler[:5]:
            print(f"      {c}")
    if gecersiz:
        print(f"  geçersiz         : {gecersiz}")
    print(f"defter toplamı     : {len(mevcut)} karar")
    print(f"kalibrasyon        : {kalib}")

    if a.dry_run:
        print("(--dry-run: yazılmadı)")
        return
    JUDGE.parent.mkdir(parents=True, exist_ok=True)
    JUDGE.write_text(json.dumps(defter, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {JUDGE.relative_to(REPO).as_posix()}")
    print("sıradaki: python3 pipelines/frontend/build_person_clusters.py")


if __name__ == "__main__":
    main()
