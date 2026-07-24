#!/usr/bin/env python3
"""Ana harita için canonical OLAY katmanı üreticisi (H26).

SORUN: Ana #map (MapView) yalnız bundle'daki db.json'dan besleniyor (100
küratörlü savaş + 200 olay). Canonical mağazadaki 9.956 kitap-türevi olay
(Fütûh fetihleri, Vâkıdî gazveleri, Taberî/İbn Asâkir kronik olayları...)
ana haritada HİÇ görünmüyordu. Bu katman onları OPSİYONEL bir overlay olarak
getirir — v1 haritasına DOKUNMADAN (varsayılan kapalı toggle).

DÜRÜSTLÜK: Olayların kendi koordinatı yok; `location` bir canonical PLACE'e
işaret eder, koordinat oradan (gazetteer) gelir — uydurma değil, ama place'in
belirsizliğini taşır. Aynı yere düşen çok olay (Bağdat 388) → YER BAŞINA
TOPLANIR (tek marker, sayıya göre boyut, popup olay listesi) — 5.618 üst üste
marker yerine ~yer sayısı kadar temiz nokta.

Çıktı: web/public/view-data/canonical_events.json (gitignored; build'de üretilir)
Şema: [{ pid, name_tr, name_ar, lat, lon, count, subtypes:{tür:n},
         events:[{title_tr, title_ar, year_ah, subtype, book_pid, sec}] (≤ CAP) }]
Determinizm: pid'e göre sıralı; olaylar yıl+id'ye göre sıralı; timestamp yok.
Çalıştırma: python3 pipelines/frontend/build_canonical_map_layer.py
"""

import json
import re
import glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
OUT = REPO / "web" / "public" / "view-data" / "canonical_events.json"

CAP = 25  # yer başına popup'ta gösterilecek en fazla olay (count gerçek toplamı verir)

_READING_RE = re.compile(r"reading/(\d+)")
_SEC_RE = re.compile(r"§\s*(\d+)")


def load_place_index():
    """@id → (lat, lon, name_tr, name_ar) — koordinatlı canonical yerler."""
    idx = {}
    for f in glob.glob(str(CANON / "place" / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        c = d.get("coords") or {}
        lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            continue
        pref = (d.get("labels", {}) or {}).get("prefLabel", {}) or {}
        idx[d["@id"]] = (lat, lon, pref.get("tr", ""), pref.get("ar", ""))
    return idx


def parse_locator(prov):
    """provenance'tan (book_pid, sec) çıkar — 'reading/00001099 ... §1'."""
    df = (prov.get("derived_from") or [{}])[0]
    loc = df.get("page_or_locator", "") or ""
    m_book = _READING_RE.search(loc)
    m_sec = _SEC_RE.search(loc)
    return (m_book.group(1) if m_book else None,
            int(m_sec.group(1)) if m_sec else None)


def build():
    places = load_place_index()
    agg = {}  # place_pid → bucket
    for f in glob.glob(str(CANON / "event" / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        # emekli/silinmiş olayı atla
        if d.get("provenance", {}).get("deprecated"):
            continue
        loc = d.get("location")
        loc = loc[0] if isinstance(loc, list) and loc else loc
        if loc not in places:
            continue
        lat, lon, pname_tr, pname_ar = places[loc]
        types = d.get("@type") or []
        subtype = types[1].split(":")[-1] if len(types) > 1 else "Event"
        pref = (d.get("labels", {}) or {}).get("prefLabel", {}) or {}
        book_pid, sec = parse_locator(d.get("provenance", {}))
        ev = {
            "title_tr": pref.get("tr", ""),
            "title_ar": pref.get("ar", ""),
            "year_ah": (d.get("temporal") or {}).get("start_ah"),
            "subtype": subtype,
            "book_pid": book_pid,
            "sec": sec,
            "_id": d["@id"],
        }
        b = agg.setdefault(loc, {
            "pid": loc, "name_tr": pname_tr, "name_ar": pname_ar,
            "lat": round(lat, 5), "lon": round(lon, 5),
            "count": 0, "subtypes": {}, "events": [],
        })
        b["count"] += 1
        b["subtypes"][subtype] = b["subtypes"].get(subtype, 0) + 1
        b["events"].append(ev)

    out = []
    for pid in sorted(agg):
        b = agg[pid]
        # olayları yıl (None sona) + id'ye göre sırala, ilk CAP'i tut
        b["events"].sort(key=lambda e: (e["year_ah"] is None, e["year_ah"] or 0, e["_id"]))
        for e in b["events"]:
            e.pop("_id", None)
        b["events"] = b["events"][:CAP]
        out.append(b)
    # en yoğun yerler önce çizilsin diye değil — pid sıralı (determinizm); UI boyutlar
    return out


def main():
    records = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
        f.write("\n")
    total_ev = sum(r["count"] for r in records)
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  yer (marker): {len(records)}")
    print(f"  toplam çözülen olay: {total_ev}")
    top = sorted(records, key=lambda r: -r["count"])[:5]
    print("  en yoğun: " + ", ".join(f"{r['name_tr'] or r['pid']}={r['count']}" for r in top))


if __name__ == "__main__":
    main()
