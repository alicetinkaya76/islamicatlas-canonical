"""
canonicalize.py — Le Strange → canonical iac:Place records.

Two-track logic:
  - When yaqut_id present (274/434): SKIP record creation; record an augmentation
    entry in the yaqut_xref sidecar. Pass-2 integrity backfill reads this and
    appends 'le-strange' to the existing Yâqūt PID's derived_from_layers,
    plus alternate_names from le_strange_form, plus chapter/page provenance.
  - When yaqut_id absent (160/434): create a NEW place record (these are mostly
    rivers, smaller fortresses, and specific Le Strange-only entries).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "_lib"
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib import place_canonicalize as pc  # noqa: E402


# Le Strange's geo_type values map roughly the same way as Yâqūt's
# Most Le Strange records are cities, towns, fortresses, rivers, provinces
GEO_MAP_LE_STRANGE = {
    "city": ("settlement", "iac:Settlement"),
    "town": ("settlement", "iac:Settlement"),
    "village": ("settlement", "iac:Settlement"),
    "fortress": ("settlement", "iac:Settlement"),
    "castle": ("settlement", "iac:Settlement"),
    "port": ("settlement", "iac:Settlement"),
    "district": ("settlement", "iac:Settlement"),
    "province": ("region", "iac:Region"),
    "region": ("region", "iac:Region"),
}


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    options = options or {}
    strict = options.get("strict_mode", True)
    pipeline_name = options.get("pipeline_name", "canonicalize_place_le_strange")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    attributed_to = options.get(
        "attributed_to", "https://orcid.org/0000-0002-7747-6854"
    )
    license_uri = options.get(
        "license_uri", "https://creativecommons.org/licenses/by-sa/4.0/"
    )
    type_qid = options.get("reconciliation_type_qid", "Q486972")

    yaqut_xref_sidecar = options.get("yaqut_xref_sidecar")
    if yaqut_xref_sidecar is None:
        yaqut_xref_sidecar = options.get("events_sidecar")

    now = pc.now_iso()

    n_augment = 0
    n_new = 0

    for extracted in extracted_records:
        try:
            yaqut_id = extracted.get("yaqut_id")
            if yaqut_id:
                # AUGMENTATION track — record into sidecar but emit no canonical record
                if yaqut_xref_sidecar is not None:
                    _record_augmentation(
                        extracted=extracted,
                        sidecar=yaqut_xref_sidecar,
                    )
                n_augment += 1
                continue

            # NEW-RECORD track
            record = _build_new_record(
                extracted=extracted,
                pid_minter=pid_minter,
                reconciler=reconciler,
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                attributed_to=attributed_to,
                license_uri=license_uri,
                type_qid=type_qid,
                now=now,
            )
            if record is not None:
                n_new += 1
                yield record
        except Exception as exc:
            sid = extracted.get("source_record_id", "<unknown>")
            if strict:
                raise RuntimeError(f"canonicalize failed on {sid}: {exc}") from exc
            print(f"[le_strange] failed on {sid}: {exc}", file=sys.stderr)

    print(
        f"[le_strange] canonicalize: {n_new} new records emitted, "
        f"{n_augment} augmentation entries written to sidecar.",
        file=sys.stderr,
    )


def _record_augmentation(*, extracted: dict, sidecar: dict) -> None:
    """Record le-strange augmentation for an existing Yâqūt PID."""
    raw = extracted["raw_data"]
    yaqut_id = extracted["yaqut_id"]
    le_id = extracted["le_strange_id"]
    locator = extracted["source_locator"]

    # Sidecar is keyed by yaqut_id; multiple le-strange refs to same Yâqūt
    # entry would produce a list (rare but possible).
    key = f"yaqut:{yaqut_id}"
    entry = {
        "le_strange_id": le_id,
        "le_strange_form": raw.get("le_strange_form"),
        "alternate_names": raw.get("alternate_names") or [],
        "geo_type": raw.get("geo_type"),
        "modern_name": raw.get("modern_name"),
        "modern_country": raw.get("modern_country"),
        "modern_region": raw.get("modern_region"),
        "province": raw.get("province"),
        "chapter": locator.get("chapter"),
        "chapter_title": raw.get("chapter_title"),
        "page_range": locator.get("page_range"),
        "description": raw.get("description"),
    }
    # Multiple le-strange records can point to one yaqut id; collect them
    if key in sidecar:
        existing = sidecar[key]
        if isinstance(existing, list):
            existing.append(entry)
        else:
            sidecar[key] = [existing, entry]
    else:
        sidecar[key] = entry


def _build_new_record(
    *, extracted, pid_minter, reconciler, pipeline_name, pipeline_version,
    attributed_to, license_uri, type_qid, now,
):
    raw = extracted["raw_data"]
    rec_id = extracted["source_record_id"]
    le_id = extracted["le_strange_id"]
    locator = extracted["source_locator"]

    pid = pid_minter.mint(namespace="place", input_hash=rec_id)

    name_ar = raw.get("name_ar")
    name_tr = raw.get("name_tr")
    name_en = raw.get("name_en")
    le_strange_form = raw.get("le_strange_form")
    alternate_names = raw.get("alternate_names") or []
    description = raw.get("description")

    labels = pc.build_labels(
        name_ar=name_ar,
        name_tr=name_tr,
        name_en=name_en,
        alternate_names=alternate_names + ([le_strange_form] if le_strange_form else []),
        description_en=description if isinstance(description, str) else None,
    )

    coords = None
    lat = raw.get("latitude")
    lon = raw.get("longitude")
    coord_source = raw.get("coord_source", "approximate")
    if lat is not None and lon is not None:
        cmap = {
            "approximate": ("approximate", 10_000),
            "modern_known": ("exact", 100),
            "exact": ("exact", 100),
        }.get(coord_source, ("approximate", 25_000))
        coords = {
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "uncertainty": {"type": cmap[0], "note": f"Coord source: {coord_source}"},
            "precision_meters": cmap[1],
            "derived_from_source": rec_id,
        }

    geo_type = (raw.get("geo_type") or "").lower()
    types_arr = ["iac:Place"]
    subtype_field = None
    sm = GEO_MAP_LE_STRANGE.get(geo_type)
    if sm:
        subtype_field, type_uri = sm
        types_arr.append(type_uri)

    authority_xref: list[dict] = []
    if reconciler is not None and geo_type in ("city", "town", "fortress",
                                                "province", "region", "port"):
        recon_label = pc.label_for_recon(labels)
        xref = reconciler.reconcile(
            label_en=recon_label,
            type_qid=type_qid,
            context={"region_primary": raw.get("modern_country") or ""},
            source_record_id=rec_id,
        )
        if xref:
            authority_xref.append(xref)

    page_locator = (
        f"Le Strange, Lands of the Eastern Caliphate, "
        f"id={le_id}, ch. {locator.get('chapter', '?')}, "
        f"pp. {locator.get('page_range', '?')}"
    )
    provenance = pc.build_provenance(
        source_record_id=rec_id,
        source_kind="secondary_scholarly",
        page_locator=page_locator,
        edition="Cambridge: Cambridge University Press, 1905; reprint Frank Cass 1966.",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        attributed_to=attributed_to,
        license_uri=license_uri,
        record_history_note=(
            f"Initial canonicalization from Le Strange entry {le_id} "
            f"({name_en or name_ar}); no Yâqūt cross-reference. "
            f"Geographic feature type: {geo_type}."
        ),
        now=now,
    )

    note_parts = []
    if le_strange_form and le_strange_form not in (name_en, name_tr, name_ar):
        note_parts.append(f"Le Strange's spelling: {le_strange_form!r}")
    if raw.get("modern_name"):
        note_parts.append(f"Modern name: {raw['modern_name']}")
    if raw.get("modern_country"):
        note_parts.append(f"Modern country: {raw['modern_country']}")
    if raw.get("province"):
        note_parts.append(f"Le Strange province: {raw['province']}")
    if geo_type and not subtype_field:
        note_parts.append(
            f"Le Strange geo_type: {geo_type!r} "
            f"(no schema subtype mapping in v0.1.0; place_subtype omitted)."
        )

    record: dict = {
        "@id": pid,
        "@type": types_arr,
        "labels": labels,
        "provenance": provenance,
        "derived_from_layers": ["le-strange"],
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

    return record
