"""
canonicalize.py — Yâqūt intermediate → canonical iac:Place records.

For each extracted record (one per Yâqūt entry id), produce a schema-valid
canonical place record. ~12,954 records expected.

Two-pass design (mirrors the Bosworth pattern):
  - PASS 1 (this file): mint PIDs and emit canonical records WITHOUT
    located_in[] (which needs other place PIDs to exist). Parent-location
    names go to a sidecar (yaqut_parent_pending.json) keyed by canonical PID.
  - PASS 2 (pipelines/integrity/check_all.py): walk the sidecar, fuzzy-match
    each parent name against the place namespace's labels, append PID to
    located_in[]; check bidirectional consistency.

(c) merge-of-formats:
  - When raw.rich is present (project's yaqut_entries.json):
      * Use rich.heading + rich.heading_tr + rich.heading_en for labels
      * Use rich.summary_tr/_en for description
      * Use rich.alternate_names for altLabel
      * Use rich.coordinates (rich's curated coord block, ~1,209 records)
      * Use rich.etymology, rich.modern_country, etc. for note
  - When only raw.lite (kompakt) is present:
      * Use lite.h/ht/he for labels
      * Use lite.st/se for description
      * Use lite.lat/lon + lite.geo_confidence for coords (~11,471 records!)
      * Use lite.tg (atlas_tags) for note enrichment

This means: on user's machine where both files exist, full enrichment.
In sandbox (only kompakt), still produces good output — coverage just shifts
from 1,209 high-confidence coords to 11,471 stratified-confidence coords.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

# Allow this module to be run directly for dev testing
_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "_lib"
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib import place_canonicalize as pc  # noqa: E402


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    options = options or {}
    strict = options.get("strict_mode", True)
    pipeline_name = options.get("pipeline_name", "canonicalize_place")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    attributed_to = options.get(
        "attributed_to", "https://orcid.org/0000-0002-7747-6854"
    )
    license_uri = options.get(
        "license_uri", "https://creativecommons.org/licenses/by-sa/4.0/"
    )
    type_qid = options.get("reconciliation_type_qid", "Q486972")
    parent_sidecar = options.get("parent_sidecar")
    persons_sidecar = options.get("persons_sidecar")

    recon_filter = options.get("recon_filter") or {}
    recon_require_one_of = recon_filter.get("require_one_of") or []

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
                parent_sidecar=parent_sidecar,
                persons_sidecar=persons_sidecar,
                recon_require_one_of=recon_require_one_of,
                now=now,
            )
            if record is not None:
                yield record
        except Exception as exc:
            sid = extracted.get("source_record_id", "<unknown>")
            if strict:
                raise RuntimeError(f"canonicalize failed on {sid}: {exc}") from exc
            print(
                f"[canonicalize_place/yaqut] failed on {sid}: {exc}",
                file=sys.stderr,
            )


def _build_record(
    *,
    extracted: dict,
    pid_minter,
    reconciler,
    pipeline_name: str,
    pipeline_version: str,
    attributed_to: str,
    license_uri: str,
    type_qid: str,
    parent_sidecar: dict | None,
    persons_sidecar: dict | None,
    recon_require_one_of: list[str],
    now: str,
) -> dict | None:
    raw = extracted["raw_data"]
    yaqut_id = extracted["yaqut_id"]
    source_record_id = extracted["source_record_id"]

    lite = raw.get("lite") or {}
    detail = raw.get("detail") or {}
    crossref = raw.get("crossref") or []
    rich = raw.get("rich")  # may be None

    # ---- merged field accessors -----------------------------------------
    # Prefer rich format when present, fall back to lite

    name_ar = (rich and rich.get("heading")) or lite.get("h")
    name_tr = (rich and rich.get("heading_tr")) or lite.get("ht")
    name_en = (rich and rich.get("heading_en")) or lite.get("he")
    summary_tr = (rich and rich.get("summary_tr")) or lite.get("st")
    summary_en = (rich and rich.get("summary_en")) or lite.get("se")
    geo_type_corrected = (rich and rich.get("geo_type_corrected")) or lite.get("gt")
    modern_country = (rich and rich.get("modern_country")) or lite.get("ct")
    modern_region = (rich and rich.get("modern_region")) or lite.get("rg")
    historical_period = (rich and rich.get("historical_period")) or lite.get("hp")
    atlas_tags = (rich and rich.get("atlas_tags")) or lite.get("tg") or []
    dia_slug = (rich and rich.get("dia_slug")) or lite.get("ds")
    dia_url = rich and rich.get("dia_url")  # only in rich
    etymology = rich and rich.get("etymology")  # only in rich
    alternate_names = (rich and rich.get("alternate_names")) or []
    full_text_ar = detail.get("ft")  # always from detail file
    parent_locations = detail.get("pl") or []  # always from detail file

    # ---- coords merge ---------------------------------------------------
    coords = None
    coord_source_str = f"yaqut:{yaqut_id}"
    if rich and rich.get("coordinates"):
        rc = rich["coordinates"]
        match_type = rc.get("match_type", "")
        # rich's match_type → schema uncertainty
        if match_type in ("heading_direct", "ptolemaic", "heading_al_prefix",
                          "heading_al_strip"):
            # Direct attestation in Yâqūt
            coords = pc.build_coords(
                lat=rc.get("lat"),
                lon=rc.get("lon"),
                confidence="exact",
                derived_from_source=coord_source_str,
            )
        elif match_type == "parent_inherit":
            # Inherited from parent — flag as centroid-ish
            coords = pc.build_coords(
                lat=rc.get("lat"),
                lon=rc.get("lon"),
                confidence="region",
                derived_from_source=coord_source_str,
                note=f"Inherited from parent location {rc.get('parent', 'unknown')!r}.",
            )
    # Fall back to lite (kompakt) coords if rich didn't provide
    if coords is None and lite.get("lat") is not None and lite.get("lon") is not None:
        coords = pc.build_coords(
            lat=lite.get("lat"),
            lon=lite.get("lon"),
            confidence=lite.get("geo_confidence"),
            derived_from_source=coord_source_str,
        )

    # ---- mint PID -------------------------------------------------------
    pid = pid_minter.mint(namespace="place", input_hash=source_record_id)

    # ---- @type + place_subtype -----------------------------------------
    types_arr: list[str] = ["iac:Place"]
    subtype_field, subtype_uri = pc.classify_geo_type(geo_type_corrected)
    if subtype_uri:
        types_arr.append(subtype_uri)

    # ---- labels --------------------------------------------------------
    labels = pc.build_labels(
        name_ar=name_ar,
        name_tr=name_tr,
        name_en=name_en,
        alternate_names=alternate_names,
        description_tr=summary_tr,
        description_en=summary_en,
    )

    # ---- authority_xref (Wikidata via reconciler) ----------------------
    authority_xref: list[dict] = []
    has_dia = bool(dia_slug)
    has_alam = bool(crossref)
    has_coords_now = coords is not None

    # NOTE: DİA cross-references go into the `note` field for now — the v0.1.0
    # authority_xref enum doesn't include 'dia'. A schema migration in v0.2.0
    # will move this to a real authority entry. See place_canonicalize.format_dia_note.

    # ---- reconciliation gate -------------------------------------------
    flags = {
        "has_coords": has_coords_now,
        "has_dia_url": has_dia,
        "has_alam_crossref": has_alam,
    }
    should_reconcile = (
        reconciler is not None
        and (
            not recon_require_one_of
            or any(flags.get(req, False) for req in recon_require_one_of)
        )
    )
    if should_reconcile:
        recon_label = pc.label_for_recon(labels)
        ctx = {
            "region_primary": modern_country or "",
        }
        xref = reconciler.reconcile(
            label_en=recon_label,
            type_qid=type_qid,
            context=ctx,
            source_record_id=source_record_id,
        )
        if xref:
            authority_xref.append(xref)

    # ---- provenance ----------------------------------------------------
    page_locator = f"Yâqūt, Muʿjam al-Buldān, entry id={yaqut_id}"
    if name_ar:
        page_locator += f" ({name_ar})"
    provenance = pc.build_provenance(
        source_record_id=source_record_id,
        source_kind="primary_textual",
        page_locator=page_locator,
        edition="Beirut: Dār Sādir, 1977 (5 vols, ed. F. Wüstenfeld base); upstream pipeline ETL.",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        attributed_to=attributed_to,
        license_uri=license_uri,
        record_history_note=(
            f"Initial canonicalization from Yâqūt entry {yaqut_id} via "
            f"{pipeline_name} {pipeline_version} (Hafta 3 place pilot). "
            f"located_in[] populated by integrity/check_all.py in second pass "
            f"from parent_locations={parent_locations!r}."
        ),
        now=now,
    )

    # ---- editorial note assembly ---------------------------------------
    note_parts: list[str | None] = []
    dia_note = pc.format_dia_note(dia_slug, dia_url)
    if dia_note:
        note_parts.append(dia_note)
    if etymology:
        note_parts.append(f"Etymology: {etymology}")
    if modern_country:
        note_parts.append(f"Modern country: {modern_country}")
    if modern_region:
        note_parts.append(f"Modern region: {modern_region}")
    if atlas_tags:
        tag_str = ", ".join(str(t) for t in atlas_tags[:10])
        note_parts.append(f"Atlas tags: {tag_str}")
    if historical_period and historical_period != "active":
        note_parts.append(f"Historical period: {historical_period}")
    if geo_type_corrected and not subtype_uri:
        note_parts.append(
            f"Yâqūt geo_type: {geo_type_corrected!r} "
            f"(no schema subtype mapping in v0.1.0; place_subtype omitted)"
        )
    if parent_locations:
        note_parts.append(
            f"Parent locations from Yâqūt: {', '.join(parent_locations[:5])}"
            + (" (+more)" if len(parent_locations) > 5 else "")
            + ". Resolved to located_in[] in pass 2."
        )
    if has_alam:
        note_parts.append(
            f"Cross-referenced to {len(crossref)} El-Aʿlām biographies; "
            f"linked to person namespace in Hafta 4."
        )
    if full_text_ar:
        # Only first 200 chars of Yâqūt's actual Arabic prose
        snippet = full_text_ar[:200]
        if len(full_text_ar) > 200:
            snippet += "..."
        note_parts.append(f"Yâqūt source text (Arabic, truncated): {snippet}")

    # ---- compose record ------------------------------------------------
    record: dict = {
        "@id": pid,
        "@type": types_arr,
        "labels": labels,
        "provenance": provenance,
    }
    if subtype_field:
        record["place_subtype"] = subtype_field
    if coords:
        record["coords"] = coords
    if authority_xref:
        record["authority_xref"] = authority_xref
    record["yaqut_id"] = f"yaqut:{yaqut_id}"
    record["derived_from_layers"] = ["yaqut"]

    note = pc.assemble_note(note_parts)
    if note:
        record["note"] = note

    # ---- sidecars -------------------------------------------------------
    if parent_sidecar is not None and parent_locations:
        parent_sidecar[pid] = {
            "yaqut_id": yaqut_id,
            "parent_locations": parent_locations[:50],
        }
    if persons_sidecar is not None and crossref:
        # Keep the alam person crossrefs for Hafta 4 person-namespace linkage.
        persons_sidecar[pid] = {
            "yaqut_id": yaqut_id,
            "person_count": len(crossref),
            "persons": crossref[:200],  # cap for sidecar size
        }

    return record
