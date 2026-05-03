"""resolve.py — Muqaddasī adapter resolver wrapper (ADR-008)."""

from __future__ import annotations

import json
from pathlib import Path


def resolve(extracted_records, resolver, options: dict | None = None):
    options = options or {}
    adapter_id = options.get("adapter_id", "muqaddasi")
    entity_type = options.get("entity_type", "place")
    seed_path: Path | None = options.get("seed_path")

    seed = _load_seed(seed_path) if seed_path else {}

    for extracted in extracted_records:
        raw = extracted.get("raw_data", {}) or {}
        record_id = extracted["source_record_id"]
        yaqut_id = extracted.get("yaqut_id")

        authority_xref: list[dict] = []
        if record_id in seed:
            qid = seed[record_id].get("qid")
            if qid:
                authority_xref.append({"authority": "wikidata", "id": qid})

        # Source CURIE list — include yaqut crossref for resolver merge
        source_curies = [record_id]
        if yaqut_id:
            source_curies.append(f"yaqut:{yaqut_id}")

        labels = {
            "prefLabel": {
                "en": raw.get("name_en") or raw.get("iqlim_en"),
                "tr": raw.get("name_tr") or raw.get("iqlim_tr"),
                "ar": raw.get("name_ar") or raw.get("iqlim_ar"),
            },
            "altLabel": {},
            "transliteration": {},
        }

        coords = None
        if raw.get("lat") is not None and raw.get("lon") is not None:
            coords = {"lat": raw["lat"], "lon": raw["lon"]}

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
