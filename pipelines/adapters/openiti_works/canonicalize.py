"""
canonicalize.py — Convert an OpenITI work entry into an iac:work-* record.

Consumes the openiti_author_resolution.json sidecar produced by
openiti_author_resolve pre-pass (executed BEFORE this adapter).

Distinctive features:
  - openiti_uri stored in dedicated work.openiti_uri field + mirrored as
    authority_xref entry (authority="openiti_uri")
  - subjects from corpus_genres.json join — primary_genre and
    rule_based_type both kept (deduped) when both present
  - composition_temporal: explicit year if present, else
    {"end_ce": author_death_ce, "approximation": "before"} —
    indicates "composed before this date" in the timeline
  - extant_manuscripts derived from versions_detail (manuscript
    provenance + word count)
  - original_language from languages[0]
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import work_canonicalize as wc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "OpenITI corpus snapshot 2024-2026 (https://openiti.org)."

# OpenITI ISO 639-3 → schema canonical language tag map
_LANG_MAP = {
    "ara": "ar",
    "fas": "fa",
    "per": "fa",          # alias
    "tur": "tr",
    "ott": "ota",         # Ottoman Turkish — kept as ISO 639-3
    "urd": "ur",
    "lat": "la",
    "eng": "en",
}


def _alt_titles_from_raw(raw: dict) -> list[str]:
    """Extract alternate titles from common OpenITI fields."""
    out = []
    for key in ("alternative_titles", "alt_titles", "title_alternatives"):
        v = raw.get(key)
        if isinstance(v, list):
            out.extend([str(x) for x in v if x])
        elif isinstance(v, str):
            out.append(v)
    # Some OpenITI exports put alternates in title_lat_variants / title_ar_variants
    for key in ("title_lat_variants", "title_ar_variants"):
        v = raw.get(key)
        if isinstance(v, list):
            out.extend([str(x) for x in v if x])
    return out


def _build_subjects(genre_data: dict) -> list[str]:
    """Map corpus_genres entry → unified subjects[] list. Keeps both
    primary_genre and rule_based_type if they disagree."""
    out: list[str] = []
    if not isinstance(genre_data, dict):
        return out

    pg = genre_data.get("primary_genre")
    rb = genre_data.get("rule_based_type")

    if pg:
        mapped = wc.OPENITI_GENRE_PASSTHROUGH.get(pg.lower(), pg.lower())
        if mapped not in out:
            out.append(mapped)
    if rb:
        mapped = wc.OPENITI_GENRE_PASSTHROUGH.get(rb.lower(), rb.lower())
        if mapped not in out:
            out.append(mapped)

    return out[:5]   # cap


def _build_extant_manuscripts(versions_detail) -> list:
    """Convert OpenITI versions_detail entries into a list of URI strings.
    work.schema v0.1.0 expects extant_manuscripts.items to be string URIs.
    Richer per-version metadata (size_bytes, word_count, source) is folded
    into the work's `note` field via the calling adapter."""
    if not isinstance(versions_detail, list):
        return []
    out = []
    for v in versions_detail[:25]:
        if isinstance(v, str) and v:
            out.append(v)
        elif isinstance(v, dict):
            uri = v.get("uri") or v.get("primary_uri") or v.get("id")
            if uri and isinstance(uri, str):
                out.append(uri)
    return out


