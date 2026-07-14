"""
canonicalize.py — Haçlı kaleleri (24) → iac:institution- mint.

S6 muhafazakâr eşleme doktrini: kale ≠ palace → subtype "other", kale tipi
(concentric_castle vs.) + Haçlı devleti + UNESCO bayrağı note'ta. image_url
ALINMAZ (Wikimedia hotlink; lisans/atıf işi Faz 2). located_in doldurulmaz
(kırsal kaleler; şehir çapası yok — koordinat yeter).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from pipelines._lib.institution_common import base_provenance

EDITION = "islamicatlas v1 Salibiyyât katmanı (Haçlı kaleleri alt-listesi)"


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_institution_salibiyyat")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n = 0

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]

        labels: dict = {"prefLabel": {}}
        for lang, field in (("tr", "name_tr"), ("en", "name_en"), ("ar", "name_ar")):
            if raw.get(field):
                labels["prefLabel"][lang] = raw[field]
        if raw.get("description_tr"):
            labels["description"] = {"tr": raw["description_tr"][:5000]}

        note_bits = [f"Haçlı kalesi — v1 tip: {raw.get('type')}"]
        if raw.get("crusader_state"):
            note_bits.append(f"Haçlı devleti: {raw['crusader_state']}")
        if raw.get("unesco"):
            note_bits.append("UNESCO Dünya Mirası")
        if raw.get("ownership_history"):
            note_bits.append(str(raw["ownership_history"])[:400])

        record = {
            "@id": pid_minter.mint("institution", rid),
            "@type": ["iac:Institution"],
            "institution_subtype": "other",
            "labels": labels,
            "derived_from_layers": ["salibiyyat"],
            "note": " · ".join(note_bits)[:2000],
            "provenance": base_provenance(
                rid, f"salibiyyat_atlas_layer.json id={raw['id']}",
                EDITION, pipeline_name, pipeline_version, now,
                f"Salibiyyât castles conversion (H11 S9): initial "
                f"canonicalization by {pipeline_name}."),
        }
        if isinstance(raw.get("lat"), (int, float)) and isinstance(raw.get("lon"), (int, float)):
            record["coords"] = {"lat": raw["lat"], "lon": raw["lon"]}
        n += 1
        yield record

    print(f"[canonicalize] salibiyyat-castles: minted={n}")
