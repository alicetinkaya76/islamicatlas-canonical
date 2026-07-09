"""
dia_works_h5_audit.py — Diagnostic sidecar generator for Hafta 6 hand-off.

Hafta 5 explicitly DID NOT mint canonical iac:work-* records from
dia_works.json (44,611 work-mentions across 3,369 DİA slugs), because
spot-audit revealed systemic mis-attribution from the upstream DİA
parser (e.g., "abbadi-ebu-mansur" carried Mu'cemü'l-büldân, which is
Yâqūt's, not Abbâdî's).

This script produces a per-slug × per-title diagnostic file. For each
title attributed to a DİA slug, we compute:

  1. title_fingerprint via wc.title_fingerprint()
  2. Whether the title's fingerprint is also a label fingerprint of
     any record in the science_works namespace (curated, ~300 records)
  3. Whether it's a label fingerprint in openiti_works (~9,104 records)
  4. The set of resolved author PIDs across all matched works

Output: data/_state/dia_works_h5_audit.json

Usage in Hafta 6 (the audit consumer):
  - DİA slug + title that matches BOTH science_works AND openiti_works
    with overlapping author PIDs → high-confidence attribution → mint
    a canonical record + SAME-AS link to the existing science/openiti
    work
  - DİA slug + title with ONE match → moderate confidence; cross-check
    with Brockelmann/GAL pipeline or Kashf al-Zunun
  - DİA slug + title with NO match → low confidence; flag for manual
    review or accept as DİA-unique attribution
  - Title fingerprint matches a work whose authors[] DOES NOT include
    the resolved DİA scholar PID → STRONG signal of mis-attribution
    (the upstream parser likely picked up a bibliography reference, not
    a "works by" entry)

This script reads ONLY existing work records and dia_works.json; it does
NOT mint any iac:work-* records. Hafta 6 is the proper minting session.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from pipelines._lib import work_canonicalize as wc


# --------------------------------------------------------------------------- #
# Helpers — load existing canonical work store
# --------------------------------------------------------------------------- #


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _iter_canonical_dir(path: Path, glob_pattern: str) -> Iterator[dict]:
    """Iterate per-record JSON files matching the glob."""
    if not path.exists():
        return
    for p in sorted(path.glob(glob_pattern)):
        try:
            with p.open(encoding="utf-8") as fh:
                yield json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue


def build_fingerprint_index(
    works_iter: Iterator[dict],
    source_filter: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """Build {fingerprint: [work_pid, ...]} inverted index, plus a
    {work_pid: {labels, authors, source}} side dict for audit context.

    source_filter examples:
      - "science-works:"  → only include science_works records
      - "openiti:"        → only include openiti_works records
      - None              → include everything
    """
    fp_to_works: dict[str, list[str]] = defaultdict(list)
    work_meta: dict[str, dict] = {}
    for w in works_iter:
        wid = w.get("@id")
        if not wid:
            continue
        if source_filter:
            prov = w.get("provenance") or {}
            df = prov.get("derived_from") or []
            if not df:
                continue
            sid = df[0].get("source_id", "")
            if not sid.startswith(source_filter):
                continue
        labels = w.get("labels") or {}
        fps = wc.fingerprint_all_labels(labels)
        for fp in fps:
            fp_to_works[fp].append(wid)
        work_meta[wid] = {
            "labels": labels,
            "authors": list(w.get("authors") or []),
            "title_tr": labels.get("prefLabel", {}).get("tr"),
            "title_en": labels.get("prefLabel", {}).get("en"),
            "title_ar": labels.get("prefLabel", {}).get("ar"),
            "fingerprints": list(fps),
        }
    return dict(fp_to_works), work_meta


# --------------------------------------------------------------------------- #
# DİA scholar → person PID resolution
# --------------------------------------------------------------------------- #


def build_dia_slug_to_person_pid(person_iter: Iterator[dict]) -> dict[str, str]:
    """Find DİA-derived person records and map their slug → PID. The
    slug appears in provenance.derived_from[].source_id of the form
    'dia:<slug>'."""
    out: dict[str, str] = {}
    for p in person_iter:
        pid = p.get("@id")
        if not pid:
            continue
        prov = p.get("provenance") or {}
        for d in (prov.get("derived_from") or []):
            sid = (d.get("source_id") or "")
            if sid.startswith("dia:"):
                slug = sid.split(":", 1)[1]
                out[slug] = pid
                break
    return out


# --------------------------------------------------------------------------- #
# Audit core — per-title check
# --------------------------------------------------------------------------- #


def audit_title(
    *,
    title: str,
    sci_fp_index: dict[str, list[str]],
    op_fp_index: dict[str, list[str]],
    sci_meta: dict[str, dict],
    op_meta: dict[str, dict],
    dia_scholar_pid: str | None,
) -> dict:
    """Audit a single title from dia_works.json.

    Returns a dict capturing:
      - title (raw)
      - title_fingerprint
      - matches_in_science_works[] (work_pids, with their authors)
      - matches_in_openiti_works[]
      - mis_attribution_signal: True if any matched work's authors
        does NOT include dia_scholar_pid
    """
    fp = wc.title_fingerprint(title)
    norm = wc.normalize_title_for_fingerprint(title)

    sci_matches = sci_fp_index.get(fp, []) if fp else []
    op_matches = op_fp_index.get(fp, []) if fp else []

    sci_match_details = [
        {"pid": wid, "authors": sci_meta[wid]["authors"],
         "title_tr": sci_meta[wid]["title_tr"]}
        for wid in sci_matches if wid in sci_meta
    ]
    op_match_details = [
        {"pid": wid, "authors": op_meta[wid]["authors"],
         "title_tr": op_meta[wid]["title_tr"]}
        for wid in op_matches if wid in op_meta
    ]

    # Mis-attribution signal: if we can resolve the DİA scholar's PID
    # and AT LEAST ONE matched work explicitly excludes that scholar
    # from its authors, the upstream DİA parser likely lifted a
    # bibliography reference rather than a "works by" entry.
    mis_attribution_signal = False
    matched_authors_union: set[str] = set()
    if dia_scholar_pid:
        all_match_authors: list[set[str]] = []
        for d in sci_match_details + op_match_details:
            authors_set = set(d["authors"])
            matched_authors_union |= authors_set
            all_match_authors.append(authors_set)
        if all_match_authors:
            mis_attribution_signal = (
                dia_scholar_pid not in matched_authors_union
            )

    confidence_band = _compute_confidence_band(
        sci_match_count=len(sci_matches),
        op_match_count=len(op_matches),
        scholar_in_match=(
            dia_scholar_pid is not None and
            dia_scholar_pid in matched_authors_union
        ),
        scholar_resolvable=(dia_scholar_pid is not None),
    )

    return {
        "title": title,
        "title_normalized": norm,
        "title_fingerprint": fp or None,
        "match_in_science_works": sci_match_details,
        "match_in_openiti_works": op_match_details,
        "matched_author_pids": sorted(matched_authors_union),
        "dia_scholar_pid": dia_scholar_pid,
        "mis_attribution_signal": mis_attribution_signal,
        "confidence_band": confidence_band,
    }


def _compute_confidence_band(
    *,
    sci_match_count: int,
    op_match_count: int,
    scholar_in_match: bool,
    scholar_resolvable: bool,
) -> str:
    """Bucket the audit result into a 5-level confidence band that
    Hafta 6 minting strategy can branch on."""
    if not scholar_resolvable:
        return "scholar_unresolved"
    if sci_match_count > 0 and op_match_count > 0 and scholar_in_match:
        return "high_validated_both_sources"
    if (sci_match_count > 0 or op_match_count > 0) and scholar_in_match:
        return "moderate_validated_one_source"
    if (sci_match_count > 0 or op_match_count > 0) and not scholar_in_match:
        return "low_likely_misattribution"
    return "no_external_match_dia_only"


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def run_audit(
    *,
    dia_works_path: Path,
    work_dir: Path,           # data/canonical/work/  (per-record JSON files)
    person_dir: Path,         # data/canonical/person/
    output_path: Path,        # data/_state/dia_works_h5_audit.json
    work_jsonl_fallback: Path | None = None,   # alt: one big jsonl
) -> dict:
    """Generate the dia_works H5 audit sidecar.

    work_dir + person_dir are the Mac canonical layout; if work_dir is
    empty/missing AND work_jsonl_fallback exists, we fall back to the
    jsonl form.
    """
    # Load works → fingerprint indexes
    if work_dir.exists() and any(work_dir.glob("iac_work_*.json")):
        works_iter_factory = lambda: _iter_canonical_dir(work_dir, "iac_work_*.json")
    elif work_jsonl_fallback and work_jsonl_fallback.exists():
        works_iter_factory = lambda: _iter_jsonl(work_jsonl_fallback)
    else:
        raise FileNotFoundError(
            f"No work records found at {work_dir} or fallback {work_jsonl_fallback}"
        )

    sci_fp_index, sci_meta = build_fingerprint_index(
        works_iter_factory(), source_filter="science-works:"
    )
    op_fp_index, op_meta = build_fingerprint_index(
        works_iter_factory(), source_filter="openiti:"
    )

    # Load persons → DİA slug → PID map
    persons_iter = _iter_canonical_dir(person_dir, "iac_person_*.json")
    dia_slug_to_pid = build_dia_slug_to_person_pid(persons_iter)

    # Load dia_works.json
    with dia_works_path.open(encoding="utf-8") as fh:
        dia_works = json.load(fh)
    if not isinstance(dia_works, dict):
        raise ValueError(
            f"dia_works.json expected to be a dict (slug → [titles]); got {type(dia_works).__name__}"
        )

    # Per-slug × per-title audit
    per_slug: dict[str, list[dict]] = {}
    summary = {
        "total_slugs": 0,
        "slugs_with_resolved_scholar_pid": 0,
        "total_titles": 0,
        "matched_in_science_works": 0,
        "matched_in_openiti_works": 0,
        "matched_in_either": 0,
        "matched_in_both": 0,
        "mis_attribution_signal_count": 0,
        "confidence_band_counts": defaultdict(int),
    }

    for slug, title_list in dia_works.items():
        if not isinstance(title_list, list):
            continue
        summary["total_slugs"] += 1
        scholar_pid = dia_slug_to_pid.get(slug)
        if scholar_pid:
            summary["slugs_with_resolved_scholar_pid"] += 1

        slug_audits: list[dict] = []
        for title in title_list:
            if not isinstance(title, str) or not title.strip():
                continue
            summary["total_titles"] += 1
            entry = audit_title(
                title=title,
                sci_fp_index=sci_fp_index,
                op_fp_index=op_fp_index,
                sci_meta=sci_meta,
                op_meta=op_meta,
                dia_scholar_pid=scholar_pid,
            )
            sci_n = len(entry["match_in_science_works"])
            op_n = len(entry["match_in_openiti_works"])
            if sci_n > 0:
                summary["matched_in_science_works"] += 1
            if op_n > 0:
                summary["matched_in_openiti_works"] += 1
            if sci_n > 0 or op_n > 0:
                summary["matched_in_either"] += 1
            if sci_n > 0 and op_n > 0:
                summary["matched_in_both"] += 1
            if entry["mis_attribution_signal"]:
                summary["mis_attribution_signal_count"] += 1
            summary["confidence_band_counts"][entry["confidence_band"]] += 1
            slug_audits.append(entry)

        per_slug[slug] = slug_audits

    # Convert defaultdict for JSON serialization
    summary["confidence_band_counts"] = dict(summary["confidence_band_counts"])

    output = {
        "summary": summary,
        "per_slug": per_slug,
        "metadata": {
            "generator": "dia_works_h5_audit.py v0.1.0",
            "purpose": (
                "Hafta 6 hand-off: do not mint dia_works canonical records "
                "until per-slug × per-title attribution is validated against "
                "Brockelmann/GAL ground truth + DİA chunk re-extraction."
            ),
            "science_works_indexed": len(sci_meta),
            "openiti_works_indexed": len(op_meta),
            "dia_slugs_with_pid": len(dia_slug_to_pid),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Generate dia_works Hafta 5 audit sidecar (Hafta 6 hand-off)."
    )
    ap.add_argument("--dia-works", type=Path,
                    default=Path("data/sources/dia/dia_works.json"))
    ap.add_argument("--work-dir", type=Path,
                    default=Path("data/canonical/work"))
    ap.add_argument("--person-dir", type=Path,
                    default=Path("data/canonical/person"))
    ap.add_argument("--out", type=Path,
                    default=Path("data/_state/dia_works_h5_audit.json"))
    ap.add_argument("--work-jsonl-fallback", type=Path, default=None,
                    help="Alternative input: a single jsonl with all work records")
    args = ap.parse_args()

    summary = run_audit(
        dia_works_path=args.dia_works,
        work_dir=args.work_dir,
        person_dir=args.person_dir,
        output_path=args.out,
        work_jsonl_fallback=args.work_jsonl_fallback,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
