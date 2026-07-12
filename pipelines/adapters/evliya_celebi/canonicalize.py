"""
canonicalize.py — Evliyâ konumları → place (yerleşim alt kümesi), darp deseni.

Kategori yönlendirmesi (H10 Stage 7 kararı — sayılar journal'da):
  YERLEŞİM (place'e; iki-track):  şehir, kasaba, köy, kale, liman, ada
  YAPI (institution-bekleyen):    cami, türbe, hamam, tekke, han, saray,
                                  medrese, mescit, köprü, kilise, çeşme,
                                  bedesten — konya/maqrizi ile aynı havuz;
                                  ADR-006 §6.4 kararı (Ali) gelince dönüşür
  DOĞAL/BELİRSİZ (triage):        dağ, göl, nehir, bilinmeyen — place
                                  şemasına sokulabilir ama Yâqūt'un doğal
                                  yer geleneğinden farklı kaynak kalitesi;
                                  insan triage'ı

Track'ler: match → augment sidecar (derived_from_layers += evliya-celebi),
new → mint (@type Settlement; temporal_coverage ≈ Seyahatnâme dönemi
1640-1684 yalnız year_approx varsa o yıl), review → kuyruk (mint yok).
10 sefer event-aktivasyonuna kadar sidecar'da sayılır.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = ("Evliyâ Çelebi Seyahatnâme Atlas Katmanı v2.0.0 (2026-04-02); "
           "kaynaklar: Başaran Google Maps, al-Thurayyā Gazetteer, Wikidata, "
           "Üçdal Neşriyat")

SETTLEMENT = {"şehir", "kasaba", "köy", "kale", "liman", "ada"}
BUILDING = {"cami", "türbe", "hamam", "tekke", "han", "saray", "medrese",
            "mescit", "köprü", "kilise", "çeşme", "bedesten"}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_place_evliya")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("evliya_augment")
    if side is None:
        side = {}
    for k in ("augments", "_review_skipped", "institution_pending",
              "nature_triage", "voyages_pending"):
        side.setdefault(k, {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"match": 0, "new": 0, "review": 0, "building": 0, "nature": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        cat = (raw.get("category") or "bilinmeyen").strip()

        if cat in BUILDING:
            stats["building"] += 1
            b = side["institution_pending"]
            b[cat] = b.get(cat, 0) + 1
            continue
        if cat not in SETTLEMENT:
            stats["nature"] += 1
            nt = side["nature_triage"]
            nt[cat] = nt.get(cat, 0) + 1
            continue

        labels = {"prefLabel": {}}
        for k, lang in (("name_tr", "tr"), ("name_en", "en"), ("name_ar", "ar")):
            v = (raw.get(k) or "").strip()
            if v and v not in labels["prefLabel"].values():
                labels["prefLabel"][lang] = v
        if not labels["prefLabel"]:
            labels["prefLabel"]["tr"] = rid
        temporal = {}
        if isinstance(raw.get("year_approx"), int):
            temporal["start_ce"] = raw["year_approx"]

        decision = resolver.resolve(
            entity_type="place", adapter_id="evliya-celebi",
            extracted_record_id=rid, labels=labels, temporal=temporal,
            coords={"lat": raw.get("lat"), "lon": raw.get("lng")})

        if decision.kind == "match":
            stats["match"] += 1
            side["augments"].setdefault(decision.matched_pid, []).append({
                "evliya_id": raw.get("id"), "confidence": decision.confidence,
                "name_tr": raw.get("name_tr"), "category": cat,
                "voyage_id": raw.get("voyage_id"),
                "description_tr": (raw.get("description_tr") or "")[:2000] or None,
                "description_en": (raw.get("description_en") or "")[:2000] or None,
            })
            continue
        if decision.kind == "review":
            stats["review"] += 1
            side["_review_skipped"][rid] = {
                "queue_id": decision.queue_id, "confidence": decision.confidence,
                "name_tr": raw.get("name_tr"), "category": cat}
            continue

        stats["new"] += 1
        yield _build_place(raw, labels, temporal, rid, cat, pid_minter,
                           pipeline_name, pipeline_version, now)

    resolver.close()
    print(f"[canonicalize] evliya: match(augment)={stats['match']} "
          f"new(mint)={stats['new']} review={stats['review']} "
          f"building(institution-pending)={stats['building']} "
          f"nature/unknown(triage)={stats['nature']}")


def _build_place(raw, labels, temporal, rid, cat, pid_minter,
                 pipeline_name, pipeline_version, now) -> dict:
    pid = pid_minter.mint("place", rid)
    desc = {}
    if raw.get("description_tr"):
        desc["tr"] = raw["description_tr"][:5000]
    if raw.get("description_en"):
        desc["en"] = raw["description_en"][:5000]
    if desc:
        labels = {**labels, "description": desc}
    record = {
        "@id": pid,
        "@type": ["iac:Place", "iac:Settlement"],
        "place_subtype": "settlement",
        "labels": labels,
        "coords": {"lat": raw["lat"], "lon": raw["lng"],
                   "uncertainty": {"type": "centroid"},
                   "precision_meters": 10000,
                   "derived_from_source": rid},
        "derived_from_layers": ["evliya-celebi"],
        "note": (f"Evliyâ Çelebi Seyahatnâme konumu (kategori: {cat}; "
                 f"sefer: {raw.get('voyage_id') or '?'}). 17. yy Osmanlı "
                 f"coğrafyası.")[:2000],
        "provenance": {
            "derived_from": [{
                "source_id": rid,
                "source_type": "digital_corpus",
                "page_or_locator": (f"Seyahatnâme, sefer {raw.get('voyage_id')}"
                                    + (f", cilt {raw.get('volume')}" if raw.get("volume") else "")),
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
                        f"{pipeline_version} (H10 Stage 7; Tier-2 kind=new).",
            }],
            "deprecated": False,
        },
    }
    if temporal:
        record["temporal_coverage"] = temporal
    return record
