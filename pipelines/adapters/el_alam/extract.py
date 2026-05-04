"""
extract.py — Read alam_lite.json and yield each Ziriklī biography, joined with
DİA xref (alam_id → dia_slug) and Yâqūt place xref hints from the Hafta 3
crossref file.

Each yielded record has:
  - raw: the alam_lite entry (id, h, ht, he, dt, de, c, g, hd, md, lat, lon)
  - dia_slug: DİA slug if alam_id is in dia_to_alam_xref (Track A signal)
  - yaqut_place_attestations: list of {yaqut_id, name_ar} where this person
    was attested as notable in a Yâqūt place entry (consumed by integrity
    pass for person.active_in_places resolution)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path]) -> Iterator[dict]:
    alam_path = next(p for p in input_paths if p.name == "alam_lite.json")
    xref_path = next(p for p in input_paths if p.name == "dia_alam_xref.json")
    yaqut_xref_path = next(p for p in input_paths if p.name == "yaqut_alam_crossref_enriched.json")

    with alam_path.open(encoding="utf-8") as fh:
        alam = json.load(fh)
    with xref_path.open(encoding="utf-8") as fh:
        xref = json.load(fh)
    with yaqut_xref_path.open(encoding="utf-8") as fh:
        yxref_full = json.load(fh)

    # alam_to_dia: alam_id (str/int) → dia_slug
    a2d_raw = xref.get("alam_to_dia", {}) if isinstance(xref, dict) else {}
    # Keys are stored as strings; build int-keyed dict for safety
    alam_to_dia: dict = {}
    for k, v in a2d_raw.items():
        try:
            alam_to_dia[int(k)] = v
        except (TypeError, ValueError):
            pass

    # Yâqūt cross-ref: walk cross_references[place_name].persons[] and invert
    # by alam_id → list of {yaqut_id, place_heading}.
    alam_to_yaqut_attestations: dict[int, list[dict]] = defaultdict(list)
    cr = (yxref_full or {}).get("cross_references", {}) if isinstance(yxref_full, dict) else {}
    for place_heading, place_block in cr.items():
        if not isinstance(place_block, dict):
            continue
        yaqut_id = place_block.get("yaqut_id")
        for p in place_block.get("persons", []) or []:
            aid = p.get("alam_id")
            if aid is None:
                continue
            try:
                aid = int(aid)
            except (TypeError, ValueError):
                continue
            alam_to_yaqut_attestations[aid].append({
                "yaqut_id": yaqut_id,
                "place_heading_ar": place_heading,
                "role": p.get("role"),  # 'origin', 'death_place', 'attested', etc.
            })

    n_total = 0
    n_yielded = 0
    n_track_a = 0
    n_track_b = 0
    for entry in alam:
        n_total += 1
        aid = entry.get("id")
        try:
            aid_int = int(aid) if aid is not None else None
        except (TypeError, ValueError):
            aid_int = None
        dia_slug = alam_to_dia.get(aid_int) if aid_int is not None else None
        yaqut_attests = alam_to_yaqut_attestations.get(aid_int, []) if aid_int is not None else []

        if dia_slug:
            n_track_a += 1
        else:
            n_track_b += 1
        n_yielded += 1

        yield {
            "raw": entry,
            "alam_id": aid_int,
            "dia_slug": dia_slug,
            "yaqut_place_attestations": yaqut_attests,
        }

    print(f"[extract] alam scanned: {n_total:,}; yielded: {n_yielded:,} "
          f"(Track A augment via DİA xref: {n_track_a:,}; Track B new mint: {n_track_b:,})")
