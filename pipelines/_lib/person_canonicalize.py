"""
person_canonicalize.py — Shared helpers for person-namespace adapters (Hafta 4).

Four adapters seed iac:person-* in Hafta 4:
  - bosworth-rulers-fixup (830 inline rulers from 186 dynasty records)
  - science-layer (182 curated scholars)
  - dia (~7,300 DİA biography slugs)
  - el-alam (~13,940 Ziriklī biographies; two-track: augment DİA-known, mint new for rest)

Each adapter passes raw normalized data; helpers produce a schema-valid canonical
record. The adapter is in charge of provenance specifics (source_id pattern,
page locator, source_kind tier label).

Design constraint inherited from Hafta 3:
  - The schema-valid authority_xref enum does NOT include 'dia', 'el-alam', 'ei1'
    in v0.1.0. We put these references in `note` (mirroring the place layer's
    DİA cross-reference handling), and queue a v0.2.0 enum migration as a
    separate task at the end of Hafta 4.

Convention: dates are stored CE in temporal blocks. AH dates are kept
in the `note` field when paired (e.g., '(ö. 680/1282)' → death_temporal.start_ce=1282
and note carries the AH/CE pair string for display).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

# Reuse some helpers from place_canonicalize for consistency
from .place_canonicalize import (
    has_arabic_script,
    truncate,
    try_int,
    try_float,
    now_iso,
    assemble_note,
)


# --------------------------------------------------------------------------- #
# Death-date parsing (DİA's parenthetical "d" field)
# --------------------------------------------------------------------------- #

# Examples:
#   "(ö. 680/1282)"           — AH/CE
#   "(ö. 32/653)"             — AH/CE
#   "(ö. 305/917-18)"         — AH/CE-range (CE end ambiguous)
#   "(ö. 1082/1671'den sonra)" — terminus post quem
#   "(ö. 12/633)"             — early Islamic, AH<100
#   "(ö. ?)"                  — unknown (skip)
#   "(ö.h. 100)"              — AH-only
#   "(ö.m. 1500)"             — CE-only

_DEATH_RE_PAIR = re.compile(
    r"ö\.?\s*"                            # ö. / ö (literal)
    r"(?:h\.?\s*)?(\d{1,4})"              # AH year (h.) optional prefix
    r"\s*/\s*"
    r"(\d{1,4})(?:[-–](\d{1,4}))?"       # CE year, optional range end
    r"(?:'?(?:den|dan|tan|ten)?\s*sonra)?",  # 'den sonra (after)
)

_DEATH_RE_AH_ONLY = re.compile(r"ö\.?\s*h\.?\s*(\d{1,4})")
_DEATH_RE_CE_ONLY = re.compile(r"ö\.?\s*m\.?\s*(\d{1,4})")


def parse_death_paren(d: str | None) -> dict | None:
    """Parse DİA's parenthetical 'd' field into a temporal-conformant dict.

    Returns None if no usable date is found. Otherwise returns a dict
    with one or more of: start_ce, start_ah, approximation, note.

    The `temporal` schema requires anyOf: start_ce | start_ah | iso_start_date,
    so we always emit at least one date axis when we return non-None.
    """
    if not d:
        return None
    s = d.strip().lstrip("(").rstrip(")").strip()
    if not s or s in ("ö. ?", "ö.?", "ö.", "?"):
        return None

    out: dict = {}
    is_after = "sonra" in s.lower()

    # AH/CE pair (most common)
    m = _DEATH_RE_PAIR.search(s)
    if m:
        ah = try_int(m.group(1))
        ce = try_int(m.group(2))
        ce_end = try_int(m.group(3))
        if ah:
            out["start_ah"] = ah
        if ce:
            out["start_ce"] = ce
        if ce_end:
            # Two CE years (e.g., "917-18" = 917 or 918) → end_ce
            # Handle short form: "305/917-18" means CE 917 or 918
            if ce_end < 100 and ce:
                # "917-18" style: append last 2 digits
                century = (ce // 100) * 100
                ce_end = century + ce_end
            out["end_ce"] = ce_end
            out["approximation"] = "circa"
        if is_after:
            out["approximation"] = "after"
        elif "approximation" not in out:
            out["approximation"] = "exact"
        return out if out else None

    # AH-only
    m = _DEATH_RE_AH_ONLY.search(s)
    if m:
        ah = try_int(m.group(1))
        if ah:
            return {"start_ah": ah, "approximation": "after" if is_after else "exact"}

    # CE-only
    m = _DEATH_RE_CE_ONLY.search(s)
    if m:
        ce = try_int(m.group(1))
        if ce:
            return {"start_ce": ce, "approximation": "after" if is_after else "exact"}

    # Bare 4-digit year — try to interpret as CE
    bare = re.search(r"\b(\d{3,4})\b", s)
    if bare:
        y = try_int(bare.group(1))
        if y and 500 <= y <= 2100:
            return {"start_ce": y, "approximation": "after" if is_after else "circa"}

    return None


# --------------------------------------------------------------------------- #
# Label normalization for dedup
# --------------------------------------------------------------------------- #


def strip_diacritics(s: str) -> str:
    """Strip combining diacritical marks for case-insensitive label dedup."""
    if not s:
        return s
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def label_dedup_key(s: str) -> str:
    """Normalized form for altLabel dedup checks (case + diacritic insensitive)."""
    return strip_diacritics(s.strip().lower())


# --------------------------------------------------------------------------- #
# Label builder for persons (separate from place builder)
# --------------------------------------------------------------------------- #


_DEFAULT_PROFESSION_HINTS = {
    "scholar": ["âlim", "alim", "scholar", "ulema"],
    "ruler": ["sultan", "halife", "khalifa", "emir", "amir", "ḫān", "han", "shah", "şah", "padişah", "ruler", "imam"],
    "vizier": ["vezir", "vizier", "wazir", "vâzir"],
    "judge": ["kadi", "qāḍī", "qadi", "kadı", "judge"],
    "mufti": ["müftü", "mufti", "mufti"],
    "narrator": ["râvî", "ravi", "narrator", "muhaddis", "muḥaddiṯ"],
    "poet": ["şair", "poet", "şâir", "poet"],
    "architect": ["mimar", "architect", "mi'mâr"],
    "calligrapher": ["hattat", "calligrapher", "ḫaṭṭāṭ"],
    "musician": ["müzisyen", "musician", "musiki"],
    "physician": ["hekim", "tabib", "ṭabīb", "physician"],
    "astronomer": ["astronom", "münaccim", "munajjim"],
    "mathematician": ["matematikçi", "mathematician", "ḥāsib"],
    "philosopher": ["filozof", "feylesof", "philosopher", "ḥakīm", "hakim"],
    "merchant": ["tüccar", "merchant", "tâcir"],
    "patron": ["patron", "hâmî"],
    "scribe": ["kâtip", "scribe", "katib"],
    "translator": ["mütercim", "translator", "tarjuman"],
    "geographer": ["coğrafyacı", "geographer", "jughrāfī"],
    "historian": ["tarihçi", "historian", "müerrih", "muerrih"],
}


def build_person_labels(
    *,
    name_ar: str | None = None,
    name_tr: str | None = None,
    name_en: str | None = None,
    full_name_ar: str | None = None,
    full_name_tr: str | None = None,
    full_name_en: str | None = None,
    alternate_names: list[str] | None = None,
    description_tr: str | None = None,
    description_en: str | None = None,
    description_ar: str | None = None,
) -> dict:
    """Build a multilingual_text-conformant labels block for a person.

    `name_*` go to prefLabel (short forms used for display).
    `full_name_*` go to altLabel for that language (longer nasab forms).
    `alternate_names` is a flat list dispatched by Arabic-script vs Latin.

    Dedup is case- and diacritic-insensitive within each language bucket.
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
    if not pref:
        pref["en"] = "(unnamed person)"

    labels: dict = {"prefLabel": pref}

    if name_ar and has_arabic_script(name_ar):
        labels["originalScript"] = {"ar": truncate(name_ar, 500)}

    # altLabel: full forms + alternate_names, dedup against prefLabel within each bucket
    alt: dict[str, list[str]] = {}

    def _add(lang_key: str, value: str):
        if not value or not value.strip():
            return
        v_clean = truncate(value, 500)
        if not v_clean:
            return
        # Dedup against prefLabel
        pref_in_lang = pref.get(lang_key)
        if pref_in_lang and label_dedup_key(v_clean) == label_dedup_key(pref_in_lang):
            return
        # Dedup against existing altLabel entries
        existing_keys = {label_dedup_key(x) for x in alt.get(lang_key, [])}
        if label_dedup_key(v_clean) in existing_keys:
            return
        alt.setdefault(lang_key, []).append(v_clean)

    if full_name_en and full_name_en != name_en:
        _add("en", full_name_en)
    if full_name_tr and full_name_tr != name_tr:
        _add("tr", full_name_tr)
    if full_name_ar and full_name_ar != name_ar:
        ar_key = "ar" if has_arabic_script(full_name_ar) else "ar-Latn-x-alalc"
        _add(ar_key, full_name_ar)

    if alternate_names:
        for aname in alternate_names:
            if not aname or not str(aname).strip():
                continue
            ac = str(aname).strip()
            if has_arabic_script(ac):
                _add("ar", ac)
            else:
                # Latin-script alts → 'tr' bucket (dataset is Turkish-curated)
                _add("tr", ac)

    if alt:
        # Cap each language to 20 alts
        labels["altLabel"] = {k: v[:20] for k, v in alt.items()}

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


