"""
canonicalize.py — Mekke + Bağdat yapıları → iac:institution- mint (H15).

Konya/Kahire CityAtlas'larına iki kardeş: Ezrakî'den Mekke, Hatîb'den
Bağdat. located_in = şehir çapası (extract'te kitaba gömülü; Mekke 11505 /
Bağdat 2027 — en belirgin kayıtlar, H15 ölçümü). S6 muhafazakâr alt-tip
doktrini: enum'a oturmayan tür → "other" + v1 türü note'ta.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from pipelines._lib.institution_common import base_provenance, build_type

_TYPE_MAP = {
    "mosque": "mosque", "market": "market", "bridge": "bridge",
    "bath": "hammam", "palace": "palace",
    # gate/quarter/well/canal/monument/cemetery/street/fief/house/
    # boundary_marker/marker → other (enum'da yok; anlam esnetilmez)
}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_institution_book_layers")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "coords": 0, "other": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        subtype = _TYPE_MAP.get(raw.get("type") or "", "other")
        if subtype == "other":
            stats["other"] += 1

        labels: dict = {"prefLabel": {}}
        if raw.get("name_tr"):
            labels["prefLabel"]["tr"] = raw["name_tr"][:500]
        if raw.get("name_ar"):
            labels["prefLabel"]["ar"] = raw["name_ar"][:500]
        if not labels["prefLabel"]:
            labels["prefLabel"]["ar"] = rid
        desc = {}
        if raw.get("summary_tr"):
            desc["tr"] = raw["summary_tr"][:2000]
        if raw.get("quote_ar"):
            desc["ar"] = raw["quote_ar"][:2000]
        if desc:
            labels["description"] = desc

        note_bits = [f"Kaynak: {raw['_book']} §{raw['sec']}"
                     + (f" {raw['page']}" if raw.get("page") else ""),
                     f"v1 tür: {raw.get('type')}"]
        if raw.get("measurements_text"):
            note_bits.append(f"Ölçüler: {raw['measurements_text'][:300]}")
        if raw.get("builder_ar"):
            note_bits.append(f"Bâni: {raw['builder_ar'][:150]}")
        if raw.get("date_text"):
            note_bits.append(f"Tarih ifadesi: {raw['date_text'][:150]}")
        note_bits.append(f"Çıkarım güveni: {raw.get('confidence')}")

        record = {
            "@id": pid_minter.mint("institution", rid),
            "@type": build_type(subtype),
            "institution_subtype": subtype,
            "labels": labels,
            "located_in": raw["_city_pid"],
            "derived_from_layers": [raw["_prefix"]],
            "note": " · ".join(note_bits)[:2000],
            "provenance": base_provenance(
                rid,
                f"{raw['_book']} §{raw['sec']} {raw.get('page') or ''} "
                f"(reading/{raw['_pidnum']})",
                f"OpenITI metni üzerinden Claude yapılandırılmış çıkarım "
                f"(H14); kaynak eser {raw['_work_pid']}",
                pipeline_name, pipeline_version, now,
                f"Book-layer canonical mint (H15): {pipeline_name}; sahip "
                f"kararıyla doğrudan yayın (H14 Karar)."),
        }
        if isinstance(raw.get("lat"), (int, float)):
            record["coords"] = {"lat": raw["lat"], "lon": raw["lon"]}
            stats["coords"] += 1
        stats["minted"] += 1
        yield record

    print(f"[canonicalize] book-structures: minted={stats['minted']} "
          f"coords={stats['coords']} subtype-other={stats['other']}")
