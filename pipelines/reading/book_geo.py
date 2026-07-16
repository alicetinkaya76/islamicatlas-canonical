#!/usr/bin/env python3
"""
book_geo.py — kitap-katmanlaştırma coğrafya araçları (H14; İbn Cübeyr
runbook'undan çıkarılan ortak modül).

Üç kademeli bağlama (hepsi koşu-kanıtlı):
  1. birebir AR-etiket + ad varyantları (tip-öneki/parantez/honorifik/vav)
  2. mağaza-mükerrer kümesi (<50 km) → en belirgin kayda bağla + not
  3. dağınık adaylar → BAĞLAM seçimi (çağıran politika verir):
     - rota bağlamı (seyahat): komşu duraklara en yakın aday (<=800 km)
     - merkez bağlamı (şehir yapıları): merkeze en yakın aday (<=radius)
     - bağlamsız (olaylar): bağlanmaz, adaylar kayda yazılır
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from pipelines.reading.extract_book_mentions import STOPLIST, norm_ar  # noqa: E402

_PREFIXES = ("جزيرة", "حصن", "قصر", "مدينة", "قرية", "جبل", "وادي", "نهر",
             "بلد", "باب", "بئر", "مسجد", "دار", "سوق", "مقبرة")
_HONORIFICS = {"المكرمة", "المشرفة", "المعظمة", "المنورة", "المقدسة"}


def haversine(a, b, c, d) -> float:
    p = math.pi / 180
    x = (math.sin((c - a) * p / 2) ** 2
         + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(x))


def build_geo_lexicon():
    """(lex, ambig): lex[n] = (pid, lat, lon, not|None); ambig[n] = [pid...]"""
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
    curies = dict(conn.execute("SELECT pid, COUNT(*) FROM source_curie GROUP BY pid"))
    raw = defaultdict(list)
    for text, pid, lat, lon in conn.execute(
            "SELECT l.text, l.pid, b.lat, b.lon FROM label l "
            "JOIN entity_bracket b ON b.pid = l.pid "
            "WHERE b.entity_type='place' AND l.lang='ar'"):
        n = norm_ar(text.strip())
        if n.startswith("و") and len(n) > 4:
            n = n[1:]
        if len(n) < 3 or n in STOPLIST:
            continue
        raw[n].append((pid, lat, lon, curies.get(pid, 1)))
    conn.close()
    lex, ambig = {}, {}
    for n, cands in raw.items():
        geo = [c for c in cands if c[1] is not None]
        best = max(cands, key=lambda c: c[3])
        if len(cands) == 1:
            lex[n] = (best[0], best[1], best[2], None)
        elif geo and all(haversine(geo[0][1], geo[0][2], g[1], g[2]) < 50 for g in geo):
            lex[n] = (best[0], best[1], best[2],
                      f"dup-cluster ({len(cands)} kayıt; en belirgin seçildi)")
        else:
            ambig[n] = [(c[0], c[1], c[2]) for c in cands][:6]
    return lex, ambig


def name_variants(name: str) -> list[str]:
    base = name.strip()
    outs = [base]
    if "(" in base:
        outs.append(base.split("(", 1)[0].strip())
        outs.append(base.split("(", 1)[1].rstrip(")").strip())
    for b in list(outs):
        if " و" in b:
            outs.extend(x.strip(" و") for x in b.split(" و") if x.strip(" و"))
    final = []
    hon = {norm_ar(h) for h in _HONORIFICS}
    pref = {norm_ar(x) for x in _PREFIXES}
    for b in outs:
        n = norm_ar(b)
        if n.startswith("و") and len(n) > 4:
            n = n[1:]
        toks = [w for w in n.split() if w not in hon]
        n = " ".join(toks)
        if not n:
            continue
        final.append(n)
        if len(toks) > 1 and toks[0] in pref:
            final.append(" ".join(toks[1:]))
    return list(dict.fromkeys(final))


def link_records(records: list[dict], name_key: str = "place_ar",
                 center: tuple | None = None, radius_km: float = 120.0) -> dict:
    """Kayıtlara place_pid/lat/lon işler (in-place). center verilirse
    merkez-bağlam politikası (şehir yapıları); verilmezse bağlamsız
    (olaylar: dağınık adaylar bağlanmaz)."""
    lex, ambig = build_geo_lexicon()
    stats = {"linked": 0, "unlinked": 0, "suspect": 0}
    for r in records:
        name = r.get(name_key) or r.get("name_ar") or ""
        if not name:
            stats["unlinked"] += 1
            continue
        hit = None
        for v in name_variants(name):
            if v in lex:
                hit = lex[v]
                break
        if hit:
            pid, lat, lon, note = hit
            r["place_pid"], r["lat"], r["lon"] = pid, lat, lon
            if note:
                r["geo_note"] = note
            stats["linked"] += 1
        else:
            cands = None
            for v in name_variants(name):
                if v in ambig:
                    cands = ambig[v]
                    break
            if cands and center:
                geo = [(p, la, lo) for p, la, lo in cands if la is not None]
                if geo:
                    best = min(geo, key=lambda c: haversine(center[0], center[1], c[1], c[2]))
                    d = haversine(center[0], center[1], best[1], best[2])
                    if d <= radius_km:
                        r["place_pid"], r["lat"], r["lon"] = best
                        r["geo_note"] = (f"BELİRSİZ ({len(cands)} aday) — merkez-"
                                         f"bağlamıyla seçildi ({d:.0f} km)")
                        stats["linked"] += 1
                        continue
            if cands:
                r["geo_candidates"] = [c[0] for c in cands]
            stats["unlinked"] += 1
        # merkez politikasında yarıçap dışı = şüpheli (haritada gizlenir)
        if center and r.get("lat") is not None:
            if haversine(center[0], center[1], r["lat"], r["lon"]) > radius_km:
                r["geo_suspect"] = True
                stats["suspect"] += 1
    return stats
