#!/usr/bin/env python3
"""Merkezî defterin aranabilir katmanı (H56 üçüncü dalga).

SORUN (denetim, ölçüldü): `SearchBar` indeksi TAMAMEN v1'in `db.json`'ından ve
beş "lite" dosyadan kuruluyor. Sonuç: mağazadaki

    olay        9.956   →   aranabilir 0
    kurum       5.423   →   aranabilir 0
    eser        9.404   →   aranabilir 0

Yani havuzu büyütmenin arama ekseninde karşılığı sıfırdı. Kullanıcı "Kâdisiye"
yazdığında v1'in 100 küratörlü savaşını buluyor, defterdeki 9.956 kitap-türevi
olayı bulamıyordu.

──────────────────────────────────────────────────────────────────────────────
NE İNDEKSLENİR — KURAL: **GERÇEKTEN AÇILAN HEDEFİ OLAN KAYIT.**

H46 doktrini: *sahte tıklanabilirlik, dürüst boşluktan kötüdür.* Arama sonucu
tıklanınca boş ekrana götürüyorsa, o sonucu hiç göstermemek daha dürüsttür.
Ölçüldü:

  OLAY  — 9.956 kaydın **9.102'si** (%91) provenance'ında kitap+bölüm çapası
          taşıyor → `#library?book=<pid>&sec=<n>` GERÇEKTEN açılıyor
          (H55'te uçtan uca doğrulandı: 91 bölümlük Fütûhu'l-Büldân).
          Çapası olmayan 854 kayıt İNDEKSLENMEZ.

  ESER  — 9.404 kaydın **9.385'i** havuzdaki bir müellife bağlı →
          `#scholars?pid=<müellif>` kişinin "Merkezî defterdeki eserleri"
          listesini açıyor (H55). Sitede okunabilen 17'si doğrudan
          `#library?book=` alır. Müellifsiz 19 kayıt İNDEKSLENMEZ.

  KURUM — **HİÇ İNDEKSLENMEZ.** 5.423 kaydın sıfırında açılabilir hedef yok:
          kurumları gösteren üç görünüm (Khitat, Konya, Kahire) v1'in canlı
          symlink'indeki dosyaları okuyor ve o dosyalarda canonical
          institution pid'i mint EDİLMEMİŞ. Join anahtarı olmadan üretilecek
          her bağ boş ekrana götürürdü. Sayı `counts`'ta dürüstçe raporlanır.
──────────────────────────────────────────────────────────────────────────────

TEMBEL YÜKLEME: dosya ~2,6 MB — depodaki `dia_lite` (2,8 MB) ve `ei1_lite`
(2,8 MB) ile aynı büyüklük sınıfında ve onlarla aynı yolu izler: `SearchBar`
bunu ancak kullanıcı arama kutusuna ODAKLANDIĞINDA çeker (mevcut `sourcesArmed`
deseni). Açılış paketi etkilenmez.

NORMALİZASYON: burada YAPILMAZ. Ham ad yazılır; arayüz tek otorite
`bookkit/normalize` ile bir kez normalize eder. İki farklı normalize
uygulaması, H44/H51'de tam olarak bu depoda kırık aramaya yol açtı.

Çıktı: web/public/view-data/canonical_search.json
Determinizm: tip + pid sıralı, timestamp yok.
"""

import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
AUTHOR_WORKS = REPO / "web" / "public" / "view-data" / "author_works.json"
OUT = REPO / "web" / "public" / "view-data" / "canonical_search.json"

