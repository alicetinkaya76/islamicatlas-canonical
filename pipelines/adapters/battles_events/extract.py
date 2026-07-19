"""
extract.py — battles.csv (50) + events.csv (50) → intermediate.

EVENT NAMESPACE AKTİVASYONUNUN ilk kaynağı (H11 Karar 2). causal_links /
monuments / diplomacy / trade_routes dosyaları BU adapter'da yield edilmez
(kenar tablosu + şemasız sınıflar — sidecar'da sayılır; PHASE0_CLOSEOUT).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        kind = "battle" if "battles" in path.name else "event"
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rid = row.get("battle_id") or row.get("event_id")
                yield {
                    "source_record_id": f"battles-events:{kind}:{rid}",
                    "raw_data": {**{k: (v.strip() if isinstance(v, str) else v)
                                    for k, v in row.items()},
                                 "_kind": kind},
                    "source_locator": {"file": path.name, "id": rid},
                }
