"""
extract.py — salibiyyat_atlas_layer.json castles[] (24 Haçlı kalesi) →
intermediate. Events ayrı adapter'da (salibiyyat_events).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        with path.open(encoding="utf-8") as fh:
            layer = json.load(fh)
        for c in layer.get("castles", []):
            yield {
                "source_record_id": f"salibiyyat:{c['id']}",
                "raw_data": c,
                "source_locator": {"file": path.name, "id": c["id"]},
            }
