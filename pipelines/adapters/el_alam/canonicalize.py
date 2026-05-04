"""
canonicalize.py — Two-track adapter (Le Strange pattern from Hafta 3, person edition).

For each alam_lite entry:

  TRACK A (dia_slug present):
    The DİA adapter has already minted a person PID for this individual. We do
    NOT mint a new PID. Instead we emit a sidecar record telling
    person_integrity.py to:
      - append a derived_from entry to the existing person's provenance
      - add Ziriklī's Arabic heading to altLabel.ar (if not already present)
      - record the Yâqūt place attestations for that person (so the
        forward-only person→place resolution pass can populate
        active_in_places[] from BOTH DİA and Alam)

  TRACK B (no dia_slug):
    Mint a new iac:person- PID. Full canonicalization from alam_lite alone.
    death_temporal from hd/md; description from dt/de; profession from
    classify_profession on the description; type from build_type_array.

Both tracks emit yaqut_place_attestations to el_alam_yaqut_xref_pending
sidecar regardless of which track they took (so the integrity pass can
resolve them uniformly).
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import person_canonicalize as pc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = (
    "Khayr al-Dīn al-Ziriklī, al-Aʿlām (Beirut: Dār al-ʿIlm li’l-Malāyīn, "
    "8th ed. 2002), 8 vols."
)


def _build_temporal_alam(year_h, year_c, approx="exact"):
    """Same defensive clamp pattern as DİA's _build_temporal."""
    out = {}
    note_bits = []
    try:
        ah = int(year_h) if year_h is not None else None
    except (TypeError, ValueError):
        ah = None
    try:
        ce = int(year_c) if year_c is not None else None
    except (TypeError, ValueError):
        ce = None

    if ah is not None and 1 <= ah <= 1700:
        out["start_ah"] = ah
    elif ah is not None:
        note_bits.append(f"AH={ah} discarded (out of schema range)")

    if ce is not None and -3000 <= ce <= 3000:
        out["start_ce"] = ce
    elif ce is not None:
        note_bits.append(f"CE={ce} discarded (out of schema range)")

    if not out:
        return None
    out["approximation"] = approx
    if note_bits:
        out["note"] = "; ".join(note_bits)
    return out


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "person"
    sidecars = options.get("sidecars", {})
    augment_pending = sidecars.get("el_alam_augment_pending", {})
    persons_pending = sidecars.get("el_alam_persons_pending", {})
    yaqut_xref_pending = sidecars.get("el_alam_yaqut_xref_pending", {})
    recon_filter = options.get("recon_filter") or {}
    min_year_for_recon = recon_filter.get("min_year_ce", 1000)

    pipeline_name = options.get("pipeline_name", "canonicalize_person_el_alam")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        raw = record["raw"]
        aid = record["alam_id"]
        dia_slug = record["dia_slug"]
        yaqut_attests = record["yaqut_place_attestations"]

        # Useful field shorthand
        h_ar = raw.get("h")          # heading_ar
        ht = raw.get("ht")           # heading_tr (Turkish transliteration)
        he = raw.get("he")           # heading_en (English ALA-LC)
        dt = raw.get("dt")           # description_tr
        de = raw.get("de")           # description_en
        hd = raw.get("hd")           # death_hijri
        md = raw.get("md")           # death_miladi
        gender = raw.get("g")        # 'M' / 'F'
        century = raw.get("c")       # century CE int
        lat = raw.get("lat")
        lon = raw.get("lon")

        # ---------------------------------------------------------------
        # TRACK A — augment-only sidecar; do NOT mint a new PID.
        # ---------------------------------------------------------------
        if dia_slug:
            # The DİA adapter's PID for this slug is computable since the
            # minter is idempotent: input_hash is "dia:<slug>"
            try:
                existing_pid = pid_minter.mint(namespace, f"dia:{dia_slug}")
            except Exception:
                existing_pid = None
            # If for some reason that lookup fails (e.g. non-bio slug skipped
            # by DİA filter), fall through to Track B as a safety net.
            if existing_pid:
                augment_pending[existing_pid] = {
                    "alam_id": aid,
                    "dia_slug": dia_slug,
                    "heading_ar": h_ar,
                    "heading_tr": ht,
                    "heading_en": he,
                    "description_tr": dt,
                    "description_en": de,
                    "death_hijri": hd,
                    "death_miladi": md,
                    "gender": gender,
                    "century_ce": century,
                    "lat": lat,
                    "lon": lon,
                }
                if yaqut_attests:
                    yaqut_xref_pending[existing_pid] = yaqut_attests
                continue  # no record yielded for Track A

        # ---------------------------------------------------------------
        # TRACK B — mint a new PID
        # ---------------------------------------------------------------
        input_hash = f"el-alam:{aid}"
        pid = pid_minter.mint(namespace, input_hash)

        labels = pc.build_person_labels(
            name_ar=h_ar,
            name_tr=ht,
            name_en=he,
            description_tr=dt,
            description_en=de,
        )

        # Death temporal
        death_temporal = _build_temporal_alam(hd, md, "exact")

        # Without death AND without birth AND without floruit → cannot satisfy
        # schema's anyOf temporal requirement. Skip.
        if not death_temporal:
            # Try century-CE midpoint as a floruit fallback
            if century is not None:
                try:
                    cint = int(century)
                    if 1 <= cint <= 25:
                        floruit = {
                            "start_ce": (cint - 1) * 100 + 50,
                            "approximation": "floruit",
                            "uncertainty_years": 50,
                        }
                    else:
                        floruit = None
                except (TypeError, ValueError):
                    floruit = None
            else:
                floruit = None
            if not floruit:
                continue
        else:
            floruit = None

        # Profession from description (Turkish desc has best signal)
        professions = pc.classify_profession(dt or de or "")
        if not professions:
            professions = ["scholar"]
        types = pc.build_type_array(professions)

        # Provenance
        provenance = pc.build_provenance(
            source_record_id=f"el-alam:{aid}",
            source_kind="tertiary_reference",
            page_locator=f"al-Ziriklī, al-Aʿlām (8th ed. 2002), entry alam_id={aid}",
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=(
                f"Initial canonicalization from al-Aʿlām alam_id={aid} "
                f"by el-alam adapter (Hafta 4) [Track B — no DİA cross-ref]."
            ),
        )

        # Wikidata reconciliation: only post-1000 CE figures (Tier-b filter)
        authority_xref = []
        recon_label = pc.label_for_recon(labels)
        death_year = (death_temporal or floruit or {}).get("start_ce")
        if (reconciler is not None and recon_label
                and death_year and death_year >= min_year_for_recon):
            try:
                hit = reconciler.reconcile(
                    label_en=recon_label,
                    type_qid=options.get("reconciliation_type_qid", "Q5"),
                    source_record_id=input_hash,
                    context={"death_year_ce": death_year},
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
        if death_temporal:
            person["death_temporal"] = death_temporal
        if floruit:
            person["floruit_temporal"] = floruit
        if authority_xref:
            person["authority_xref"] = authority_xref

        # Note: includes Alam reference + place hints (lat/lon for Alam are usually
        # the city of death or active region — informative but not coords for the
        # person; person coords would be wrong).
        note_bits = [
            pc.format_alam_note(aid, h_ar),
        ]
        if century:
            note_bits.append(f"Ziriklī century_ce={century}")
        if gender:
            note_bits.append(f"Gender: {gender}")
        if lat is not None and lon is not None:
            note_bits.append(f"Ziriklī place coords (city/region of activity): {lat}, {lon}")
        person["note"] = pc.assemble_note(note_bits)

        # Sidecar
        persons_pending[pid] = {
            "alam_id": aid,
            "heading_ar": h_ar,
            "heading_tr": ht,
            "death_year_ce": death_year,
        }
        if yaqut_attests:
            yaqut_xref_pending[pid] = yaqut_attests

        yield person
