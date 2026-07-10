"""
extract.py — İbn Battûta Rihle atlas katmanı → intermediate.

317 geokodlu durak (tr/en/ar ad + CE/AH varış + Rihla src_page + anlatı).
7 sefer + 1 gezgin event-aktivasyonuna kadar YIELD EDİLMEZ (sidecar sayar;
gezgin kişi olarak zaten person store'da — dia:ibn-battuta).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    src = next(p for p in input_paths if p.suffix == ".json" and "atlas" in p.name)
    data = json.loads(src.read_text(encoding="utf-8"))
    for stop in data.get("travel_stops", []):
        yield {
            "source_record_id": f"ibn-battuta:{stop.get('id')}",
            "raw_data": stop,
            "source_locator": {"file": src.name, "id": stop.get("id"),
                               "voyage_id": stop.get("voyage_id"),
                               "src_page": stop.get("src_page")},
        }
