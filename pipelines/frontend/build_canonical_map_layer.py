#!/usr/bin/env python3
"""Ana harita için canonical OLAY katmanı üreticisi (H26; H56'da onarıldı).

SORUN: Ana #map (MapView) yalnız bundle'daki db.json'dan besleniyor (100
küratörlü savaş + 200 olay). Canonical mağazadaki 9.956 kitap-türevi olay
(Fütûh fetihleri, Vâkıdî gazveleri, Taberî/İbn Asâkir kronik olayları...)
ana haritada HİÇ görünmüyordu. Bu katman onları OPSİYONEL bir overlay olarak
getirir — v1 haritasına DOKUNMADAN (varsayılan kapalı toggle).

DÜRÜSTLÜK: Olayların kendi koordinatı yok; `location` bir canonical PLACE'e
işaret eder, koordinat oradan (gazetteer) gelir — uydurma değil, ama place'in
belirsizliğini taşır. Aynı yere düşen çok olay (Bağdat 388) → YER BAŞINA
TOPLANIR (tek marker, sayıya göre boyut, popup olay listesi).

──────────────────────────────────────────────────────────────────────────────
H56 DENETİMİ — bu dosyada ÜÇ kusur ölçüldü ve onarıldı:

  1) İKİ BAĞIMSIZ KESME ÜST ÜSTE BİNİYORDU. Burada `CAP = 25`, arayüzde
     `slice(0, 12)`. Marker popup'ı yerin GERÇEK olay sayısını yazıyor ama
     listeyi kesiyordu: Bağdat marker'ı "388" yazıp 12 satır gösteriyordu ve
     "+376 daha" satırının açılacak HİÇBİR hedefi yoktu.
     Ölçüldü: 5.618 çözülen olayın yalnız 2.616'sı (%46) ekrana ulaşıyordu.
     KARAR: kesme KALDIRILDI. Dağılım ölçüldü — en yoğun yer 388 olay, 721
     marker; CAP'siz payload %100 kapsıyor ve dosya ~1,6 MB oluyor. Katman
     zaten OPSİYONEL ve TEMBEL yükleniyor (varsayılan kapalı toggle), yani
     bu maliyet yalnız katmanı açan kullanıcıya düşüyor. Arayüz listeyi
     kaydırılabilir yapar; sayı ile içerik artık ÇELİŞMİYOR.

  2) KOORDİNAT BELİRSİZLİĞİ YAYINA HİÇ TAŞINMIYORDU. Kaynak place kaydı
     belirsizliğini dürüstçe ilan ediyor (`coords.uncertainty.type`,
     `coords.precision_meters`) — 18.411 yerde dolu: centroid 14.532 ·
     approximate 2.456 · exact 1.423; hassasiyet 250 km olan 5.121 yer var.
     Bu dosya hiçbirini okumuyordu: 250 km hassasiyetli bir bölge noktası,
     100 m hassasiyetli bir şehirle BİREBİR aynı görsel kesinlikte
     çiziliyordu. Artık `u` (tip) ve `pm` (metre) marker'a yazılıyor.

  3) EMEKLİ YERE BAĞLI OLAYLAR ZOMBİ MARKER ÜRETİYORDU. Yer indeksi yalnız
     koordinat bakıyordu; `deprecated` denetimi yoktu ve
     `deprecated_in_favor_of` hiç kullanılmıyordu. Sonuç: Kudüs'te sayı
     BÖLÜNÜYORDU (aktif kayıt 14 olay + emekli kayıt 1 olay, aynı koordinat).
     Artık emekli yerler indekse alınmıyor ve olayın location'ı zincir
     boyunca kazanana çözülüyor (H49/H50 dersi: "pid yaşar" ≠ "UI bulur").

  Ayrıca `subtype`: alt türü olmayan kayıtlara `"Event"` yazılıyordu — yani
  "alt tür yok" bilgisi ekranda bir TÜR gibi duruyordu (2.721 kayıt). Artık
  alan hiç yazılmaz; etiketlemeyi arayüz yapar.
──────────────────────────────────────────────────────────────────────────────

Çıktı: web/public/view-data/canonical_events.json (gitignored; build'de üretilir)
Şema: [{ pid, name_tr, name_ar, lat, lon, u?, pm?, count, subtypes:{tür:n},
         events:[{title_tr, title_ar, year_ah, subtype?, book_pid, sec}] }]
Determinizm: pid'e göre sıralı; olaylar yıl+id'ye göre sıralı; timestamp yok.
"""

