"""
extract.py — al-Muqaddasī → normalized intermediate records.

Reads muqaddasi_atlas_layer.json (the main file with 21 aqualim + 2049 places +
1427 routes) and muqaddasi_xref.json (muq-id → yaqut_id cross-references).

Yields TWO kinds of records:
  - iqlim records: type='iqlim', id like 'muqaddasi-iqlim:جزيرة العرب'
  - place records: type='place', id='muq-NNNN' format

Iqlim records become @type=['iac:Place', 'iac:Iqlim'] in canonicalize.
Place records merge into existing Yâqūt PIDs when yaqut_id cross-ref exists;
the resolver decides "merge" vs "new" via the source_curie 'yaqut:N' lookup.

Routes (1427) are skipped here — they belong to a future event/transport
namespace adapter scheduled for Hafta 5+.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    by_name = {p.name: p for p in source_paths}

    atlas_path = by_name.get("muqaddasi_atlas_layer.json")
    xref_path = by_name.get("muqaddasi_xref.json")
    if atlas_path is None or not atlas_path.exists():
        raise FileNotFoundError("muqaddasi_atlas_layer.json missing.")
    if xref_path is None or not xref_path.exists():
        raise FileNotFoundError("muqaddasi_xref.json missing.")

    with atlas_path.open(encoding="utf-8") as fh:
        atlas = json.load(fh)
    with xref_path.open(encoding="utf-8") as fh:
        xref_data = json.load(fh)

    # Build muq-id → yaqut_id map (best yaqut crossref for each muq id)
    muq_to_yaqut: dict[str, int] = {}
    for muq_id, refs in xref_data.items():
        if not refs:
            continue
        # Pick the crossref with method='geo' (most reliable) over 'name'
        best = next((r for r in refs if r.get("m") == "geo"), refs[0])
        if best.get("s") == "yaqut" and best.get("id") is not None:
            muq_to_yaqut[muq_id] = int(best["id"])

    # 1) Yield iqlim records (21 top-level regions)
    for i, iqlim in enumerate(atlas.get("aqualim") or [], start=1):
        iqlim_ar = iqlim.get("iqlim_ar", "").strip()
        if not iqlim_ar:
            continue
        # Synthetic id from Arabic name
        synthetic_id = f"muq-iqlim-{i:03d}"
        yield {
            "source_record_id": f"muqaddasi:{synthetic_id}",
            "muqaddasi_id": synthetic_id,
            "record_kind": "iqlim",
            "raw_data": {
                "iqlim_ar": iqlim_ar,
                "iqlim_tr": iqlim.get("iqlim_tr"),
                "iqlim_en": iqlim.get("iqlim_en"),
                "type_ar": iqlim.get("type_ar"),
                "line": iqlim.get("line"),
                "declared_regions": iqlim.get("declared_regions") or [],
                "child_count": len(iqlim.get("children") or []),
            },
            "source_locator": {
                "file": atlas_path.name,
                "line": iqlim.get("line"),
            },
        }

    # 2) Yield place records (2049 individual settlements)
    for place in atlas.get("places") or []:
        muq_id = place.get("id")
        if not muq_id:
            continue
        yaqut_id = muq_to_yaqut.get(muq_id)
        yield {
            "source_record_id": f"muqaddasi:{muq_id}",
            "muqaddasi_id": muq_id,
            "record_kind": "place",
            "yaqut_id": yaqut_id,
            "raw_data": place,
            "source_locator": {
                "file": atlas_path.name,
                "muq_id": muq_id,
            },
        }

    # 3) Routes are deliberately skipped — Hafta 5+ event/transport namespace.
