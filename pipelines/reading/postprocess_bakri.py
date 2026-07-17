#!/usr/bin/env python3
"""
postprocess_bakri.py — Bekrî Mu'cem madde katmanı (H15b).

LLM çıkarımı (harf-bölümü başlıkları elenmiş, gerçek toponim maddeleri) →
mağazanın AR-etiket sözlüğüne SIKI birebir bağlama (bileşik-ad bölme YOK —
yapısal kısayolun 7-pid mıknatıs dersi). vocalization_ar + region_hint_ar
Bekrî'nin ayırt edici katkısı olarak korunur.

Çıktı: web/public/reading/00000991/layer.json (kind=entries) +
        data/sources/book-layers/00000991_entries.json +
        data/_state/bakri_augment_pending.json (place augment)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.reading.book_geo import build_geo_lexicon  # noqa: E402
from pipelines.reading.extract_book_mentions import norm_ar  # noqa: E402

# Harf-bölümü başlığı token'ları (yapısal kısayolun tuzağı — ELE)
_LETTERS = {norm_ar(x) for x in
            ("الهمزة", "الالف", "الألف", "الباء", "التاء", "الثاء", "الجيم",
             "الحاء", "الخاء", "الدال", "الذال", "الراء", "الزاي", "السين",
             "الشين", "الصاد", "الضاد", "الطاء", "الظاء", "العين", "الغين",
             "الفاء", "القاف", "الكاف", "اللام", "الميم", "النون", "الهاء",
             "الواو", "الياء", "باب")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    entries = raw["entries"] if isinstance(raw, dict) else raw

    # benzersizleştir + harf-başlığı ele
    seen, records = set(), []
    for e in entries:
        hw = (e.get("headword_ar") or "").strip()
        if not hw or e.get("sec") is None:
            continue
        key = (hw, e["sec"])
        if key in seen:
            continue
        seen.add(key)
        toks = [norm_ar(w.strip(" و")) for w in hw.split()]
        if any(tk in _LETTERS for tk in toks):
            continue
        records.append(e)
    records.sort(key=lambda r: (r["sec"], r["headword_ar"]))
    for i, r in enumerate(records):
        r["seq"] = i + 1
        r["name_ar"] = r["headword_ar"]        # UI ortak alanı
        r["type"] = "entry"

    # SIKI bağlama: tam-ad birebir (bölme yok)
    lex, _ = build_geo_lexicon()
    linked = 0
    aug: dict[str, list] = {}
    for r in records:
        n = norm_ar(r["headword_ar"].strip())
        if n.startswith("و") and len(n) > 4:
            n = n[1:]
        hit = lex.get(n)
        if hit:
            pid, lat, lon, note = hit
            r["place_pid"], r["lat"], r["lon"] = pid, lat, lon
            if note:
                r["geo_note"] = note
            linked += 1
            aug.setdefault(pid, []).append({"stop_id": r["seq"], "confidence": 0.85})

    manifest = json.loads((REPO_ROOT / "web/public/reading/00000991/manifest.json")
                          .read_text(encoding="utf-8"))
    layer = {
        "metadata": {
            "kind": "entries",
            "source_work": manifest["pid"],
            "book": manifest.get("name_tr"),
            "extraction": "Claude bölüm-bazlı madde çıkarımı (H15b; yapısal "
                          "kısayol harf-bölümü tuzağı yüzünden terk edildi)",
            "status": "PUBLISHED — sahip kararıyla doğrudan (H14 Karar)",
            "n_records": len(records), "n_geocoded": linked,
        },
        "kind": "entries", "records": records,
    }
    (REPO_ROOT / "web/public/reading/00000991/layer.json").write_text(
        json.dumps(layer, ensure_ascii=False), encoding="utf-8")
    (REPO_ROOT / "data/sources/book-layers/00000991_entries.json").write_text(
        json.dumps(layer, ensure_ascii=False, indent=1), encoding="utf-8")
    (REPO_ROOT / "data/_state/bakri_augment_pending.json").write_text(
        json.dumps({"augments": aug}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[bakri] madde={len(records)} · koordinatlı={linked} · "
          f"augment-pid={len(aug)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
