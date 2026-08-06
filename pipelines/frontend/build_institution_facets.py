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
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INST_DIR = REPO / "data" / "canonical" / "institution"
EVLIYA = REPO / "web" / "public" / "view-data" / "evliya_atlas_layer.json"
OUT = REPO / "web" / "public" / "view-data" / "institution_facets.json"
KUYRUK = REPO / "data" / "review_queue" / "institution_tip_ve_ust.jsonl"

# Kahire merkez — maqrizi katmanının toplu `located_in` hedefi.
KAHIRE = (30.0444, 31.2357)
# "Büyük Kahire" için makul üst sınır; bunun ötesi ayrı bir yerleşimdir.
UZAK_KM = 50.0
# v1'in kendi sınıflandırma güveni bu eşiğin altındaysa TİP ŞÜPHELİDİR.
GUVEN_ESIK = 0.5


def haversine(a, b) -> float:
    R = 6371.0
    p = math.pi / 180
    x = (math.sin((b[0] - a[0]) * p / 2) ** 2
         + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))


def evliya_guven() -> dict:
    """canonical pid → v1 `category_confidence`.

    H56: v1 evliya katmanı 5.444 yerin HEPSİNDE bir sınıflandırma güveni
    taşıyor; adaptör bunu tamamen DÜŞÜRÜYORDU — canonical note'unda `güven`
    geçen evliya kaydı sayısı 0. Sonuç: kaynak "bu kategoriye %20 eminim"
    derken merkezî defter SERT bir `institution_subtype` (ve ondan türeyen
    `@type`) ilan ediyordu. Ölçüldü: eşleşen 2.575 kaydın 321'i eşiğin
    altında ve sonuçlar gözle görülür yanlış:
        "Üsküp Saat Kulesi"  → mosque  (güven 0,4)
        "Kolçvar (Cetatea Colț)" → palace (güven 0,4)
        "Nalband (Perdikkas)" → mosque  (güven 0,2)   [yerleşim adı]
    Doğru tip TAHMİN EDİLMEZ; güven yayınlanır ve kayıt kuyruğa alınır.
    """
    if not EVLIYA.is_file():
        return {}
    try:
        d = json.loads(EVLIYA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for k in (d.get("places") or []):
        pid, c = k.get("pid"), k.get("category_confidence")
        if pid and isinstance(c, (int, float)):
            out[pid] = (float(c), k.get("category"))
    return out

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

    guven = evliya_guven()
    kuyruk = []
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

        # ── H56: TİP GÜVENİ (v1'den, adaptörün düşürdüğü bilgi) ───────────
        g = guven.get(r.get("@id"))
        if g is not None:
            skor, v1_kat = g
            fac["tip_guven"] = {"v": round(skor, 2), "_kaynak": "v1"}
            s["tip_guven"] += 1
            if skor < GUVEN_ESIK and r.get("institution_subtype"):
                fac["tip_supheli"] = {"v": True, "_kaynak": "v1"}
                s["tip_supheli"] += 1
                kuyruk.append({
                    "queue_id": f"inst-tip-{num:08d}",
                    "adapter_id": "institution-type-confidence",
                    "pid": r.get("@id"),
                    "ad_tr": ((r.get("labels") or {}).get("prefLabel") or {}).get("tr"),
                    "canonical_subtype": r.get("institution_subtype"),
                    "v1_kategori": v1_kat,
                    "v1_guven": round(skor, 2),
                    "sorun": ("Kaynak bu kategoriye eşiğin altında güveniyor; merkezî "
                              "defter yine de SERT bir tip (ve ondan türeyen @type) "
                              "ilan ediyor."),
                    "needs_human_review": True,
                    "not": "Doğru tip TAHMİN EDİLMEDİ.",
                })

        # ── H56: TOPLU ÜST KONUM (maqrizi) ────────────────────────────────
        kaynak_izi = json.dumps(prov, ensure_ascii=False)
        if "maqrizi" in kaynak_izi and r.get("located_in"):
            fac["ust_toplu"] = {"v": True, "_kaynak": "adapter"}
            s["ust_toplu"] += 1
            lat, lon = c.get("lat"), c.get("lon")
            if lat is not None and lon is not None:
                km = haversine(KAHIRE, (lat, lon))
                if km > UZAK_KM:
                    fac["ust_uzaklik_km"] = {"v": round(km), "_kaynak": "turetilmis"}
                    # Koordinatı zaten ŞÜPHELİ işaretliyse mesafe KANIT DEĞİLDİR;
                    # o kayıtlar kuyruğa alınmaz (24 kayıt), yalnız işaretlenir.
                    if "koord_supheli" not in fac:
                        s["ust_uzak_guvenli"] += 1
                        kuyruk.append({
                            "queue_id": f"inst-ust-{num:08d}",
                            "adapter_id": "institution-blanket-containment",
                            "pid": r.get("@id"),
                            "ad_tr": ((r.get("labels") or {}).get("prefLabel") or {}).get("tr"),
                            "located_in": r.get("located_in"),
                            "kahireye_km": round(km),
                            "sorun": ("Hıtat katmanının 801 kaydının TAMAMI tek Tier-2 "
                                      "çözümüyle Kahire'ye bağlandı (adaptörün belgeli "
                                      "kararı); bu kaydın kendi koordinatı Kahire'den "
                                      "çok uzakta — çoğu Yukarı Mısır (Saîd) manastırı."),
                            "needs_human_review": True,
                            "not": "Doğru üst konum TAHMİN EDİLMEDİ (toponim çözümü gerekir).",
                        })
                    else:
                        s["ust_uzak_supheli_koord"] += 1

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
    KUYRUK.parent.mkdir(parents=True, exist_ok=True)
    kuyruk.sort(key=lambda x: x["queue_id"])
    KUYRUK.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in kuyruk),
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
    print(f"  TİP GÜVENİ (v1'den kurtarıldı): {s['tip_guven']} kayıt "
          f"· eşik altı SERT tip {s['tip_supheli']}")
    print(f"  TOPLU ÜST KONUM (maqrizi→Kahire): {s['ust_toplu']} kayıt "
          f"· >{int(UZAK_KM)} km ve koordinatı güvenilir {s['ust_uzak_guvenli']} "
          f"· >{int(UZAK_KM)} km ama koordinatı şüpheli {s['ust_uzak_supheli_koord']}")
    print(f"  insan kuyruğu: {KUYRUK.relative_to(REPO).as_posix()} ({len(kuyruk)} kayıt)")


if __name__ == "__main__":
    main()
