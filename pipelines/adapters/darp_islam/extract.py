"""
extract.py — DarpIslam mint corpus → normalized intermediate.

Joins darpislam_lite.json (metadata + 3,381 geocoded mints) with the seven
detail shards (id-keyed dicts: nomisma_uri, yakut_tr/en hints, dynasty_meta,
emissions, ...). Deterministic, no network (ADR-006 extract contract).

Yields one record per GEOCODED mint (lite already excludes the 77 unlocated
ones — metadata.total_mints 3,458 vs geocoded 3,381; the gap is reported by
the caller from metadata, never estimated).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    lite_path = next(p for p in input_paths if p.name == "darpislam_lite.json")
    detail_paths = sorted(p for p in input_paths if "detail" in p.name)

    with lite_path.open(encoding="utf-8") as fh:
        lite = json.load(fh)

    details: dict[str, dict] = {}
    for dp in detail_paths:
        with dp.open(encoding="utf-8") as fh:
            details.update(json.load(fh))

    meta = lite.get("metadata", {})
    for mint in lite.get("mints", []):
        mid = mint.get("id")
        yield {
            "source_record_id": f"darp-islam:{mid}",
            "raw_data": {**mint, "detail": details.get(str(mid), {})},
            "source_locator": {"file": lite_path.name, "id": mid,
                               "dataset_version": meta.get("version"),
                               "dataset_date": meta.get("date")},
        }
