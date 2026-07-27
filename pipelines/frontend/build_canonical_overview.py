#!/usr/bin/env python3
"""Canonical mağaza ÖZETİ üreticisi (H28) — Pano/Analiz'in canonical'laşması için.

SORUN (denetim bulgusu): Pano "Genel Bakış" v1 db.json .length (âlim 450, savaş
100) ile v2 SOURCE_COUNTS'u (13.844) ETİKETSİZ karıştırıyor; 67k+ kayıtlık
canonical mağaza Pano/Analiz'de HİÇ görünmüyor. Bu üretici, mağazanın GERÇEK
ölçeğini (namespace sayıları + Ulema Havuzu + kitap-türevi olaylar) tek küçük
JSON'a yazar; Dashboard bunu AYRI, etiketli "Merkezî Defter" bölümünde gösterir.

Elle sayı YOK — hepsi bu koşunun taramasından. Aktif = provenance.deprecated
DEĞİL (emekli/yumuşak-silinmiş kayıt sayılmaz; projeksiyon -100 verir).

Çıktı: web/src/data/canonical_overview.json (source_counts.json gibi bundle'lanır)
Determinizm: girdi aynıysa çıktı aynı (timestamp yok).
Çalıştırma: python3 pipelines/frontend/build_canonical_overview.py
"""

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
ULEMA = REPO / "web" / "public" / "books" / "ulema_pool.json"
CEVENTS = REPO / "web" / "public" / "view-data" / "canonical_events.json"
OUT = REPO / "web" / "src" / "data" / "canonical_overview.json"

NAMESPACES = ["person", "place", "work", "dynasty", "event", "institution"]


def count_active(ns: str) -> int:
    """Aktif (emekli olmayan) kayıt sayısı. Hız için ham metinde deprecated
    işaretini arar; işaret varsa JSON'u açıp doğrular (yanlış-pozitif önlenir)."""
    n = 0
    for f in glob.glob(str(CANON / ns / "*.json")):
        txt = Path(f).read_text(encoding="utf-8")
        if '"deprecated"' in txt:
            try:
                if json.loads(txt).get("provenance", {}).get("deprecated"):
                    continue
            except json.JSONDecodeError:
                pass
        n += 1
    return n


def build() -> dict:
    store = {ns: count_active(ns) for ns in NAMESPACES}
    store_total = sum(store.values())

    ulema = None
    if ULEMA.is_file():
        d = json.loads(ULEMA.read_text(encoding="utf-8"))
        ulema = d.get("n") or len(d.get("kisiler", []))

    ce_places = ce_events = None
    if CEVENTS.is_file():
        d = json.loads(CEVENTS.read_text(encoding="utf-8"))
        ce_places = len(d)
        ce_events = sum(r.get("count", 0) for r in d)

    return {
        "generated_by": "pipelines/frontend/build_canonical_overview.py",
        "note": ("ELLE DÜZENLEMEYİN — canonical mağaza taramasından üretilir. "
                 "Aktif = emekli olmayan kayıt. Pano/Analiz 'Merkezî Defter' "
                 "bölümü buradan beslenir."),
        "store": {**store, "total": store_total},
        "ulema_pool": ulema,
        "canonical_events": {"events": ce_events, "places": ce_places},
    }


def main():
    out = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    s = out["store"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  mağaza TOPLAM aktif: {s['total']:,}".replace(",", "."))
    for ns in NAMESPACES:
        print(f"    {ns:<12} {s[ns]:>7,}".replace(",", "."))
    print(f"  ulema havuzu: {out['ulema_pool']}")
    print(f"  canonical olay: {out['canonical_events']['events']} "
          f"({out['canonical_events']['places']} yer)")


if __name__ == "__main__":
    main()
