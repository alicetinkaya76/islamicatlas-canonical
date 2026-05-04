"""
canonicalize.py — Convert a DİA slug record into an iac:person- record.

Input is the dict produced by extract():
  - slug, title, name_ar, death_paren
  - n_chunks, chunks_text_concat
  - lite: dict with dh/dc/bp/dp/bh/bc/fn/ni/mz/aq/fl etc.
  - alam_id: int|None (from dia_alam_xref)

Field mapping:
  slug → CURIE 'dia:<slug>' for input_hash
  title (from chunks 'n') → labels.prefLabel.tr (DİA is Turkish-curated)
  name_ar → labels.prefLabel.ar (or originalScript.ar)
  lite.fn → labels.altLabel.tr (full nasab form)
  lite.ni → person.nisba (single string → list)
  lite.dh/dc → death_temporal {start_ah, start_ce, approximation=exact}
              or fall back to parse_death_paren(death_paren)
  lite.bh/bc → birth_temporal
  lite.fl → profession (mapped via DIA_FIELD_TO_PROFESSION)
  lite.mz → laqab (madhab marker — Hanefî, Şâfiî etc.)
            (Note: in P0.2 schema migration, mz → person.madhab will be a
             concept-PID. Phase 0: keep as text in laqab[] / note for display.)
  lite.aq → note (aqîde, schools like Mu'tezilî)
  lite.bp/dp → birth_place / death_place sidecar (string only; resolved
               against place namespace by person_integrity.py)
  alam_id → cross-source resolver Tier-1 hint via dia_to_alam_xref sidecar
  description.tr → first ~5000 chars of chunks_text_concat
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import person_canonicalize as pc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "Türkiye Diyanet Vakfı İslâm Ansiklopedisi (DİA), online edition; pipeline ETL."

# DİA `fl` (Turkish field labels) → person.schema profession enum
DIA_FIELD_TO_PROFESSION = {
    "edebiyat": "poet",
    "siyaset": "ruler",        # most often ruler/statesman, fallback
    "fıkıh": "scholar",
    "tarih": "historian",
    "tasavvuf": "scholar",
    "hadis": "narrator",
    "tefsir": "scholar",
    "tıp": "physician",
    "felsefe": "philosopher",
    "mûsiki": "musician",
    "musiki": "musician",
    "kelâm": "scholar",
    "kelam": "scholar",
    "astronomi": "astronomer",
    "matematik": "mathematician",
    "coğrafya": "geographer",
    "cografya": "geographer",
    "mimari": "architect",
    "mimarlik": "architect",
    "mimarlık": "architect",
    "hat": "calligrapher",
    "hattatlık": "calligrapher",
    "hattatlik": "calligrapher",
    "ticaret": "merchant",
    "ulum": "scholar",
    "ulûm": "scholar",
    "tıb": "physician",
    "tib": "physician",
}

# Title case heuristic for DİA's CAPS titles
_TITLE_CASE_RE = re.compile(r"\b[\w']+", re.UNICODE)


def _detitle(s: str) -> str:
    """Convert ALL-CAPS DİA titles to title case while preserving things like
    "b." (ibn-abbreviation) and Roman numerals."""
    if not s:
        return s
    if not s.isupper():
        return s
    # Simple title case; preserve b./bin/binti/al-/el- markers
    parts = []
    for w in s.split():
        wl = w.lower()
        if wl in {"b.", "bn", "el-", "al-", "es-", "et-", "es-", "en-", "en", "ed-",
                  "ed", "el", "al", "fi", "fî", "li-", "li", "vs.", "ve"}:
            parts.append(wl)
        elif re.fullmatch(r"[IVXLC]+\.?", w):  # Roman numerals
            parts.append(w)
        else:
            # First-letter caps, rest lower; preserve apostrophes
            chars = list(wl)
            if chars:
                chars[0] = chars[0].upper()
            parts.append("".join(chars))
    return " ".join(parts)


def _build_temporal(year_h, year_c, approx="exact"):
    """Build a temporal block from year_h (AH int) and year_c (CE int).

    Defensive clamping: schema constraints are AH ∈ [1, 1700] and CE ∈ [-3000, 3000].
    Real-world DİA data occasionally has miscalculated AH years (e.g., 1784 AH for a
    person who died 1838 CE — that AH would be ~2375 CE, impossible). When AH is out
    of range:
      - if CE is in range, use CE only and emit a note
      - if both are out of range, return None
    """
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
        note_bits.append(f"AH={ah} discarded (out of schema range 1..1700)")

    if ce is not None and -3000 <= ce <= 3000:
        out["start_ce"] = ce
    elif ce is not None:
        note_bits.append(f"CE={ce} discarded (out of schema range -3000..3000)")

    if not out:
        return None
    out["approximation"] = approx
    if note_bits:
        out["note"] = "; ".join(note_bits)
    return out


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "person"
    sidecars = options.get("sidecars", {})
    persons_pending = sidecars.get("dia_persons_pending", {})
    dia_to_alam_xref = sidecars.get("dia_to_alam_xref", {})
    bd_places_pending = sidecars.get("dia_birth_death_places_pending", {})
    recon_filter = options.get("recon_filter") or {}
    min_chunks_for_recon = recon_filter.get("min_chunks_for_recon", 5)

    pipeline_name = options.get("pipeline_name", "canonicalize_person_dia")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        slug = record["slug"]
        # Idempotent PID — slug is the natural source key
        input_hash = f"dia:{slug}"
        pid = pid_minter.mint(namespace, input_hash)

        title = _detitle(record["title"])
        name_ar = record["name_ar"]
        death_paren = record["death_paren"]
        lite = record.get("lite") or {}
        alam_id = record.get("alam_id")

        # Description from concatenated chunks (truncated)
        # DİA text is Turkish-curated — put under tr.
        full_text = record.get("chunks_text_concat") or lite.get("ds") or ""
        description_tr = full_text[:5000] if full_text else None

        # Labels
        labels = pc.build_person_labels(
            name_tr=title,
            name_ar=name_ar,
            full_name_tr=lite.get("fn"),
            description_tr=description_tr,
        )

        # Death temporal: prefer lite's structured (dh, dc), fallback to parsing 'd' paren
        death_temporal = None
        if lite.get("dh") or lite.get("dc"):
            death_temporal = _build_temporal(lite.get("dh"), lite.get("dc"), "exact")
        elif death_paren:
            death_temporal = pc.parse_death_paren(death_paren)

        # Birth temporal
        birth_temporal = None
        if lite.get("bh") or lite.get("bc"):
            birth_temporal = _build_temporal(lite.get("bh"), lite.get("bc"), "exact")

        # If neither birth nor death is present, the record cannot satisfy
        # the temporal schema (anyOf: start_ce | start_ah | iso_start_date).
        # We skip these rather than trying to fabricate a floruit from the
        # `wc` field — that field's semantics are not "wafat century" as
        # initially assumed (it ranges to 25+ which is impossible for any
        # century-AH or century-CE), so deriving a date from it is unsafe.
        floruit = None  # placeholder; not populated from DİA in v0.1.0

        # Schema constraint (P0.2 hard rule, but already enforced in v0.1.0 by anyOf):
        # at least one of birth/death/floruit must be present.
        if not (birth_temporal or death_temporal or floruit):
            # Skip this record — not enough date info to satisfy the schema.
            # In strict mode this would otherwise fail validation.
            continue

        # Profession
        professions = []
        for f in (lite.get("fl") or []):
            if not f:
                continue
            p = DIA_FIELD_TO_PROFESSION.get(f.lower())
            if p and p not in professions:
                professions.append(p)
        # Heuristic from `ds` (description short)
        ds_text = lite.get("ds") or ""
        if ds_text:
            extra = pc.classify_profession(ds_text)
            for p in extra:
                if p not in professions:
                    professions.append(p)
        if not professions:
            professions = ["scholar"]  # safest default

        # @type
        types = pc.build_type_array(professions)

        # Nisba: lite.ni is a single string → list with one element
        nisba_list = []
        if lite.get("ni"):
            nisba_list = [pc.truncate(str(lite["ni"]).strip(), 200)]

        # Laqab: include madhab as it's the most common honorific tag in DİA
        laqab_list = []
        if lite.get("mz"):
            laqab_list.append(f"{lite['mz']} (mezhep)")
        if lite.get("aq"):
            laqab_list.append(f"{lite['aq']} (akîde)")

        # provenance
        provenance = pc.build_provenance(
            source_record_id=f"dia:{slug}",
            source_kind="tertiary_reference",
            page_locator=f"DİA, slug={slug}, https://islamansiklopedisi.org.tr/{slug}",
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=(
                f"Initial canonicalization from DİA slug={slug} ({record['n_chunks']} chunks) "
                f"by dia adapter (Hafta 4)."
                + (f" El-Aʿlām cross-ref: alam_id={alam_id}." if alam_id else "")
                + (f" Madhab: {lite['mz']}." if lite.get('mz') else "")
            ),
        )

        # Wikidata reconciliation (Tier-b: famous bios only)
        authority_xref = []
        recon_label = pc.label_for_recon(labels)
        if reconciler is not None and recon_label and record["n_chunks"] >= min_chunks_for_recon:
            try:
                hit = reconciler.reconcile(
                    label_en=recon_label,
                    type_qid=options.get("reconciliation_type_qid", "Q5"),
                    source_record_id=input_hash,
                    context={"death_year_ce": (death_temporal or birth_temporal or floruit or {}).get("start_ce")},
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
        if nisba_list:
            person["nisba"] = nisba_list
        if laqab_list:
            person["laqab"] = laqab_list
        if birth_temporal:
            person["birth_temporal"] = birth_temporal
        if death_temporal:
            person["death_temporal"] = death_temporal
        if floruit:
            person["floruit_temporal"] = floruit
        if authority_xref:
            person["authority_xref"] = authority_xref

        # Note: DİA URL + alam xref + birth/death place hints
        note_bits = [
            pc.format_dia_note(slug, f"https://islamansiklopedisi.org.tr/{slug}"),
        ]
        if alam_id:
            note_bits.append(pc.format_alam_note(alam_id))
        if lite.get("bp"):
            note_bits.append(f"DİA birth place: {lite['bp']}")
        if lite.get("dp"):
            note_bits.append(f"DİA death place: {lite['dp']}")
        if death_paren:
            note_bits.append(pc.format_death_paren_display(death_paren))
        if lite.get("c1") or lite.get("c2") or lite.get("c3"):
            cats = " > ".join(c for c in [lite.get("c1"), lite.get("c2"), lite.get("c3")] if c)
            if cats:
                note_bits.append(f"DİA categories: {cats}")
        if record["n_chunks"]:
            note_bits.append(f"Chunk count: {record['n_chunks']}")
        person["note"] = pc.assemble_note(note_bits)

        # Sidecars
        persons_pending[pid] = {
            "slug": slug,
            "title": title,
            "death_year_ce": (death_temporal or {}).get("start_ce"),
            "n_chunks": record["n_chunks"],
            "alam_id": alam_id,
        }
        if alam_id:
            dia_to_alam_xref[pid] = {
                "alam_id": alam_id,
                "slug": slug,
            }
        if lite.get("bp") or lite.get("dp"):
            bd_places_pending[pid] = {
                "birth_place_string": lite.get("bp"),
                "death_place_string": lite.get("dp"),
            }

        yield person
