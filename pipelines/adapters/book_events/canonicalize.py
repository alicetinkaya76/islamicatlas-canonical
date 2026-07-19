"""
canonicalize.py — kitap-olayları → iac:event- mint (H15).

Salibiyyat deseni: birincil-metin tanıklığı, Arapça pasaj description.ar'da,
sayfa çapası locator'da. location = H14 geocoding'in place_pid'i (varsa;
geo_suspect'ler extract'a girmez). Sahip kararı (H14): doğrudan yayın;
confidence note'ta taşınır.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"

_TYPE_MAP = {
    "conquest": "iac:Conquest", "battle": "iac:Battle", "raid": "iac:Battle",
    "siege": "iac:Battle", "treaty": "iac:Treaty", "founding": "iac:Founding",
    "revolt": "iac:Revolt", "migration": "iac:Event",
    "administration": "iac:Event", "revelation_context": "iac:Event",
    "other": "iac:Event",
}


def _parse_ah(date_h: str) -> int | None:
    """'87' / '162' / '5-03' / '578-10-26' → yıl (AH)."""
    head = str(date_h).strip().split("-")[0]
    if head.lstrip("-").isdigit():
        y = int(head)
        if -1 <= y <= 1500:
            return y
    return None


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_event_book_layers")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "no_year": 0, "loc": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        ah = _parse_ah(raw["date_h"])
        if ah is None:
            stats["no_year"] += 1
            continue

        etype = _TYPE_MAP.get(raw.get("event_type") or "other", "iac:Event")
        labels: dict = {"prefLabel": {"tr": raw["title_tr"][:500]}}
        if raw.get("title_ar"):
            labels["prefLabel"]["ar"] = raw["title_ar"][:500]
        desc = {}
        if raw.get("summary_tr"):
            desc["tr"] = raw["summary_tr"][:2000]
        if raw.get("quote_ar"):
            desc["ar"] = raw["quote_ar"][:2000]
        if desc:
            labels["description"] = desc

        note_bits = [f"Kaynak: {raw['_book']} §{raw['sec']}"
                     + (f" {raw['page']}" if raw.get("page") else "")]
        if raw.get("date_text"):
            note_bits.append(f"Tarih ifadesi: {raw['date_text']}")
        if raw.get("leader_ar"):
            note_bits.append(f"Önder: {raw['leader_ar']}")
        note_bits.append(f"Çıkarım güveni: {raw.get('confidence')}")
        if raw.get("place_ar") and not raw.get("place_pid"):
            note_bits.append(f"Yer (çözülmemiş): {raw['place_ar']}")
        if raw.get("geo_note"):
            note_bits.append(raw["geo_note"])

        record = {
            "@id": pid_minter.mint("event", rid),
            "@type": ["iac:Event", etype] if etype != "iac:Event" else ["iac:Event"],
            "labels": labels,
            "temporal": {"start_ah": ah,
                         "approximation": "exact" if raw["date_h"].count("-") else "circa"},
            "note": " · ".join(note_bits)[:2000],
            "provenance": {
                "derived_from": [{
                    "source_id": rid,
                    "source_type": "primary_textual",
                    "page_or_locator": f"{raw['_book']} §{raw['sec']} "
                                       f"{raw.get('page') or ''} "
                                       f"(reading/{raw['_pidnum']})",
                    "extraction_method": "structured_json",
                    "edition_or_version": f"OpenITI metni üzerinden Claude "
                                          f"yapılandırılmış çıkarım (H14); "
                                          f"kaynak eser {raw['_work_pid']}",
                }],
                "generated_by": {"pipeline_name": pipeline_name,
                                 "pipeline_version": pipeline_version},
                "generated_at": now,
                "attributed_to": ATTRIBUTED_TO,
                "created": now, "modified": now,
                "license": LICENSE,
                "record_history": [{
                    "change_type": "create", "changed_at": now,
                    "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                    "note": f"Book-layer canonical mint (H15): {pipeline_name}; "
                            f"sahip kararıyla doğrudan yayın (H14 Karar).",
                }],
                "deprecated": False,
            },
        }
        if raw.get("place_pid") and not raw.get("geo_suspect"):
            record["location"] = raw["place_pid"]
            stats["loc"] += 1
        stats["minted"] += 1
        yield record

    print(f"[canonicalize] book-events: minted={stats['minted']} "
          f"location={stats['loc']} yıl-parse-edilemedi={stats['no_year']}")
