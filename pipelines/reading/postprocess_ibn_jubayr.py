#!/usr/bin/env python3
"""
postprocess_ibn_jubayr.py — İbn Cübeyr durak çıkarımının son-işlemi
(H14; v1 "kitabı Claude'a yükle → katman çıkar" sürecinin bizim boru
hattımızdaki disiplinli sürümü).

Girdi : çıkarım workflow'unun ham durakları (JSON; --input)
Adım  : (1) sıraya diz (sec, bölüm-içi sıra korunur)
        (2) ardışık aynı-yer duraklarını birleştir (norm(name_ar) eşit)
        (3) koordinat: mağazanın AR-etiket sözlüğüyle BİREBİR eşleme
            (mentions çıkarımıyla aynı korumalar: tekil-pid, tip-ötesi,
            stoplist) → pid+lat/lon; eşleşmeyen koordinatsız kalır
        (4) HER kayda needs_human_review=true (North Star: otomatik
            çıkarım onaysız yayınlanmaz); confidence<high ayrıca işaretli
Çıktı : data/sources/ibn-jubayr/ibn_jubayr_stops_draft.json
        (v1 ibn_battuta_atlas_layer şekline yakın: metadata+stops)
        + data/review_queue/ibn-jubayr-stops.jsonl (onay kuyruğu)
        + web/public/reading/00002694/stops_draft.json (UI taslak rotası)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.reading.extract_book_mentions import (  # noqa: E402
    STOPLIST, TOKEN, norm_ar)
import sqlite3
from collections import defaultdict


def haversine(a, b, c, d):
    import math
    p = math.pi / 180
    x = (math.sin((c - a) * p / 2) ** 2
         + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(x))


def build_stop_lexicon():
    """Rota-geocoding sözlüğü: mentions'tan FARKLI olarak çok-pid'li adlara
    izin verir — adaylar 50 km içinde kümeleniyorsa AYNI ŞEHRİN mağaza
    mükerrerleridir (Mekke×8 vakası) → en belirgin (en çok kaynak-curie'li)
    kayda bağlanır + dup-cluster notu; dağınıksa (Trablus Şam/Libya sınıfı)
    bağlanmaz, aday listesi incelemeciye gider. Her kayıt zaten
    needs_human_review."""
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
        elif geo and all(haversine(geo[0][1], geo[0][2], g[1], g[2]) < 50
                         for g in geo):
            lex[n] = (best[0], best[1], best[2],
                      f"dup-cluster ({len(cands)} kayıt; en belirgin seçildi)")
        else:
            ambig[n] = [c[0] for c in cands][:6]
    return lex, ambig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="ham durak JSON (workflow çıktısı)")
    args = ap.parse_args()
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    stops = raw["stops"] if isinstance(raw, dict) else raw
    stops = [s for s in stops if s.get("name_ar") and s.get("sec") is not None]
    stops.sort(key=lambda s: (s["sec"],))

    # (2) ardışık aynı-yer birleştirme
    merged: list[dict] = []
    for s in stops:
        key = norm_ar(s["name_ar"])
        if merged and norm_ar(merged[-1]["name_ar"]) == key:
            m = merged[-1]
            m["stay_summary_tr"] = (m.get("stay_summary_tr") or "")
            add = s.get("stay_summary_tr") or ""
            if add and add not in m["stay_summary_tr"]:
                m["stay_summary_tr"] = (m["stay_summary_tr"] + " " + add).strip()[:1200]
            if not m.get("arrival_h") and s.get("arrival_h"):
                m["arrival_h"] = s["arrival_h"]
                m["arrival_text"] = s.get("arrival_text")
            if s.get("departure_text"):
                m["departure_text"] = s["departure_text"]
            seen = {(p.get("name"), p.get("role")) for p in m.get("people") or []}
            for p in s.get("people") or []:
                if (p.get("name"), p.get("role")) not in seen:
                    m.setdefault("people", []).append(p)
            m.setdefault("secs", [m["sec"]])
            if s["sec"] not in m["secs"]:
                m["secs"].append(s["sec"])
            m["is_stay"] = bool(m.get("is_stay")) or bool(s.get("is_stay"))
            continue
        s["secs"] = [s["sec"]]
        merged.append(s)

    # (3) koordinat çözümü — rota sözlüğü (küme-çözümlü)
    lex, ambig = build_stop_lexicon()
    linked = unlinked = 0
    # tip-önekleri: çıkarım adları "جزيرة طريف/حصن قبرة/مدينة X" biçiminde
    # gelebilir; sözlük çıplak ad ister — önek soyulmuş varyantlar denenir.
    _PREFIXES = ("جزيرة", "حصن", "قصر", "مدينة", "قرية", "جبل", "وادي", "نهر", "بلد")

    _HONORIFICS = {"المكرمة", "المشرفة", "المعظمة", "المنورة", "المقدسة"}

    def _variants(name: str):
        base = name.strip()
        outs = [base]
        if "(" in base:                       # "بغداد (مدينة السلام)" → iki ad
            outs.append(base.split("(", 1)[0].strip())
            outs.append(base.split("(", 1)[1].rstrip(")").strip())
        for b in list(outs):
            if " و" in b:                     # "مصر والقاهرة" → parçalar
                outs.extend(x.strip(" و") for x in b.split(" و") if x.strip(" و"))
        final = []
        for b in outs:
            n = norm_ar(b)
            if n.startswith("و") and len(n) > 4:
                n = n[1:]
            toks = [w for w in n.split() if w not in
                    {norm_ar(h) for h in _HONORIFICS}]
            n = " ".join(toks)
            if not n:
                continue
            final.append(n)
            if len(toks) > 1 and toks[0] in [norm_ar(x) for x in _PREFIXES]:
                final.append(" ".join(toks[1:]))
        return list(dict.fromkeys(final))

    def lookup(name: str):
        for c in _variants(name):
            if c in lex:
                return lex[c]
        return None

    def lookup_ambig(name: str):
        for c in _variants(name):
            if c in ambig:
                return c, ambig[c]
        return None, None

    for i, s in enumerate(merged):
        s["seq"] = i + 1
        hit = lookup(s["name_ar"])
        if hit:
            pid, lat, lon, geo_note = hit
            s["place_pid"] = pid
            s["lat"], s["lon"] = lat, lon
            if geo_note:
                s["geo_note"] = geo_note
            linked += 1
        else:
            key, cands = lookup_ambig(s["name_ar"])
            if cands:
                s["_ambig_cands"] = cands   # 2. geçişte rota-bağlamıyla seçilir
            unlinked += 1
        s["needs_human_review"] = True

    # (3b) BELİRSİZ adaylar: ROTA-BAĞLAMI seçimi — komşu geocode'lu duraklara
    # (seq ±5) en yakın aday; >800 km kopuksa bağlanmaz (Mansûra vakası:
    # 'en belirgin' kuralı İspanya dönüş durağını Orta Asya adaşına bağladı).
    import sqlite3 as _sq
    conn = _sq.connect(REPO_ROOT / "data/_index/lookup.sqlite")

    def _coords_of(cpid):
        row = conn.execute("SELECT lat, lon FROM entity_bracket WHERE pid=?",
                           (cpid,)).fetchone()
        return row if row and row[0] is not None else None

    def _neighbors(idx):
        out = []
        for d in range(1, 6):
            for j in (idx - d, idx + d):
                if 0 <= j < len(merged) and merged[j].get("lat") is not None:
                    out.append((merged[j]["lat"], merged[j]["lon"]))
            if len(out) >= 2:
                break
        return out

    for idx, s in enumerate(merged):
        cands = s.pop("_ambig_cands", None)
        if not cands or s.get("lat") is not None:
            continue
        nbrs = _neighbors(idx)
        best = None
        for cpid in cands:
            co = _coords_of(cpid)
            if not co:
                continue
            dmin = min((haversine(co[0], co[1], a, b) for a, b in nbrs),
                       default=None)
            if dmin is not None and (best is None or dmin < best[3]):
                best = (cpid, co[0], co[1], dmin)
        if best and best[3] <= 800:
            s["place_pid"], s["lat"], s["lon"] = best[0], best[1], best[2]
            s["geo_note"] = (f"BELİRSİZ ({len(cands)} aday) — rota-bağlamıyla "
                             f"seçildi ({best[3]:.0f} km komşuya); incelemede "
                             f"doğrulanmalı")
            s["geo_candidates"] = cands
            linked += 1
            unlinked -= 1
        else:
            s["geo_candidates"] = cands

    # (3c) süreklilik süpürmesi: her geocode'lu durak için iki komşuya da
    # >800 km ise geo_suspect — taslak haritada gizlenir, kuyrukta kalır.
    n_suspect = 0
    for idx, s in enumerate(merged):
        if s.get("lat") is None:
            continue
        nbrs = _neighbors(idx)
        if nbrs and all(haversine(s["lat"], s["lon"], a, b) > 800
                        for a, b in nbrs):
            s["geo_suspect"] = True
            n_suspect += 1
    conn.close()

    out_dir = REPO_ROOT / "data/sources/ibn-jubayr"
    out_dir.mkdir(parents=True, exist_ok=True)
    layer = {
        "metadata": {
            "layer": "ibn-jubayr-rihla",
            "source_work": "iac:work-00002694",
            "source_text": "0614IbnJubayr.Rihla (OpenITI; Rafed neşri sayfa çapaları)",
            "extraction": "Claude bölüm-bazlı yapılandırılmış çıkarım "
                          "(25 paralel ajan) + deterministik birleştirme + "
                          "birebir AR-etiket koordinat çözümü — H14",
            "status": "DRAFT — needs_human_review; onaysız yayınlanmaz "
                      "(North Star)",
            "n_stops": len(merged),
            "n_geocoded": linked,
        },
        "stops": merged,
    }
    (out_dir / "ibn_jubayr_stops_draft.json").write_text(
        json.dumps(layer, ensure_ascii=False, indent=1), encoding="utf-8")
    (REPO_ROOT / "web/public/reading/00002694/stops_draft.json").write_text(
        json.dumps(layer, ensure_ascii=False), encoding="utf-8")
    qdir = REPO_ROOT / "data/review_queue"
    qdir.mkdir(exist_ok=True)
    with (qdir / "ibn-jubayr-stops.jsonl").open("w", encoding="utf-8") as f:
        for s in merged:
            f.write(json.dumps({
                "queue_id": f"ibnjubayr-stop-{s['seq']:03d}",
                "adapter_id": "ibn-jubayr-rihla",
                "kind": "extracted_travel_stop",
                "name_ar": s["name_ar"], "name_tr": s.get("name_tr"),
                "arrival": s.get("arrival_text"), "sec": s["sec"],
                "page": s.get("page"), "confidence": s.get("confidence"),
                "place_pid": s.get("place_pid"),
                "quote_ar": (s.get("quote_ar") or "")[:200],
            }, ensure_ascii=False) + "\n")

    print(f"  süreklilik: geo_suspect={n_suspect}")
    lows = sum(1 for s in merged if s.get("confidence") != "high")
    dated = sum(1 for s in merged if s.get("arrival_h") or s.get("arrival_text"))
    print(f"[ibn_jubayr] durak={len(merged)} (ham {len(stops)}) · "
          f"koordinatlı={linked} · koordinatsız={unlinked} · tarihli={dated} · "
          f"confidence<high={lows} → taslak + onay kuyruğu yazıldı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
