#!/usr/bin/env python3
"""
h20_layer_curie_resolve.py — Dalga 3: kaynak-curie'si OLMAYAN katman
kayıtlarının Tier-2 ile MEVCUT mağaza kayıtlarına eşleştirilmesi (H20).

Sorun (H19 kapısı): le-strange kabı %50 (215/434), darp-islam %69
(2.338/3.381). Eksikler MİNT eksiği değil — eksiklerin çoğu Bağdat, Basra,
Kûfe gibi mağazada zaten var olan ünlü şehirler; yalnız kaynak curie'si
(le-strange:4 / darp-islam:9) hiçbir pid'e bağlı değil.

Bu script MAĞAZAYA YAZMAZ. Yalnız ölçer + sınıflandırır:
    match  → data/_state/h20_<layer>_augment_pending.json `augments` altında
             (apply_layer_augments.py'nin okuduğu şekil: {pid: [event,...]})
    review → resolver kuyruğu data/review_queue/h20-<layer>.jsonl
             (borderline'lar insanda kalır — North Star)
    new    → `unmatched` altında triage havuzu; MİNT YOK

Zamansal sinyal BİLEREK verilmez: bu kaynaklarda yıl kimlik değil TANIKLIK
yılıdır (sikke basım aralığı; Le Strange'in kuruluş notu) — H10 final-review
dersi (Aydhab/Sehwan/Kûlam). Yer eşleşmesi ad + konum üstünden kurulur;
koordinat varsa sinyal sayısı 2 olur ve auto-match kapısı açılabilir.

Usage:
  python3 pipelines/integrity/h20_layer_curie_resolve.py --layer le-strange
  python3 pipelines/integrity/h20_layer_curie_resolve.py --layer darp-islam
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402

LAYERS = {
    "le-strange": {
        "data": "web/public/data/le_strange_eastern_caliphate.json",
        "records_key": None,             # dosya doğrudan liste
        "adapter": "h20-lestrange",
        "evidence_key": "lestrange_id",
        "out": "data/_state/h20_lestrange_augment_pending.json",
    },
    "darp-islam": {
        "data": "web/public/data/darpislam_lite.json",
        "records_key": "mints",
        "adapter": "h20-darpislam",
        "evidence_key": "darp_id",
        "out": "data/_state/h20_darpislam_augment_pending.json",
    },
}


def load_records(cfg: dict) -> list[dict]:
    raw = json.loads((REPO_ROOT / cfg["data"]).read_text(encoding="utf-8"))
    return raw if cfg["records_key"] is None else raw[cfg["records_key"]]


def extract(layer: str, rec: dict) -> tuple[dict, dict]:
    """→ (labels, coords) — kaynak-şeması farklı, çıktı resolver şeması."""
    pref, alts = {}, []
    if layer == "le-strange":
        for lang, key in (("en", "name_en"), ("tr", "name_tr"), ("ar", "name_ar")):
            v = (rec.get(key) or "").strip()
            if v:
                pref[lang] = v
        # modern_name "Şehir, Ülke" biçimli olabilir (Le Strange id=4:
        # "Baghdad, Iraq"). Ülke ekini KES: token_set_ratio ülke adını alt-küme
        # sayıp koordinatsız ülke/eyalet kayıtlarına 1.0 verir — "Iraq" kaydı
        # 25 sahte kuyruk girdisi çekmişti (bu koşunun kanıtı, H11 S6'nın
        # (Meçhul Cami) mıknatısının aynısı).
        modern = (rec.get("modern_name") or "").split(",")[0].strip() or None
        alts = [v for v in ([rec.get("le_strange_form"), modern]
                            + list(rec.get("alternate_names") or []))
                if isinstance(v, str) and v.strip()]
        lat, lon = rec.get("latitude"), rec.get("longitude")
    else:
        for lang, key in (("en", "name_en"), ("tr", "name_tr"), ("ar", "name_ar")):
            v = (rec.get(key) or "").strip()
            if v:
                pref[lang] = v
        lat, lon = rec.get("lat"), rec.get("lng")
    labels = {"prefLabel": pref}
    if alts:
        labels["altLabel"] = {"und": list(dict.fromkeys(alts))}
    coords = {"lat": lat, "lon": lon} if isinstance(lat, (int, float)) and \
        isinstance(lon, (int, float)) else {}
    return labels, coords


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, choices=sorted(LAYERS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reset", action="store_true",
                    help="bu adapter'ın karar cache satırlarını + kuyruk "
                         "dosyasını sil (çıkarım mantığı değişince şart)")
    args = ap.parse_args()
    layer, cfg = args.layer, LAYERS[args.layer]

    resolver = EntityResolver(REPO_ROOT)
    if args.reset:
        cc = resolver._cache_connect()
        n = cc.execute("DELETE FROM decision_cache WHERE adapter_id = ?",
                       (cfg["adapter"],)).rowcount
        cc.commit()
        q = REPO_ROOT / "data" / "review_queue" / f"{cfg['adapter']}.jsonl"
        if q.exists():
            q.unlink()
        print(f"[h20:{layer}] reset: {n} cache satırı + kuyruk dosyası silindi")
    conn = resolver._connect()
    if conn is None:
        raise RuntimeError("lookup.sqlite yok — önce build_lookup koş.")

    mapped_ids = {row[0].split(":", 1)[1] for row in conn.execute(
        "SELECT source_id FROM source_curie WHERE source_id LIKE ?", (f"{layer}:%",))}
    records = load_records(cfg)
    missing = [r for r in records if str(r["id"]) not in mapped_ids]
    n_missing_total = len(missing)
    if args.limit:
        missing = missing[:args.limit]
    print(f"[h20:{layer}] evren={len(records)} "
          f"curie'li={len(records) - n_missing_total} curie'siz={n_missing_total}"
          f"{f' (bu koşuda {len(missing)})' if args.limit else ''}")

    # Aynı katmandan MİNT edilmiş pid'ler: bunlara eşleşme, katman-içi
    # dublet adayıdır — augment edilmez (kayıtta layer zaten var), ayrı raporlanır.
    self_layer_pids = {row[0] for row in conn.execute(
        "SELECT pid FROM source_curie WHERE source_id LIKE ?", (f"{layer}:%",))}

    augments: dict[str, list] = {}
    crosswalk: dict[str, str] = {}
    self_layer: dict[str, dict] = {}
    unmatched: dict[str, dict] = {}
    n_review = 0

    for rec in missing:
        curie = f"{layer}:{rec['id']}"
        labels, coords = extract(layer, rec)
        if not labels["prefLabel"]:
            unmatched[curie] = {"name": None, "reason": "labelsiz kayıt",
                                "confidence": 0.0}
            continue
        d = resolver.resolve(
            entity_type="place", adapter_id=cfg["adapter"],
            extracted_record_id=curie, source_curies=[curie],
            labels=labels, coords=coords)          # temporal BİLEREK yok
        name = labels["prefLabel"].get("en") or next(iter(labels["prefLabel"].values()))
        if d.kind == "match":
            crosswalk[curie] = d.matched_pid
            if d.matched_pid in self_layer_pids:
                self_layer[curie] = {"pid": d.matched_pid, "name": name,
                                     "confidence": round(d.confidence, 4)}
                continue
            augments.setdefault(d.matched_pid, []).append({
                cfg["evidence_key"]: rec["id"], "name": name,
                "confidence": round(d.confidence, 4), "tier": d.tier,
                "has_coords": bool(coords),
            })
        elif d.kind == "review":
            n_review += 1
        else:
            unmatched[curie] = {"name": name, "has_coords": bool(coords),
                                "confidence": round(d.confidence, 4)}

    resolver.close()
    n_match_events = sum(len(v) for v in augments.values())
    out = REPO_ROOT / cfg["out"]
    out.write_text(json.dumps({
        "_meta": {
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "layer": layer, "universe": len(records),
            "already_curied": len(records) - n_missing_total,
            "missing_curie": n_missing_total,
            "resolved_this_run": len(missing),
            "auto_match_records": n_match_events + len(self_layer),
            "auto_match_pids": len(augments),
            "self_layer_matches": len(self_layer),
            "review_queued": n_review, "unmatched": len(unmatched),
            "note": ("auto_match = Tier-2 auto kapısı (place auto=0.90, >=2 sinyal); "
                     "self_layer = aynı katmandan mint edilmiş pid'e eşleşme "
                     "(katman-içi dublet adayı, augment EDİLMEZ); "
                     "temporal sinyal bilerek verilmedi (tanıklık yılı ≠ kimlik); "
                     "crosswalk kaydı curie yazımı İÇİN DEĞİL, kanıt içindir — "
                     "provenance.derived_from ekleme kararı insana aittir"),
        },
        "augments": augments,
        "crosswalk": crosswalk,
        "self_layer_matches": self_layer,
        "unmatched": unmatched,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"[h20:{layer}] auto-match={n_match_events} kayıt → {len(augments)} pid | "
          f"self-layer={len(self_layer)} | review={n_review} | unmatched={len(unmatched)}")
    print(f"[h20:{layer}] → {cfg['out']} + data/review_queue/{cfg['adapter']}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
