"""
canonicalize.py — Muqaddasī intermediate → canonical iac:Place / iac:Iqlim records.

Two record kinds are produced:
  - iqlim records: 21 top-level regions, @type=['iac:Place', 'iac:Iqlim']
  - place records: 2,049 individual settlements, @type=['iac:Place', 'iac:Settlement']
    when settled (most have certainty='certain' which we treat as settlement).

Cross-source merge: when a Muqaddasī place has yaqut_id, we still mint a NEW
PID in this pass (the resolver-merge happens later in integrity/check_all.py
or via the Tier-1 lookup index). The yaqut cross-ref is recorded in:
  - record.note (for the audit trail)
  - sidecar 'muqaddasi_yaqut_pending.json' for pass-2 merge resolution

This deferred-merge pattern keeps Pass-1 idempotent and avoids race conditions
between Yâqūt and Muqaddasī when both adapters run in the same session.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "_lib"
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib import place_canonicalize as pc  # noqa: E402

# Map Muqaddasī's certainty enum → schema uncertainty.type
MUQ_CERTAINTY_TO_UNCERTAINTY: dict[str, tuple[str, int]] = {
    "certain":      ("exact",       100),
    "exact":        ("exact",       100),
    "modern_known": ("exact",       100),
    "approximate":  ("approximate", 10_000),
    "estimated":    ("approximate", 25_000),
    "inferred":     ("approximate", 25_000),
    "region":       ("centroid",    50_000),
    "country":      ("centroid",    250_000),
    "uncertain":    ("approximate", 50_000),
}


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    options = options or {}
    strict = options.get("strict_mode", True)
    pipeline_name = options.get("pipeline_name", "canonicalize_place_muqaddasi")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    attributed_to = options.get(
        "attributed_to", "https://orcid.org/0000-0002-7747-6854"
    )
    license_uri = options.get(
        "license_uri", "https://creativecommons.org/licenses/by-sa/4.0/"
    )
    type_qid = options.get("reconciliation_type_qid", "Q486972")

    # Sidecar for cross-source merge data — keyed by minted PID
    yaqut_xref_sidecar = options.get("yaqut_xref_sidecar")
    if yaqut_xref_sidecar is None:
        # Fallback to events_sidecar slot for backward-compat (run_adapter
        # passes a few sidecar dicts; we use whichever is configured).
        yaqut_xref_sidecar = options.get("events_sidecar")

    now = pc.now_iso()

    for extracted in extracted_records:
        try:
            record = _build_record(
                extracted=extracted,
                pid_minter=pid_minter,
                reconciler=reconciler,
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                attributed_to=attributed_to,
                license_uri=license_uri,
                type_qid=type_qid,
                yaqut_xref_sidecar=yaqut_xref_sidecar,
                now=now,
            )
            if record is not None:
                yield record
        except Exception as exc:
            sid = extracted.get("source_record_id", "<unknown>")
            if strict:
                raise RuntimeError(f"canonicalize failed on {sid}: {exc}") from exc
            print(f"[muqaddasi] failed on {sid}: {exc}", file=sys.stderr)


def _build_record(
    *, extracted, pid_minter, reconciler, pipeline_name, pipeline_version,
    attributed_to, license_uri, type_qid, yaqut_xref_sidecar, now,
):
    raw = extracted["raw_data"]
    rec_id = extracted["source_record_id"]
    kind = extracted["record_kind"]
    pid = pid_minter.mint(namespace="place", input_hash=rec_id)

    if kind == "iqlim":
        return _build_iqlim_record(
            pid=pid, raw=raw, rec_id=rec_id, locator=extracted["source_locator"],
            pipeline_name=pipeline_name, pipeline_version=pipeline_version,
            attributed_to=attributed_to, license_uri=license_uri,
            type_qid=type_qid, reconciler=reconciler, now=now,
        )
    elif kind == "place":
        return _build_place_record(
            pid=pid, raw=raw, rec_id=rec_id,
            yaqut_id=extracted.get("yaqut_id"),
            locator=extracted["source_locator"],
            pipeline_name=pipeline_name, pipeline_version=pipeline_version,
            attributed_to=attributed_to, license_uri=license_uri,
            type_qid=type_qid, reconciler=reconciler, now=now,
            yaqut_xref_sidecar=yaqut_xref_sidecar,
        )
    return None


def _build_iqlim_record(
    *, pid, raw, rec_id, locator, pipeline_name, pipeline_version,
    attributed_to, license_uri, type_qid, reconciler, now,
):
    iqlim_ar = raw["iqlim_ar"]
    iqlim_tr = raw.get("iqlim_tr")
    iqlim_en = raw.get("iqlim_en")
    type_ar = raw.get("type_ar", "")
    declared_regions = raw.get("declared_regions") or []

    labels = pc.build_labels(
        name_ar=iqlim_ar,
        name_tr=iqlim_tr,
        name_en=iqlim_en,
    )

    # Reconcile this iqlim against Wikidata (most are well-known regions)
    authority_xref: list[dict] = []
    if reconciler is not None:
        recon_label = pc.label_for_recon(labels)
        # Use Q1620908 (region) as the type hint for iqlims — schema-matched
        xref = reconciler.reconcile(
            label_en=recon_label,
            type_qid="Q1620908",  # region
            context=None,
            source_record_id=rec_id,
        )
        if xref:
            authority_xref.append(xref)

    page_locator = (
        f"al-Muqaddasī, Aḥsan al-Taqāsīm, line {locator.get('line', '?')} "
        f"({type_ar} → iqlim)"
    )
    provenance = pc.build_provenance(
        source_record_id=rec_id,
        source_kind="primary_textual",
        page_locator=page_locator,
        edition="M. J. de Goeje (ed.), BGA III (Leiden, 1906); upstream pipeline ETL.",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        attributed_to=attributed_to,
        license_uri=license_uri,
        record_history_note=(
            f"Initial canonicalization from al-Muqaddasī iqlim {iqlim_ar!r} "
            f"({iqlim_en or iqlim_tr}) via {pipeline_name} {pipeline_version}. "
            f"Top-level regional schema; child settlements canonicalized "
            f"separately and link to this PID via falls_within_iqlim."
        ),
        now=now,
    )

    note_parts = []
    if declared_regions:
        note_parts.append(
            f"Declared sub-regions per al-Muqaddasī: {', '.join(declared_regions[:10])}"
            + (f" (+{len(declared_regions)-10} more)" if len(declared_regions) > 10 else "")
        )
    if type_ar:
        note_parts.append(f"Muqaddasī classification: {type_ar} (top-level iqlim)")
    note_parts.append(
        f"This is one of al-Muqaddasī's 21 top-level iqlims; predates Yâqūt's "
        f"regional schema by ~240 years."
    )

    record: dict = {
        "@id": pid,
        "@type": ["iac:Place", "iac:Iqlim"],
        "place_subtype": "iqlim",
        "labels": labels,
        "provenance": provenance,
        "derived_from_layers": ["makdisi"],   # schema enum uses 'makdisi' for the layer
    }
    if authority_xref:
        record["authority_xref"] = authority_xref
    note = pc.assemble_note(note_parts)
    if note:
        record["note"] = note
    return record


def _build_place_record(
    *, pid, raw, rec_id, yaqut_id, locator, pipeline_name, pipeline_version,
    attributed_to, license_uri, type_qid, reconciler, now, yaqut_xref_sidecar,
):
    name_ar = raw.get("name_ar", "").strip()
    name_tr = raw.get("name_tr")
    name_en = raw.get("name_en")
    desc_tr = raw.get("desc_tr")
    desc_en = raw.get("desc_en")
    lat = raw.get("lat")
    lon = raw.get("lon")
    certainty = raw.get("certainty", "uncertain")
    coord_source = raw.get("coord_source")
    iqlim_ar = raw.get("iqlim_ar")
    thurayya_uri = raw.get("thurayya_uri")

    labels = pc.build_labels(
        name_ar=name_ar,
        name_tr=name_tr,
        name_en=name_en,
        description_tr=desc_tr,
        description_en=desc_en,
    )

    # Coords with Muqaddasī-specific certainty mapping
    coords = None
    if lat is not None and lon is not None:
        cmap = MUQ_CERTAINTY_TO_UNCERTAINTY.get(certainty,
                                                 ("approximate", 25_000))
        coords = {
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "uncertainty": {"type": cmap[0]},
            "precision_meters": cmap[1],
            "derived_from_source": rec_id,
        }
        if coord_source:
            coords["uncertainty"]["note"] = f"Coord source: {coord_source}"

    authority_xref: list[dict] = []
    if reconciler is not None and certainty in ("certain", "exact", "modern_known"):
        # Only reconcile high-confidence places to keep recon volume manageable
        recon_label = pc.label_for_recon(labels)
        xref = reconciler.reconcile(
            label_en=recon_label,
            type_qid=type_qid,
            context=None,
            source_record_id=rec_id,
        )
        if xref:
            authority_xref.append(xref)

    page_locator = (
        f"al-Muqaddasī, Aḥsan al-Taqāsīm, "
        f"id={raw.get('id')} ({name_ar}, certainty={certainty})"
    )
    provenance = pc.build_provenance(
        source_record_id=rec_id,
        source_kind="primary_textual",
        page_locator=page_locator,
        edition="M. J. de Goeje (ed.), BGA III (Leiden, 1906); upstream pipeline ETL.",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        attributed_to=attributed_to,
        license_uri=license_uri,
        record_history_note=(
            f"Initial canonicalization from al-Muqaddasī place {raw.get('id')} "
            f"({name_ar}). Cross-references to Yâqūt id={yaqut_id} "
            f"recorded for pass-2 merge." if yaqut_id else
            f"Initial canonicalization from al-Muqaddasī place {raw.get('id')} "
            f"({name_ar}). No Yâqūt cross-reference."
        ),
        now=now,
    )

    note_parts = []
    if iqlim_ar:
        note_parts.append(
            f"Muqaddasī iqlim membership: {iqlim_ar} "
            f"(falls_within_iqlim resolved in pass 2)."
        )
    if thurayya_uri:
        note_parts.append(f"Thurayya gazetteer URI: {thurayya_uri}")
    if coord_source:
        note_parts.append(f"Coordinate sources: {coord_source}")
    if yaqut_id:
        note_parts.append(
            f"Cross-reference to Yâqūt entry yaqut:{yaqut_id} (resolver-merge "
            f"into existing Yâqūt PID expected in integrity pass 2)."
        )
    note_parts.append(
        f"al-Muqaddasī (d. 390/1000) classifies this as a settlement of "
        f"certainty='{certainty}'."
    )

    # Decide @type
    types_arr = ["iac:Place"]
    subtype_field: str | None = None
    if certainty in ("certain", "exact", "modern_known"):
        types_arr.append("iac:Settlement")
        subtype_field = "settlement"

    record: dict = {
        "@id": pid,
        "@type": types_arr,
        "labels": labels,
        "provenance": provenance,
        "derived_from_layers": ["makdisi"],
    }
    if subtype_field:
        record["place_subtype"] = subtype_field
    if coords:
        record["coords"] = coords
    if authority_xref:
        record["authority_xref"] = authority_xref
    note = pc.assemble_note(note_parts)
    if note:
        record["note"] = note

    # Sidecar for pass-2 yaqut merge
    if yaqut_id and yaqut_xref_sidecar is not None:
        yaqut_xref_sidecar[pid] = {
            "muqaddasi_id": raw.get("id"),
            "yaqut_id": yaqut_id,
            "yaqut_curie": f"yaqut:{yaqut_id}",
            "iqlim_ar": iqlim_ar,
        }

    return record
