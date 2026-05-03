"""
resolve.py — Bosworth adapter resolver wrapper (ADR-008).

For Hafta 2 the dynasty namespace starts empty, so every Bosworth record
resolves to kind="new" via the resolver's Tier 2 stub. This file exists
to keep the adapter contract uniform with downstream adapters (Yâqūt /
Le Strange / DİA / OpenITI) where the resolver does real work in
P0.2 / P0.3.

Feature extraction in this file converts the Bosworth intermediate format
into the resolver's input shape: a Wikidata QID hint (when present in
the seed), the bosworth-nid CURIE as a source CURIE, and the English /
Turkish prefLabel for fuzzy matching.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def resolve(extracted_records, resolver, options: dict | None = None):
    options = options or {}
    adapter_id = options.get("adapter_id", "bosworth")
    entity_type = options.get("entity_type", "dynasty")
    seed_path: Path | None = options.get("seed_path")

    seed = _load_seed(seed_path) if seed_path else {}

    for extracted in extracted_records:
        raw = extracted.get("raw_data", {}) or {}
        dyn = raw.get("dynasty", {})
        record_id = extracted["source_record_id"]

        # Authority IDs known to us (from the curated offline seed).
        authority_xref: list[dict] = []
        if record_id in seed:
            qid = seed[record_id].get("qid")
            if qid:
                authority_xref.append({"authority": "wikidata", "id": qid})

        # Source CURIE — both the bosworth-nid:N anchor and the
        # adapter-internal record id (same string, but kept explicit).
        source_curies = [record_id]

        labels = {
            "prefLabel": {
                "en": dyn.get("dynasty_name_en") or None,
                "tr": dyn.get("dynasty_name_tr") or None,
                "ar": dyn.get("dynasty_name_ar") or None,
            },
            "altLabel": {},
            "transliteration": {},
        }

        temporal = {
            "start_ce": _try_int(dyn.get("date_start_ce")),
            "end_ce": _try_int(dyn.get("date_end_ce")),
            "start_ah": _try_int(dyn.get("date_start_hijri")),
            "end_ah": _try_int(dyn.get("date_end_hijri")),
        }

        coords = None  # dynasties don't have coords; capital does (sidecared)

        decision = resolver.resolve(
            entity_type=entity_type,
            adapter_id=adapter_id,
            extracted_record_id=record_id,
            authority_xref=authority_xref,
            source_curies=source_curies,
            labels=labels,
            temporal=temporal,
            coords=coords,
            nisba=[],
            kunya=None,
        )

        yield extracted, decision


# ----- helpers ------------------------------------------------------------


def _load_seed(seed_path: Path) -> dict:
    if not seed_path or not Path(seed_path).exists():
        return {}
    try:
        with Path(seed_path).open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _try_int(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None
