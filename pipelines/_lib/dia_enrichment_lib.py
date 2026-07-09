"""
dia_enrichment_lib.py — Utilities for the H8 dia_person_enrichment_v8 adapter.

Contains: per-slug chunk aggregation, Arabic-script classification, extended
death-paren parsing (covers 5 date format families), sentence-boundary
truncation for long-tail narratives (>50K chars per ADR-012), and provenance
entry construction for the dia-chunks-v8:<slug> CURIE.

Mirrors H4 dia adapter's aggregation logic (sort by `c`, space-join) to
preserve byte-identical results for non-truncated entries — making it easy
to verify "v8 description.tr is genuinely an extension of H4's, not a
different concatenation."

Wraps person_canonicalize.parse_death_paren() where possible, extends it
where Stage 2b analyzer v2 revealed unsupported patterns (gregorian_range,
approximate, gregorian_only).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterator


# Arabic-script Unicode blocks
ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")

# Death-date regex patterns (priority order — first match wins).
DATE_PATTERNS = [
    ("hijri_gregorian", re.compile(
        r"\(\s*ö\.\s*(?P<hijri>\d{1,4})\s*/\s*(?P<gregorian>\d{3,4})\s*\)",
        re.IGNORECASE,
    )),
    ("gregorian_range", re.compile(
        r"\(\s*(?P<g_birth>1[5-9]\d{2}|20\d{2})\s*[-\u2013]\s*(?P<g_death>1[5-9]\d{2}|20\d{2})\s*\)"
    )),
    ("gregorian_only", re.compile(
        r"\(\s*ö\.\s*(?P<gregorian>1[5-9]\d{2}|20\d{2})\s*\)",
        re.IGNORECASE,
    )),
    ("approximate_pre", re.compile(
        r"\(\s*ö\.\s*(?:h\.|m\.|yaklaşık)\s*(?P<year>\d{2,4})",
        re.IGNORECASE,
    )),
    ("approximate_post", re.compile(
        r"\(\s*ö\.\s*(?P<year>\d{2,4})\s*(?:civarı|civari|civarinda|sonu|öncesi|sonrası)",
        re.IGNORECASE,
    )),
    ("hijri_only", re.compile(
        r"\(\s*ö\.\s*(?P<hijri>\d{2,4})\s*\)",
        re.IGNORECASE,
    )),
]

# Sentence-boundary regex for truncation fallback
SENTENCE_END_RE = re.compile(r"[.!?:](?=\s|$)")

# ADR-012 limit
DESCRIPTION_MAX_LEN = 50_000


def aggregate_chunks_by_slug(chunks: list[dict]) -> dict[str, dict]:
    """Group chunks by `s`, sort each group by `c`, concatenate `t` with space.

    Returns mapping slug → dict with keys:
        n_chunks, t_total, primary_n, primary_a, primary_d, primary_sec.

    Aggregation strategy mirrors pipelines/adapters/dia/extract.py
    (H4 vintage) so v8 narratives are byte-identical to H4's for chunks
    aggregating below 5000 chars (the H4 truncation point).
    """
    by_slug: dict[str, list[dict]] = defaultdict(list)
    for ch in chunks:
        slug = ch.get("s")
        if slug:
            by_slug[slug].append(ch)

    result: dict[str, dict] = {}
    for slug, group in by_slug.items():
        group_sorted = sorted(
            group, key=lambda c: (c.get("c") or 0, c.get("_id") or 0)
        )
        t_total = " ".join(
            c.get("t", "") for c in group_sorted if c.get("t")
        )
        primary_a = next(
            (c["a"] for c in group_sorted if (c.get("a") or "").strip()), ""
        )
        primary_d = next(
            (c["d"] for c in group_sorted if (c.get("d") or "").strip()), ""
        )
        primary_n = (group_sorted[0].get("n") or "").strip()
        primary_sec = next(
            (c["sec"] for c in group_sorted if (c.get("sec") or "").strip()), ""
        )
        result[slug] = {
            "n_chunks": len(group_sorted),
            "t_total": t_total,
            "primary_n": primary_n,
            "primary_a": primary_a,
            "primary_d": primary_d,
            "primary_sec": primary_sec,
        }
    return result


def classify_arabic_script(s: str) -> str:
    """Classify a string by Arabic-script content.

    Returns one of:
        'empty'           — string is empty / whitespace-only / None
        'arabic_primary'  — majority of letters are Arabic-script
        'mixed_script'    — has Arabic-script chars but Latin is majority
        'non_arabic'      — no Arabic-script chars at all
    """
    if not isinstance(s, str) or not s.strip():
        return "empty"
    if not ARABIC_SCRIPT_RE.search(s):
        return "non_arabic"
    ar = sum(1 for c in s if ARABIC_SCRIPT_RE.match(c))
    latin = sum(1 for c in s if c.isascii() and c.isalpha())
    if ar > latin:
        return "arabic_primary"
    return "mixed_script"


def parse_death_paren_extended(d: str) -> dict | None:
    """Extended death-paren parser covering 5 formats (Stage 2b analyzer v2
    discovered the diversity beyond person_canonicalize.parse_death_paren).

    Returns dict with keys:
        category    : 'hijri_gregorian' | 'hijri_only' | 'gregorian_range'
                    | 'gregorian_only' | 'approximate'
        raw         : original string
        hijri       : int | None  (AH year)
        gregorian   : int | None  (CE year)
        approximation: 'exact' | 'circa'
        g_birth     : int | None  (only for gregorian_range)

    Returns None if no pattern matches.
    """
    if not isinstance(d, str) or not d.strip():
        return None
    for name, pat in DATE_PATTERNS:
        m = pat.search(d)
        if not m:
            continue
        groups = {k: v for k, v in m.groupdict().items() if v is not None}
        result: dict = {"category": name, "raw": d, "hijri": None, "gregorian": None}
        if name == "hijri_gregorian":
            result["hijri"] = int(groups["hijri"])
            result["gregorian"] = int(groups["gregorian"])
            result["approximation"] = "exact"
        elif name == "hijri_only":
            result["hijri"] = int(groups["hijri"])
            result["approximation"] = "exact"
        elif name == "gregorian_range":
            result["gregorian"] = int(groups["g_death"])
            result["g_birth"] = int(groups["g_birth"])
            result["approximation"] = "exact"
        elif name == "gregorian_only":
            result["gregorian"] = int(groups["gregorian"])
            result["approximation"] = "exact"
        elif name in ("approximate_pre", "approximate_post"):
            result["category"] = "approximate"  # collapse both subtypes
            result["hijri"] = int(groups["year"])
            result["approximation"] = "circa"
        return result
    return None


def build_temporal_from_parsed_d(d_parsed: dict | None) -> dict | None:
    """Convert parse_death_paren_extended output → temporal.schema.json struct.

    Returns dict with start_ah / start_ce / approximation fields, or None
    if both AH and CE are out of schema range.

    Schema constraints (from schemas/_common/temporal.schema.json):
        start_ah ∈ [1, 1700]
        start_ce ∈ [-3000, 3000]
    """
    if d_parsed is None:
        return None
    temporal: dict = {}
    ah = d_parsed.get("hijri")
    ce = d_parsed.get("gregorian")
    if ah and 1 <= ah <= 1700:
        temporal["start_ah"] = ah
    if ce and -3000 <= ce <= 3000:
        temporal["start_ce"] = ce
    if not temporal:
        return None  # Out-of-range; cannot encode
    temporal["approximation"] = d_parsed.get("approximation", "exact")
    return temporal


TRUNCATION_MARKER = " [… truncated]"


def truncate_at_sentence_boundary(text: str, max_len: int = DESCRIPTION_MAX_LEN) -> tuple[str, bool]:
    """Truncate text at last sentence boundary, guaranteeing result <= max_len.

    Returns (text, was_truncated). If len(text) <= max_len, returns text
    unchanged with was_truncated=False.

    Reserves the truncation marker length before searching, so the marker is
    accounted for in the cap. Cut position is always <= (max_len - marker_len),
    so the final string is guaranteed <= max_len.

    Search window: [search_end - 200, search_end] for sentence-end punctuation,
    where search_end = max_len - marker_len.
    Fallback: last whitespace before search_end - 50.
    Degenerate: max_len <= marker_len returns marker truncated to fit.

    H8 Stage 5 bug fix: previously the marker was appended AFTER cut_pos which
    could be at max_len, causing the final string to exceed max_len by up to
    marker_len chars. Discovered by efgani-cemaleddin (74,318 char aggregated
    narrative producing a 50,008-char description.tr, failing ADR-012
    maxLength: 50000).
    """
    if len(text) <= max_len:
        return text, False
    marker_len = len(TRUNCATION_MARKER)
    if max_len <= marker_len:
        # Degenerate: not enough room even for the marker; return marker
        # truncated to fit. Pathological case; production never hits this.
        return TRUNCATION_MARKER[:max_len], True
    search_end = max_len - marker_len
    search_start = max(0, search_end - 200)
    search_region = text[search_start:search_end]
    matches = list(SENTENCE_END_RE.finditer(search_region))
    if matches:
        cut_pos = search_start + matches[-1].end()
    else:
        # Fallback: cut at last whitespace before search_end - 50
        fallback_end = max(0, search_end - 50)
        cut_pos = text.rfind(" ", 0, fallback_end)
        if cut_pos == -1:
            cut_pos = fallback_end
    # Defensive: guarantee cut_pos in [0, search_end]
    cut_pos = max(0, min(cut_pos, search_end))
    return text[:cut_pos] + TRUNCATION_MARKER, True


def build_h8_provenance_entry(slug: str) -> dict:
    """Build the dia-chunks-v8:<slug> derived_from entry."""
    return {
        "source_id": f"dia-chunks-v8:{slug}",
        "source_type": "tertiary_reference",
        "page_or_locator": f"DİA chunks (per-slug aggregated), slug={slug}",
        "extraction_method": "structured_json",
        "edition_or_version": "Türkiye Diyanet Vakfı İslâm Ansiklopedisi (DİA), dia_chunks.json source; H8 dia_person_enrichment_v8 upgrade pass.",
    }


def has_h8_v8_provenance(record: dict) -> bool:
    """Idempotency probe — true if record already carries dia-chunks-v8:*."""
    derived = record.get("provenance", {}).get("derived_from", [])
    for d in derived:
        if not isinstance(d, dict):
            continue
        sid = d.get("source_id")
        if isinstance(sid, str) and sid.startswith("dia-chunks-v8:"):
            return True
    return False
