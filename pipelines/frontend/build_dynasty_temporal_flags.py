#!/usr/bin/env python3
"""Hanedan yıl aralıklarının GÜVENİLİRLİK bayrakları (H56).

SORUN (denetim, ölçüldü):
    Ana haritanın hanedan popup'ı ve global arama, v1 `db.json`'daki
    `start`–`end` çiftini ÇIPLAK basıyor. Dokuz kayıtta bu çift ya imkânsız ya
    da nöbetçi değer:

      id  30 Eyyûbîler          1169 – 15     (start > end)
      id  32 Lübnan Ma'noğulları  16 – 1697   (start < 622)
      id  51 Âl-i Cülandâ          7 – 9      (ikisi de < 622)
      id  58 Mali Keita Kralları 1230 – 15    (start > end)
      id  59 Songay Kralları       9 – 1592   (start < 622)
      id  60 Kenem/Bornu           9 – 2025   (start < 622 + nöbetçi son)
      id  62 Kilva Sultanları     10 – 1550   (start < 622)
      id  89 Hârezmşahlar          7 – 1231   (start < 622)
      id 132 Çağataylılar        1227 – 15    (start > end)

    İslam takvimi 622'de başlar; bir İslam hanedanının 622'den önce başlaması
    imkânsızdır. Bu değerler büyük olasılıkla HİCRÎ YÜZYIL numarasıdır ve yıl
    alanına düşmüştür — ama BU BİR TAHMİNDİR ve bu script tahmini VERİYE
    YAZMAZ. Yalnız "bu aralık güvenilmez" der ve kaydı insan kuyruğuna atar.

    Ayrıca dördü (30, 51, 58, 132) haritada HİÇBİR YILDA çizilmiyor, çünkü
    `d.start <= yıl <= d.end` koşulu hiçbir yıl için sağlanmıyor. Yani bu
    ekranda görünmezliğin sebebi bir filtre kararı değil, BOZUK VERİ.

NÖBETÇİ DEĞER — ve neden bu bir tahmin DEĞİL:
    Sekiz kayıtta `end == 2025`. Bunların SEKİZİNİN de canonical karşılığında
    `temporal.end_ce` **null**'dur; yani merkezî defter bağımsız olarak
    "bitmemiş" diyor (Âl Suûd, Brunei Sultanları, Yogyakarta Sultanları,
    Alevî Şerifler…). Dolayısıyla 2025'i "devam ediyor" diye göstermek bir
    yorum değil, iki kaynağın ortak ifadesidir.

    `end == 15` olan ÜÇ kayıtta da canonical `end_ce` null'dur — ama bu üç
    hanedan (Eyyûbîler, Mali Keita, Çağataylılar) devam ETMİYOR. Yani orada
    canonical de yanlış. Bu yüzden 15 "devam ediyor" sayılmaz; tutarsız
    işaretlenir.

NE YAPAR: sınıflandırır ve kuyruğa yazar. NE YAPMAZ: doğru yılı tahmin etmez,
db.json'u değiştirmez (v1 verisi), canonical'ı değiştirmez.

Çıktılar:
    web/public/view-data/dynasty_temporal_flags.json   (arayüz okur)
    data/review_queue/dynasty_temporal.jsonl           (insan kuyruğu)
Determinizm: id sıralı, timestamp yok.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "web" / "src" / "data" / "db.json"
DYN_DIR = REPO / "data" / "canonical" / "dynasty"
OUT = REPO / "web" / "public" / "view-data" / "dynasty_temporal_flags.json"
KUYRUK = REPO / "data" / "review_queue" / "dynasty_temporal.jsonl"

HICRET = 622          # İslam takviminin başlangıcı (CE)
NOBETCI_SON = 2025    # v1'in "devam ediyor" nöbetçisi
V1_ID_RE = re.compile(r"bosworth-nid:(\d+)")


def canonical_index() -> dict:
    """v1 id → canonical hanedan kaydı (curie üzerinden; ad eşleştirme YOK)."""
    out = {}
    if not DYN_DIR.is_dir():
        return out
    for f in sorted(DYN_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        m = V1_ID_RE.search(json.dumps(r, ensure_ascii=False))
        if m:
            out[int(m.group(1))] = r
    return out


def siniflandir(d: dict, kan: dict | None) -> tuple[str, list[str]]:
    """('saglam' | 'devam' | 'tutarsiz', [gerekçe]) döndürür."""
    s, e = d.get("start"), d.get("end")
    nedenler = []

    if s is None or e is None:
        return "tutarsiz", ["başlangıç ya da bitiş yılı yok"]

    kan_son_bos = kan is not None and (kan.get("temporal") or {}).get("end_ce") is None

    if isinstance(s, int) and s < HICRET:
        nedenler.append(f"başlangıç {s} < 622 (İslam takvimi başlangıcından önce)")
    if isinstance(e, int) and 0 < e < HICRET:
        nedenler.append(f"bitiş {e} < 622")
    if isinstance(s, int) and isinstance(e, int) and e != NOBETCI_SON and s > e:
        nedenler.append(f"başlangıç {s} > bitiş {e}")

    if nedenler:
        return "tutarsiz", nedenler

    # Nöbetçi son: YALNIZ canonical de "bitmemiş" diyorsa devam sayılır.
    if e == NOBETCI_SON:
        if kan_son_bos:
            return "devam", ["v1 nöbetçi 2025 + canonical end_ce null → devam ediyor"]
        return "tutarsiz", ["v1 nöbetçi 2025 ama canonical bir bitiş yılı taşıyor"]

    return "saglam", []


def main() -> None:
    if not DB.is_file():
        print("atlandı: db.json yok")
        return
    db = json.loads(DB.read_text(encoding="utf-8"))
    dynasties = db.get("dynasties") or []
    kan = canonical_index()

    bayrak, kuyruk = {}, []
    sayac = {"toplam": len(dynasties), "saglam": 0, "devam": 0, "tutarsiz": 0,
             "canonical_eslesen": 0, "haritada_hic_cizilmeyen": 0}

    for d in sorted(dynasties, key=lambda x: x.get("id", 0)):
        vid = d.get("id")
        if vid is None:
            continue
        k = kan.get(vid)
        if k:
            sayac["canonical_eslesen"] += 1
        durum, nedenler = siniflandir(d, k)
        sayac[durum] += 1

        # Haritada hiçbir yılda çizilmiyor mu? (622–1924 zaman çubuğu aralığı)
        s, e = d.get("start"), d.get("end")
        cizilmez = not (isinstance(s, int) and isinstance(e, int)
                        and s <= 1924 and e >= 622 and s <= e)
        if cizilmez:
            sayac["haritada_hic_cizilmeyen"] += 1

        if durum != "saglam":
            bayrak[str(vid)] = {"d": durum, "s": s, "e": e,
                                **({"g": nedenler} if nedenler else {}),
                                **({"h": 1} if cizilmez else {})}
        if durum == "tutarsiz":
            kuyruk.append({
                "queue_id": f"dynasty-temporal-{vid:03d}",
                "adapter_id": "dynasty-temporal-audit",
                "v1_id": vid,
                "ad_tr": d.get("tr"),
                "ad_en": d.get("en"),
                "v1_start": s,
                "v1_end": e,
                "canonical_pid": (k or {}).get("@id"),
                "canonical_start_ce": ((k or {}).get("temporal") or {}).get("start_ce"),
                "canonical_end_ce": ((k or {}).get("temporal") or {}).get("end_ce"),
                "canonical_start_ah": ((k or {}).get("temporal") or {}).get("start_ah"),
                "canonical_end_ah": ((k or {}).get("temporal") or {}).get("end_ah"),
                "nedenler": nedenler,
                "haritada_hic_cizilmiyor": cizilmez,
                "needs_human_review": True,
                "not": ("Doğru yıl TAHMİN EDİLMEDİ. Değerler hicrî yüzyıl numarası "
                        "olabilir; kaynağa (Bosworth, New Islamic Dynasties) bakılmalı."),
            })

    doc = {
        "_doc": (
            "Hanedan yıl aralıklarının güvenilirlik bayrakları. 'tutarsiz' = "
            "aralık imkânsız (622 öncesi ya da başlangıç>bitiş) — arayüz çıplak "
            "yıl BASMAZ, 'kaynakta tutarsız' der. 'devam' = v1 nöbetçi 2025 ve "
            "canonical end_ce null → 'devam ediyor'. Doğru yıl TAHMİN EDİLMEZ; "
            "tutarsız kayıtlar data/review_queue/dynasty_temporal.jsonl'a "
            "yazılır. Bayrağı olmayan id 'saglam' demektir. "
            "Üretici: build_dynasty_temporal_flags.py"
        ),
        "counts": sayac,
        "flags": {k: bayrak[k] for k in sorted(bayrak, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    KUYRUK.parent.mkdir(parents=True, exist_ok=True)
    KUYRUK.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in kuyruk),
                      encoding="utf-8")

    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"         {KUYRUK.relative_to(REPO).as_posix()} ({len(kuyruk)} kayıt)")
    print(f"  hanedan {sayac['toplam']} · canonical eşleşen {sayac['canonical_eslesen']}")
    print(f"  sağlam {sayac['saglam']} · devam ediyor {sayac['devam']} "
          f"· TUTARSIZ {sayac['tutarsiz']}")
    print(f"  haritada hiçbir yılda çizilmeyen: {sayac['haritada_hic_cizilmeyen']}")
    for x in kuyruk:
        print(f"    ! {x['v1_id']:>3} {x['ad_tr']}: {x['v1_start']}–{x['v1_end']} "
              f"({'; '.join(x['nedenler'])})")


if __name__ == "__main__":
    main()
