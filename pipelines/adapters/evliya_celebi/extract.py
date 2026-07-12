"""
extract.py — Evliyâ Çelebi Seyahatnâme atlas katmanı → intermediate.

5,444 geokodlu konum (tr/en/ar ad + anlatı + kategori + sefer bağı).
Kategori yönlendirmesi canonicalize'dadır (yerleşim-sınıfı place'e; yapı
sınıfı institution-bekleyen havuza; doğal/`bilinmeyen` sınıflar triage'a).
10 sefer (voyages) event-aktivasyonuna kadar YIELD EDİLMEZ (sidecar'a sayılır).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    src = next(p for p in input_paths if p.name == "evliya_atlas_layer.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    for place in data.get("places", []):
        yield {
            "source_record_id": f"evliya-celebi:{place.get('id')}",
            "raw_data": place,
            "source_locator": {"file": src.name, "id": place.get("id"),
                               "voyage_id": place.get("voyage_id"),
                               "volume": place.get("volume")},
        }
