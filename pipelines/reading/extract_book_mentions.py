#!/usr/bin/env python3
"""
extract_book_mentions.py — Çekirdek Külliyat kitap→yer anılma çıkarımı
(H13 S-E; "her kitabın kendi haritası").

Okuma verisindeki her bölümün Arapça metni, mağazanın 18,380 Arapça-etiketli
yer kaydına karşı taranır. FUZZY YOK — dia_travel'da kanıtlanmış
belirsizlik-korumalı birebir desen, Arapça sürümü:

  norm(metin n-gramı) == norm(yer etiketi)  VE  etiket TEKİL pid'e çıkıyor
  VE  norm uzunluğu >= 4  VE  editoryal stoplist'te değil

Normalizasyon: hareke/tatvil temizliği, أإآ→ا, ى→ي, ة→ه, baştaki و
kliliği her iki tarafta düşer. En-uzun-eşleşme önce (4→1 token).

Çıktı: web/public/reading/<pidnum>/mentions.json
         {places: [{pid,name,lat,lon,total,secs:[…]}], sections:{i:[pid…]}}
       + data/_state/core_canon_mentions_batch1.json (ileriki olay-mint /
         küratörlük çalışmalarının girdisi; canonical'a YAZILMAZ).
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
READING = REPO_ROOT / "web/public/reading"

DIAC = re.compile(r"[ؐ-ًؚ-ٰٟـ]")
TOKEN = re.compile(r"[؀-ۿ]+")

# Genel-ad çakışmaları: klasik metinde yer adı olmayan sık kelimeler.
# (İlk koşunun top-eşleşme dökümünden ELLE seçildi — journal'da gerekçe.)
STOPLIST = {"الجمعة", "الجماعة", "السلام", "الاسلام", "القبلة", "الحرم",
            "الجنة", "النار", "الدنيا", "الاخرة", "البيت", "المسجد",
            "الكعبة", "منبر", "السوق", "الباب", "القصر", "الدار", "النهر",
            "الجبل", "البحر", "العرب", "العجم",
            # genel cins isimler (ilk koşu top-eşleşme dökümünden):
            "مدينة", "قرية", "بلاد", "كبيرة", "قالوا", "ساقطة", "التي",
            "ألتي", "ألتى", "النبي", "قصبة", "جزيرة", "ناحية", "كورة",
            # sayılar/günler/sık fiil-isimler (2. koşu dökümünden):
            "ثلاث", "ثلاثة", "اربع", "اربعة", "خمسة", "ستة", "سبعة",
            "ثمان", "ثمانية", "تسعة", "عشرة", "عشرون", "ثلاثون",
            "الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس", "السبت",
            "فكان", "اراد", "أراد", "الرجل", "رجلان", "ورجلان", "سائر",
            "مياه", "نخيل", "كثيرة", "قليلة", "العروس", "المراكب",
            "اذرع", "أذرع", "قرات", "مشهد", "البلدة", "رستاق", "طويل",
            # 3. koşu dökümü (belirgin-kayıt homografları):
            "كلام", "جريب", "ستين", "خراب", "الحال", "الظهر", "الصفة",
            "الحجارة", "سواء", "باذن", "بأذن", "كوفى", "البير", "مرحب",
            "السرية", "الغد", "الشمال", "اليمين", "يسير", "قريب", "بعيد",
            "عظيم", "الفتح", "النصر", "الخليج", "سوق", "نهر", "وادي",
            "جبل", "عين", "بئر", "قصر", "حصن", "دير", "تل"}
# not: kavim adları (الروم/الترك/الهند...) tip-ötesi korumaya bırakıldı;
# genel cins isimler kesinlik için bilinçli feda.


def norm_ar(s: str) -> str:
    """ة→ه YAPILMAZ (ilk koşu kanıtı: yer 'علية' ile edat 'عليه' birleşip
    her kitapta binlerce sahte anılma üretti)."""
    s = DIAC.sub("", s)
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
         .replace("ى", "ي"))
    return s


def build_lexicon() -> dict:
    """norm(ad) → (pid, orijinal_ad, lat, lon); yalnız TEKİL-pid adlar.

    TİP-ÖTESİ KORUMA (ilk koşu kanıtı: عمرو/يزيد/الحسن/إسماعيل kişi adları
    yer olarak eşleşti): tek-token bir ad mağazada HERHANGİ bir kişi
    etiketiyle de çakışıyorsa sözlüğe girmez — metinde o kelime çoğunlukla
    kişidir; yer okuması tekil-pid olsa bile güvenilmez."""
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
    person_words: set[str] = set()
    for (text,) in conn.execute(
            "SELECT l.text FROM label l JOIN entity_bracket b ON b.pid=l.pid "
            "WHERE b.entity_type='person' AND l.lang IN ('ar','tr')"):
        for w in TOKEN.findall(text):
            person_words.add(norm_ar(w))
    raw: dict[str, set] = defaultdict(set)
    meta: dict[str, tuple] = {}
    for text, pid, lat, lon in conn.execute(
            "SELECT l.text, l.pid, b.lat, b.lon FROM label l "
            "JOIN entity_bracket b ON b.pid = l.pid "
            "WHERE b.entity_type='place' AND l.lang='ar'"):
        n = norm_ar(text.strip())
        if n.startswith("و") and len(n) > 4:
            n = n[1:]
        if len(n) < 4 or n in STOPLIST:
            continue
        if " " not in n and n in person_words:
            continue                      # tip-ötesi çakışma → dışarıda
        raw[n].add(pid)
        meta[n] = (text.strip(), lat, lon)
    # belirginlik: ≥2 kaynak-curie'li YA DA otorite bağlı kayıtlar
    prominent: set[str] = set()
    for pid, cnt in conn.execute(
            "SELECT pid, COUNT(*) FROM source_curie GROUP BY pid HAVING COUNT(*) >= 2"):
        prominent.add(pid)
    for (pid,) in conn.execute("SELECT DISTINCT pid FROM authority_xref"):
        prominent.add(pid)
    conn.close()
    lex = {}
    for n, pids in raw.items():
        if len(pids) != 1:
            continue
        toks = n.split()
        # künye koruması: çok-kelimeli adın TÜM token'ları kişi-kelimesiyse
        # (أبو محمد) yer okuması güvenilmez
        if len(toks) > 1 and all(w in person_words for w in toks):
            continue
        name, lat, lon = meta[n]
        pid = next(iter(pids))
        lex[n] = (pid, name, lat, lon, pid in prominent)
    return lex


def main() -> int:
    lex = build_lexicon()
    # ilk-token indeksli n-gram sözlüğü (1..4 token)
    by_first: dict[str, list] = defaultdict(list)
    for n in lex:
        toks = tuple(n.split())
        if 1 <= len(toks) <= 4:
            by_first[toks[0]].append(toks)
    for k in by_first:
        by_first[k].sort(key=len, reverse=True)   # uzun eşleşme önce
    print(f"sözlük: {len(lex):,} tekil ad")

    shelf = json.loads((READING / "core_shelf.json").read_text(encoding="utf-8"))
    aggregate = {}
    # GEÇİŞ 1: ham eşleşmeleri topla (kitap → bölüm → ad → sayı)
    raw_books: dict[str, dict] = {}
    for book in shelf["books"]:
        pdir = READING / book["pidnum"]
        manifest = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
        sec_places: dict[int, dict] = {}
        place_secs: dict[str, dict] = {}
        for sec in manifest["sections"]:
            i = sec["i"]
            data = json.loads((pdir / f"sec_{i:04d}.json").read_text(encoding="utf-8"))
            counts: dict[str, int] = defaultdict(int)
            for para in data["paras"]:
                toks = [norm_ar(t) for t in TOKEN.findall(para["t"])]
                # klitik varyantı: baştaki ال korunur (etiketler genelde ال'li);
                # ek olarak و düşmüş varyantı norm'da hazır.
                j = 0
                while j < len(toks):
                    hit = None
                    for cand in by_first.get(toks[j], ()):
                        if tuple(toks[j:j + len(cand)]) == cand:
                            hit = cand
                            break
                    if hit:
                        counts[" ".join(hit)] += 1
                        j += len(hit)
                    else:
                        j += 1
            if counts:
                sec_places[i] = counts
        raw_books[book["pidnum"]] = {"manifest": manifest, "sec_places": sec_places,
                                     "book": book}

    # DF: ad kaç kitapta geçiyor? Tek-kelimelik SİLİK ad her kitapta
    # geçiyorsa homograftır (şöhret-veya-yerellik kuralı, H13 S-E).
    df: dict[str, int] = defaultdict(int)
    for rb in raw_books.values():
        seen = set()
        for counts in rb["sec_places"].values():
            seen.update(counts)
        for n in seen:
            df[n] += 1

    def accept(n: str) -> bool:
        pid, name, lat, lon, prom = lex[n]
        if " " in n:
            return True
        return prom or df[n] <= 3

    # GEÇİŞ 2: filtrele + yaz
    for pidnum, rb in raw_books.items():
        manifest, book = rb["manifest"], rb["book"]
        pdir = READING / pidnum
        sec_places = {i: {n: c for n, c in counts.items() if accept(n)}
                      for i, counts in rb["sec_places"].items()}
        sec_places = {i: c for i, c in sec_places.items() if c}
        place_secs: dict[str, dict] = {}
        for i, counts in sec_places.items():
            for n, c in counts.items():
                pid, name, lat, lon, prom = lex[n]
                e = place_secs.setdefault(pid, {"pid": pid, "name": name,
                                                "lat": lat, "lon": lon,
                                                "total": 0, "secs": []})
                e["total"] += c
                if i not in e["secs"]:
                    e["secs"].append(i)

        places = sorted(place_secs.values(), key=lambda e: -e["total"])
        out = {
            "pid": manifest["pid"],
            "n_places": len(places),
            "n_geocoded": sum(1 for p in places if p["lat"] is not None),
            "places": places,
            "sections": {str(i): sorted(c, key=lambda n: -c[n])[:12]
                         for i, c in sec_places.items()},
            "sec_pids": {str(i): [lex[n][0] for n in
                                  sorted(c, key=lambda n: -c[n])[:12]]
                         for i, c in sec_places.items()},
        }
        out["sections"] = {str(i): [lex[n][1] for n in
                                    sorted(c, key=lambda n: -c[n])[:12]]
                           for i, c in sec_places.items()}
        (pdir / "mentions.json").write_text(
            json.dumps(out, ensure_ascii=False), encoding="utf-8")
        aggregate[manifest["pid"]] = {"uri": manifest["uri"],
                                      "n_places": len(places),
                                      "top": [(p["name"], p["total"]) for p in places[:8]]}
        print(f"✓ {book['name_tr'][:40]:42s} yer: {len(places):5,} "
              f"(koordinatlı {out['n_geocoded']:5,}) · top: "
              f"{', '.join(p['name'] for p in places[:4])}")

    (REPO_ROOT / "data/_state/core_canon_mentions_batch1.json").write_text(
        json.dumps({"_doc": "Kitap→yer anılmaları (birebir, belirsizlik-korumalı; "
                            "olay-mint/küratörlük girdisi).", "books": aggregate},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
