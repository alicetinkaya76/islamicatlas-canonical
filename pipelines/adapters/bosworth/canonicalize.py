"""
canonicalize.py — Bosworth intermediate → canonical iac:Dynasty records.

For each extracted record (one per NID), produce a dict that conforms to
schemas/dynasty.schema.json. Mapping rules below mirror the manifest table
in NEXT_SESSION_PROMPT.md. Hafta 2 emits 186 records in one pass.

Two-pass design
---------------
* PASS 1 (this file): mint PIDs and emit canonical records WITHOUT
  predecessor/successor/had_capital/territory. Capital + region info goes
  to a sidecar (data/_state/bosworth_capital_pending.json) to be backfilled
  in Hafta 3 when the iac:place- namespace is populated by Yâqūt.

* PASS 2 (pipelines/integrity/check_all.py): walk dynasty_relations.csv,
  resolve dynasty_id → PID for both ends of each 'selef' edge, append
  predecessor/successor arrays into already-written canonical files,
  re-validate.

PID identity
------------
The PID minter's input_hash is "bosworth-nid:{id}", which is also the
provenance.derived_from[0].source_id. Re-running the adapter on identical
inputs produces identical PIDs (idempotency criterion H2.7 / acceptance).

Government-type mapping
-----------------------
The CSV's `government_type` is in Turkish and has 12 distinct values; the
schema's enum is 5 values in English. Mapping below covers ~95% of records;
mixed/uncategorisable values cleanly omit `dynasty_subtype` and `@type`
stays at `["iac:Dynasty"]`.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from typing import Iterator

# Government type (Turkish CSV) → schema enum (English).
# NOTE: 'Hanedan/Beylik' is intentionally NOT in this map — it is the CSV
# team's catch-all category covering everything from Tulunids to Safavids
# and would mis-type 112 records if mapped to 'beylik'. Records with that
# value (or with a mixed value containing '|') keep `dynasty_subtype` unset.
GOV_TYPE_MAP: dict[str, tuple[str, str]] = {
    "hilafet": ("caliphate", "iac:Caliphate"),
    "sultanlık": ("sultanate", "iac:Sultanate"),
    "sultanlik": ("sultanate", "iac:Sultanate"),
    "şahlık": ("sultanate", "iac:Sultanate"),
    "sahlik": ("sultanate", "iac:Sultanate"),
    "hanlık": ("sultanate", "iac:Sultanate"),
    "hanlik": ("sultanate", "iac:Sultanate"),
    "emirlik": ("emirate", "iac:Emirate"),
    "atabeglik": ("emirate", "iac:Emirate"),
    "i̇mamet": ("imamate", "iac:Imamate"),
    "imamet": ("imamate", "iac:Imamate"),
    "beylik": ("beylik", "iac:Beylik"),
}

# Name-based subtype classifier (highest precedence). Patterns are matched
# against `dynasty_name_en` with word boundaries; the first hit wins.
# Order matters: more specific patterns first.
NAME_CLASSIFIER: list[tuple[re.Pattern, tuple[str, str]]] = [
    (re.compile(r"\bCaliph(?:s|ate)?\b", re.IGNORECASE),
     ("caliphate", "iac:Caliphate")),
    (re.compile(r"\bImam(?:s|ate|ī|ī Imāms)?\b", re.IGNORECASE),
     ("imamate", "iac:Imamate")),
    (re.compile(r"\bSultan(?:s|ate)?\b", re.IGNORECASE),
     ("sultanate", "iac:Sultanate")),
    (re.compile(r"\bShāh(?:s)?\b|\bShah(?:s)?\b", re.IGNORECASE),
     ("sultanate", "iac:Sultanate")),
    (re.compile(r"\bKhān(?:s|ate)?\b|\bKhan(?:s|ate)?\b", re.IGNORECASE),
     ("sultanate", "iac:Sultanate")),
    (re.compile(r"\bAtabeg(?:s)?\b", re.IGNORECASE),
     ("emirate", "iac:Emirate")),
    (re.compile(r"\bEmir(?:s|ate)?\b|\bAmīr(?:s)?\b", re.IGNORECASE),
     ("emirate", "iac:Emirate")),
    (re.compile(r"\bBey(?:s|lik)?\b|\bOghullari\b", re.IGNORECASE),
     ("beylik", "iac:Beylik")),
]


def _classify_subtype(dynasty_name_en: str, government_type_raw: str) -> tuple[str | None, str | None]:
    """Return (dynasty_subtype, type_uri) or (None, None) if unclassifiable.

    Resolution order:
      1. Name-based pattern match (high-confidence signal — when a Bosworth
         entry literally calls them 'Caliphs' or 'Sultans', that is the
         category).
      2. CSV government_type direct mapping (clean enum values only).
      3. Otherwise unmapped: leaves @type at ['iac:Dynasty'].
    """
    name = (dynasty_name_en or "").strip()
    for pat, (subtype, uri) in NAME_CLASSIFIER:
        if pat.search(name):
            return subtype, uri
    gov = (government_type_raw or "").strip().lower()
    if gov and "|" not in gov and gov in GOV_TYPE_MAP:
        return GOV_TYPE_MAP[gov]
    return None, None


# Pattern matching Arabic script (Unicode block U+0600 – U+06FF + Supplement / Extended-A).
ARABIC_SCRIPT_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    options = options or {}
    strict = options.get("strict_mode", True)
    pipeline_name = options.get("pipeline_name", "canonicalize_dynasty")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    attributed_to = options.get(
        "attributed_to", "https://orcid.org/0000-0002-7747-6854"
    )
    license_uri = options.get(
        "license_uri", "https://creativecommons.org/licenses/by-sa/4.0/"
    )
    type_qid = options.get("reconciliation_type_qid", "Q164950")
    capital_sidecar = options.get("capital_sidecar")

    now = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    for extracted in extracted_records:
        try:
            record = _build_canonical_record(
                extracted=extracted,
                pid_minter=pid_minter,
                reconciler=reconciler,
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                attributed_to=attributed_to,
                license_uri=license_uri,
                type_qid=type_qid,
                capital_sidecar=capital_sidecar,
                now=now,
            )
            if record is not None:
                yield record
        except Exception as exc:
            sid = extracted.get("source_record_id", "<unknown>")
            if strict:
                raise RuntimeError(f"canonicalize failed on {sid}: {exc}") from exc
            print(
                f"[canonicalize_dynasty] failed on {sid}: {exc}",
                file=sys.stderr,
            )


def _build_canonical_record(
    *,
    extracted: dict,
    pid_minter,
    reconciler,
    pipeline_name: str,
    pipeline_version: str,
    attributed_to: str,
    license_uri: str,
    type_qid: str,
    capital_sidecar: dict | None,
    now: str,
) -> dict | None:
    raw = extracted["raw_data"]
    dyn = raw["dynasty"]
    rulers = raw["rulers"]
    locator = extracted["source_locator"]
    source_record_id = extracted["source_record_id"]

    dynasty_id = dyn.get("dynasty_id", "").strip()
    if not dynasty_id:
        return None

    pid = pid_minter.mint(namespace="dynasty", input_hash=source_record_id)

    # ---- @type + dynasty_subtype ---------------------------------------
    types_arr: list[str] = ["iac:Dynasty"]
    gov_raw = dyn.get("government_type", "").strip()
    subtype_field, subtype_type = _classify_subtype(
        dynasty_name_en=dyn.get("dynasty_name_en", ""),
        government_type_raw=gov_raw,
    )
    if subtype_type:
        types_arr.append(subtype_type)

    # ---- labels --------------------------------------------------------
    labels = _build_labels(dyn)

    # ---- temporal ------------------------------------------------------
    temporal = _build_temporal(dyn)
    if not temporal:
        # Schema requires temporal; cannot proceed without one.
        raise ValueError(
            f"NID-{dynasty_id}: no parseable temporal anchor (start_ce/start_ah)."
        )

    # ---- bosworth_id ---------------------------------------------------
    try:
        bosworth_id = f"NID-{int(dynasty_id):03d}"
    except ValueError:
        bosworth_id = None

    # ---- rulers --------------------------------------------------------
    rulers_canonical = _build_rulers(rulers)

    # ---- authority_xref via reconciler --------------------------------
    authority_xref: list[dict] = []
    if reconciler is not None:
        label_for_recon = _label_for_recon(labels)
        ctx = {
            "start_ce": _try_int(dyn.get("date_start_ce")),
            "end_ce": _try_int(dyn.get("date_end_ce")),
            "region_primary": dyn.get("region_primary", ""),
        }
        xref = reconciler.reconcile(
            label_en=label_for_recon,
            type_qid=type_qid,
            context=ctx,
            source_record_id=source_record_id,
        )
        if xref:
            authority_xref.append(xref)

    # ---- provenance ----------------------------------------------------
    page_locator = (
        f"Bosworth, New Islamic Dynasties, NID-{int(dynasty_id):03d}"
        if dynasty_id.isdigit()
        else f"Bosworth, New Islamic Dynasties, {locator.get('chapter') or 'unspecified'}"
    )
    provenance = {
        "derived_from": [
            {
                "source_id": source_record_id,
                "source_type": "secondary_scholarly",
                "page_or_locator": page_locator,
                "extraction_method": "structured_csv",
                "edition_or_version": "Edinburgh University Press 2004 (paperback reprint).",
            }
        ],
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
                "note": (
                    f"Initial canonicalization from Bosworth NID-{dynasty_id} via "
                    f"{pipeline_name} {pipeline_version} (Hafta 2 ETL pilot). "
                    f"predecessor/successor arrays populated by integrity/check_all.py "
                    f"in second pass."
                ),
            }
        ],
        "deprecated": False,
    }

    # ---- compose record ------------------------------------------------
    record: dict = {
        "@id": pid,
        "@type": types_arr,
        "labels": labels,
        "temporal": temporal,
        "provenance": provenance,
    }
    if subtype_field:
        record["dynasty_subtype"] = subtype_field
    if bosworth_id:
        record["bosworth_id"] = bosworth_id
    if rulers_canonical:
        record["rulers"] = rulers_canonical
    if authority_xref:
        record["authority_xref"] = authority_xref

    # Editorial note — preserves raw values that didn't fit canonical fields.
    note_parts: list[str] = []
    key_en = dyn.get("key_contribution_en", "").strip()
    key_tr = dyn.get("key_contribution_tr", "").strip()
    if key_en:
        note_parts.append(f"Key contribution: {key_en}")
    if key_tr:
        note_parts.append(f"Önemli katkı: {key_tr}")
    if gov_raw and subtype_field is None:
        note_parts.append(
            f"Government type (raw, unmapped to schema enum): {gov_raw!r} — "
            f"dynasty_subtype omitted; @type kept at iac:Dynasty only."
        )
    if dyn.get("end_cause"):
        note_parts.append(f"End cause: {dyn['end_cause']}")
    if note_parts:
        full_note = " || ".join(note_parts)
        record["note"] = full_note[:5000]

    # ---- capital sidecar (Hafta 3 pickup) ------------------------------
    if capital_sidecar is not None:
        cap_entry = _build_capital_sidecar_entry(dyn)
        if cap_entry is not None:
            capital_sidecar[pid] = cap_entry

    return record


# ----- field builders -----------------------------------------------------


def _build_labels(dyn: dict) -> dict:
    pref: dict[str, str] = {}
    en = dyn.get("dynasty_name_en", "").strip()
    tr = dyn.get("dynasty_name_tr", "").strip()
    ar = dyn.get("dynasty_name_ar", "").strip()
    if en:
        pref["en"] = en[:500]
    if tr:
        pref["tr"] = tr[:500]
    if ar:
        # name_ar in the CSV is mostly transliterated Latin (e.g.
        # "al-Khulafā' al-Rāshidūn"). It's still useful as an Arabic
        # transliteration label; only treat it as Arabic-script if it
        # contains Arabic Unicode.
        if ARABIC_SCRIPT_RE.search(ar):
            pref["ar"] = ar[:500]
        else:
            # ALA-LC-style transliteration; canonical key for that scheme.
            pref["ar-Latn-x-alalc"] = ar[:500]

    if "en" not in pref:
        # multilingual_text requires at least one prefLabel; fall back.
        pref["en"] = (tr or ar or f"NID-{dyn.get('dynasty_id', '?')}")[:500]

    labels: dict = {"prefLabel": pref}

    # description (multilingual_text optional but valuable for search projection)
    description: dict[str, str] = {}
    narr_en = dyn.get("narrative_en", "").strip()
    narr_tr = dyn.get("narrative_tr", "").strip()
    if narr_en:
        description["en"] = narr_en[:5000]
    if narr_tr:
        description["tr"] = narr_tr[:5000]
    if description:
        labels["description"] = description

    # Originalscript: if dynasty_name_ar IS Arabic-script, also stick it in originalScript
    if ar and ARABIC_SCRIPT_RE.search(ar):
        labels["originalScript"] = {"ar": ar[:500]}

    return labels


def _build_temporal(dyn: dict) -> dict:
    out: dict = {}
    raw_fields = (
        ("start_ce", dyn.get("date_start_ce")),
        ("end_ce", dyn.get("date_end_ce")),
        ("start_ah", dyn.get("date_start_hijri")),
        ("end_ah", dyn.get("date_end_hijri")),
    )
    is_circa = any(_is_circa(v) for _k, v in raw_fields)
    s_ce = _parse_loose_year(dyn.get("date_start_ce"))
    e_ce = _parse_loose_year(dyn.get("date_end_ce"))
    s_ah = _parse_loose_year(dyn.get("date_start_hijri"))
    e_ah = _parse_loose_year(dyn.get("date_end_hijri"))
    if s_ce is not None and -3000 <= s_ce <= 3000:
        out["start_ce"] = s_ce
    if e_ce is not None and -3000 <= e_ce <= 3000:
        out["end_ce"] = e_ce
    if s_ah is not None and 1 <= s_ah <= 1700:
        out["start_ah"] = s_ah
    if e_ah is not None and 1 <= e_ah <= 1700:
        out["end_ah"] = e_ah

    if "start_ce" not in out and "start_ah" not in out:
        return {}

    # Pipeline-level cross-check: end >= start
    if (
        "start_ce" in out
        and "end_ce" in out
        and out["end_ce"] < out["start_ce"]
    ):
        # Drop the inconsistent end; keep the start. Better an open range
        # than an invalid one.
        out.pop("end_ce")
    if (
        "start_ah" in out
        and "end_ah" in out
        and out["end_ah"] < out["start_ah"]
    ):
        out.pop("end_ah")

    out["approximation"] = "circa" if is_circa else "exact"
    if is_circa:
        out["uncertainty_years"] = 25
    return out


def _build_rulers(raw_rulers: list[dict]) -> list[dict]:
    out: list[dict] = []
    last_start = None
    out_of_order = False

    for r in raw_rulers:
        name = (r.get("short_name") or r.get("full_name_original") or "").strip()
        if not name:
            continue
        ruler: dict = {"name": name[:300]}

        # name_ar: only set if full_name_original contains Arabic script.
        full_orig = (r.get("full_name_original") or "").strip()
        if full_orig and ARABIC_SCRIPT_RE.search(full_orig):
            ruler["name_ar"] = full_orig[:300]

        # regnal_title: prefer 'title' (English regnal designation),
        # fallback to 'laqab'.
        title = (r.get("title") or "").strip()
        laqab = (r.get("laqab") or "").strip()
        regnal = title or laqab
        if regnal:
            ruler["regnal_title"] = regnal[:300]

        rsce = _parse_loose_year(r.get("reign_start_ce"))
        rece = _parse_loose_year(r.get("reign_end_ce"))
        rsah = _try_int(r.get("reign_start_hijri"))
        reah = _try_int(r.get("reign_end_hijri"))
        if rsce is not None and -3000 <= rsce <= 3000:
            ruler["reign_start_ce"] = rsce
        if rece is not None and -3000 <= rece <= 3000:
            ruler["reign_end_ce"] = rece
        if rsah is not None and 1 <= rsah <= 1700:
            ruler["reign_start_ah"] = rsah
        if reah is not None and 1 <= reah <= 1700:
            ruler["reign_end_ah"] = reah

        # Editorial note from CSV
        note_bits = []
        if r.get("notes"):
            note_bits.append(r["notes"])
        if r.get("relationship_to_prev"):
            note_bits.append(f"İlişki: {r['relationship_to_prev']}")
        if r.get("death_type"):
            note_bits.append(f"Death: {r['death_type']}")
        if note_bits:
            ruler["note"] = " || ".join(note_bits)[:2000]

        # Track ordering for the chronological invariant
        if rsce is not None:
            if last_start is not None and rsce < last_start:
                out_of_order = True
            last_start = rsce

        out.append(ruler)

    # If chronological order is broken, re-sort by reign_start_ce when present;
    # rulers without a known reign_start_ce keep their relative order at the end.
    if out_of_order:
        with_year = [r for r in out if "reign_start_ce" in r]
        without_year = [r for r in out if "reign_start_ce" not in r]
        with_year.sort(key=lambda r: r["reign_start_ce"])
        out = with_year + without_year

    return out


def _build_capital_sidecar_entry(dyn: dict) -> dict | None:
    """Return a non-canonical sidecar payload for capital + territory backfill.

    Hafta 3 will read this dict (keyed by canonical PID) and resolve
    capital_name → place PID, regions_all → list of region PIDs.
    """
    capital_name = (dyn.get("capital_city") or "").strip()
    capital_lat = _try_float(dyn.get("capital_lat"))
    capital_lon = _try_float(dyn.get("capital_lon"))
    regions_all = (dyn.get("regions_all") or "").strip()
    region_primary = (dyn.get("region_primary") or "").strip()

    if not capital_name and not regions_all:
        return None

    entry = {}
    if capital_name:
        entry["capital_name"] = capital_name[:500]
    if capital_lat is not None:
        entry["capital_lat"] = capital_lat
    if capital_lon is not None:
        entry["capital_lon"] = capital_lon
    if regions_all:
        # Split on ';' which is Bosworth's region separator.
        regions_list = [r.strip() for r in regions_all.split(";") if r.strip()]
        entry["regions_all"] = regions_list[:50]
    if region_primary:
        entry["region_primary"] = region_primary[:200]
    return entry


def _label_for_recon(labels: dict) -> str | None:
    """Pick the best English label for Wikidata reconciliation."""
    pref = labels.get("prefLabel", {})
    en = pref.get("en")
    if en:
        # Bosworth's labels often start with "The ". Strip for cleaner matching.
        cleaned = en
        if cleaned.lower().startswith("the "):
            cleaned = cleaned[4:].strip()
        return cleaned
    return pref.get("tr") or pref.get("ar-Latn-x-alalc") or pref.get("ar")


# ----- low-level helpers --------------------------------------------------


def _try_int(s) -> int | None:
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


def _try_float(s) -> float | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _is_circa(s) -> bool:
    if s is None:
        return False
    s = str(s).strip().lower()
    return any(s.startswith(p) for p in ("c.", "ca.", "ca ", "circa "))


def _parse_loose_year(s) -> int | None:
    """Parse year-ish strings: 'c. 1012', '1056?', '755/56', '662–680'."""
    if s is None:
        return None
    if isinstance(s, int):
        return s
    s = str(s).strip()
    if not s:
        return None
    for prefix in ("c. ", "C. ", "ca. ", "CA. ", "ca ", "circa "):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):].strip()
            break
    s = s.rstrip("?").strip()
    s = s.replace("–", "-").replace("—", "-").replace("/", "-")
    head: list[str] = []
    for ch in s:
        if ch.isdigit() or (ch == "-" and not head):
            head.append(ch)
        else:
            if head:
                break
    candidate = "".join(head)
    if candidate in ("", "-"):
        return None
    try:
        return int(candidate)
    except ValueError:
        return None
