#!/usr/bin/env python3
"""
build_view_data.py — v1 görünüm verisini CANONICAL'dan üretir (H23, veri
akışı birleşmesi). "Tek doğruluk kaynağı" ilkesi: silme/merge/düzeltme
canonical'da yapılır, görünüm dosyası buradan türetilir → v1 ekranı
DEĞİŞMEDEN merkezî deftere bağlanır.

TASARIM (kanıtla): canonical, v1'in KÜRASYONLU zenginliğini (geo tip,
etiket, dönem, ülke) TAŞIMAZ. Bu yüzden iki-katman:
  OTORİTE  (canonical): kayıt listesi, pref/alt etiketler, açıklama,
           koordinat, DEPRECATED durumu (emekli/merge kayıtlar DÜŞER),
           yönlendirme (deprecated_in_favor_of).
  ZENGİNLİK (v1 lite):  canonical'da karşılığı olmayan alanlar (gt/gtt/
           gte, tg, hp, ct, rg, ds, geo_confidence, lt) — curie üzerinden
           eşlenip KORUNUR. v1 kürasyonu kaybolmaz.

Sonuç: v1 şemasıyla BİREBİR aynı JSON (UI kodu değişmez, piksel parite),
ama artık canonical otorite. Kuyruk-eritme düzeltmeleri (27 hayalet,
372 dublet, 1.193 augment) ilk kez EKRANA yansır.
"""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "web/public/data"
SQLITE = REPO / "data/_index/lookup.sqlite"


def curie_map(cur, prefix):
    return dict(cur.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?",
        (prefix + ":%",)))


def load_canonical(pid, ns):
    p = REPO / "data/canonical" / ns / (pid.replace("iac:", "iac_").replace("-", "_") + ".json")
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_yaqut(cur):
    """place namespace; v1 yaqut_lite şeması korunur."""
    lite = json.loads((DATA / "yaqut_lite.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "yaqut")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in lite:
        pid = cmap.get(f"yaqut:{r['id']}")
        can = load_canonical(pid, "place") if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)              # canonical yoksa v1 aynen (dürüstlük)
            continue
        prov = can.get("provenance") or {}
        if prov.get("deprecated"):
            stats["emekli"] += 1
            continue                   # emekli/merge kayıt LİSTEDEN DÜŞER
        stats["aktif"] += 1
        # OTORİTE alanları canonical'dan tazele; ZENGİNLİK v1'den kalır
        pl = (can.get("labels") or {}).get("prefLabel") or {}
        desc = (can.get("labels") or {}).get("description") or {}
        co = can.get("coords") or {}
        merged = dict(r)               # v1 zenginliği taban
        if pl.get("ar"): merged["h"] = pl["ar"]
        if pl.get("tr"): merged["ht"] = pl["tr"]
        if pl.get("en"): merged["he"] = pl["en"]
        if desc.get("tr"): merged["st"] = desc["tr"]
        if desc.get("en"): merged["se"] = desc["en"]
        if co.get("lat") is not None: merged["lat"] = co["lat"]
        if co.get("lon") is not None: merged["lon"] = co["lon"]
        merged["pid"] = can["@id"]     # yeni: canonical köprüsü
        out.append(merged)
    return "yaqut_lite.json", out, stats


BUILDERS = {"yaqut": build_yaqut}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default="all")
    ap.add_argument("--out-dir", default=str(REPO / "web/public/view-data"))
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    cur = con.cursor()
    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    keys = BUILDERS if args.view == "all" else {args.view: BUILDERS[args.view]}
    for k, fn in keys.items():
        name, data, stats = fn(cur)
        (outdir / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"{k:12s} → {name}: {len(data):6d} kayıt "
              f"(aktif {stats['aktif']} · emekli-düşen {stats['emekli']} · "
              f"canonical-yok {stats['yok']})")
    con.close()


if __name__ == "__main__":
    main()
