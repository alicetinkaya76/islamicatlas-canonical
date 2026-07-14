"""
canonicalize.py — Salibiyyât tanıklıkları (790) → iac:event- mint.

- temporal ŞEMADA ZORUNLU → yılsız 36 tanıklık MINT EDİLMEZ, sidecar
  `yearless_skipped` listesine düşer (Faz 2 tarihlendirme işi).
- outcome şema enum'u (victory_attacker/...) ile kaynak enum'u (inconclusive,
  crusader_victory, ...) HİZALANMAZ → alan hiç yazılmaz; bilgi taşıyan ham
  değer note'ta korunur (anlam çevirisi = yorum, yapılmaz).
- location: katmanın iç gazetteer'i (123 yer, ad+koordinat) place_id başına
  BİR kez Tier-2 ile çözülür (battles-events deseni); çözülmeyen boş kalır,
  gazetteer adı note'a düşer.
- cross_refs.atlas_battles (4 cluster → canonical battles-events olayı)
  sidecar `cluster_xrefs`e yazılır — sameAs birleştirmesi tarihçi işi.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"

# Kaynak type → şema @type. Kapsanmayanlar düz iac:Event kalır (ham tip note'ta).
_TYPE_MAP = {
    "siege": "iac:Battle", "battle": "iac:Battle", "encounter": "iac:Battle",
    "military": "iac:Battle", "naval": "iac:Battle", "raid": "iac:Battle",
    "crusader_defeat": "iac:Battle", "muslim_defeat": "iac:Battle",
    "muslim_victory": "iac:Battle",
    "conquest": "iac:Conquest", "crusader_capture": "iac:Conquest",
    "muslim_capture": "iac:Conquest", "muslim_conquest": "iac:Conquest",
    "treaty": "iac:Treaty",
    "assassination": "iac:Death", "death": "iac:Death",
}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_event_salibiyyat")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("salibiyyat_events")
    if side is None:
        side = {}
    side.setdefault("yearless_skipped", [])
    side.setdefault("location_unresolved", {})
    side.setdefault("cluster_xrefs", {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")
    place_cache: dict[str, str | None] = {}   # SAL_P#### → place pid | None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "yearless": 0, "loc_linked": 0, "loc_unlinked": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        src = raw["_source_meta"]
        gaz = raw["_gazetteer"]

        year = raw.get("year")
        if not isinstance(year, int):
            stats["yearless"] += 1
            side["yearless_skipped"].append(
                {"source_record_id": rid, "title": raw.get("title"),
                 "source": src.get("name_tr")})
            continue

        # location: gazetteer place'i Tier-2 ile (place_id başına bir kez).
        # "Urfa (Edessa)" biçimi pref+alt'a AYRILIR — parantezli bileşik
        # dizgi token_set'i sulandırıyordu (H11 S9 ilk koşu kanıtı).
        location = None
        pid_key = raw.get("place_id")
        if pid_key and gaz.get("name") and isinstance(gaz.get("lat"), (int, float)):
            if pid_key not in place_cache:
                name = gaz["name"]
                base, alt = name, []
                if "(" in name and name.endswith(")"):
                    base = name.split("(", 1)[0].strip()
                    alt = [name.split("(", 1)[1].rstrip(")").strip()]
                q_labels = {"prefLabel": {"tr": base}}
                if alt:
                    q_labels["altLabel"] = {"tr": alt}
                d = resolver.resolve(
                    entity_type="place", adapter_id="salibiyyat-events",
                    extracted_record_id=f"salibiyyat:{pid_key}",
                    labels=q_labels,
                    coords={"lat": gaz["lat"], "lon": gaz["lon"]})
                place_cache[pid_key] = d.matched_pid if d.kind == "match" else None
                if place_cache[pid_key] is None:
                    side["location_unresolved"][pid_key] = gaz["name"]
            location = place_cache[pid_key]
        stats["loc_linked" if location else "loc_unlinked"] += 1

        etype = _TYPE_MAP.get(raw.get("type") or "")
        labels: dict = {"prefLabel": {}}
        if raw.get("title"):
            labels["prefLabel"]["tr"] = raw["title"]
        if raw.get("title_en"):
            labels["prefLabel"]["en"] = raw["title_en"]
        if raw.get("title_ar"):
            labels["prefLabel"]["ar"] = raw["title_ar"]
        if raw.get("arabic_text"):
            labels["description"] = {"ar": raw["arabic_text"][:5000]}

        pid = pid_minter.mint("event", rid)
        if raw.get("cluster_id"):
            side["cluster_xrefs"].setdefault(raw["cluster_id"], []).append(pid)

        note_bits = [f"Vekāyi'nâme tanıklığı — {src.get('name_tr', raw.get('source_id'))}, "
                     f"{src.get('work_tr', '?')}"]
        note_bits.append(f"v1 tip: {raw.get('type')}")
        oc = raw.get("outcome")
        if oc and oc not in ("inconclusive", "not_applicable"):
            note_bits.append(f"v1 sonuç: {oc}")
        if not location and gaz.get("name"):
            note_bits.append(f"Konum (çözülmemiş): {gaz['name']}")
        if raw.get("cluster_id"):
            note_bits.append(f"Küme: {raw['cluster_id']}")

        record = {
            "@id": pid,
            "@type": ["iac:Event", etype] if etype else ["iac:Event"],
            "labels": labels,
            "temporal": {"start_ce": year, "approximation": "exact"},
            "note": " · ".join(note_bits)[:2000],
            "provenance": {
                "derived_from": [{
                    "source_id": rid,
                    "source_type": "primary_textual",
                    "page_or_locator": f"salibiyyat_atlas_layer.json id={raw['id']}",
                    "extraction_method": "structured_json",
                    "edition_or_version": (f"{src.get('name_tr','?')}, "
                                           f"{src.get('work_tr','?')} — islamicatlas "
                                           f"v1 Salibiyyât katmanı"),
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
                    "note": f"Salibiyyât layer conversion (H11 S9): initial "
                            f"canonicalization by {pipeline_name}.",
                }],
                "deprecated": False,
            },
        }
        if location:
            record["location"] = location
        stats["minted"] += 1
        yield record

    resolver.close()
    print(f"[canonicalize] salibiyyat-events: minted={stats['minted']} "
          f"yearless-skipped={stats['yearless']} "
          f"loc-linked={stats['loc_linked']} loc-unlinked={stats['loc_unlinked']} "
          f"unresolved-places={len(side['location_unresolved'])}")
