"""
extract.py — Encyclopaedia of Islam 1st ed. (ei1_lite 7,568 entries) → intermediate.

Joins ei1_geo (474 person birth/death coords), ei1_works (306 person→title
lists). Routing by `at`:
    biography (4,531) · geography (1,066) · dynasty (31)  → yielded
    concept (203) · unknown (1,270) · cross_reference (467) → NOT yielded —
      no canonical home (concept ns is P1; unknown needs triage; xrefs are
      redirect stubs). Counted in the summary the canonicalizer prints;
      routed to the sidecar's `skipped_classes` for the record.
Field glossary (2-char keys): t/tn title+translit, ds/dt/da EN/TR/AR summary,
au author, is page, vol volume, bc/dc birth/death CE, bh/dh AH, bp/dp places.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

_YIELDED = {"biography", "geography", "dynasty"}


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    lite = json.load(next(p for p in input_paths if p.name == "ei1_lite.json").open(encoding="utf-8"))
    geo_rows = json.load(next(p for p in input_paths if p.name == "ei1_geo.json").open(encoding="utf-8"))
    works = json.load(next(p for p in input_paths if p.name == "ei1_works.json").open(encoding="utf-8"))
    geo = {}
    for g in geo_rows:
        geo.setdefault(g["id"], []).append(g)

    for rec in lite:
        at = rec.get("at") or "unknown"
        rid = rec.get("id")
        yield {
            "source_record_id": f"ei1:{rid}",
            "raw_data": {**rec,
                         "geo": geo.get(rid, []),
                         "work_titles": works.get(str(rid), [])},
            "source_locator": {"file": "ei1_lite.json", "id": rid,
                               "entity_class": at,
                               "vol": rec.get("vol"), "page": rec.get("is")},
        }