def _normalize_language(lang_code: str | None) -> str | None:
    if not lang_code or not isinstance(lang_code, str):
        return None
    return _LANG_MAP.get(lang_code.lower(), lang_code.lower())


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "work"
    sidecars = options.get("sidecars", {})
    resolution_map: dict = sidecars.get("openiti_author_resolution", {})
    unresolved_sidecar = sidecars.get("openiti_works_unresolved", {})
    authors_pending = sidecars.get("openiti_works_authors_pending", {})

    # If runner did not pre-load the resolution map sidecar, load it ourselves
    # from the canonical state path. The pre-pass openiti_author_resolve must
    # have run before this adapter; otherwise resolution_map stays empty
    # and all works land in the unresolved sidecar.
    if not resolution_map:
        from pathlib import Path as _Path
        import json as _json
        candidate = _Path("data/_state/openiti_author_resolution.json")
        if candidate.exists():
            try:
                with candidate.open(encoding="utf-8") as _fh:
                    resolution_map = _json.load(_fh)
                print(f"[openiti-works] auto-loaded resolution map: {len(resolution_map)} entries")
            except Exception as _e:
                print(f"[openiti-works] WARNING: could not load resolution map: {_e}")

    # Same self-load fallback for author metadata used by composition_temporal
    author_metadata: dict = sidecars.get("openiti_author_metadata", {})
    if not author_metadata:
        from pathlib import Path as _Path
        import json as _json
        ca_path = _Path("data/sources/openiti/corpus_authors.json")
        if ca_path.exists():
            try:
                with ca_path.open(encoding="utf-8") as _fh:
                    raw_authors = _json.load(_fh)
                if isinstance(raw_authors, list):
                    for _a in raw_authors:
                        if isinstance(_a, dict):
                            _aid = _a.get("author_id") or _a.get("id")
                            if _aid:
                                author_metadata[_aid] = {
                                    "death_ce": _a.get("death_ce"),
                                    "death_ah": _a.get("death_ah") or _a.get("death_hijri"),
                                }
                elif isinstance(raw_authors, dict):
                    for _aid, _a in raw_authors.items():
                        if isinstance(_a, dict):
                            author_metadata[_aid] = {
                                "death_ce": _a.get("death_ce"),
                                "death_ah": _a.get("death_ah") or _a.get("death_hijri"),
                            }
                print(f"[openiti-works] auto-loaded author metadata: {len(author_metadata)} entries")
            except Exception as _e:
                print(f"[openiti-works] WARNING: could not load author metadata: {_e}")

    pipeline_name = options.get("pipeline_name", "canonicalize_work_openiti_works")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        raw = record["raw"]
        wid = record["source_id"]
        author_id = record.get("author_id")

        # Idempotent PID
        input_hash = f"openiti:{wid}"
        pid = pid_minter.mint(namespace, input_hash)

        # Title block — corpus_works.json uses work_title (Latin only).
        title_ar = raw.get("title_ar") or raw.get("ar_title") or raw.get("title_native")
        title_lat = (raw.get("work_title") or raw.get("title_lat") or
                     raw.get("title_translit") or raw.get("title"))
        title_en = raw.get("title_en")

        # Build labels
        labels = wc.build_work_labels(
            title_en=title_en,
            title_tr=title_lat,    # OpenITI Latin transliteration → tr bucket
            title_ar=title_ar,
            alternate_titles=_alt_titles_from_raw(raw),
        )

        # Subjects from genre join
        subjects = _build_subjects(record.get("genre_data") or {})

        # @type
        types = wc.build_work_type_array(subjects=subjects)

        # Author resolution from sidecar
        authors: list[str] = []
        author_resolution_status = "no_author_id"
        if author_id:
            res = resolution_map.get(author_id) or {}
            res_pid = res.get("pid")
            if res_pid:
                authors = [res_pid]
                authors_pending[pid] = list(authors)
                author_resolution_status = f"tier_{res.get('tier','?')}_pid={res_pid}"
            else:
                author_resolution_status = (
                    f"unresolved_in_map (tier={res.get('tier','-')}, "
                    f"reason={res.get('reason','no_entry')})"
                )
                unresolved_sidecar[pid] = {
                    "openiti_work_id": wid,
                    "openiti_author_id": author_id,
                    "title_lat": title_lat,
                    "title_ar": title_ar,
                    "resolution_entry": res,
                }
        else:
            unresolved_sidecar[pid] = {
                "openiti_work_id": wid,
                "openiti_author_id": None,
                "title_lat": title_lat,
                "title_ar": title_ar,
                "reason": "no_author_id_in_corpus_works",
            }

        # Composition temporal
        composition_temporal = None
        explicit_year = raw.get("composition_year") or raw.get("year_ce")
        explicit_ah = raw.get("composition_year_ah") or raw.get("year_ah")
        if explicit_year or explicit_ah:
            composition_temporal = wc.build_composition_temporal(
                year_ce=explicit_year,
                year_ah=explicit_ah,
                approximation="circa",
            )
        elif author_id and author_id in author_metadata:
            ad = author_metadata[author_id] or {}
            ad_ce = ad.get("death_ce")
            ad_ah = ad.get("death_ah")
            if isinstance(ad_ce, int) or isinstance(ad_ah, int):
                composition_temporal = wc.build_composition_temporal(
                    end_year_ce=ad_ce,
                    year_ah=ad_ah if isinstance(ad_ah, int) else None,
                    approximation="before",
                )

        # Authority xref — OpenITI URI as primary cross-ref.
        # Schema work.openiti_uri pattern is '<AHYear><Author>.<WorkSlug>' (2 dot-segments).
        # corpus_works often has version-level URIs with 3 segments
        # (e.g. '1111Majlisi.BiharAnwar.Shia001432Vols-ara1'). We strip
        # the trailing version segment for the structural openiti_uri field;
        # the full version-URI stays in authority_xref + note.
        authority_xref = []
        primary_uri_full = raw.get("primary_uri") or wid
        primary_uri_work = primary_uri_full
        if primary_uri_full and primary_uri_full.count(".") >= 2:
            primary_uri_work = ".".join(primary_uri_full.split(".")[:2])
        if primary_uri_work:
            # Schema authority_xref.id pattern is 2-segment work-level (no version suffix)
            authority_xref.append(wc.make_openiti_xref(primary_uri_work, confidence=1.0))

        # Original language
        languages_field = raw.get("languages")
        original_language = None
        if isinstance(languages_field, list) and languages_field:
            original_language = _normalize_language(languages_field[0])
        elif isinstance(languages_field, str):
            original_language = _normalize_language(languages_field)

        # Extant manuscripts: schema requires iac:manuscript-* PIDs (namespace
        # not minted until H6+). Fold OpenITI URIs into note for now.
        manuscript_uris = _build_extant_manuscripts(raw.get("versions_detail"))

        # Provenance
        page_locator = (
            f"OpenITI corpus_works.json work_id={wid}, "
            f"primary_uri={primary_uri_full or 'n/a'}, author_id={author_id or 'n/a'}"
        )
        record_history_note = (
            f"Initial canonicalization from OpenITI corpus snapshot "
            f"({wid}); author resolution: {author_resolution_status}; "
            f"openiti-works adapter (Hafta 5)."
        )
        provenance = wc.build_work_provenance(
            source_record_id=f"openiti:{wid}",
            source_kind="primary_textual",   # OpenITI = digitized primary editions
            page_locator=page_locator,
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=record_history_note,
        )

        # Build record
        work: dict = {
            "@id": pid,
            "@type": types,
            "labels": labels,
            "provenance": provenance,
        }
        if composition_temporal:
            work["composition_temporal"] = composition_temporal
        if subjects:
            work["subjects"] = subjects
        if authors:
            work["authors"] = authors
        if authority_xref:
            work["authority_xref"] = authority_xref
        if original_language:
            work["original_language"] = original_language
        # Do NOT write extant_manuscripts[] until H6 mints manuscript namespace.
        if primary_uri_work:
            work["openiti_uri"] = primary_uri_work

        # Note — preserves OpenITI-specific provenance + resolution status
        note_bits = [
            f"Promoted from OpenITI corpus_works ({wid}).",
        ]
        # Versions count + word count summary
        versions = raw.get("versions_detail") or []
        if isinstance(versions, list):
            total_words = 0
            for v in versions:
                wc_count = (v.get("word_count") if isinstance(v, dict) else None)
                if isinstance(wc_count, int):
                    total_words += wc_count
            note_bits.append(
                wc.format_openiti_work_note(
                    uri=primary_uri_full,
                    word_count=total_words if total_words else None,
                    version_count=len(versions) if len(versions) > 1 else None,
                )
            )
        if manuscript_uris:
            note_bits.append(
                f"OpenITI manuscript URIs ({len(manuscript_uris)}): "
                + ", ".join(manuscript_uris[:5])
                + (f" (+{len(manuscript_uris)-5} more)" if len(manuscript_uris) > 5 else "")
            )
        if not authors:
            note_bits.append(
                f"[UNRESOLVED] author_id={author_id or 'none'}; "
                "see openiti_works_unresolved sidecar."
            )
        work["note"] = wc.assemble_note([b for b in note_bits if b])

        # Smoke validation
        validation_errors = wc.quick_validate_work(work)
        if validation_errors:
            work["_quick_validation_errors"] = validation_errors

        yield work
