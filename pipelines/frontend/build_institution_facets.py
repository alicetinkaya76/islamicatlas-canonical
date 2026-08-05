#!/usr/bin/env python3
"""Kurum kayıtlarının gizli zenginliğini yayın katmanına çıkarır (H56).

H54'te yerler için yapılanın kurum eksenindeki karşılığı. Denetim ölçtü:
5.423 kurum kaydının `note` alanı %100 dolu ve içinde ekrana hiç çıkmayan
olgular var.

EN ÖNEMLİSİ — KOORDİNAT GÜVEN İŞARETİ:
    62 kayıtta note açıkça "Koordinat düşük güvenilirlikli (v1 geocoding)"
    diyor ve `grep web/src` bu ifade için SIFIR isabet veriyor. Yani kayıt
    dürüstçe "buranın yeri şüpheli" diyor, ekran bunu hiç söylemiyor.
    Bunların 21'i tam olarak (28.0, 31.0) — Mısır'ın geometrik merkezi —
    üzerinde ve hepsi manastır (dayr). Canlı Kahire haritasında, gerçekten
    konumu bilinen yapılarla aynı görsel kesinlikte çiziliyorlar.

    NOT: denetim bunu "bayraksız kopyalanmış" diye raporlamıştı; ölçünce
    bayrağın CANONICAL'DA MEVCUT olduğu ama note'ta hapis kaldığı görüldü.
    Kusur "bayrak yok" değil, "bayrak ekrana çıkmıyor" — farklı onarım.

ÇAKIŞMA (türetilmiş, note'tan değil): 89 koordinat noktasını 3 ya da daha çok
kurum paylaşıyor; bu noktalarda toplam 557 kayıt var. Aynı noktaya yığılmak
tek başına hata değildir (bir külliyede çok yapı olabilir) ama kullanıcı kaç
kaydın aynı noktada olduğunu görebilmeli.

DİĞER AYIKLANAN OLGULAR: dönem, durum (mevcut/yıkılmış/restore), mahalle,
bânî, v1 kategorisi.

NE TAŞIMAZ: ham `note` metni. Kişi tarafında note'un %84'ü üretim iziydi
(H44) ve ham göstermek yanıltıcıydı; burada da `Çıkarım güveni:` ve `Kaynak:`
gibi boru hattı izleri AYIKLANIR ama METİN OLARAK BASILMAZ — güven değeri
ayrı bir alan olarak taşınır, izin kendisi değil.

KAYNAK İŞARETİ: her olgu `_kaynak` taşır — "alan" (canonical yapısal alan)
ya da "note" (metinden ayıklandı).

Çıktı: web/public/view-data/institution_facets.json
Determinizm: pid sıralı, timestamp yok.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INST_DIR = REPO / "data" / "canonical" / "institution"
OUT = REPO / "web" / "public" / "view-data" / "institution_facets.json"

DESEN = {
    "donem":    re.compile(r"Dönem:\s*([^·|;\n]+)"),
    "durum":    re.compile(r"Durum:\s*([^·|;\n]+)"),
    "mahalle":  re.compile(r"Mahalle:\s*([^·|;\n]+)"),
    # "Bâni: عمرو بن العاص" (477 kayıt) DEĞER taşır; "Bânisi bilinmiyor."
    # (iki nokta YOK) serbest metindir ve değer değildir — ayırt edilir.
    "bani":     re.compile(r"Bâni(?:si)?:\s*([^·|;\n]+)"),
    "kategori": re.compile(r"v1 (?:kategori|tür):\s*([^·|;\n]+)"),
    "guven":    re.compile(r"Çıkarım güveni:\s*(\w+)"),
}
# Koordinatın kendisi şüpheli — bu bir olgu değil, bir UYARI.
DUSUK_KOORD = re.compile(r"Koordinat düşük güvenilirlikli")
BOS = {"unknown", "bilinmiyor", "belirsiz", "n/a", "none", "-", ""}


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def main() -> None:
    if not INST_DIR.is_dir():
        print("atlandı: canonical/institution yok")
        return

    kayitlar = []
    nokta = Counter()
    for f in sorted(INST_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        kayitlar.append(r)
        c = r.get("coords") or {}
        if c.get("lat") is not None and c.get("lon") is not None:
            nokta[(round(c["lat"], 5), round(c["lon"], 5))] += 1

    out = {}
    s = Counter()
    s["kayit"] = len(kayitlar)
    for r in kayitlar:
        prov = r.get("provenance") or {}
        if prov.get("deprecated"):
            s["deprecated_atlandi"] += 1
            continue
        num = _num(r.get("@id"))
        if num is None:
            continue

        fac = {}
        # ── canonical YAPISAL alanlar ─────────────────────────────────────
        if r.get("institution_subtype"):
            fac["tip"] = {"v": r["institution_subtype"], "_kaynak": "alan"}
            s["alan_tip"] += 1
        if r.get("located_in"):
            fac["ust"] = {"v": r["located_in"], "_kaynak": "alan"}
            s["alan_ust"] += 1
        if r.get("patron_dynasty"):
            fac["hanedan"] = {"v": r["patron_dynasty"], "_kaynak": "alan"}
            s["alan_hanedan"] += 1
        ft = r.get("founded_temporal")
        if ft:
            fac["kurulus"] = {"v": ft, "_kaynak": "alan"}
            s["alan_kurulus"] += 1

        # ── koordinat dürüstlüğü ─────────────────────────────────────────
        c = r.get("coords") or {}
        note = r.get("note")
        if isinstance(note, dict):
            note = note.get("tr") or note.get("en")
        note = note if isinstance(note, str) else ""

        if note and DUSUK_KOORD.search(note):
            fac["koord_supheli"] = {"v": True, "_kaynak": "note"}
            s["koord_supheli"] += 1
        if c.get("lat") is not None and c.get("lon") is not None:
            paylasan = nokta[(round(c["lat"], 5), round(c["lon"], 5))]
            if paylasan >= 3:
                # Türetilmiş olgu: aynı noktayı kaç kurum paylaşıyor.
                fac["ayni_nokta"] = {"v": paylasan, "_kaynak": "turetilmis"}
                s["ayni_nokta_kayit"] += 1

        # ── note'tan AYIKLANAN olgular ────────────────────────────────────
        if note.strip():
            for anahtar, desen in DESEN.items():
                m = desen.search(note)
                if not m:
                    continue
                v = m.group(1).strip().strip("'\".,·")
                if v.lower() in BOS:
                    continue
                fac[anahtar] = {"v": v[:80], "_kaynak": "note"}
                s[f"note_{anahtar}"] += 1

        if fac:
            out[str(num)] = fac
            s["facet_olan"] += 1

    cakisan_nokta = sum(1 for v in nokta.values() if v >= 3)
    doc = {
        "_doc": (
            "Kurum kayıtlarının yayın-katmanı olguları. Canonical YAPISAL alanlar "
            "(tip/ust/hanedan/kurulus) + note'tan AYIKLANMIŞ olgular (dönem, durum, "
            "mahalle, bânî, kategori, çıkarım güveni) + TÜRETİLMİŞ olgu (aynı "
            "koordinatı kaç kurum paylaşıyor). `koord_supheli` = kaydın KENDİSİ "
            "koordinatının düşük güvenilirlikli olduğunu söylüyor; bu uyarı bugüne "
            "dek note içinde hapisti ve ekrana hiç çıkmıyordu. Her olgu `_kaynak` "
            "taşır: alan / note / turetilmis. Ham note METNİ TAŞINMAZ. "
            "Üretici: build_institution_facets.py"
        ),
        "counts": {**dict(s), "cakisan_nokta_3plus": cakisan_nokta,
                   "tekil_koordinat": len(nokta)},
        "facets": {k: out[k] for k in sorted(out, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  kurum {s['kayit']} → facet'i olan {s['facet_olan']}")
    print(f"  ALAN : tip {s['alan_tip']} · üst {s['alan_ust']} "
          f"· hanedan {s['alan_hanedan']} · kuruluş {s['alan_kurulus']}")
    print(f"  NOTE : dönem {s['note_donem']} · durum {s['note_durum']} "
          f"· mahalle {s['note_mahalle']} · bânî {s['note_bani']} "
          f"· kategori {s['note_kategori']} · güven {s['note_guven']}")
    print(f"  KOORDİNAT DÜRÜSTLÜĞÜ: şüpheli işaretli {s['koord_supheli']} "
          f"(bugüne dek ekranda 0) · 3+ kurum paylaşan nokta {cakisan_nokta} "
          f"({s['ayni_nokta_kayit']} kayıt)")


if __name__ == "__main__":
    main()
