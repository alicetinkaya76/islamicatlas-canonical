#!/usr/bin/env python3
"""source_counts.json üretici — sitedeki kaynak rozetlerinin GERÇEK sayıları.

Sorun:
    App.jsx / Dashboard.jsx / LandingPage.jsx içindeki rozet sayıları elle
    yazılmış ("13.9K", "1,020", "17"...) ve veriden kopmuş durumda. Bu script
    her kaynağın kayıt sayısını web/public/data/ ve web/public/reading/
    altındaki gerçek dosyalardan SAYAR — tahmin/uydurma yok.

Çıktı:
    web/src/data/source_counts.json
        {
          "generated_by": "pipelines/frontend/build_source_counts.py",
          "note": "...",
          "sources": {
            "<anahtar>": {
              "count":  <int|null>,   # ham sayı; kısaltma YOK (gösterim JSX işi)
              "detail": {...}|null,   # alt kırılım (varsa)
              "files":  [...],        # sayımın dayandığı dosyalar (repo-göreli)
              "status": "ok" | "missing" | "bundle"
            }, ...
          },
          "source_files": [...]       # kullanılan tüm dosyaların birleşik listesi
        }

Sayım kuralları (kaynak → ölçülen şey):
    yaqut      yaqut_lite.json                 liste uzunluğu (yer)
    alam       alam_lite.json                  liste uzunluğu (biyografi)
    dia        dia_lite.json                   liste uzunluğu (madde)
    ei1        ei1_lite.json                   liste uzunluğu (madde)
    rihla      ibn_battuta_atlas_layer.json    travel_stops (durak)
    khitat     maqrizi_khitat_atlas_layer.json structures (yapı)
    lestrange  le_strange_eastern_caliphate.json  liste uzunluğu (coğrafi kayıt)
    cityatlas  data/city-atlas/*.json          şehir dosyalarının toplamı (yapı)
    darpislam  darpislam_lite.json             mints (geokodlu darphane; metadata
                                               total_mints ham toplamı detail'de)
    salibiyyat salibiyyat_atlas_layer.json     events (olay; *_backup sayılmaz)
    evliya     evliya_atlas_layer.json         places (durak/yer)
    science    science_layer.json              scholars (âlim; alt sayılar detail'de)
    muqaddasi  muqaddasi_atlas_layer.json      places (yerleşim)
    battles    public/data'da savaş dosyası yok → src/data/db.json "battles"
               (status="bundle": veri fetch edilen bir dosya değil, JS bundle içinde)
    library    reading/core_shelf.json         books (kitap)

Eksik dosyada sayı UYDURULMAZ: count=null, status="missing".

Determinizm: girdi aynıysa çıktı bayt-bayt aynıdır (timestamp yok, anahtarlar
sabit sırada, sort_keys kullanılmaz — sözlükler zaten sabit sırayla kurulur).
Çalıştırma:  python3 pipelines/frontend/build_source_counts.py
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "web" / "public" / "data"
READING = REPO / "web" / "public" / "reading"
DB_JSON = REPO / "web" / "src" / "data" / "db.json"
OUT = REPO / "web" / "src" / "data" / "source_counts.json"


def rel(p: Path) -> str:
    """Repo köküne göreli, POSIX ayraçlı yol (çıktı metadatası için)."""
    return p.relative_to(REPO).as_posix()


def load(p: Path):
    """JSON yükle; dosya yoksa None döndür (sayı uydurmak yerine 'missing')."""
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def fmt(n) -> str:
    """Konsol özeti için binlik ayraçlı HAM sayı (13940 → '13.940').
    Kısaltma ("13,9K" vb.) bilerek YOK — gösterim biçimlendirmesi JSX işi."""
    if n is None:
        return "—"
    return f"{n:,}".replace(",", ".")


def entry(count, detail, files, status="ok"):
    return {"count": count, "detail": detail, "files": files, "status": status}


def count_list_file(name: str, unit: str):
    """Düz liste JSON'u: uzunluğu say."""
    p = DATA / name
    d = load(p)
    if d is None:
        return entry(None, None, [rel(p)], "missing")
    return entry(len(d), {"unit": unit}, [rel(p)])


