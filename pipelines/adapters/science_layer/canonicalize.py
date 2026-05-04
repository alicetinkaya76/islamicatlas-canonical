"""
canonicalize.py — Convert a science_layer scholar dict into an iac:person- record.

Distinctive features over Bosworth rulers:
  - Full trilingual names (en/tr/ar) and full_name forms (longer nasab)
  - birth_place + active_places carry coordinates and city names — but not
    PIDs. We sidecar them for resolution against the Yâqūt-anchored place
    namespace in person_integrity.py (forward-only per Y4.4 decision).
  - profession derived from `fields` field (mapped to person.schema enum).
  - xref_alam and xref_yaqut hints fed to the cross-source resolver.
  - description built from key_contribution + scholarly_context (multilingual
    if available).
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import person_canonicalize as pc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "İslam Medeniyeti Akademisi v7 (curated; Selçuk University, 2026)."

# fields enum from science_layer → profession enum from person.schema
_FIELD_TO_PROFESSION = {
    "mathematics": "mathematician",
    "astronomy": "astronomer",
    "geography": "geographer",
    "philosophy": "philosopher",
    "medicine": "physician",
    "history": "historian",
    "literature": "poet",       # closest available in person.schema enum
    "religious_sciences": "scholar",
    "theology": "scholar",
    "natural_sciences": "scholar",
    "social_sciences": "scholar",
    "music": "musician",
    "navigation": "geographer",
    "optics": "philosopher",     # natural philosophy umbrella
    "engineering": "scholar",    # no engineer enum value
    "architecture": "architect",
    "chemistry": "scholar",
    "culture": "scholar",
    "translation": "translator",
}


def _multilingual_get(d, key, lang):
    """Get d[key][lang] safely from a possibly-nested multilingual dict."""
    if not d or not isinstance(d, dict):
        return None
    v = d.get(key)
    if isinstance(v, dict):
        return v.get(lang)
    return None


def _build_description(sc: dict) -> dict:
    """Concatenate key_contribution + scholarly_context per language."""
    out = {}
    for lang in ("tr", "en", "ar"):
        bits = []
        kc = _multilingual_get(sc, "key_contribution", lang)
        sx = _multilingual_get(sc, "scholarly_context", lang)
        hn = _multilingual_get(sc, "historiographical_note", lang)
        if kc:
            bits.append(kc)
        if sx:
            bits.append(sx)
        if hn:
            bits.append(f"[Tarih notu] {hn}" if lang == "tr" else f"[Historiographical note] {hn}")
        if bits:
            out[lang] = " || ".join(bits)
    return out


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "person"
    sidecars = options.get("sidecars", {})
    xref_alam_sc = sidecars.get("science_layer_xref_alam", {})
    xref_yaqut_sc = sidecars.get("science_layer_xref_yaqut", {})
    active_places_sc = sidecars.get("science_layer_active_places_pending", {})

    pipeline_name = options.get("pipeline_name", "canonicalize_person_science_layer")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        sc = record["raw"]
        sid = record["source_id"]  # e.g. "scholar_0001"

        # Idempotent PID
        input_hash = f"science-layer:{sid}"
        pid = pid_minter.mint(namespace, input_hash)

        # Names
        name = sc.get("name") or {}
        full_name = sc.get("full_name") or {}

        # Description
        desc = _build_description(sc)

        # Labels
        labels = pc.build_person_labels(
            name_en=name.get("en"),
            name_tr=name.get("tr"),
            name_ar=name.get("ar"),
            full_name_en=full_name.get("en"),
            full_name_tr=full_name.get("tr"),
            full_name_ar=full_name.get("ar"),
            description_tr=desc.get("tr"),
            description_en=desc.get("en"),
            description_ar=desc.get("ar"),
        )

        # Temporal — birth/death
        birth_y = sc.get("birth_year")
        death_y = sc.get("death_year")
        birth_temporal = None
        death_temporal = None
        if birth_y is not None:
            birth_temporal = {"start_ce": int(birth_y), "approximation": "exact"}
        if death_y is not None:
            death_temporal = {"start_ce": int(death_y), "approximation": "exact"}

        # Profession from fields[]
        professions = []
        for f in (sc.get("fields") or []):
            p = _FIELD_TO_PROFESSION.get(f)
            if p and p not in professions:
                professions.append(p)
        # Always ensure at least one: scholar fallback
        if not professions:
            professions = ["scholar"]

        # @type
        types = pc.build_type_array(professions)

        # provenance
        provenance = pc.build_provenance(
            source_record_id=f"science-layer:{sid}",
            source_kind="manual_editorial",
            page_locator=(
                f"İslam Medeniyeti Akademisi v7, scholar id={sid}"
                + (f", lecture_id={sc.get('lecture_id')}" if sc.get('lecture_id') else "")
            ),
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=(
                f"Initial canonicalization from science_layer.json scholar id={sid} "
                f"by science-layer adapter (Hafta 4). Tier-1 seed for cross-source "
                f"resolver (DİA + El-Aʿlām). active_places + birth_place sidecar'd "
                f"for resolution by person_integrity.py."
            ),
        )

        # Authority xref — Wikidata recon attempt
        authority_xref = []
        recon_label = pc.label_for_recon(labels)
        if reconciler is not None and recon_label:
            try:
                hit = reconciler.reconcile(
                    label_en=recon_label,
                    type_qid=options.get("reconciliation_type_qid", "Q5"),
                    source_record_id=input_hash,
                    context={"death_year_ce": death_y},
                )
                if hit:
                    authority_xref.append(hit)
            except Exception:
                pass

        # Build record
        person: dict = {
            "@id": pid,
            "@type": types,
            "labels": labels,
            "profession": professions,
            "provenance": provenance,
        }
        if birth_temporal:
            person["birth_temporal"] = birth_temporal
        if death_temporal:
            person["death_temporal"] = death_temporal
        if authority_xref:
            person["authority_xref"] = authority_xref

        # Cross-source xref hints → sidecars (consumed by resolver in DİA + Alam adapters)
        xa = sc.get("xref_alam")
        if xa and isinstance(xa, dict) and xa.get("id"):
            xref_alam_sc[pid] = {
                "alam_id": xa["id"],
                "name_ar": xa.get("name_ar"),
                "name_tr": xa.get("name_tr"),
                "death_h": xa.get("death_h"),
                "death_m": xa.get("death_m"),
                "scholar_name_en": name.get("en"),
                "scholar_death_year": death_y,
            }
        xy = sc.get("xref_yaqut")
        if xy and isinstance(xy, dict) and xy.get("id"):
            xref_yaqut_sc[pid] = {
                "yaqut_id": xy["id"],
                "name_ar": xy.get("name_ar"),
                "name_tr": xy.get("name_tr"),
                "type": xy.get("type"),
                "distance_km": xy.get("distance_km"),
                "scholar_name_en": name.get("en"),
            }

        # Active places sidecar (for forward person.active_in_places resolution)
        ap_entry = {
            "birth_place": sc.get("birth_place"),
            "active_places": sc.get("active_places") or [],
        }
        if ap_entry["birth_place"] or ap_entry["active_places"]:
            active_places_sc[pid] = ap_entry

        # Note: include short DİA/cross-source hints if any survived training
        note_bits = [
            f"Promoted from science_layer.json scholar id={sid}, lecture_week={sc.get('lecture_week') or 'n/a'}.",
        ]
        if sc.get("key_works"):
            kw = sc["key_works"]
            if isinstance(kw, list):
                kw_text = "; ".join(str(w) for w in kw if w)[:500]
                if kw_text:
                    note_bits.append(f"Key works: {kw_text}")
            elif isinstance(kw, str):
                note_bits.append(f"Key works: {kw[:500]}")
        if sc.get("modern_parallel"):
            mp = sc["modern_parallel"]
            mp_str = mp.get("en") if isinstance(mp, dict) else mp
            if mp_str:
                note_bits.append(f"Modern parallel: {str(mp_str)[:300]}")
        person["note"] = pc.assemble_note(note_bits)

        yield person
