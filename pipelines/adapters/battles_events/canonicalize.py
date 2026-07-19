"""
canonicalize.py — savaşlar + olaylar → iac:event- (NAMESPACE AKTİVASYONU).

H11 Karar 2: event.schema v0.3.0 setinde zaten tanımlı (şema değişikliği
SIFIR); bu adapter namespace'i ilk kez doldurur. Namespace boş olduğundan
two-track yok — hepsi mint; ama LOCATION Tier-2 place-çözümüyle bağlanır
(isim + koordinat; eşleşmezse location alanı BOŞ bırakılır — şemada opsiyonel;
asla koordinattan yeni place mint edilmez).

@type eşlemesi: battle → iac:Battle; events.csv kategorileri →
  Dini/Siyasi/Hukuki/Kültürel → iac:Event · Mimari → iac:Founding ·
  Bilimsel → iac:Composition · Felaket → iac:Disaster · Ekonomik → iac:Event
Yerel kenarlar (causes/caused_by/related_*) kaynak-id olarak sidecar'a —
event-PID haritası tamamlanınca ayrı bağlama koşusu (preceded_by/causes
alanları PID ister).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = ("islamicatlas v1 battles-events editorial layer (battles.csv + "
           "events.csv; kaynak kolonu yok — self-authored dataset, bosworth "
           "emsali provenance)")

_CAT_TO_TYPE = {"Mimari": "iac:Founding", "Bilimsel": "iac:Composition",
                "Felaket": "iac:Disaster"}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_event_battles")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("battles_edges")
    if side is None:
        side = {}
    side.setdefault("edges", [])
    side.setdefault("id_to_pid", {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "loc_linked": 0, "loc_unlinked": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        kind = raw["_kind"]

        etype = ("iac:Battle" if kind == "battle"
                 else _CAT_TO_TYPE.get(raw.get("category") or "", "iac:Event"))
        pid = pid_minter.mint("event", rid)
        side["id_to_pid"][rid] = pid

        labels = {"prefLabel": {}}
        if raw.get("name_tr"):
            labels["prefLabel"]["tr"] = raw["name_tr"]
        if raw.get("name_en"):
            labels["prefLabel"]["en"] = raw["name_en"]
        desc = {}
        if raw.get("narrative_tr"):
            desc["tr"] = raw["narrative_tr"][:5000]
        if raw.get("narrative_en"):
            desc["en"] = raw["narrative_en"][:5000]
        if desc:
            labels["description"] = desc

        temporal = {}
        if (raw.get("date_ce") or "").lstrip("-").isdigit():
            temporal["start_ce"] = int(raw["date_ce"])
        if (raw.get("date_hijri") or "").lstrip("-").isdigit():
            ah = int(raw["date_hijri"])
            if 1 <= ah <= 1700:
                temporal["start_ah"] = ah
        temporal["approximation"] = "exact"

        # LOCATION: Tier-2 place çözümü (isim + koordinat çift-sinyali).
        location = None
        loc_name = (raw.get("location_tr") or "").split("→")[0].split(",")[0].strip()
        try:
            lat, lon = float(raw.get("lat") or ""), float(raw.get("lon") or "")
        except ValueError:
            lat = lon = None
        if loc_name and lat is not None:
            d = resolver.resolve(
                entity_type="place", adapter_id="battles-events",
                extracted_record_id=f"{rid}:loc",
                labels={"prefLabel": {"tr": loc_name}},
                coords={"lat": lat, "lon": lon})
            if d.kind == "match":
                location = d.matched_pid
                stats["loc_linked"] += 1
            else:
                stats["loc_unlinked"] += 1

        record = {
            "@id": pid,
            "@type": ["iac:Event", etype] if etype != "iac:Event" else ["iac:Event"],
            "labels": labels,
            "temporal": temporal,
            "provenance": {
                "derived_from": [{
                    "source_id": rid,
                    "source_type": "manual_editorial",
                    "page_or_locator": f"{extracted['source_locator']['file']} "
                                       f"id={extracted['source_locator']['id']}",
                    "extraction_method": "structured_json",
                    "edition_or_version": EDITION,
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
                    "note": f"Event namespace activation (H11 S2): initial "
                            f"canonicalization by {pipeline_name}.",
                }],
                "deprecated": False,
            },
        }
        if location:
            record["location"] = location
        note_bits = []
        if raw.get("significance"):
            note_bits.append(f"Önem: {raw['significance']}.")
        if raw.get("result_summary"):
            note_bits.append(raw["result_summary"])
        if kind == "battle" and raw.get("battle_type"):
            note_bits.append(f"Tür: {raw['battle_type']}.")
        if loc_name and not location:
            note_bits.append(f"Konum (çözülmemiş): {raw.get('location_tr')}.")
        if note_bits:
            record["note"] = " ".join(note_bits)[:2000]

        # Yerel kenarlar → sidecar (PID-bağlama ayrı koşu)
        for col in ("causes_event_id", "caused_by_event_id",
                    "related_battle_ids", "related_scholar_ids",
                    "related_ruler_ids", "dynasty_id", "dynasty_id_1",
                    "dynasty_id_2_or_enemy"):
            v = (raw.get(col) or "").strip()
            if v:
                side["edges"].append({"from": rid, "col": col, "raw": v})

        stats["minted"] += 1
        yield record

    resolver.close()
    print(f"[canonicalize] battles-events: minted={stats['minted']} "
          f"location-linked={stats['loc_linked']} "
          f"location-unlinked={stats['loc_unlinked']} "
          f"edges-pending={len(side['edges'])}")