def build() -> dict:
    sources = {}

    # --- düz liste dosyaları -------------------------------------------------
    sources["yaqut"] = count_list_file("yaqut_lite.json", "yer")
    sources["alam"] = count_list_file("alam_lite.json", "biyografi")
    sources["dia"] = count_list_file("dia_lite.json", "madde")
    sources["ei1"] = count_list_file("ei1_lite.json", "madde")
    sources["lestrange"] = count_list_file(
        "le_strange_eastern_caliphate.json", "coğrafi kayıt")

    # --- rihla: travel_stops -------------------------------------------------
    p = DATA / "ibn_battuta_atlas_layer.json"
    d = load(p)
    if d is None:
        sources["rihla"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["rihla"] = entry(
            len(d["travel_stops"]),
            {"unit": "durak",
             "travelers": len(d.get("travelers", [])),
             "voyages": len(d.get("travel_voyages", []))},
            [rel(p)])

    # --- khitat: structures --------------------------------------------------
    p = DATA / "maqrizi_khitat_atlas_layer.json"
    d = load(p)
    if d is None:
        sources["khitat"] = entry(None, None, [rel(p)], "missing")
    else:
        cats = d.get("categories", {})
        sources["khitat"] = entry(
            len(d["structures"]),
            {"unit": "yapı", "categories": len(cats)},
            [rel(p)])

    # --- cityatlas: city-atlas/*.json toplamı --------------------------------
    city_dir = DATA / "city-atlas"
    city_files = sorted(city_dir.glob("*.json")) if city_dir.is_dir() else []
    if not city_files:
        sources["cityatlas"] = entry(None, None, [rel(city_dir)], "missing")
    else:
        per_city, total = {}, 0
        for cf in city_files:
            d = load(cf)
            n = len(d) if isinstance(d, list) else None
            per_city[cf.stem] = n
            total += n or 0
        sources["cityatlas"] = entry(
            total,
            {"unit": "yapı", "per_city": per_city,
             # H19: dürüstlük notu — cairo.json, maqrizi/khitat katmanının
             # zengin formu (AYNI 801 yapı); kaynaklar-arası TOPLAM alınırken
             # khitat ile çifte sayılmamalı.
             "overlap": {"cairo": "khitat (aynı 801 yapı)"}},
            [rel(cf) for cf in city_files])

    # --- darpislam: mints ----------------------------------------------------
    p = DATA / "darpislam_lite.json"
    d = load(p)
    if d is None:
        sources["darpislam"] = entry(None, None, [rel(p)], "missing")
    else:
        meta = d.get("metadata", {})
        sources["darpislam"] = entry(
            len(d["mints"]),
            {"unit": "darphane (geokodlu, haritada gösterilen)",
             "metadata_total_mints": meta.get("total_mints"),
             "metadata_geocoded": meta.get("geocoded"),
             "metadata_total_emissions": meta.get("total_emissions")},
            [rel(p)])

    # --- salibiyyat: events (backup dosyası SAYILMAZ) ------------------------
    p = DATA / "salibiyyat_atlas_layer.json"
    d = load(p)
    if d is None:
        sources["salibiyyat"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["salibiyyat"] = entry(
            len(d["events"]),
            {"unit": "olay",
             "castles": len(d.get("castles", [])),
             "routes": len(d.get("routes", [])),
             "locations": len(d.get("locations", [])),
             "clusters": len(d.get("clusters", []))},
            [rel(p)])

    # --- evliya: places ------------------------------------------------------
    p = DATA / "evliya_atlas_layer.json"
    d = load(p)
    if d is None:
        sources["evliya"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["evliya"] = entry(
            len(d["places"]),
            {"unit": "yer/durak", "voyages": len(d.get("voyages", []))},
            [rel(p)])

    # --- science: scholars + alt sayılar -------------------------------------
    p = DATA / "science_layer.json"
    d = load(p)
    if d is None:
        sources["science"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["science"] = entry(
            len(d["scholars"]),
            {"unit": "âlim",
             "institutions": len(d.get("institutions", [])),
             "knowledge_routes": len(d.get("knowledge_routes", [])),
             "discoveries": len(d.get("discoveries", []))},
            [rel(p)])

    # --- muqaddasi: places ---------------------------------------------------
    p = DATA / "muqaddasi_atlas_layer.json"
    d = load(p)
    if d is None:
        sources["muqaddasi"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["muqaddasi"] = entry(
            len(d["places"]),
            {"unit": "yerleşim",
             "routes": len(d.get("routes", [])),
             "aqualim": len(d.get("aqualim", []))},
            [rel(p)])

    # --- battles: public/data'da savaş dosyası yok → db.json bundle ----------
    d = load(DB_JSON)
    if d is None or "battles" not in d:
        sources["battles"] = entry(None, None, [rel(DB_JSON)], "missing")
    else:
        sources["battles"] = entry(
            len(d["battles"]),
            {"unit": "savaş",
             "note": ("public/data altında ayrı savaş dosyası yok; sayı JS "
                      "bundle'a gömülen web/src/data/db.json 'battles' "
                      "listesinden"),
             "db_events": len(d.get("events", []))},
            [rel(DB_JSON)], status="bundle")

    # --- library: core_shelf books -------------------------------------------
    p = READING / "core_shelf.json"
    d = load(p)
    if d is None:
        sources["library"] = entry(None, None, [rel(p)], "missing")
    else:
        sources["library"] = entry(
            len(d["books"]),
            {"unit": "kitap", "batches": len(d.get("batches", []))},
            [rel(p)])

    all_files = sorted({f for s in sources.values() for f in s["files"]})
    return {
        "generated_by": "pipelines/frontend/build_source_counts.py",
        "note": ("ELLE DÜZENLEMEYİN — bu dosya veriden üretilir. Sayılar ham "
                 "tamsayıdır; '13,9K' gibi kısaltma/biçimlendirme JSX "
                 "tarafında yapılır. Eksik dosyada count=null, "
                 "status='missing'."),
        "sources": sources,
        "source_files": all_files,
    }


def main():
    out = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"yazıldı: {rel(OUT)}")
    print(f"{'kaynak':<11} {'sayı':>8}  durum")
    for key, s in out["sources"].items():
        print(f"{key:<11} {fmt(s['count']):>8}  {s['status']}")


if __name__ == "__main__":
    main()
