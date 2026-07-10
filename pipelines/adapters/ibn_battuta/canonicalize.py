"""
canonicalize.py — İbn Battûta durakları → place (iki-track, evliya deseni).

match → augment sidecar (derived_from_layers += ibn-battuta; varış tarihi +
Rihla locator kanıtı) · new → Settlement mint (temporal = varış yılı CE) ·
review → kuyruk (mint yok). Rota şehirleri çoğunlukla store'da → augment
ağırlıklı beklenir. 7 sefer `voyages_pending`'e sayılır (event-aktivasyonu).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "İbn Battûta Rihle atlas katmanı (ibn_battuta_atlas_layer.json)"


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_place_ibn_battuta")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("ibn_battuta_augment")
    if side is None:
        side = {}
    side.setdefault("augments", {})
    side.setdefault("_review_skipped", {})
    side.setdefault("voyages_pending", {"count": 7, "note": "event-aktivasyonu bekliyor"})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"match": 0, "new": 0, "review": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]

        labels = {"prefLabel": {}}
        for k, lang in (("tr", "tr"), ("en", "en"), ("ar", "ar")):
            v = (raw.get(k) or "").strip()
            if v and v not in labels["prefLabel"].values():
                labels["prefLabel"][lang] = v
        if not labels["prefLabel"]:
            labels["prefLabel"]["tr"] = rid
        arr_year = None
        arr = (raw.get("arr") or "")[:4]
        if arr.isdigit():
            arr_year = int(arr)
        temporal = {"start_ce": arr_year} if arr_year else {}

        decision = resolver.resolve(
            entity_type="place", adapter_id="ibn-battuta",
            extracted_record_id=rid, labels=labels, temporal=temporal,
            coords={"lat": raw.get("lat"), "lon": raw.get("lon")})

        if decision.kind == "match":
            stats["match"] += 1
            side["augments"].setdefault(decision.matched_pid, []).append({
                "stop_id": raw.get("id"), "confidence": decision.confidence,
                "name_tr": raw.get("tr"), "voyage_id": raw.get("voyage_id"),
                "arrival": raw.get("arr"), "arrival_ah": raw.get("arr_ah"),
                "src_page": raw.get("src_page"),
                "narrative_tr": (raw.get("narr_tr") or "")[:2000] or None,
            })
            continue
        if decision.kind == "review":
            stats["review"] += 1
            side["_review_skipped"][rid] = {
                "queue_id": decision.queue_id, "confidence": decision.confidence,
                "name_tr": raw.get("tr")}
            continue

        stats["new"] += 1
        yield _build_place(raw, labels, temporal, rid, pid_minter,
                           pipeline_name, pipeline_version, now)

    resolver.close()
    print(f"[canonicalize] ibn-battuta: match(augment)={stats['match']} "
          f"new(mint)={stats['new']} review={stats['review']} voyages_pending=7")


def _build_place(raw, labels, temporal, rid, pid_minter,
                 pipeline_name, pipeline_version, now) -> dict:
    pid = pid_minter.mint("place", rid)
    desc = {}
    if raw.get("narr_tr"):
        desc["tr"] = raw["narr_tr"][:5000]
    if raw.get("narr_en"):
        desc["en"] = raw["narr_en"][:5000]
    if desc:
        labels = {**labels, "description": desc}
    record = {
        "@id": pid,
        "@type": ["iac:Place", "iac:Settlement"],
        "place_subtype": "settlement",
        "labels": labels,
        "coords": {"lat": raw["lat"], "lon": raw["lon"],
                   "uncertainty": {"type": "centroid"},
                   "precision_meters": 10000,
                   "derived_from_source": rid},
        "derived_from_layers": ["ibn-battuta"],
        "note": (f"İbn Battûta Rihle durağı (sefer {raw.get('voyage_id')}, "
                 f"sıra {raw.get('seq')}; varış {raw.get('arr') or '?'} / "
                 f"{raw.get('arr_ah') or '?'} AH; bölge "
                 f"{raw.get('region_tr') or '?'}).")[:2000],
        "provenance": {
            "derived_from": [{
                "source_id": rid,
                "source_type": "primary_textual",
                "page_or_locator": (f"Rihla, s. {raw.get('src_page')}"
                                    if raw.get("src_page") else
                                    f"Rihla, sefer {raw.get('voyage_id')} sıra {raw.get('seq')}"),
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
                "note": f"Initial canonicalization by {pipeline_name} "
                        f"{pipeline_version} (H10 Stage 8; Tier-2 kind=new).",
            }],
            "deprecated": False,
        },
    }
    if temporal:
        record["temporal_coverage"] = temporal
    return record
