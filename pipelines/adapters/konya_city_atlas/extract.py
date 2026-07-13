"""
extract.py — konya.json (Konya City Atlas, 583 yapı) → intermediate.

Kaynak: islamicatlas.org v1 city-atlas katmanı (İ.H. Konyalı, *Âbideleri ve
Kitabeleriyle Konya Tarihi* 2007 dizini + Konyapedia zenginleştirmesi).
INSTITUTION NAMESPACE'İN İLK KAYNAĞI (H11 Karar 6 / ADR-015).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        with path.open(encoding="utf-8") as fh:
            rows = json.load(fh)
        # Kaynakta mükerrer id var (kp_beyşehi_r_gölü_2 ×3; sonrakiler
        # koordinatsız kopyalar) — İLK geçiş kalır, gerisi loglanıp atlanır;
        # aynı rid ikinci kez yield edilirse aynı PID'e yazıp dosyayı ezerdi.
        seen: set[str] = set()
        for row in rows:
            if row["id"] in seen:
                print(f"  WARN duplicate source id skipped: {row['id']} "
                      f"({row.get('name_tr')})")
                continue
            seen.add(row["id"])
            yield {
                "source_record_id": f"konya-city-atlas:{row['id']}",
                "raw_data": row,
                "source_locator": {"file": path.name, "id": row["id"]},
            }
