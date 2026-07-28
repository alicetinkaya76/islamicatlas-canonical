#!/usr/bin/env python3
"""Alatlı senkronik atlas verisi (H30, H31'de KAYNAK DÜZELTİLDİ).

Alatlı'nın (Tarihe Yön Veren Metinler) biricik katkısı SENKRONİK bakış: bir yılda
"bize" yön veren metinlerin yazarları kimlerdi, aynı anda "Batı'ya" yön verenler?

H31 DÜZELTMESİ — İKİ ÖNEMLİ HATA GİDERİLDİ
------------------------------------------
(1) KAYNAK: İlk sürüm iki ayrı yerden besleniyordu (canonical=Doğu,
    yan-tablo=Batı). ÖLÇÜM bunun ÇARPIK olduğunu gösterdi: canonical'daki
    Alatlı izli kayıtlar `bize` kanonunun ALT KÜMESİ (232 / 359) — kalanı
    inceleme kuyruğunda. Üstelik canonical'da 6 `batiya` kaydı da var, yani
    "canonical = Doğu" varsayımı yanlıştı.
    → Artık TEK KAYNAK: `data/sources/alatli/main.json` (677 kayıt, `canon`
      etiketi kaynağın kendisinden). Canonical yalnız BAĞLANTI katmanı: alatli
      id → pid eşlenirse kayıt tıklanabilir olur.
(2) ETİKET: İlk sürüm "DOĞU / BATI" yazıyordu. Upstream'in kendi notu:
    "canon = Alatlı'nın editöryel çerçevesi (COĞRAFYA DEĞİL)". Bu yüzden
    UI etiketi artık Alatlı'nın kendi terimleri: `bize` / `batiya`; coğrafi
    ya da etnik bir ayrım olmadığı ekranda yazar.

DÜRÜSTLÜK KURALLARI
    - Tarihsiz kayıt ÇİZİLMEZ (677'nin 662'si tarihli; 15'i düşer).
    - `canon` iki değeri birden taşıyan 4 kayıt İKİ ŞERİTTE DE görünür,
      `both: true` ile işaretlenir (uydurulmuş tek-taraf ataması yok).
    - Koordinat + cilt/sayfa atfı H32'de upstream'den aktarıldı (sidecar
      `_alatli_geo_cites.json`; 526 koordinat, 666 atıf). Sidecar yoksa görünüm
      bozulmaz, alanlar boş kalır — koordinat ASLA uydurulmaz.
    - Telif: docs/h25/ALATLI_TELIF_KAPISI.md — Alatlı-türevi kayıtlar araştırma
      sürümünde kalır; çıktı `publication_gate: "alatli"` ile işaretlenir.

Çıktı: web/public/view-data/alatli_synchronic.json (gitignored; build'de üretilir)
Determinizm: yıl+ad sıralı, timestamp yok.
"""

import glob
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN = REPO / "data" / "sources" / "alatli" / "main.json"
GEOCITES = REPO / "data" / "sources" / "alatli" / "_alatli_geo_cites.json"
CANON_DIR = REPO / "data" / "canonical" / "person"
OUT = REPO / "web" / "public" / "view-data" / "alatli_synchronic.json"

_SRC_RE = re.compile(r'"source_id"\s*:\s*"alatli:([^"]+)"')


def canonical_links() -> dict[str, str]:
    """alatli kaynak-id → canonical pid (yalnız AKTİF kayıtlar).

    Kayıt tıklanabilirliği için; şerit üyeliği BURADAN türetilmez (H31 dersi:
    canonical, kanonun alt kümesidir)."""
    out: dict[str, str] = {}
    for f in glob.glob(str(CANON_DIR / "*.json")):
        txt = Path(f).read_text(encoding="utf-8")
        if "alatli:" not in txt:
            continue
        d = json.loads(txt)
        if d.get("provenance", {}).get("deprecated"):
            continue
        for sid in _SRC_RE.findall(txt):
            out.setdefault(sid, d["@id"])
    return out


