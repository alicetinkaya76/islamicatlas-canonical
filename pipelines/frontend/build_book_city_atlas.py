#!/usr/bin/env python3
"""Kitap → Şehir Atlası üreticisi — config-güdümlü (H25 ölçekleme).

build_mecca_atlas.py'nin genelleştirilmiş hâli. Şehir-topografyası anlatan
her kitap (reading/<pid>/layer.json kind=structures) için CityAtlas kaydı
üretir. Yeni bir şehir eklemek = CITIES'e bir satır + registry girişi.

NEDEN BÖYLE (bkz. build_mecca_atlas.py'nin uzun notu — silindi, buraya taşındı):
Ortaçağ şehir tarihleri (Ezrakî/Hatîb/İbn Asâkir) yapıları GÖRELİ tarif eder,
modern koordinat vermez. Kitabın canonical institution kayıtları koordinatsız
(located_in <şehir>). Okuma-katmanındaki koordinatlar, anılan varlığın bir
canonical PLACE'e çözülmesinden gelir (Tier-2) — hepsi doğru değil (aynı adlı
homonim başka yere düşer). Bu yüzden:
  - HARİTA: yalnız şehir BÖLGE KUTUSUNA düşen + geo_suspect OLMAYAN koordinat
    iğnelenir; konum "varlık-çözümlü, yaklaşık" etiketli (SAHTE HASSASİYET YOK).
  - LİSTE: kaydın tamamı; koordinatsız/kutu-dışı olanlar göreli tarif + Arapça
    pasajla görünür.
  - Registry altbaşlığı farkı açıkça söyler (modern ölçüm değil).

Çıktı: web/public/view-data/city-atlas/<city_id>.json (gitignored; build'de üretilir)
Şema: CityAtlas kayıt sözleşmesi — CityAtlasView/Detail konya/cairo gibi okur.
Determinizm: girdi aynıysa çıktı bayt-bayt aynı.
Çalıştırma: python3 pipelines/frontend/build_book_city_atlas.py
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
READING = REPO / "web" / "public" / "reading"
OUTDIR = REPO / "web" / "public" / "view-data" / "city-atlas"

# Şehir-topografyası kitapları. Kutu = koordinat İĞNELEME kapısı (bölge düzeyi;
# çözümlü koordinatlar sokak değil bölge hassasiyetinde). id_prefix bilimsel
# müellif kısaltması (kayıt id'leri anlamlı kalsın). Yeni şehir = yeni satır.
CITIES = [
    {"city_id": "mecca",    "pidnum": "00001848", "id_prefix": "azraqi",
     "box": {"lat0": 20.5, "lat1": 22.3, "lon0": 39.0, "lon1": 40.6}},
    {"city_id": "baghdad",  "pidnum": "00000261", "id_prefix": "khatib",
     "box": {"lat0": 32.1, "lat1": 34.5, "lon0": 43.2, "lon1": 45.6}},
    {"city_id": "damascus", "pidnum": "00000228", "id_prefix": "ibnasakir",
     "box": {"lat0": 32.3, "lat1": 34.7, "lon0": 35.1, "lon1": 37.5}},
]


def in_box(lat, lon, b) -> bool:
    return (lat is not None and lon is not None
            and b["lat0"] <= lat <= b["lat1"] and b["lon0"] <= lon <= b["lon1"])


def build_city(cfg):
    layer = json.loads((READING / cfg["pidnum"] / "layer.json").read_text(encoding="utf-8"))
    recs = layer["records"]
    out, pinned, dropped = [], 0, 0
    for r in recs:
        seq = r.get("seq")
        location = {}
        if r.get("summary_tr"):
            location["description_tr"] = r["summary_tr"]   # göreli tarif → "Konum"
        lat, lon = r.get("lat"), r.get("lon")
        # İĞNELEME kapısı: bölge kutusunda VE geo_suspect değil (uydurma yok)
        if in_box(lat, lon, cfg["box"]) and not r.get("geo_suspect"):
            location["lat"] = round(lat, 5)
            location["lng"] = round(lon, 5)   # CityAtlasMap 'lng' okur
            location["geocoding_confidence"] = "varlık-çözümlü ~"
            pinned += 1
        elif lat is not None and lon is not None:
            dropped += 1

        rec = {
            "id": f"{cfg['id_prefix']}_{seq}",
            "name_tr": r.get("name_tr") or r.get("name_ar") or "(adsız)",
            "name_ar": r.get("name_ar", ""),
            "category": r.get("type", "other"),   # registry kategori anahtarıyla birebir
            "period": "belirsiz",                  # ortaçağ şehir tarihi: büyük ölçüde tarihsiz
            "current_status": "belirsiz",
            "location": location,
            "_sec": r.get("sec"),
            "_place_pid": r.get("place_pid"),
        }
        if r.get("builder_ar"):
            rec["patron"] = {"name": r["builder_ar"]}   # Bâni → detay panelinde
        if r.get("quote_ar"):
            rec["source_excerpt_ar"] = r["quote_ar"]     # → "Kaynak Metin"
            rec["source_line"] = f"§{r.get('sec')} {r.get('page', '')}".strip()
        out.append(rec)

    out.sort(key=lambda x: (x.get("_sec") is None, x.get("_sec") or 0, x["id"]))
    return out, {"total": len(out), "pinned": pinned, "dropped": dropped}


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for cfg in CITIES:
        records, st = build_city(cfg)
        outp = OUTDIR / f"{cfg['city_id']}.json"
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"{cfg['city_id']:<10} yazıldı: toplam {st['total']:>4} · "
              f"iğne {st['pinned']:>4} (bölge içi) · kutu-dışı homonim {st['dropped']:>3} · "
              f"koordinatsız {st['total'] - st['pinned'] - st['dropped']:>4}")


if __name__ == "__main__":
    main()
