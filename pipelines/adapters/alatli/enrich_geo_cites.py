#!/usr/bin/env python3
"""Alatlı: upstream'den KOORDİNAT + CİLT/SAYFA ATFI aktarımı (H32).

Senkronik atlasın iki eksiği vardı (H30/H31 journal'ında dürüstçe kayıtlı):
  - harita YOK  → repoda koordinat yoktu (uydurulmadı)
  - "kaynağa in" YOK → repoda cilt/sayfa atfı yoktu

Upstream (`~/Desktop/alev_alatlı/corpus_json/app_data.json`) ikisini de taşıyor:
koordinat 522/677, atıf 677/677. Bu script yalnız BU İKİ ALANI repoya sidecar
olarak aktarır.

TELİF SINIRI (bilinçli, ADR/H25 kapısıyla tutarlı)
    ALINAN : place.lat/lon (olgu — Wikidata/coğrafi), cites[].vol + book_page +
             pdf_page + role + text (BİBLİYOGRAFİK KÜNYE — eser adı/yayınevi/yıl,
             olgusal atıf bilgisi).
    ALINMAYAN: `desc` (açıklama düzyazısı olabilir). ALATLI_TELIF_KAPISI.md'nin
             "store'da Alatlı düzyazısı YOK — hiç pasaj alınmadı" ilkesi
             korunur. Gerekirse ileride Wikidata'dan (CC0) alınır.
    Sidecar da Alatlı katmanındadır → yayın kapısı (`alatli`) aynen geçerli.

Çıktı: data/sources/alatli/_alatli_geo_cites.json   { alatli_id: {place, cites} }
Determinizm: id sıralı; timestamp yok.
Çalıştırma: python3 pipelines/adapters/alatli/enrich_geo_cites.py [--src PATH]
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "sources" / "alatli" / "_alatli_geo_cites.json"
DEFAULT_SRC = Path.home() / "Desktop" / "alev_alatlı" / "corpus_json" / "app_data.json"

CITE_KEYS = ("vol", "book_page", "pdf_page", "role", "text")


def build(src: Path) -> dict:
    data = json.loads(src.read_text(encoding="utf-8"))
    people = data.get("people") or []
    out: dict[str, dict] = {}
    n_geo = n_cite = 0
    for p in people:
        pid = p.get("id")
        if not pid:
            continue
        rec: dict = {}
        place = p.get("place") or {}
        lat, lon = place.get("lat"), place.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            rec["place"] = {
                "label": place.get("label"),
                "lat": round(float(lat), 5),
                "lon": round(float(lon), 5),
            }
            n_geo += 1
        cites = [
            {k: c.get(k) for k in CITE_KEYS if c.get(k) is not None}
            for c in (p.get("cites") or []) if isinstance(c, dict)
        ]
        if cites:
            rec["cites"] = cites
            n_cite += 1
        if rec:
            out[pid] = rec
    doc = {
        "_doc": ("Alatlı upstream'inden aktarılan KOORDİNAT + CİLT/SAYFA ATFI. "
                 "`desc` BİLEREK alınmadı (düzyazı olabilir; telif kapısı ilkesi: "
                 "store'da Alatlı pasajı yok). Üretici: "
                 "pipelines/adapters/alatli/enrich_geo_cites.py"),
        "_source": str(src),
        "_counts": {"kayit": len(out), "koordinatli": n_geo, "atifli": n_cite},
        "records": {k: out[k] for k in sorted(out)},
    }
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    a = ap.parse_args()
    if not a.src.is_file():
        raise SystemExit(f"upstream bulunamadı: {a.src}")
    doc = build(a.src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    c = doc["_counts"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  kayıt: {c['kayit']} · koordinatlı: {c['koordinatli']} · atıflı: {c['atifli']}")


if __name__ == "__main__":
    main()