import json
import re
import glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
OUT = REPO / "web" / "public" / "view-data" / "canonical_events.json"

# Aklıselim tavanı: kesme DEĞİL, kaçak denetimi. Ölçülen en yoğun yer 388
# olay taşıyor; bunu aşan bir yer çıkarsa veri tarafında bir şey bozulmuş
# demektir ve SESSİZCE kesmek yerine log'lanır.
SANITY = 2000

_READING_RE = re.compile(r"reading/(\d+)")
_SEC_RE = re.compile(r"§\s*(\d+)")

# uncertainty.type → tek harfli kod (payload küçük kalsın)
U_KOD = {"exact": "e", "approximate": "a", "centroid": "c"}


def load_place_index():
    """@id → kayıt. Emekli yerler DIŞARIDA; yönlendirme haritası ayrı döner."""
    idx, yonlendirme = {}, {}
    emekli_koordinatli = 0
    for f in glob.glob(str(CANON / "place" / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        prov = d.get("provenance") or {}
        c = d.get("coords") or {}
        lat, lon = c.get("lat"), c.get("lon")
        if prov.get("deprecated"):
            # Emekli kayıt indekse GİRMEZ; ama halefi biliniyorsa olayın
            # location'ı oraya çevrilebilsin diye yönlendirme saklanır.
            hedef = prov.get("deprecated_in_favor_of")
            if hedef:
                yonlendirme[d["@id"]] = hedef
            if lat is not None and lon is not None:
                emekli_koordinatli += 1
            continue
        if lat is None or lon is None:
            continue
        pref = (d.get("labels", {}) or {}).get("prefLabel", {}) or {}
        u = c.get("uncertainty")
        u_tip = u.get("type") if isinstance(u, dict) else (u if isinstance(u, str) else None)
        idx[d["@id"]] = {
            "lat": lat, "lon": lon,
            "tr": pref.get("tr", ""), "ar": pref.get("ar", ""),
            "u": U_KOD.get(u_tip),
            "pm": c.get("precision_meters"),
        }
    return idx, yonlendirme, emekli_koordinatli


def cozumle(loc, idx, yonlendirme):
    """Emekli pid → halefi (zincir + döngü korumalı). Bulunamazsa None."""
    gorulen = set()
    while loc is not None and loc not in idx:
        if loc in gorulen:
            return None
        gorulen.add(loc)
        loc = yonlendirme.get(loc)
    return loc


def parse_locator(prov):
    """provenance'tan (book_pid, sec) çıkar — 'reading/00001099 ... §1'."""
    df = (prov.get("derived_from") or [{}])[0]
    loc = df.get("page_or_locator", "") or ""
    m_book = _READING_RE.search(loc)
    m_sec = _SEC_RE.search(loc)
    return (m_book.group(1) if m_book else None,
            int(m_sec.group(1)) if m_sec else None)


def build():
    idx, yonlendirme, emekli_koordinatli = load_place_index()
    agg = {}
    s = {"olay": 0, "deprecated_olay": 0, "location_yok": 0,
         "yonlendirilen": 0, "cozulemeyen": 0, "alt_tursuz": 0}

    for f in glob.glob(str(CANON / "event" / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        s["olay"] += 1
        if d.get("provenance", {}).get("deprecated"):
            s["deprecated_olay"] += 1
            continue
        loc = d.get("location")
        loc = loc[0] if isinstance(loc, list) and loc else loc
        if not loc:
            s["location_yok"] += 1
            continue
        ham = loc
        loc = cozumle(loc, idx, yonlendirme)
        if loc is None:
            s["cozulemeyen"] += 1
            continue
        if loc != ham:
            s["yonlendirilen"] += 1

        p = idx[loc]
        types = d.get("@type") or []
        # H56: alt türü yoksa "Event" YAZMA — "tür yok" bir tür değildir.
        subtype = types[1].split(":")[-1] if len(types) > 1 else None
        if subtype is None:
            s["alt_tursuz"] += 1
        pref = (d.get("labels", {}) or {}).get("prefLabel", {}) or {}
        book_pid, sec = parse_locator(d.get("provenance", {}))
        ev = {
            "title_tr": pref.get("tr", ""),
            "title_ar": pref.get("ar", ""),
            "year_ah": (d.get("temporal") or {}).get("start_ah"),
            "book_pid": book_pid,
            "sec": sec,
            "_id": d["@id"],
        }
        if subtype:
            ev["subtype"] = subtype

        b = agg.setdefault(loc, {
            "pid": loc, "name_tr": p["tr"], "name_ar": p["ar"],
            "lat": round(p["lat"], 5), "lon": round(p["lon"], 5),
            "count": 0, "subtypes": {}, "events": [],
        })
        # H56: koordinat belirsizliği marker'a taşınır (eskiden hiç taşınmıyordu).
        if p["u"] and "u" not in b:
            b["u"] = p["u"]
        if p["pm"] is not None and "pm" not in b:
            b["pm"] = p["pm"]
        b["count"] += 1
        anahtar = subtype or "_yok"
        b["subtypes"][anahtar] = b["subtypes"].get(anahtar, 0) + 1
        b["events"].append(ev)

    out, kacak = [], []
    for pid in sorted(agg):
        b = agg[pid]
        b["events"].sort(key=lambda e: (e["year_ah"] is None, e["year_ah"] or 0, e["_id"]))
        for e in b["events"]:
            e.pop("_id", None)
        # H56: KESME YOK. Tavan yalnız kaçak denetimi; aşılırsa SESSİZ KALINMAZ.
        if len(b["events"]) > SANITY:
            kacak.append((pid, len(b["events"])))
            b["events"] = b["events"][:SANITY]
            b["_kesildi"] = True
        out.append(b)
    return out, s, kacak, emekli_koordinatli


def main():
    records, s, kacak, emekli_koordinatli = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
        f.write("\n")

    toplam = sum(r["count"] for r in records)
    payload = sum(len(r["events"]) for r in records)
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  olay dosyası {s['olay']} · yer (marker) {len(records)}")
    print(f"  çözülen olay {toplam} · payload'a giren {payload} "
          f"(%{payload*100//max(toplam,1)}) — KESME YOK")
    # Sessiz düşürme yok: neyin neden dışarıda kaldığı yazılır.
    print(f"  DIŞARIDA: location alanı yok {s['location_yok']} "
          f"· location çözülemedi {s['cozulemeyen']} · deprecated olay {s['deprecated_olay']}")
    print(f"  emekli yere bağlıyken halefe YÖNLENDİRİLEN olay: {s['yonlendirilen']}")
    print(f"  (emekli ama koordinatlı yer, artık indekse alınmıyor: {emekli_koordinatli})")
    print(f"  alt türü olmayan olay (artık 'Event' YAZILMIYOR): {s['alt_tursuz']}")
    belirsiz = sum(r["count"] for r in records if r.get("u") in ("c", "a"))
    print(f"  belirsiz koordinat üzerindeki olay: {belirsiz} "
          f"(%{belirsiz*100//max(toplam,1)}) — marker artık bunu söylüyor")
    if kacak:
        print(f"  ! aklıselim tavanı aşan yer: {kacak}")
    top = sorted(records, key=lambda r: -r["count"])[:5]
    print("  en yoğun: " + ", ".join(f"{r['name_tr'] or r['pid']}={r['count']}" for r in top))


if __name__ == "__main__":
    main()
