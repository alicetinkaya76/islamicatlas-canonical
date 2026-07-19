"""
extract.py — evliya_atlas_layer.json'ın 12 YAPI kategorisi (2,608) →
intermediate.

H10 evliya-celebi adapter'ı yerleşim kategorilerini (şehir/kasaba/köy/kale)
place olarak işledi; 12 yapı kategorisini (cami 1097 · türbe 456 · hamam 303
· tekke 143 · han 131 · saray 101 · medrese 99 · mescit 90 · köprü 63 ·
kilise 54 · çeşme 50 · bedesten 21) 'institution şeması yok' diye
institution_pending'e saydı (data/_state/evliya_augment_pending.json).
ADR-015 ile şema geldi; bu adapter o havuzu işler. source_record_id
öneki H10 ile aynı ('evliya-celebi:EC_NNNNN') — pid_minter anahtarı
namespace'li olduğundan place koşusuyla çakışmaz.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

BUILDING_CATS = {"cami", "mescit", "türbe", "hamam", "tekke", "han", "saray",
                 "medrese", "köprü", "kilise", "çeşme", "bedesten"}


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        with path.open(encoding="utf-8") as fh:
            layer = json.load(fh)
        for place in layer.get("places", []):
            if place.get("category") not in BUILDING_CATS:
                continue
            yield {
                "source_record_id": f"evliya-celebi:{place['id']}",
                "raw_data": place,
                "source_locator": {"file": path.name, "id": place["id"]},
            }
