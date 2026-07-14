"""
extract.py — salibiyyat_atlas_layer.json events[] (790 tanıklık) → intermediate.

Kaynak: islamicatlas v1 Salibiyyât katmanı — 6 Müslüman vekāyi'nâmecisinin
(İbn el-Esîr, Makrîzî, Üsâme b. Münkız, Ebû Şâme, İbn Şeddâd, İmâdüddîn)
Haçlı dönemi (1096-1438) tanıklıkları; Arapça pasaj + üç-dilli başlık +
koordinat. Kayıtlar OLAY-TANIKLIĞIDIR (kronik pasajı başına bir kayıt),
tekilleştirilmiş olay değil — 119'u cluster'lı; cluster→canonical eşlemesi
sidecar'a düşer, otomatik birleştirme YAPILMAZ.

castles[]/boundaries/routes bu adapter'da İŞLENMEZ (kaleler ayrı adapter →
institution; poligon/rota katmanları şemasız — Faz 2 frontend işi, journal).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        with path.open(encoding="utf-8") as fh:
            layer = json.load(fh)
        sources = {s["id"]: s for s in layer.get("sources", [])}
        gazetteer = {p["place_id"]: p for p in layer.get("locations", [])}
        for ev in layer.get("events", []):
            yield {
                "source_record_id": f"salibiyyat:{ev['id']}",
                "raw_data": {**ev,
                             "_source_meta": sources.get(ev.get("source_id")) or {},
                             "_gazetteer": gazetteer.get(ev.get("place_id")) or {}},
                "source_locator": {"file": path.name, "id": ev["id"]},
            }
