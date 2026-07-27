#!/usr/bin/env python3
"""Alatlı senkronik atlas verisi (H30) — "aynı tarihte Doğu ve Batı yan yana".

Alatlı'nın (Tarihe Yön Veren Metinler) biricik katkısı SENKRONİK bakış: bir yılda
İslam dünyasında kim yaşıyordu, aynı anda Batı'da kim? Bu üretici o karşılaştırmayı
tek JSON'a indirger; UI (Zaman Çizelgesi → Senkronik mod) iki paralel şerit çizer.

İKİ ŞERİT, İKİ FARKLI KAYNAK DURUMU (dürüstlük):
  DOĞU  → canonical mağaza (source_id prefix `alatli:`), 227 aktif kişi.
          Tarih: birth/death/floruit_temporal (start_ce | start_ah→CE).
  BATI  → data/sources/alatli/_alatli_western_held.json, 280 kişi.
          Bunlar canonical'a MINT EDİLMEDİ (H25 kapsam+telif kararı); yan-tabloda
          durur. Alanlar olgusaldır (ad/doğum/ölüm/yer/Wikidata QID).

TELİF KAPISI (docs/h25/ALATLI_TELIF_KAPISI.md):
  Telif-hassas olan tek şey Alatlı'nın SEÇİMİ (hangi kişiler) — düzyazı ALINMADI.
  Karar: Alatlı-türevli kayıtlar "kişisel/araştırma sürümünde kalır", kamuya açık
  CC-BY-SA dump'a İZİN gelene kadar GİRMEZ. Bu dosya araştırma arayüzü içindir;
  bu yüzden çıktı `publication_gate: "alatli"` ile İŞARETLENİR ve UI ekranda
  kapıyı yazar. Yayın hattı kurulduğunda tek satırla dışlanır.

Çıktı: web/public/view-data/alatli_synchronic.json (gitignored; build'de üretilir)
Determinizm: yıl+ad sıralı; timestamp yok.
Çalıştırma: python3 pipelines/frontend/build_alatli_synchronic.py
"""

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical" / "person"
WEST = REPO / "data" / "sources" / "alatli" / "_alatli_western_held.json"
OUT = REPO / "web" / "public" / "view-data" / "alatli_synchronic.json"


def ah_to_ce(ah: int) -> int:
    """Hicrî→Milâdî yıl (tarih dönüşümü meşrudur; koordinat dönüşümü DEĞİL)."""
    return round(ah * 0.970229 + 621.567)


def temporal_ce(t) -> int | None:
    """Bir *_temporal bloğundan CE yılı çıkar (CE öncelikli, yoksa AH→CE)."""
    if not isinstance(t, dict):
        return None
    for k in ("start_ce", "end_ce"):
        if isinstance(t.get(k), int):
            return t[k]
    for k in ("start_ah", "end_ah"):
        if isinstance(t.get(k), int):
            return ah_to_ce(t[k])
    return None


def build_east():
    """canonical mağazadan Alatlı-izli aktif kişiler."""
    out = []
    for f in glob.glob(str(CANON / "*.json")):
        txt = Path(f).read_text(encoding="utf-8")
        if "alatli:" not in txt:
            continue
        d = json.loads(txt)
        if d.get("provenance", {}).get("deprecated"):
            continue
        birth = temporal_ce(d.get("birth_temporal"))
        death = temporal_ce(d.get("death_temporal"))
        anchor = death or birth or temporal_ce(d.get("floruit_temporal"))
        if anchor is None:
            continue          # tarihsiz kayıt senkronik eksene KONULMAZ (uydurma yok)
        pref = (d.get("labels", {}) or {}).get("prefLabel", {}) or {}
        name = pref.get("tr") or pref.get("en") or pref.get("ar") or ""
        # H29: "i"+U+0307 artefaktı (Türkçe İ.lower()) — görüntüde onarılır
        name = name.replace("i̇", "i")
        xref = d.get("authority_xref") or {}
        qid = xref.get("wikidata") if isinstance(xref, dict) else None
        out.append({
            "pid": d["@id"],
            "name": name,
            "birth_ce": birth,
            "death_ce": death,
            "anchor_ce": anchor,
            "qid": qid,
            "side": "dogu",
        })
    out.sort(key=lambda r: (r["anchor_ce"], r["name"]))
    return out


def build_west():
    """yan-tablodan Batı figürleri (canonical DEĞİL; kapı arkasında)."""
    if not WEST.is_file():
        return []
    d = json.loads(WEST.read_text(encoding="utf-8"))
    out = []
    for key, v in d.items():
        if not isinstance(v, dict):
            continue
        birth, death = v.get("birth_ce"), v.get("death_ce")
        anchor = death if isinstance(death, int) else birth
        if not isinstance(anchor, int):
            continue
        out.append({
            "held_id": key,               # pid YOK — mint edilmedi (dürüst)
            "name": v.get("name_tr") or v.get("name_en") or "",
            "birth_ce": birth if isinstance(birth, int) else None,
            "death_ce": death if isinstance(death, int) else None,
            "anchor_ce": anchor,
            "place": v.get("place_label"),
            "qid": v.get("qid"),
            "mentions": v.get("record_count"),
            "side": "bati",
        })
    out.sort(key=lambda r: (r["anchor_ce"], r["name"]))
    return out


def main():
    east, west = build_east(), build_west()
    years = [r["anchor_ce"] for r in east + west]
    doc = {
        "generated_by": "pipelines/frontend/build_alatli_synchronic.py",
        "source": ("Alatlı, Tarihe Yön Veren Metinler "
                   "(Kapadokya Üniversitesi Yayınları)"),
        # UI bu kapıyı EKRANDA yazar; yayın hattı bunu görüp dışlar.
        "publication_gate": "alatli",
        "gate_note": ("Alatlı-türevli kayıtlar araştırma sürümünde kalır; kamuya "
                      "açık CC-BY-SA dump'a izin/karar gelene kadar girmez "
                      "(docs/h25/ALATLI_TELIF_KAPISI.md)."),
        "west_note": ("Batı figürleri canonical mağazaya MINT EDİLMEDİ (kapsam+"
                      "telif kararı); yan-tablodan okunur, pid taşımaz."),
        "range_ce": [min(years), max(years)] if years else None,
        "counts": {"dogu": len(east), "bati": len(west)},
        "dogu": east,
        "bati": west,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  DOĞU (canonical) : {len(east):>4}")
    print(f"  BATI (yan-tablo) : {len(west):>4}")
    print(f"  CE aralığı       : {doc['range_ce']}")


if __name__ == "__main__":
    main()
