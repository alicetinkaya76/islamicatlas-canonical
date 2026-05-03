"""
place_canonicalize.py — Shared helpers for place-namespace adapters.

Three adapters seed iac:place-* in Hafta 3 (Yâqūt, Muqaddasī, Le Strange).
Each has its own extract.py and a thin canonicalize wrapper, but the actual
record-building logic is shared here for consistency:

  - field-level builders (labels, coords, temporal_coverage, provenance)
  - geo_type → schema subtype mapping (3 schemas: settlement, region, iqlim)
  - geo_confidence → coords.uncertainty.type mapping (5 levels)
  - editorial-note assembly
  - Arabic-script detection and label-key heuristics

Each adapter passes raw normalized data; the helpers produce a schema-valid
canonical record, mint the PID via the supplied minter, optionally call the
reconciler, and emit the result. The adapter is in charge of provenance
specifics (source_id pattern, page locator, layer name).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# Arabic script Unicode block detector (used for label-key disambiguation)
ARABIC_SCRIPT_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Map Yâqūt's 80+ corrected geo_type values to the 3 schema subtypes.
# Anything not in this map keeps @type=['iac:Place'] only and dynasty_subtype unset.
# The original geo_type is preserved in `note` for forward compatibility (Phase
# 0.3+ may add iac:Mountain, iac:RiverSystem, iac:Desert, etc.).
GEO_TYPE_TO_SUBTYPE: dict[str, tuple[str, str]] = {
    # Settlement-class
    "city": ("settlement", "iac:Settlement"),
    "town": ("settlement", "iac:Settlement"),
    "village": ("settlement", "iac:Settlement"),
    "district": ("settlement", "iac:Settlement"),
    "quarter": ("settlement", "iac:Settlement"),
    "fortress": ("settlement", "iac:Settlement"),
    "settlement": ("settlement", "iac:Settlement"),
    "tribe_settlement": ("settlement", "iac:Settlement"),
    "port": ("settlement", "iac:Settlement"),
    "palace": ("settlement", "iac:Settlement"),
    "ribat": ("settlement", "iac:Settlement"),
    # Region-class
    "region": ("region", "iac:Region"),
    "kura": ("region", "iac:Region"),
    "kūra": ("region", "iac:Region"),
    # Iqlim-class (Muqaddasī's regional schema)
    "iqlim": ("iqlim", "iac:Iqlim"),
    "iqlīm": ("iqlim", "iac:Iqlim"),
}

# Map this dataset's geo_confidence → schema's coords.uncertainty.type (5-level enum).
# The schema enum is: exact, centroid, approximate, unlocated, disputed.
# Yâqūt-lite's enum: exact, country, region, approximate, inferred.
GEO_CONFIDENCE_TO_UNCERTAINTY: dict[str, tuple[str, int]] = {
    # (schema_uncertainty_type, suggested_precision_meters)
    "exact":       ("exact",       100),     # surveyed or directly attested
    "approximate": ("approximate", 10_000),  # ~10km uncertainty
    "inferred":    ("approximate", 25_000),  # ~25km derived from textual cues
    "region":      ("centroid",    50_000),  # modern_region centroid (~50km)
    "country":     ("centroid",    250_000), # modern_country centroid (~250km)
    "centroid":    ("centroid",    50_000),
}


def now_iso() -> str:
    """ISO-8601 UTC timestamp."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def has_arabic_script(s: str) -> bool:
    """True if string contains any Unicode Arabic-script codepoint."""
    if not s:
        return False
    return bool(ARABIC_SCRIPT_RE.search(s))


