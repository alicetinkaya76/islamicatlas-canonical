#!/usr/bin/env python3
"""Mekke Şehir Atlası üreticisi — Ezrakî'nin Ahbâru Mekke'sinden (H25).

NEDEN AYRI BİR ÜRETİCİ / NEDEN KONYA GİBİ DEĞİL
------------------------------------------------
Konya ve Kahire şehir atlasları MODERN SAHA ÖLÇÜMÜ koordinatları taşır
(location.lat/lng, sokak düzeyi). Ezrakî (ö. 250/864) ise Mekke'yi GÖRELİ
tarif eder: "Safâ tarafında, mescit duvarına bitişik; aralarında ancak bir
adamın yan geçebileceği kadar boşluk; doğu köşeleri arası ~7 zirâ". Bunlar
ortaçağ göreli topografyasıdır, modern koordinat DEĞİLDİR.

Bu yüzden Ezrakî'nin canonical INSTITUTION kayıtları (633) BİLEREK koordinatsız
mint edildi (yalnız located_in Mekke). Modern iğne-haritası zorlamak SAHTE
HASSASİYET üretirdi — projenin kaçındığı tam da bu (bkz. CLAUDE.md "north star:
never fabricate"). Ölçülen kanıt: kitabın okuma-katmanındaki 808 özellikten
yalnız 199'u bir canonical PLACE'e çözülüp koordinat aldı; bunların da sadece
109'u Mekke bölgesine düşüyor (kalan 90 = aynı adlı homonim, yanlış çözüm) ve
"yakın" olanlar bile sokak hassasiyetinde değil (Ebû Kubeys ~40 km sapmış).

DÜRÜST TASARIM (H25 Karar-1)
----------------------------
- Kaynak = kitabın okuma-katmanı atlası (reading/00001848/layer.json, 808
  özellik; canonical 633 institution da BUNDAN mint edildi).
- HARİTA: yalnız Mekke bölge kutusuna düşen koordinatlar iğnelenir (~109);
  koordinat "varlık-çözümlü, yaklaşık" olarak işaretlenir (uydurma yok).
- LİSTE: 808'in tamamı yan panelde (kategoriye göre süzülebilir); koordinatsız
  ~699 kayıt Ezrakî'nin göreli tarifi + Arapça pasaj + bölüm künyesiyle görünür.
- Registry altbaşlığı FARKI AÇIKÇA söyler: "göreli topografya, modern ölçüm
  değil" → okur Konya/Kahire ile aynı sanmaz.

Çıktı: web/public/view-data/city-atlas/mecca.json  (gitignored; build'de üretilir)
Şema: CityAtlas kayıt sözleşmesi (category/period/current_status/name_*/location/
      source_excerpt_ar/source_line) — CityAtlasView.jsx & CityAtlasDetail.jsx
      hiç değişmeden okur.

Determinizm: girdi aynıysa çıktı bayt-bayt aynı (timestamp yok; seq'e göre sıralı).
Çalıştırma: python3 pipelines/frontend/build_mecca_atlas.py
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
READING = REPO / "web" / "public" / "reading" / "00001848" / "layer.json"
OUT = REPO / "web" / "public" / "view-data" / "city-atlas" / "mecca.json"

# Mekke bölge kutusu — koordinat İĞNELEME kapısı. Bölge düzeyi (±~0.9°),
# çünkü çözümlü koordinatlar sokak değil bölge hassasiyetinde; kutu dışına
# düşen (yanlış homonim çözümü) koordinatlar İĞNELENMEZ ama kayıt listede kalır.
MECCA_BOX = {"lat0": 20.5, "lat1": 22.3, "lon0": 39.0, "lon1": 40.6}

# reading `type` → CityAtlas kategori anahtarı (registry'deki categories ile birebir).
# Ezrakî'nin özellik türleri; hepsi registry'de renk/ikon/etiketle tanımlı.
TYPE_TO_CAT = {
    "mountain": "mountain",
    "house": "house",
    "well": "well",
    "mosque": "mosque",
    "monument": "monument",
    "gate": "gate",
    "quarter": "quarter",
    "marker": "marker",
    "boundary_marker": "boundary_marker",
    "cemetery": "cemetery",
    "other": "other",
}


def in_mecca(lat, lon) -> bool:
    return (lat is not None and lon is not None
            and MECCA_BOX["lat0"] <= lat <= MECCA_BOX["lat1"]
            and MECCA_BOX["lon0"] <= lon <= MECCA_BOX["lon1"])


def build():
    d = json.loads(READING.read_text(encoding="utf-8"))
    recs = d["records"]

    out = []
    pinned = 0
    coord_dropped = 0  # koordinatı var ama Mekke kutusu dışında (yanlış homonim)
    for r in recs:
        seq = r.get("seq")
        name_tr = r.get("name_tr") or r.get("name_ar") or "(adsız)"
        cat = TYPE_TO_CAT.get(r.get("type", "other"), "other")

        # Koordinat kapısı: yalnız Mekke kutusundakiler iğnelenir.
        lat, lon = r.get("lat"), r.get("lon")
        location = {}
        if r.get("summary_tr"):
            # Ezrakî'nin göreli tarifi/özeti → detay panelinde "Konum" bölümü
            location["description_tr"] = r["summary_tr"]
        if in_mecca(lat, lon):
            location["lat"] = round(lat, 5)
            location["lng"] = round(lon, 5)  # CityAtlasMap 'lng' okur (lon değil)
            # Konum kaynağı: varlık çözümü (place_pid), saha ölçümü değil → dürüst etiket
            location["geocoding_confidence"] = "varlık-çözümlü ~"
            pinned += 1
        elif lat is not None and lon is not None:
            coord_dropped += 1

        rec = {
            "id": f"azraqi_{seq}",
            "name_tr": name_tr,
            "name_ar": r.get("name_ar", ""),
            "category": cat,
            "period": "belirsiz",         # Ezrakî'nin Mekke'si büyük ölçüde tarihsiz/tesisî
            "current_status": "belirsiz",  # mevcut/yıkılmış güvenle türetilemez
            "location": location,
            "_sec": r.get("sec"),          # kitapta oku köprüsü için (gelecek yetenek)
            "_place_pid": r.get("place_pid"),
        }
        if r.get("quote_ar"):
            rec["source_excerpt_ar"] = r["quote_ar"]           # → "Kaynak Metin"
            rec["source_line"] = f"§{r.get('sec')} {r.get('page', '')}".strip()
        out.append(rec)

    # Determinizm: seq'e göre sırala (seq yoksa id sonuna at)
    out.sort(key=lambda x: (x.get("_sec") is None, x.get("_sec") or 0, x["id"]))
    return out, {"total": len(out), "pinned": pinned, "coord_dropped": coord_dropped}


def main():
    records, stats = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  toplam kayıt : {stats['total']}")
    print(f"  haritada iğne: {stats['pinned']}  (Mekke bölge kutusu içi, yaklaşık)")
    print(f"  koordinat düşürülen (kutu dışı homonim): {stats['coord_dropped']}")
    print(f"  koordinatsız (yalnız göreli tarif): "
          f"{stats['total'] - stats['pinned'] - stats['coord_dropped']}")


if __name__ == "__main__":
    main()
