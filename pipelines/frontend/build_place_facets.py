#!/usr/bin/env python3
"""Yer kayıtlarının gizli zenginliğini yayın katmanına çıkarır (H54).

SORUN (H51 yer denetimi, iki bulgu bir arada):
  1) Canonical yer alanlarının HİÇBİRİ arayüze çıkmıyordu — `place_subtype`,
     `located_in`, `temporal_coverage`, `authority_xref`, `yaqut_id` için
     `grep web/src` sıfır isabet veriyordu.
  2) Deponun en zengin yer katmanı `note` alanında STRING olarak hapisti:
     modern ülke 11.237 · modern bölge 8.531 · geo_type 6.999 · DİA bağlantısı
     6.776 · etimoloji 6.000 · tarihsel dönem 2.320.

     Ve `place_subtype` yalnız ÜÇ kaba değer taşıyor (settlement/region/iqlim)
     iken `note` içinde 65 İNCE TİP duruyor: mountain 1.216, water 704,
     river 352, valley 344, well 237, monastery 171… Yani canonical, bu boyutta
     v1'in `yaqut_lite`'ından FAKİR.

ŞEMA KARARI — ve neden şemaya dokunulmadı:
    Cazip olan `place.schema.json`'a `place_subtype_fine` eklemekti. Yapılmadı:
    ADR-013 gereği şema seti ATOMİK değişir (v0.4.0 → v0.5.0, tüm fixture ve
    reçeteler), ve H31/H49'da iki kez öğrenildi ki şemayı zorlamak yerine
    mevcut yapıyı kullanmak daha ucuz. Yayın katmanı (view-data) şemaya TABİ
    DEĞİL; zenginlik oraya taşınır, canonical olduğu gibi kalır.
    Şemaya yeni alan eklenip eklenmeyeceği Ali'nin ADR kararıdır — bu dosya
    o kararı beklemeden kullanıcıya değeri verir ve kararı da kolaylaştırır
    (ayrıştırmanın gerçekten çalıştığını sayıyla gösterir).

NE TAŞIR: canonical yapısal alanlar + note'tan AYIKLANMIŞ olgular.
NE TAŞIMAZ: ham `note` metni. Ayrıştırılamayan kısım gösterilmez — kişi
tarafında `note`un %84'ü üretim iziydi (H44) ve ham göstermek yanıltıcıydı.

KAYNAK İŞARETİ: her olgu `_kaynak` taşır — "alan" (canonical yapısal alan) ya
da "note" (metinden ayıklandı). Ayıklanmış bilgi, doğrulanmış alan gibi
gösterilmemeli.

Çıktı: web/public/view-data/place_facets.json
Determinizm: pid sıralı, timestamp yok.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLACE_DIR = REPO / "data" / "canonical" / "place"
OUT = REPO / "web" / "public" / "view-data" / "place_facets.json"

# note'tan ayıklanan olgular — desenler ÖLÇÜLEREK seçildi (H51 denetimi).
DESEN = {
    "tip":       re.compile(r"geo_type:\s*'?\"?([\w\- ]+)'?\"?"),
    "ulke":      re.compile(r"Modern country:\s*([^|;\n]+)"),
    "bolge":     re.compile(r"Modern region:\s*([^|;\n]+)"),
    "etimoloji": re.compile(r"[Ee]tymolog\w*:\s*([^|;\n]+)"),
    "donem":     re.compile(r"Historical period:\s*([^|;\n]+)"),
}
# Anlam taşımayan doldurma değerleri — gösterilmez.
BOS = {"unknown", "bilinmiyor", "n/a", "none", "-", ""}


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def main() -> None:
    if not PLACE_DIR.is_dir():
        print("atlandı: canonical/place yok")
        return

    out, sayac = {}, {
        "kayit": 0, "facet_olan": 0,
        "alan_subtype": 0, "alan_located_in": 0, "alan_temporal": 0, "alan_xref": 0,
        "note_tip": 0, "note_ulke": 0, "note_bolge": 0, "note_etimoloji": 0, "note_donem": 0,
        "deprecated_atlandi": 0,
    }
    for f in sorted(PLACE_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        sayac["kayit"] += 1
        prov = r.get("provenance") or {}
        if prov.get("deprecated"):
            sayac["deprecated_atlandi"] += 1   # yayında görünmeyen kayda facet üretilmez
            continue
        num = _num(r.get("@id"))
        if num is None:
            continue

        fac = {}
        # ── canonical YAPISAL alanlar (doğrulanmış) ─────────────────────────
        if r.get("place_subtype"):
            fac["subtype"] = {"v": r["place_subtype"], "_kaynak": "alan"}
            sayac["alan_subtype"] += 1
        if r.get("located_in"):
            fac["ust"] = {"v": r["located_in"], "_kaynak": "alan"}
            sayac["alan_located_in"] += 1
        tc = r.get("temporal_coverage")
        if tc:
            fac["donem_alan"] = {"v": tc, "_kaynak": "alan"}
            sayac["alan_temporal"] += 1
        xr = r.get("authority_xref")
        if xr:
            fac["xref"] = {"v": xr, "_kaynak": "alan"}
            sayac["alan_xref"] += 1

        # ── note'tan AYIKLANMIŞ olgular (türetilmiş) ───────────────────────
        note = r.get("note")
        if isinstance(note, dict):
            note = note.get("tr") or note.get("en")
        if isinstance(note, str) and note.strip():
            for anahtar, desen in DESEN.items():
                m = desen.search(note)
                if not m:
                    continue
                v = m.group(1).strip().strip("'\".,")
                if v.lower() in BOS:
                    continue
                fac[anahtar] = {"v": v[:80], "_kaynak": "note"}
                sayac[f"note_{anahtar}"] += 1

        if fac:
            out[str(num)] = fac
            sayac["facet_olan"] += 1

    # İnce tip dağılımı — "canonical v1'den fakir" bulgusunun ölçüsü.
    from collections import Counter
    ince = Counter(v["tip"]["v"] for v in out.values() if "tip" in v)

    doc = {
        "_doc": ("Yer kayıtlarının yayın-katmanı olguları. Canonical YAPISAL alanlar "
                 "(subtype/located_in/temporal_coverage/authority_xref) + note'tan "
                 "AYIKLANMIŞ olgular (tip/ülke/bölge/etimoloji/dönem). Her olgu "
                 "`_kaynak` taşır: 'alan' = doğrulanmış canonical alan, 'note' = "
                 "metinden ayıklandı. Ham note METNİ TAŞINMAZ. Şemaya dokunulmadı — "
                 "ADR kararı beklemeden değeri verir. Üretici: build_place_facets.py"),
        "counts": {**sayac, "ince_tip_tekil": len(ince),
                   "ince_tip_ilk10": dict(ince.most_common(10))},
        "facets": {k: out[k] for k in sorted(out, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  kayıt {sayac['kayit']} → facet'i olan {sayac['facet_olan']} "
          f"(deprecated atlandı {sayac['deprecated_atlandi']})")
    print(f"  ALAN  : subtype {sayac['alan_subtype']} · located_in {sayac['alan_located_in']} "
          f"· temporal {sayac['alan_temporal']} · xref {sayac['alan_xref']}")
    print(f"  NOTE  : tip {sayac['note_tip']} · ülke {sayac['note_ulke']} "
          f"· bölge {sayac['note_bolge']} · etimoloji {sayac['note_etimoloji']} "
          f"· dönem {sayac['note_donem']}")
    print(f"  ince tip tekil: {len(ince)} (canonical place_subtype yalnız 3 değer taşıyor)")


if __name__ == "__main__":
    main()
