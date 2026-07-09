"""
canonicalize.py — Convert a science_layer key_work or filtered discovery
into an iac:work-* record.

Design parallels pipelines/adapters/science_layer/canonicalize.py (Hafta 4
person adapter) so future maintainers can read both side-by-side.

Distinctive features over a hypothetical generic work adapter:
  - Trilingual labels (en/tr/ar) directly from the curated source
  - Year-precise composition_temporal (curated source guarantees a year)
  - subjects[] from `field` field, mapped via SCIENCE_FIELD_TO_SUBJECT
  - authors[] resolved from scholar_id via pid_minter idempotency:
      input_hash "science-layer:scholar_NNNN" → existing person PID
    No new PID is minted for the author here; this is a pure lookup. If
    the science-layer person adapter has not yet run, the scholar PID
    will not exist and authors[] is left empty (orphan_works sidecar).
  - significance.tr / significance.en captured into note (preserves the
    "why this matters" text that islamicatlas.org renders on scholar
    pages).
  - description language-prioritized: tr > en > ar (Turkish-anchored
    dataset; mirrors person adapter).

Discovery-specific handling:
  - Discoveries that PASSED extract.py's filter are minted as works
    with an `iac:DiscoveryClaim` subtype (if schema supports) — fallback
    to plain `iac:Work` when the subtype is rejected by validator.
  - Discoveries that FAILED the filter: a dict entry written to the
    science_works_discovery_drops sidecar (Hafta 6 review queue), no
    record yielded.
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import work_canonicalize as wc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "İslam Medeniyeti Akademisi v7 (curated; Selçuk University, 2026)."


def _multilingual_get(d, key, lang):
    """Get d[key][lang] safely from a possibly-nested multilingual dict."""
    if not d or not isinstance(d, dict):
        return None
    v = d.get(key)
    if isinstance(v, dict):
        return v.get(lang)
    return None


def _build_work_description_from_keywork(kw: dict) -> dict:
    """For key_works: significance.{tr,en,ar} -> description language buckets."""
    out = {}
    for lang in ("tr", "en", "ar"):
        sig = _multilingual_get(kw, "significance", lang)
        if sig:
            out[lang] = sig
    return out


def _build_work_description_from_discovery(disc: dict) -> dict:
    """For discoveries: description.{tr,en,ar} maps directly."""
    out = {}
    for lang in ("tr", "en", "ar"):
        d = _multilingual_get(disc, "description", lang)
        if d:
            out[lang] = d
    return out


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "work"
    sidecars = options.get("sidecars", {})
    authors_pending = sidecars.get("science_works_authors_pending", {})
    discovery_drops = sidecars.get("science_works_discovery_drops", {})
    orphan_works = sidecars.get("science_works_orphan_works", {})

    pipeline_name = options.get("pipeline_name", "canonicalize_work_science_works")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        kind = record["kind"]
        sid = record["source_id"]
        scholar_id = record.get("scholar_id")
        scholar_name = record.get("scholar_name") or {}

        # Discoveries that didn't pass the filter: log to sidecar, skip.
        if kind == "discovery" and not record.get("passed_filter", False):
            disc = record["raw"]
            discovery_drops[sid] = {
                "discovery_id": sid,
                "name": disc.get("name"),
                "scholar_id": scholar_id,
                "year": disc.get("year"),
                "field": disc.get("field"),
                "reason": "name_does_not_match_written_work_pattern",
            }
            continue

        raw = record["raw"]

        # Idempotent PID minting
        input_hash = f"science-works:{sid}"
        pid = pid_minter.mint(namespace, input_hash)

        # Title block — multilingual
        title_block = raw.get("title") if kind == "key_work" else raw.get("name")
        if not isinstance(title_block, dict):
            title_block = {}

        title_en = title_block.get("en")
        title_tr = title_block.get("tr")
        title_ar = title_block.get("ar")

        # Description
        if kind == "key_work":
            desc = _build_work_description_from_keywork(raw)
        else:
            desc = _build_work_description_from_discovery(raw)

        # Labels
        labels = wc.build_work_labels(
            title_en=title_en,
            title_tr=title_tr,
            title_ar=title_ar,
            description_tr=desc.get("tr"),
            description_en=desc.get("en"),
            description_ar=desc.get("ar"),
        )

        # Composition temporal — `year` is CE (1-2 digit precision; conservative
        # `circa` for < 1000 CE since exact dating of early-Islamic-era works
        # is rarely confirmed)
        year = raw.get("year")
        approximation = "exact"
        if year is not None:
            try:
                yi = int(year)
                if yi < 1000:
                    approximation = "circa"
            except (TypeError, ValueError):
                year = None
        composition_temporal = wc.build_composition_temporal(
            year_ce=year, approximation=approximation
        )

        # Subjects — map field to unified subject token
        field = raw.get("field")
        subjects: list[str] = []
        if field:
            sub = wc.SCIENCE_FIELD_TO_SUBJECT.get(field)
            if sub and sub not in subjects:
                subjects.append(sub)

        # @type
        types = wc.build_work_type_array(subjects=subjects)

        # Author resolution — idempotent lookup of the person PID minted
        # by the science-layer person adapter in Hafta 4.
        authors: list[str] = []
        if scholar_id:
            scholar_input_hash = f"science-layer:{scholar_id}"
            author_pid = wc.try_resolve_author_pid(
                pid_minter=pid_minter,
                candidate_input_hashes=[scholar_input_hash],
            )
            if author_pid:
                authors = [author_pid]
                # Persist author bidirectional intent for Pass A
                authors_pending[pid] = list(authors)
            else:
                # Person PID not yet in index — flag as orphan for triage
                orphan_works[pid] = {
                    "scholar_id": scholar_id,
                    "scholar_input_hash": scholar_input_hash,
                    "title_tr": title_tr,
                    "title_en": title_en,
                    "reason": "scholar_pid_not_resolved_at_canonicalize_time",
                }

        # Provenance
        page_locator = (
            f"İslam Medeniyeti Akademisi v7, "
            f"scholar_id={scholar_id}, kind={kind}"
            + (f", kw_idx={record.get('kw_idx')}" if kind == "key_work" else "")
            + (f", discovery_id={sid}" if kind == "discovery" else "")
        )
        record_history_note = (
            f"Initial canonicalization from science_layer.json "
            f"({kind} entry); scholar_id={scholar_id}; "
            f"author resolution: {'success' if authors else 'orphan'}; "
            f"science-works adapter (Hafta 5)."
        )
        provenance = wc.build_work_provenance(
            source_record_id=f"science-works:{sid}",
            source_kind="manual_editorial",
            page_locator=page_locator,
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=record_history_note,
        )

        # Authority xref — Wikidata recon attempt (work_qid bias = Q571 = book)
        authority_xref = []
        recon_label = wc.label_for_recon(labels)
        if reconciler is not None and recon_label:
            try:
                hit = reconciler.reconcile(
                    label_en=recon_label,
                    type_qid=options.get("reconciliation_type_qid", "Q571"),
                    source_record_id=input_hash,
                    context={
                        "year_ce": year,
                        "author_scholar_id": scholar_id,
                        "scholar_name_en": (scholar_name or {}).get("en"),
                    },
                )
                if hit:
                    authority_xref.append(hit)
            except Exception:
                pass

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

        # Note — preserve significance text + cross-source hints
        note_bits = [
            f"Promoted from science_layer.json {kind} entry "
            f"(scholar_id={scholar_id}, source_id={sid}).",
        ]
        sig_tr = _multilingual_get(raw, "significance", "tr")
        if sig_tr:
            note_bits.append(f"Significance (TR): {sig_tr[:400]}")
        if not authors:
            note_bits.append(
                "[ORPHAN] Author PID not resolvable at mint time; "
                "see science_works_orphan_works sidecar."
            )
        cross_note = wc.format_science_layer_work_note(
            scholar_id=scholar_id,
            field=field,
            significance_tr=None,  # already captured above
        )
        if cross_note:
            note_bits.append(cross_note)
        work["note"] = wc.assemble_note(note_bits)

        # Smoke validation; full schema validation happens downstream
        validation_errors = wc.quick_validate_work(work)
        if validation_errors:
            # In strict mode the runner will raise; here we annotate the
            # work with a debug field so the runner's validator log shows
            # exactly what failed. We DO yield — the runner gets to decide.
            work["_quick_validation_errors"] = validation_errors

        yield work


# Re-export for symmetry with person_canonicalize. assemble_note is reused
# from the place_canonicalize helpers via the wc module's import chain.
def assemble_note(bits):
    return wc.assemble_note(bits)