_READING_RE = re.compile(r"reading/(\d+)")
_SEC_RE = re.compile(r"§\s*(\d+)")


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def olaylar(s: Counter):
    """Kitap+bölüm çapası OLAN olaylar. Çapasız olan indekslenmez."""
    D = CANON / "event"
    if not D.is_dir():
        return []
    out = []
    for f in sorted(D.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        s["olay"] += 1
        if (d.get("provenance") or {}).get("deprecated"):
            s["olay_deprecated"] += 1
            continue
        prov = d.get("provenance") or {}
        df = (prov.get("derived_from") or [{}])[0]
        loc = df.get("page_or_locator", "") or ""
        mb, ms = _READING_RE.search(loc), _SEC_RE.search(loc)
        if not (mb and ms):
            s["olay_hedefsiz"] += 1        # dürüstçe indeks DIŞI
            continue
        pref = (d.get("labels") or {}).get("prefLabel") or {}
        ad_tr, ad_ar = pref.get("tr") or "", pref.get("ar") or ""
        if not (ad_tr or ad_ar):
            s["olay_adsiz"] += 1
            continue
        yil = (d.get("temporal") or {}).get("start_ah")
        # Hedef HAM DİZE olarak değil SAYI olarak taşınır: "#library?book=…&sec=…"
        # 9.102 kayıtta ~28 baytlık sabit önek demekti (~250 KB). Arayüz kurar.
        rec = {"t": "ce", "n": ad_tr[:120], "b": int(mb.group(1)), "s": int(ms.group(1))}
        if ad_ar:
            rec["a"] = ad_ar[:120]
        if yil is not None:
            rec["y"] = yil
        types = d.get("@type") or []
        if len(types) > 1:
            rec["k"] = types[1].split(":")[-1]
        out.append(rec)
        s["olay_indekslendi"] += 1
    return out


def eserler(s: Counter):
    """Müellifi havuzda olan eserler → müellifin eser listesine gider."""
    if not AUTHOR_WORKS.is_file():
        s["eser_kaynak_yok"] += 1
        return []
    doc = json.loads(AUTHOR_WORKS.read_text(encoding="utf-8"))
    E, Y = doc.get("eserler") or {}, doc.get("yazar") or {}
    eser_yazar = {}
    for kisi, ws in Y.items():
        for w in ws:
            eser_yazar[str(w)] = kisi

    out = []
    for w in sorted(E, key=int):
        s["eser"] += 1
        e = E[w]
        ad_tr, ad_ar = e.get("t") or "", e.get("a") or ""
        if not (ad_tr or ad_ar):
            s["eser_adsiz"] += 1
            continue
        # Sitede okunabilen esere DOĞRUDAN kitap bağı; ötekiler müellifine.
        kisi = eser_yazar.get(w)
        if not (e.get("r") or kisi):
            s["eser_hedefsiz"] += 1        # müellifsiz 19 kayıt
            continue
        rec = {"t": "cw", "n": ad_tr[:120]}
        if e.get("r"):
            rec["b"] = int(w)              # okunabilir → doğrudan kitap
        if kisi:
            rec["p"] = int(kisi)           # müellifin eser listesi
        if ad_ar:
            rec["a"] = ad_ar[:120]
        if e.get("k"):
            rec["k"] = e["k"][0]
        if e.get("y") is not None:
            rec["y"] = e["y"]
            if e.get("yk"):
                rec["yk"] = e["yk"]        # "912 öncesi" — çıplak yıl basılmaz
        if e.get("r"):
            rec["r"] = 1
        out.append(rec)
        s["eser_indekslendi"] += 1
    return out


def main() -> None:
    s = Counter()
    kayitlar = olaylar(s) + eserler(s)

    kurum = len(list((CANON / "institution").glob("*.json"))) if (CANON / "institution").is_dir() else 0
    s["kurum_hedefsiz_indekslenmedi"] = kurum

    doc = {
        "_doc": (
            "Merkezî defterin aranabilir katmanı. YALNIZ gerçekten açılan hedefi "
            "olan kayıtlar indekslenir (H46: sahte tıklanabilirlik, dürüst "
            "boşluktan kötüdür). 'ce' = canonical olay, `b`+`s` → #library?book&sec; "
            "'cw' = canonical eser, `b` varsa #library?book, yoksa `p` ile "
            "müellifin eser listesine #scholars?pid. Hedefler SAYI olarak "
            "taşınır (sabit önek 18.487 kez tekrarlanmasın), arayüz kurar. "
            "KURUMLAR İNDEKSLENMEZ: "
            "canonical institution pid'i v1 görünüm dosyalarında mint edilmemiş, "
            "yani açılabilir hedef YOK. Adlar HAM yazılır; normalizasyon tek "
            "otorite bookkit/normalize ile arayüzde yapılır. "
            "Üretici: build_canonical_search_index.py"
        ),
        "counts": dict(s),
        "kayitlar": kayitlar,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  OLAY  {s['olay']} → indekslendi {s['olay_indekslendi']} "
          f"(%{s['olay_indekslendi']*100//max(s['olay'],1)}) "
          f"· hedefi yok {s['olay_hedefsiz']} · adsız {s['olay_adsiz']}")
    print(f"  ESER  {s['eser']} → indekslendi {s['eser_indekslendi']} "
          f"· hedefi yok {s['eser_hedefsiz']} · adsız {s['eser_adsiz']}")
    print(f"  KURUM {kurum} → İNDEKSLENMEDİ (açılabilir hedef yok; join anahtarı "
          f"mint edilmemiş)")
    print(f"  toplam aranabilir kayıt: {len(kayitlar)}")


if __name__ == "__main__":
    main()
