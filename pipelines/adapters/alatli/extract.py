"""extract.py — Alatlı adapter extraction stage.

data/sources/alatli/main.json (677 kişi listesi) → normalize ara-kayıtlar.
Deterministik, ağ yok. canonicalize.py bunları tüketir.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(f"Adapter source missing: {path}")
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise ValueError(f"alatli main.json must be a list, got {type(payload)}")
        for i, record in enumerate(payload):
            yield {
                "source_record_id": record.get("id") or f"alatli-{i}",
                "raw_data": record,
                "source_locator": {"file": path.name, "index": i},
            }