def build():
    rows = json.loads(MAIN.read_text(encoding="utf-8"))
    links = canonical_links()
    # H32: koordinat + cilt/sayfa atfı (upstream'den aktarılan sidecar).
    # Yoksa görünüm bozulmaz — harita/atıf alanları boş kalır (uydurma yok).
    gc = {}
    if GEOCITES.is_file():
        gc = json.loads(GEOCITES.read_text(encoding="utf-8")).get("records", {})

    bize, batiya, undated = [], [], 0
    for r in rows:
        birth, death = r.get("birth_ce"), r.get("death_ce")
        anchor = death if isinstance(death, int) else (birth if isinstance(birth, int) else None)
        if anchor is None:
            undated += 1
            continue                      # tarihsiz kayıt senkronik eksene KONULMAZ
        canon = r.get("canon") or []
        rec = {
            "id": r.get("id"),
            "name": (r.get("name_tr") or r.get("name_en") or "").replace("i̇", "i"),
            "birth_ce": birth if isinstance(birth, int) else None,
            "death_ce": death if isinstance(death, int) else None,
            "anchor_ce": anchor,
            "qid": r.get("qid"),
            "place": r.get("place_label"),
            "mentions": r.get("record_count"),
            "confidence": r.get("confidence"),
            "pid": links.get(r.get("id")),          # None ise merkezî defterde yok
            "both": len(canon) > 1,
        }
        # H32: koordinat + ilk atıf (cilt/sayfa) — "kaynağa in" ve harita için
        extra = gc.get(r.get("id")) or {}
        pl = extra.get("place") or {}
        if isinstance(pl.get("lat"), (int, float)) and isinstance(pl.get("lon"), (int, float)):
            rec["lat"], rec["lon"] = pl["lat"], pl["lon"]
            if pl.get("label"):
                rec["place"] = pl["label"]
        cites = extra.get("cites") or []
        if cites:
            c0 = cites[0]
            rec["cite"] = {k: c0[k] for k in ("vol", "book_page", "text") if c0.get(k) is not None}
            rec["cite_count"] = len(cites)
        if "bize" in canon:
            bize.append(rec)
        if "batiya" in canon:
            batiya.append(rec)

    key = lambda x: (x["anchor_ce"], x["name"])   # noqa: E731
    bize.sort(key=key)
    batiya.sort(key=key)
    years = [x["anchor_ce"] for x in bize + batiya]
    linked = sum(1 for x in bize + batiya if x["pid"])

    return {
        "generated_by": "pipelines/frontend/build_alatli_synchronic.py",
        "source": ("Alatlı, Tarihe Yön Veren Metinler "
                   "(Kapadokya Üniversitesi Yayınları)"),
        "canon_note": ("'bize' / 'batiya' Alatlı'nın EDİTÖRYEL ÇERÇEVESİDİR — "
                       "coğrafi ya da etnik bir ayrım DEĞİLDİR."),
        "publication_gate": "alatli",
        "gate_note": ("Alatlı-türevli kayıtlar araştırma sürümünde kalır; kamuya "
                      "açık CC-BY-SA dump'a izin/karar gelene kadar girmez "
                      "(docs/h25/ALATLI_TELIF_KAPISI.md)."),
        "range_ce": [min(years), max(years)] if years else None,
        "counts": {
            "bize": len(bize),
            "batiya": len(batiya),
            "both": sum(1 for x in bize if x["both"]),
            "undated_dropped": undated,
            "linked_to_store": linked,
            "with_coords": sum(1 for x in bize + batiya if x.get("lat") is not None),
            "with_cite": sum(1 for x in bize + batiya if x.get("cite")),
            "total_source_rows": len(rows),
        },
        "bize": bize,
        "batiya": batiya,
    }


def main():
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    c = doc["counts"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  kaynak satır       : {c['total_source_rows']}")
    print(f"  'bize'   şeridi    : {c['bize']}")
    print(f"  'batiya' şeridi    : {c['batiya']}  (her ikisi: {c['both']})")
    print(f"  tarihsiz (düştü)   : {c['undated_dropped']}")
    print(f"  merkezî deftere bağlı: {c['linked_to_store']}")
    print(f"  CE aralığı         : {doc['range_ce']}")


if __name__ == "__main__":
    main()
