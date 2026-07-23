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

H23 KARARLARI (ölçümle, ilk koşunun 3 sorunundan sonra):
  H23-1 AÇIKLAMA/ÖZET canonical'dan lite'a TAŞINMAZ. Sebep çift: (a) boyut
        — canonical description tam makale, "lite" 50 MB'a şişiyordu
        (dia 3→49 MB); (b) İSAM — tam DİA makale metni izne bağlı, lite'a
        koymak B planını (metni çıkar) bozar. Teaser v1'de kalır.
  H23-2 KAYNAK-SADIK ATLAS KATMANLARI (muqaddasi, evliya): places[] listesi
        o kitabın andığı yerlerdir = tarihsel metin. Canonical merge kararı
        bu listeyi DÜŞÜRMEZ (routes[] de referans veriyor). Emekli kayıt
        listede KALIR, merged_into ile işaretlenir. Kimlik+koordinat tazelenir.
        (Katalog görünümleri yaqut/alam/dia'da emekli DÜŞER — orada mükerrer
        katalog kaydı gerçekten fazlalık.)
  H23-3 EI-1'de İSİM tazelenmez: EI-1↔person eşleşmesi %33.7 FP (QID audit).
        Yalnız emekli-düşürme + pid köprüsü.
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


def ns_of(pid):
    """pid ('iac:institution-00001344') → namespace ('institution').

    Karma ns görünümlerinde (Evliyâ: place+institution) canonical'ın hangi
    dizinde olduğunu pid'in kendisinden türet — böylece tek görünüm iki ns'e
    köprü kurabilir."""
    return pid.split(":", 1)[1].split("-", 1)[0]


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
        if co.get("lat") is not None: merged["lat"] = co["lat"]
        if co.get("lon") is not None: merged["lon"] = co["lon"]
        merged["pid"] = can["@id"]     # yeni: canonical köprüsü
        out.append(merged)
    return "yaqut_lite.json", out, stats


