"""
extract.py — scholars source (49-CSV core ⋈ identity cards ⋈ meta) → intermediate.

HONEST BOUNDARY (H10 Stage 3): scholar_identity.js carries 296 cards keyed to
a db.json scholars array that is NOT in the repo — 252 cards have no name
authority and are therefore UNPROCESSABLE (flagged to PHASE0_CLOSEOUT as a
source-acquisition item: the islamicatlas.org v1 app bundle's db.json).
This extract yields ONLY the 49 named CSV scholars (44 with identity cards,
47 with meta) — counted, not estimated.

Input: scholars.csv + scholars_converted.json (deterministic derivative of
the JS literals; see convert_js_sources.py).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator

_PLACEHOLDER = "—"


def _clean(v):
    """'—' placeholders → None; strip strings."""
    if isinstance(v, str):
        v = v.strip()
        if not v or v == _PLACEHOLDER:
            return None
    return v


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    csv_path = next(p for p in input_paths if p.suffix == ".csv")
    conv_path = next(p for p in input_paths if p.name == "scholars_converted.json")

    with conv_path.open(encoding="utf-8") as fh:
        conv = json.load(fh)
    identity = conv.get("identity", {})
    meta = conv.get("meta", {})

    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = row["scholar_id"]
            card = {k: _clean(v) for k, v in (identity.get(sid) or {}).items()}
            m = {k: _clean(v) for k, v in (meta.get(sid) or {}).items()}
            yield {
                "source_record_id": f"scholars:{sid}",
                "raw_data": {
                    **{k: _clean(v) for k, v in row.items()},
                    "identity": card,
                    "meta": m,
                },
                "source_locator": {"file": csv_path.name, "scholar_id": sid},
            }