# --------------------------------------------------------------------------- #
# Profession enum classification
# --------------------------------------------------------------------------- #

# Closed enum from person.schema.json
PROFESSION_ENUM = {
    "scholar", "ruler", "vizier", "judge", "mufti", "narrator", "poet",
    "architect", "calligrapher", "musician", "physician", "astronomer",
    "mathematician", "philosopher", "merchant", "patron", "scribe",
    "translator", "geographer", "historian",
}


def classify_profession(text: str | None) -> list[str]:
    """Heuristic profession classifier: matches whole-word fragments against a
    keyword table and returns a deduplicated, validated profession list.

    Uses word-boundary matching to avoid false positives like 'Hanefî' → 'han'
    → 'ruler'. Word boundaries are computed after diacritic-stripping, so
    'âlim' and 'alim' both match the 'alim' hint.

    Always returns a list (possibly empty). Caller is responsible for
    deciding whether to set the profession field at all.
    """
    if not text:
        return []
    t = strip_diacritics(text.lower())
    found: list[str] = []
    for prof, hints in _DEFAULT_PROFESSION_HINTS.items():
        for h in hints:
            h_norm = strip_diacritics(h.lower())
            if not h_norm:
                continue
            # Word-boundary match: hint must be a complete word in t
            pat = r"(?:^|[^a-z0-9])" + re.escape(h_norm) + r"(?:$|[^a-z0-9])"
            if re.search(pat, t):
                found.append(prof)
                break
    # Dedup, preserve order
    seen = set()
    uniq = []
    for p in found:
        if p not in seen and p in PROFESSION_ENUM:
            seen.add(p)
            uniq.append(p)
    return uniq


