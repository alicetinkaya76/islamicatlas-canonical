"""
canonicalize.py — scholars → person namespace, Tier-2-resolved two-track
(darp-islam pattern, person edition).

  TRACK A (match): the scholar exists (dia/science-layer/el-alam seeded the
    famous ones). NO new record — augmentation sidecar entry with the fields
    the store typically lacks: labels.description.en / prefLabel.en gap-fill,
    kunya/nisba/laqab gap-fill, EN narrative. Applied append-only by
    pipelines/integrity/apply_scholars_augments.py.
  TRACK B (new): full person mint (labels tr/en + descriptions, birth/death
    temporal from CE years, kunya/nisba/laqab, profession=[scholar]).
  REVIEW: queued by the resolver; skipped (never minted).

madhab is a PID-ref to the (empty, P1) concept namespace → NOT populated;
the school name stays inside the note. Teacher/student edges (scholar_links)
are Stage-3b work — they need this run's id→pid map, which is emitted to the
sidecar for that purpose.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = ("islamicatlas.org v1 scholars layer (scholars.csv + "
           "scholar_identity.js v4.8.x; DİA-sourced bilingual cards)")


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    namespace = options.get("namespace", "person")
    pipeline_name = options.get("pipeline_name", "canonicalize_person_scholars")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    augment = sidecars.get("scholars_augment")
    if augment is None:
        augment = {}

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first "
                           "(pipelines/_index/build_lookup.py).")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    id_to_pid = augment.setdefault("_id_to_pid", {})   # Stage-3b edge input
    n_match = n_new = n_review = 0

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        card = raw.get("identity") or {}

        labels = {"prefLabel": {}}
        if raw.get("name_tr"):
            labels["prefLabel"]["tr"] = raw["name_tr"]
        if raw.get("name_en"):
            labels["prefLabel"]["en"] = raw["name_en"]
        if raw.get("name_ar"):  # H11 S4: db.json Arapça adları getirdi
            labels["prefLabel"]["ar"] = raw["name_ar"]
        alt = [v for v in (raw.get("name_original"),) if v]
        if alt:  # ALA-LC transliteration ("Abū Ḥanīfa al-Nuʿmān") → en bucket
            labels["altLabel"] = {"en": alt}

        temporal = {}
        d = raw.get("death_ce")  # db.json int verir; csv str verirdi
        if isinstance(d, str) and d.strip().lstrip("-").isdigit():
            d = int(d.strip())
        if isinstance(d, int):
            temporal["start_ce"] = d

        decision = resolver.resolve(
            entity_type="person", adapter_id="scholars",
            extracted_record_id=rid, labels=labels, temporal=temporal,
            kunya=card.get("kunya_tr"))

        if decision.kind == "match":
            n_match += 1
            id_to_pid[raw["scholar_id"]] = decision.matched_pid
            augment.setdefault(decision.matched_pid, []).append(
                _augment_payload(raw, card, decision))
            continue

        if decision.kind == "review":
            n_review += 1
            skipped = augment.setdefault("_review_skipped", {})
            skipped[rid] = {"queue_id": decision.queue_id,
                            "confidence": decision.confidence,
                            "name_tr": raw.get("name_tr")}
            continue

        n_new += 1
        record = _build_person(raw, card, labels, rid, pid_minter, namespace,
                               pipeline_name, pipeline_version, now)
        id_to_pid[raw["scholar_id"]] = record["@id"]
        yield record

    resolver.close()
    print(f"[canonicalize] scholars: match(augment)={n_match} "
          f"new(mint)={n_new} review(skipped)={n_review}")


def _augment_payload(raw, card, decision) -> dict:
    return {
        "scholar_id": raw["scholar_id"],
        "matched_via": f"tier{decision.tier}",
        "confidence": decision.confidence,
        "name_tr": raw.get("name_tr"),
        "preflabel_en": raw.get("name_en"),
        "description_en": raw.get("narrative_en"),
        "description_tr": raw.get("narrative_tr"),
        "description_ar": raw.get("narrative_ar"),
        "preflabel_ar": raw.get("name_ar"),
        "kunya": card.get("kunya_tr"),
        "nisba": _split_list(card.get("nisba_tr")),
        "laqab": _split_list(card.get("laqab_tr")),
        "field": raw.get("field"),
        "sub_field": raw.get("sub_field"),
    }


def _split_list(v):
    if not v:
        return []
    return [s.strip() for s in str(v).split(",") if s.strip()][:6]


def _build_person(raw, card, labels, rid, pid_minter, namespace,
                  pipeline_name, pipeline_version, now) -> dict:
    pid = pid_minter.mint(namespace, rid)
    record = {
        "@id": pid,
        "@type": ["iac:Person", "iac:Scholar"],
        "labels": labels,
        "profession": ["scholar"],
        "provenance": {
            "derived_from": [{
                "source_id": rid,
                "source_type": "digital_corpus",
                "page_or_locator": f"scholars.csv scholar_id={raw['scholar_id']}",
                "extraction_method": "structured_json",
                "edition_or_version": EDITION,
            }],
            "generated_by": {"pipeline_name": pipeline_name,
                             "pipeline_version": pipeline_version},
            "generated_at": now,
            "attributed_to": ATTRIBUTED_TO,
            "created": now,
            "modified": now,
            "license": LICENSE,
            "record_history": [{
                "change_type": "create", "changed_at": now,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": f"Initial canonicalization by {pipeline_name} "
                        f"{pipeline_version} (H10 Stage 3; Tier-2 kind=new).",
            }],
            "deprecated": False,
        },
    }
    desc = {}
    if raw.get("narrative_tr"):
        desc["tr"] = raw["narrative_tr"][:5000]
    if raw.get("narrative_en"):
        desc["en"] = raw["narrative_en"][:5000]
    if raw.get("narrative_ar"):
        desc["ar"] = raw["narrative_ar"][:5000]
    if desc:
        record["labels"]["description"] = desc
    if card.get("kunya_tr"):
        record["kunya"] = card["kunya_tr"][:200]
    nisba = _split_list(card.get("nisba_tr"))
    if nisba:
        record["nisba"] = nisba
    laqab = _split_list(card.get("laqab_tr"))
    if laqab:
        record["laqab"] = laqab
    for csv_f, rec_f in (("birth_ce", "birth_temporal"), ("death_ce", "death_temporal")):
        v = raw.get(csv_f)
        if v and str(v).lstrip("-").isdigit():
            record[rec_f] = {"start_ce": int(v), "approximation": "exact"}
    return record