def build_alam(cur):
    """person namespace; v1 alam_lite şeması korunur (curie 'el-alam:%').

    OTORİTE: h/ht/he (pref ar/tr/en) + dt/de (desc tr/en). ZENGİNLİK v1'de
    kalır: c (yüzyıl), g (cinsiyet), hd/md (vefat hicrî/mîlâdî), lat/lon —
    canonical PERSON kayıtları koordinat TAŞIMAZ, o yüzden lat/lon v1'den
    korunur."""
    lite = json.loads((DATA / "alam_lite.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "el-alam")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in lite:
        pid = cmap.get(f"el-alam:{r['id']}")
        can = load_canonical(pid, "person") if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)
            continue
        prov = can.get("provenance") or {}
        if prov.get("deprecated"):
            stats["emekli"] += 1
            continue
        stats["aktif"] += 1
        pl = (can.get("labels") or {}).get("prefLabel") or {}
        desc = (can.get("labels") or {}).get("description") or {}
        merged = dict(r)
        if pl.get("ar"): merged["h"] = pl["ar"]
        if pl.get("tr"): merged["ht"] = pl["tr"]
        if pl.get("en"): merged["he"] = pl["en"]
        merged["pid"] = can["@id"]
        out.append(merged)
    return "alam_lite.json", out, stats


def build_dia(cur):
    """person namespace; v1 dia_lite şeması korunur (curie 'dia:%', id=slug).

    OTORİTE: t (pref tr) + ds (desc tr) — DİA Türkçe kaynak, tek dil yuvası.
    ZENGİNLİK v1'de kalır: bp (doğum yeri), c1, dh/dc, fl, is, wm, tc, dia.
    dia_relations/works/travel/geo türev kenar dosyaları v1'de KALIR (bu
    görünüm yalnız dia_lite'ı canonical'a bağlar)."""
    lite = json.loads((DATA / "dia_lite.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "dia")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in lite:
        pid = cmap.get(f"dia:{r['id']}")
        can = load_canonical(pid, "person") if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)
            continue
        prov = can.get("provenance") or {}
        if prov.get("deprecated"):
            stats["emekli"] += 1
            continue
        stats["aktif"] += 1
        pl = (can.get("labels") or {}).get("prefLabel") or {}
        desc = (can.get("labels") or {}).get("description") or {}
        merged = dict(r)
        if pl.get("tr"): merged["t"] = pl["tr"]
        merged["pid"] = can["@id"]
        out.append(merged)
    return "dia_lite.json", out, stats


def build_ei1(cur):
    """person namespace; v1 ei1_lite şeması korunur (curie 'ei1:%', id=int).

    OTORİTE: t (pref en) + ds (desc en) — EI(1) İngilizce kaynak. ZENGİNLİK
    v1'de kalır: tn (normalize başlık), is, vol, at. H21 triyajı emekli
    işaretlediği hayalet ei1 kayıtları burada otomatik DÜŞER (emekli sayısı
    raporlanır)."""
    lite = json.loads((DATA / "ei1_lite.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "ei1")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in lite:
        pid = cmap.get(f"ei1:{r['id']}")
        can = load_canonical(pid, "person") if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)
            continue
        prov = can.get("provenance") or {}
        if prov.get("deprecated"):
            stats["emekli"] += 1
            continue
        stats["aktif"] += 1
        # H23-3: EI-1↔person eşleşmesi %33.7 FP (QID audit) → İSİM
        # tazelenmez, v1 başlığı kalır. Yalnız emekli-düşürme + pid köprüsü.
        merged = dict(r)
        merged["pid"] = can["@id"]
        out.append(merged)
    return "ei1_lite.json", out, stats


def build_muqaddasi(cur):
    """place namespace; {metadata, aqualim, places, routes} sarmalayıcı yapı.

    YALNIZ places[] canonical'dan tazelenir (curie 'muqaddasi:%', id=muq-NNNN);
    aqualim ve routes v1'de olduğu gibi KALIR. OTORİTE: name_ar/tr/en +
    desc_tr/en + lat/lon. ZENGİNLİK v1'de kalır: certainty, coord_source,
    iqlim_ar. metadata.total_places tazelenmiş sayıya güncellenir (yanlış sayı
    bırakma ilkesi)."""
    doc = json.loads((DATA / "muqaddasi_atlas_layer.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "muqaddasi")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in doc.get("places", []):
        pid = cmap.get(f"muqaddasi:{r['id']}")
        can = load_canonical(pid, "place") if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)
            continue
        prov = can.get("provenance") or {}
        # H23-2: KAYNAK-SADIK ATLAS KATMANI — Makdisî'nin andığı yerlerin
        # LİSTESİ tarihsel metindir; canonical'ın "bu iki kayıt aynı yer"
        # merge kararı bu listeyi DEĞİŞTİRMEZ (routes[] de bu yerlere referans
        # veriyor). Emekli kayıt DÜŞÜRÜLMEZ; yalnız kimlik + koordinat + pid.
        co = can.get("coords") or {}
        pl = (can.get("labels") or {}).get("prefLabel") or {}
        merged = dict(r)
        if prov.get("deprecated"):
            stats["emekli"] += 1                 # sayılır ama listede KALIR
            merged["merged_into"] = prov.get("deprecated_in_favor_of")
        else:
            stats["aktif"] += 1
        if co.get("lat") is not None: merged["lat"] = co["lat"]
        if co.get("lon") is not None: merged["lon"] = co["lon"]
        merged["pid"] = can["@id"]
        out.append(merged)
    doc["places"] = out
    if isinstance(doc.get("metadata"), dict):
        doc["metadata"]["total_places"] = len(out)
    return "muqaddasi_atlas_layer.json", doc, stats


def build_evliya(cur):
    """KARMA ns (place + institution); {metadata, voyages, places} sarmalayıcı.

    YALNIZ places[] canonical'dan tazelenir (curie 'evliya-celebi:%',
    id=EC_NNNNN); voyages v1'de KALIR. ns pid'den türetilir (place|institution).
    OTORİTE: name_ar/tr/en + description_tr/en/ar + lat/lng (v1 koord alanı
    'lng'). ZENGİNLİK v1'de kalır: voyage_id, volume, year_approx, category,
    source, cross_refs, category_confidence. metadata.total_places güncellenir."""
    doc = json.loads((DATA / "evliya_atlas_layer.json").read_text(encoding="utf-8"))
    cmap = curie_map(cur, "evliya-celebi")
    out, stats = [], {"aktif": 0, "emekli": 0, "yok": 0}
    for r in doc.get("places", []):
        pid = cmap.get(f"evliya-celebi:{r['id']}")
        can = load_canonical(pid, ns_of(pid)) if pid else None
        if not can:
            stats["yok"] += 1
            out.append(r)
            continue
        prov = can.get("provenance") or {}
        # H23-2: KAYNAK-SADIK ATLAS KATMANI (bkz. muqaddasi) — Evliyâ'nın
        # durak listesi metne sadıktır, merge kararı düşürmez.
        co = can.get("coords") or {}
        merged = dict(r)
        if prov.get("deprecated"):
            stats["emekli"] += 1
            merged["merged_into"] = prov.get("deprecated_in_favor_of")
        else:
            stats["aktif"] += 1
        if co.get("lat") is not None: merged["lat"] = co["lat"]
        if co.get("lon") is not None: merged["lng"] = co["lon"]   # v1 koord alanı 'lng'
        merged["pid"] = can["@id"]
        out.append(merged)
    doc["places"] = out
    if isinstance(doc.get("metadata"), dict):
        doc["metadata"]["total_places"] = len(out)
    return "evliya_atlas_layer.json", doc, stats


BUILDERS = {
    "yaqut": build_yaqut,
    "alam": build_alam,
    "dia": build_dia,
    "ei1": build_ei1,
    "muqaddasi": build_muqaddasi,
    "evliya": build_evliya,
}


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
        # düz liste görünümü → len(data); sarmalayıcı ({...places[]...}) → places sayısı
        n = len(data) if isinstance(data, list) else len(data.get("places", []))
        print(f"{k:12s} → {name}: {n:6d} kayıt "
              f"(aktif {stats['aktif']} · emekli-düşen {stats['emekli']} · "
              f"canonical-yok {stats['yok']})")
    con.close()


if __name__ == "__main__":
    main()
