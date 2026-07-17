#!/usr/bin/env python3
"""
augment_places_from_layers.py — kitap-katmanı yer bağlarını mağazaya işle
(H16; LaCie gerektirmez — layer.json'lar diskte).

İstahrî yolları (from_pid/to_pid uçları) + Havkal/İdrîsî bölgeleri
(city_pids) → geçtikleri/kapsadıkları yer kayıtlarına derived_from_layers
izi. Böylece coğrafya klasikleri place kayıtlarında kaynak-katman facet'i
olarak görünür (atlas entegrasyonu).

Her (layer, place) çifti idempotent (jenerik applier).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

LAYERS = {
    "00002702_routes": "istakhri-mesalik",
    "00001748_regions": "ibn-hawqal",
    "00001333_regions": "idrisi-nuzhat",
}


def main() -> int:
    for fname, layer_name in LAYERS.items():
        path = REPO_ROOT / "data/sources/book-layers" / f"{fname}.json"
        if not path.exists():
            print(f"✗ {fname}: layer yok"); continue
        data = json.loads(path.read_text(encoding="utf-8"))
        aug: dict[str, list] = defaultdict(list)
        for r in data["records"]:
            pids = []
            if data["kind"] == "routes":
                pids = [p for p in (r.get("from_pid"), r.get("to_pid")) if p]
            elif data["kind"] == "regions":
                pids = r.get("city_pids") or []
            for pid in pids:
                aug[pid].append({"stop_id": r["seq"], "confidence": 0.8})
        sidecar = REPO_ROOT / "data/_state" / f"{layer_name}_augment_pending.json"
        sidecar.write_text(json.dumps({"augments": dict(aug)}, ensure_ascii=False,
                                      indent=1), encoding="utf-8")
        print(f"{layer_name}: {len(aug)} yer → {sidecar.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