def truncate(s: str | None, n: int) -> str | None:
    """Truncate a string to n chars, preserving None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    return s[:n]


def try_int(s: Any) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    s = str(s).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def try_float(s: Any) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ----------------------------------------------------------------------------
# Field builders
# ----------------------------------------------------------------------------


def build_labels(
    *,
    name_ar: str | None = None,
    name_tr: str | None = None,
    name_en: str | None = None,
    transliteration: str | None = None,
    alternate_names: list[str] | None = None,
    description_tr: str | None = None,
    description_en: str | None = None,
    description_ar: str | None = None,
) -> dict:
    """Build a multilingual_text-conformant labels block.

    `transliteration` is treated as ar-Latn-x-alalc when name_ar already exists,
    or as the primary 'ar' fallback when name_ar is empty.

    `alternate_names` is dispatched by Arabic-script vs. Latin-script detection.
    """
    pref: dict[str, str] = {}
    if name_en:
        pref["en"] = truncate(name_en, 500)
    if name_tr:
        pref["tr"] = truncate(name_tr, 500)
    if name_ar:
        if has_arabic_script(name_ar):
            pref["ar"] = truncate(name_ar, 500)
        else:
            pref["ar-Latn-x-alalc"] = truncate(name_ar, 500)
    if transliteration and "ar-Latn-x-alalc" not in pref:
        pref["ar-Latn-x-alalc"] = truncate(transliteration, 500)

    # multilingual_text requires at least one prefLabel — fallback chain
    if not pref:
        pref["en"] = "(unnamed place)"

    labels: dict = {"prefLabel": pref}

    # Original script (separate from prefLabel for SearchKit ergonomics)
    if name_ar and has_arabic_script(name_ar):
        labels["originalScript"] = {"ar": truncate(name_ar, 500)}

    # Alternate names — case-insensitive dedup per language bucket
    if alternate_names:
        seen_ar: set[str] = set()
        seen_tr: set[str] = set()
        seen_en: set[str] = set()
        alt_ar: list[str] = []
        alt_tr: list[str] = []
        alt_en: list[str] = []
        # Also dedup against prefLabel values (schema requires altLabel
        # uniqueness AND it shouldn't duplicate prefLabel either).
        pref_ar_norm = (pref.get("ar") or "").strip()
        pref_tr_norm = (pref.get("tr") or "").casefold().strip()
        pref_en_norm = (pref.get("en") or "").casefold().strip()
        if pref_ar_norm:
            seen_ar.add(pref_ar_norm)
        if pref_tr_norm:
            seen_tr.add(pref_tr_norm)
        if pref_en_norm:
            seen_en.add(pref_en_norm)
        for aname in alternate_names:
            if not aname or not aname.strip():
                continue
            aname_clean = aname.strip()
            if has_arabic_script(aname_clean):
                key = aname_clean
                if key in seen_ar:
                    continue
                seen_ar.add(key)
                alt_ar.append(truncate(aname_clean, 200))
            else:
                key = aname_clean.casefold()
                if key in seen_tr:
                    continue
                seen_tr.add(key)
                alt_tr.append(truncate(aname_clean, 200))
        alt: dict = {}
        if alt_ar:
            alt["ar"] = alt_ar[:20]
        if alt_tr:
            alt["tr"] = alt_tr[:20]
        if alt_en:
            alt["en"] = alt_en[:20]
        if alt:
            labels["altLabel"] = alt

    # Description
    desc: dict = {}
    if description_tr:
        desc["tr"] = truncate(description_tr, 5000)
    if description_en:
        desc["en"] = truncate(description_en, 5000)
    if description_ar:
        desc["ar"] = truncate(description_ar, 5000)
    if desc:
        labels["description"] = desc

    return labels


def build_coords(
    *,
    lat: float | int | None,
    lon: float | int | None,
    confidence: str | None = None,
    derived_from_source: str | None = None,
    note: str | None = None,
) -> dict | None:
    """Build a coords-schema-conformant coords block, or None if unlocatable.

    `confidence` is the dataset-level confidence value (e.g. 'exact', 'country',
    'region', 'approximate', 'inferred', or None). Mapped to the schema's
    uncertainty.type enum via GEO_CONFIDENCE_TO_UNCERTAINTY.
    """
    flat = try_float(lat)
    flon = try_float(lon)
    if flat is None or flon is None:
        return None
    if not (-90 <= flat <= 90 and -180 <= flon <= 180):
        return None

    out: dict = {"lat": round(flat, 6), "lon": round(flon, 6)}

    if confidence:
        cmap = GEO_CONFIDENCE_TO_UNCERTAINTY.get(confidence.lower())
        if cmap:
            uncertainty_type, precision = cmap
            out["uncertainty"] = {"type": uncertainty_type}
            if note:
                out["uncertainty"]["note"] = truncate(note, 1000)
            out["precision_meters"] = precision

    if derived_from_source:
        out["derived_from_source"] = truncate(derived_from_source, 200)

    return out


def build_provenance(
    *,
    source_record_id: str,
    source_kind: str,
    page_locator: str,
    edition: str | None,
    pipeline_name: str,
    pipeline_version: str,
    attributed_to: str,
    license_uri: str,
    record_history_note: str,
    now: str | None = None,
) -> dict:
    """Build a provenance-schema-conformant provenance block."""
    now = now or now_iso()
    derived_entry = {
        "source_id": source_record_id,
        "source_type": source_kind,
        "page_or_locator": truncate(page_locator, 1000),
        "extraction_method": "structured_json",
    }
    if edition:
        derived_entry["edition_or_version"] = truncate(edition, 500)

    return {
        "derived_from": [derived_entry],
        "generated_by": {
            "pipeline_name": pipeline_name,
            "pipeline_version": pipeline_version,
        },
        "generated_at": now,
        "attributed_to": attributed_to,
        "created": now,
        "modified": now,
        "license": license_uri,
        "record_history": [
            {
                "change_type": "create",
                "changed_at": now,
                "changed_by": attributed_to,
                "release": "v0.1.0-phase0",
                "note": truncate(record_history_note, 1000),
            }
        ],
        "deprecated": False,
    }


def classify_geo_type(geo_type_corrected: str | None) -> tuple[str | None, str | None]:
    """Map raw geo_type string → (place_subtype, type_uri) or (None, None).

    Anything outside the mapping leaves the record at @type=['iac:Place']
    only — for v0.1.0 schema this is the right move (no iac:Mountain etc.).
    """
    if not geo_type_corrected:
        return None, None
    key = geo_type_corrected.strip().lower()
    return GEO_TYPE_TO_SUBTYPE.get(key, (None, None))


def build_authority_xref_dia(
    *,
    dia_slug: str | None,
    dia_url: str | None,
    note: str | None = None,
) -> dict | None:
    """DİA cross-reference. Note: 'dia' is not in the v0.1.0 authority enum
    (which is wikidata/pleiades/viaf/geonames/openiti/tgn/lcnaf/isni/gnd/bnf).
    For now we return None — DİA references are recorded in `note` instead.
    A schema migration in v0.2.0 will add 'dia' to the enum and this builder
    will start returning a real xref entry.

    For the time being, callers should use `format_dia_note()` to put the
    DİA reference into the editorial note.
    """
    return None  # see docstring


def format_dia_note(dia_slug: str | None, dia_url: str | None) -> str | None:
    """Format a DİA cross-reference as a free-text note fragment."""
    if not dia_slug:
        return None
    bits = [f"DİA cross-reference: slug={dia_slug}"]
    if dia_url:
        bits.append(f"URL: {dia_url}")
    return ", ".join(bits)


def label_for_recon(labels: dict) -> str | None:
    """Pick the best English-or-transliteration label for Wikidata reconciliation.

    Strips leading 'al-' for cleaner matching since Wikidata labels are
    inconsistent with the Arabic article (e.g., 'Aleppo' not 'al-Aleppo').
    """
    pref = labels.get("prefLabel", {})
    candidate = pref.get("en") or pref.get("ar-Latn-x-alalc") or pref.get("tr")
    if not candidate:
        return None
    cleaned = candidate.strip()
    # Strip Arabic-article prefixes
    for prefix in ("al-", "Al-", "el-", "El-", "AL-"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    return cleaned or candidate


def assemble_note(parts: list[str | None]) -> str | None:
    """Concatenate non-empty note fragments with ' || ' separator."""
    bits = [str(p).strip() for p in parts if p and str(p).strip()]
    if not bits:
        return None
    full = " || ".join(bits)
    return full[:5000]
