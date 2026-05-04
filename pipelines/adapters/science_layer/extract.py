"""
extract.py — Read science_layer.json and yield each scholar entry, with
shape normalised so canonicalize.py can be source-agnostic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path]) -> Iterator[dict]:
    p = input_paths[0]
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    scholars = data.get("scholars", [])
    for sc in scholars:
        yield {
            "raw": sc,
            "source_id": sc.get("id"),
        }
