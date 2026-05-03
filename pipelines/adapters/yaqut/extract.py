"""
extract.py — Yâqūt al-Hamawī → normalized intermediate records.

Reads three input files (yaqut_lite, yaqut_detail, yaqut_crossref) plus
optionally the richer yaqut_entries.json if present, joins them by entry-id,
and yields one record per place. The intermediate format stays close to
upstream; canonicalize.py decides which fields to map to the canonical schema.

When BOTH yaqut_lite (kompakt) and yaqut_entries (rich) are present the
adapter merges — entries fields take precedence (37-field provenance), but
the kompakt's `geo_confidence` and wider `lat/lon` coverage are layered in
to enrich the coords block. This implements the H3.7 (c) merge decision.

Output shape per record:

    {
      "source_record_id": "yaqut:1",
      "yaqut_id": 1,
      "raw_data": {
        "lite":     {...},   # always present
        "detail":   {...},   # full_text + parent_locations (always present)
        "crossref": [...],   # person crossrefs (only ~5% of places)
        "rich":     {...},   # 37-field zengin (optional, when project file present)
      },
      "source_locator": {
        "file": "yaqut_lite.json",
        "id":   1,
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    by_name = {p.name: p for p in source_paths}

    # Required
    lite_path = by_name.get("yaqut_lite.json")
    detail_path = by_name.get("yaqut_detail.json")
    crossref_path = by_name.get("yaqut_crossref.json")
    if not lite_path or not lite_path.exists():
        raise FileNotFoundError("yaqut_lite.json missing from source_paths.")
    if not detail_path or not detail_path.exists():
        raise FileNotFoundError("yaqut_detail.json missing from source_paths.")
    if not crossref_path or not crossref_path.exists():
        raise FileNotFoundError("yaqut_crossref.json missing from source_paths.")

    # Optional richer format (project's file)
    rich_path = by_name.get("yaqut_entries.json")
    # Auto-discover sibling rich file
    if rich_path is None:
        candidate = lite_path.parent / "yaqut_entries.json"
        if candidate.exists():
            rich_path = candidate

    with lite_path.open(encoding="utf-8") as fh:
        lite_records = json.load(fh)
    with detail_path.open(encoding="utf-8") as fh:
        detail_data = json.load(fh)
    with crossref_path.open(encoding="utf-8") as fh:
        crossref_data = json.load(fh)

    rich_by_id: dict[int, dict] = {}
    if rich_path and rich_path.exists():
        with rich_path.open(encoding="utf-8") as fh:
            rich_payload = json.load(fh)
        rich_entries = (
            rich_payload.get("entries") if isinstance(rich_payload, dict) else rich_payload
        ) or []
        for r in rich_entries:
            rid = r.get("id")
            if rid is not None:
                rich_by_id[int(rid)] = r

    # Detail keyed by string id (per JSON convention)
    # crossref keyed by string id; value is list of person dicts
    for lite in lite_records:
        rid = lite.get("id")
        if rid is None:
            continue
        rid_int = int(rid)
        rid_str = str(rid_int)

        detail = detail_data.get(rid_str) or {}
        crossref = crossref_data.get(rid_str) or []
        rich = rich_by_id.get(rid_int)

        yield {
            "source_record_id": f"yaqut:{rid_int}",
            "yaqut_id": rid_int,
            "raw_data": {
                "lite": lite,
                "detail": detail,
                "crossref": crossref,
                "rich": rich,
            },
            "source_locator": {
                "file": lite_path.name,
                "id": rid_int,
            },
        }
