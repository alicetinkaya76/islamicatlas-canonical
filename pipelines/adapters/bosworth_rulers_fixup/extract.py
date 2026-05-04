"""
extract.py — Read all canonical dynasty records and yield each ruler entry
flattened with its dynasty context. The canonicalize stage maps each ruler
to a person record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path]) -> Iterator[dict]:
    """Walk dynasty canonical records and yield (ruler, dynasty_context) pairs.

    Each yielded record has:
      - ruler: the inline ruler dict (name, regnal_title, reign_*, note)
      - ruler_index: position in the dynasty's rulers[] (for round-trip linkage)
      - dynasty_pid: iac:dynasty-NNNNNNNN
      - dynasty_label: dynasty's prefLabel.en (or .ar-Latn-x-alalc)
      - bosworth_id: e.g. "NID-001"
      - dynasty_subtype: e.g. "caliphate"
    """
    dynasty_dir = input_paths[0]
    dynasty_files = sorted(dynasty_dir.glob("iac_dynasty_*.json"))
    for dpath in dynasty_files:
        with dpath.open(encoding="utf-8") as fh:
            d = json.load(fh)
        rulers = d.get("rulers") or []
        if not rulers:
            continue
        dpref = d.get("labels", {}).get("prefLabel", {})
        dynasty_label = (
            dpref.get("en")
            or dpref.get("ar-Latn-x-alalc")
            or dpref.get("tr")
            or d["@id"]
        )
        for i, ruler in enumerate(rulers):
            yield {
                "ruler": ruler,
                "ruler_index": i,
                "dynasty_pid": d["@id"],
                "dynasty_label": dynasty_label,
                "bosworth_id": d.get("bosworth_id"),
                "dynasty_subtype": d.get("dynasty_subtype"),
                "dynasty_temporal": d.get("temporal", {}),
            }
