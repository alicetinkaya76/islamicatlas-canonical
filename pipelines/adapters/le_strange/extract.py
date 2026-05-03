"""extract.py — Le Strange → normalized intermediate records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    by_name = {p.name: p for p in source_paths}
    main_path = by_name.get("le_strange_eastern_caliphate.json")
    xref_path = by_name.get("le_strange_xref.json")
    if not main_path or not main_path.exists():
        raise FileNotFoundError("le_strange_eastern_caliphate.json missing.")

    with main_path.open(encoding="utf-8") as fh:
        records = json.load(fh)

    xref_data: dict = {}
    if xref_path and xref_path.exists():
        with xref_path.open(encoding="utf-8") as fh:
            xref_data = json.load(fh)

    for r in records:
        rid = r.get("id")
        if rid is None:
            continue
        rid_str = str(rid)
        xref = xref_data.get(rid_str) or {}
        yaqut_ref = xref.get("yaqut") or {}
        yaqut_id = yaqut_ref.get("id")
        dia_ref = xref.get("dia") or {}

        yield {
            "source_record_id": f"le-strange:{rid}",
            "le_strange_id": rid,
            "yaqut_id": yaqut_id,
            "raw_data": r,
            "xref": {"yaqut": yaqut_ref, "dia": dia_ref},
            "source_locator": {
                "file": main_path.name,
                "id": rid,
                "chapter": r.get("chapter"),
                "page_range": r.get("page_range"),
            },
        }
