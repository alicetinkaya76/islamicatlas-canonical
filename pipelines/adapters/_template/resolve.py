"""
resolve.py — Adapter template for the resolution stage.

Decide for each extracted record: does this entity already exist in the
canonical store? If yes, what's its PID? If unsure, queue for manual review.

Contract (ADR-008):
    resolve(
        extracted_records: Iterator[dict],
        resolver: EntityResolver,
        options: dict | None = None,
    ) -> Iterator[tuple[dict, ResolutionDecision]]

Most of the resolution logic lives in pipelines/_lib/entity_resolver.py.
This file's job is just to pull out the resolution-relevant features
from this adapter's intermediate format and call the shared resolver.

Three-tier strategy (see ADR-008 §8.2):
  Tier 1: deterministic key match (Wikidata QID, VIAF, source CURIEs)
  Tier 2: blocking + similarity scoring (fuzzy match)
  Tier 3: review queue for uncertain decisions (0.70..0.90)

Adapter-specific work in this file: feature extraction, i.e. how to
read your intermediate format and pass the right fields to resolver.resolve().
"""

from __future__ import annotations

from typing import Iterator


def resolve(extracted_records, resolver, options: dict | None = None):
    """Yield (extracted_record, ResolutionDecision) pairs.

    Args:
        extracted_records: from extract.py.
        resolver: pipelines._lib.entity_resolver.EntityResolver instance.
        options: adapter options. Important: must include 'adapter_id'
                 (used as namespace key for decision_cache and review_queue).

    Yields:
        (extracted_record, ResolutionDecision)
    """
    options = options or {}
    adapter_id = options.get("adapter_id", "_template")
    entity_type = options.get("entity_type", "work")  # adjust per adapter

    for extracted in extracted_records:
        raw = extracted.get("raw_data", {}) or {}
        record_id = extracted["source_record_id"]

        # ---- Adapter-specific feature extraction ------------------------
        # Pull out fields that help resolution. The shape of `raw` is
        # whatever extract.py yields. Fill in the mapping rules below
        # for your source.

        # Authority IDs from the source. Add every authority your source carries.
        authority_xref = []
        if raw.get("wikidata_qid"):
            authority_xref.append({"authority": "wikidata", "id": raw["wikidata_qid"]})
        if raw.get("viaf"):
            authority_xref.append({"authority": "viaf", "id": str(raw["viaf"])})
        if raw.get("openiti_uri"):
            authority_xref.append({"authority": "openiti", "id": raw["openiti_uri"]})
        if raw.get("pleiades_id"):
            authority_xref.append({"authority": "pleiades", "id": str(raw["pleiades_id"])})

        # Source CURIEs from cross-reference files. Examples:
        # if raw.get("dia_id"):       source_curies.append(f"dia:{raw['dia_id']}")
        # if raw.get("alam_xref"):    source_curies.append(f"alam:{raw['alam_xref']}")
        source_curies = []

        # Labels (multilingual_text shape — let resolver fuzzy-match these in Tier 2).
        labels = {
            "prefLabel": {
                "en": raw.get("title_en") or raw.get("name_en") or raw.get("title"),
                "ar": raw.get("title_ar") or raw.get("name_ar"),
                "tr": raw.get("title_tr") or raw.get("name_tr"),
            },
            "altLabel": {},  # populate per-adapter
            "transliteration": {},
        }

        # Temporal (helps Tier 2 narrow candidates by century).
        temporal = {
            "start_ce": raw.get("start_ce") or raw.get("birth_ce") or raw.get("composition_year_ce"),
            "end_ce": raw.get("end_ce") or raw.get("death_ce"),
            "start_ah": raw.get("start_ah"),
            "end_ah": raw.get("end_ah"),
        }

        # Coords (place / event / manuscript-library).
        coords = None
        if raw.get("lat") is not None and raw.get("lon") is not None:
            coords = {"lat": raw["lat"], "lon": raw["lon"]}

        # Person-specific features
        nisba = raw.get("nisba") or []
        kunya = raw.get("kunya")

        # ---- Call the shared resolver -----------------------------------
        decision = resolver.resolve(
            entity_type=entity_type,
            adapter_id=adapter_id,
            extracted_record_id=record_id,
            authority_xref=authority_xref,
            source_curies=source_curies,
            labels=labels,
            temporal=temporal,
            coords=coords,
            nisba=nisba if isinstance(nisba, list) else [nisba],
            kunya=kunya,
        )

        yield extracted, decision