# Map profession → person @type subtype where there is a 1:1
PROFESSION_TO_SUBTYPE = {
    "scholar": "iac:Scholar",
    "ruler": "iac:Ruler",
    "narrator": "iac:Narrator",
    "poet": "iac:Poet",
    "architect": "iac:Architect",
    "patron": "iac:Patron",
    "mufti": "iac:Mufti",
    "calligrapher": "iac:Calligrapher",
}


def build_type_array(professions: list[str], extra_subtypes: list[str] | None = None) -> list[str]:
    """Build the @type array. Always contains 'iac:Person'.

    Adds person subtypes from PROFESSION_TO_SUBTYPE for matching professions.
    Caps total at 4 (schema maxItems=4).
    """
    types = {"iac:Person"}
    for prof in professions:
        sub = PROFESSION_TO_SUBTYPE.get(prof)
        if sub:
            types.add(sub)
    if extra_subtypes:
        for s in extra_subtypes:
            if s in {"iac:Scholar", "iac:Ruler", "iac:Narrator", "iac:Poet",
                     "iac:Architect", "iac:Patron", "iac:Mufti", "iac:Calligrapher"}:
                types.add(s)
    out = sorted(types)
    if len(out) > 4:
        # Always keep iac:Person; pick first 3 others alphabetically
        non_p = [t for t in out if t != "iac:Person"]
        out = ["iac:Person"] + sorted(non_p)[:3]
    return out


# --------------------------------------------------------------------------- #
# Provenance builder for person records
# --------------------------------------------------------------------------- #


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
    """Build a provenance-schema-conformant provenance block for a person."""
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


# --------------------------------------------------------------------------- #
# Note formatters
# --------------------------------------------------------------------------- #


def format_dia_note(dia_slug: str | None, dia_url: str | None) -> str | None:
    """Format a DİA cross-reference (schema enum gap workaround)."""
    if not dia_slug:
        return None
    bits = [f"DİA cross-reference: slug={dia_slug}"]
    if dia_url:
        bits.append(f"URL: {dia_url}")
    return ", ".join(bits)


def format_alam_note(alam_id: int | str | None, heading_ar: str | None = None) -> str | None:
    """Format an El-Aʿlām (Ziriklī) cross-reference."""
    if alam_id is None:
        return None
    bits = [f"El-Aʿlām (Ziriklī) cross-reference: alam_id={alam_id}"]
    if heading_ar:
        bits.append(f"heading_ar={heading_ar}")
    return ", ".join(bits)


def format_ei1_note(ei1_id: int | str | None, vol: int | None = None) -> str | None:
    """Format an Encyclopaedia of Islam (1st ed.) cross-reference."""
    if ei1_id is None:
        return None
    bits = [f"EI1 cross-reference: ei1_id={ei1_id}"]
    if vol is not None:
        bits.append(f"vol={vol}")
    return ", ".join(bits)


def format_death_paren_display(d: str | None) -> str | None:
    """Echo the DİA parenthetical death string back into the note for display."""
    if not d:
        return None
    return f"DİA death-date string: {d.strip()}"


# --------------------------------------------------------------------------- #
# Label-for-recon picker (mirror place's helper)
# --------------------------------------------------------------------------- #


def label_for_recon(labels: dict) -> str | None:
    """Pick the best English-or-transliteration label for Wikidata reconciliation."""
    pref = labels.get("prefLabel", {})
    candidate = pref.get("en") or pref.get("ar-Latn-x-alalc") or pref.get("tr")
    if not candidate:
        return None
    cleaned = candidate.strip()
    for prefix in ("al-", "Al-", "el-", "El-", "AL-"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    return cleaned or candidate
