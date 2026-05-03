"""
resolve.py — Yâqūt adapter resolver wrapper (ADR-008).

For Hafta 3 the place namespace starts empty so every Yâqūt record resolves
to kind='new' via the resolver's Tier 2 stub. The wrapper exists to keep
the adapter contract uniform with downstream place adapters (Muqaddasī and
Le Strange land in this same session, and they may resolve to existing
Yâqūt PIDs once Yâqūt has been ingested).
"""

from __future__ import annotations

import json
from pathlib import Path


def resolve(extracted_records, resolver, options: dict | None = None):
    options = options or {}
    adapter_id = options.get("adapter_id", "yaqut")
    entity_type = options.get("entity_type", "place")
    seed_path: Path | None = options.get("seed_path")

    seed = _load_seed(seed_path) if seed_path else {}

    for extracted in extracted_records:
        raw = extracted.get("raw_data", {}) or {}
        lite = raw.get("lite") or {}
        rich = raw.get("rich")
        record_id = extracted["source_record_id"]

        authority_xref: list[dict] = []
        if record_id in seed:
            qid = seed[record_id].get("qid")
            if qid:
                authority_xref.append({"authority": "wikidata", "id": qid})

        source_curies = [record_id]

        labels = {
            "prefLabel": {
                "en": (rich and rich.get("heading_en")) or lite.get("he"),
                "tr": (rich and rich.get("heading_tr")) or lite.get("ht"),
                "ar": (rich and rich.get("heading")) or lite.get("h"),
            },
            "altLabel": {},
            "transliteration": {},
        }

        coords = None
        rcoords = rich and rich.get("coordinates")
        if rcoords:
            coords = {"lat": rcoords.get("lat"), "lon": rcoords.get("lon")}
        elif lite.get("lat") is not None:
            coords = {"lat": lite.get("lat"), "lon": lite.get("lon")}

        decision = resolver.resolve(
            entity_type=entity_type,
            adapter_id=adapter_id,
            extracted_record_id=record_id,
            authority_xref=authority_xref,
            source_curies=source_curies,
            labels=labels,
            temporal=None,
            coords=coords,
            nisba=[],
            kunya=None,
        )

        yield extracted, decision


def _load_seed(seed_path: Path) -> dict:
    if not seed_path or not Path(seed_path).exists():
        return {}
    try:
        with Path(seed_path).open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
