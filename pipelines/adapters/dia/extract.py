"""
extract.py — Read DİA chunks + lite + alam_xref, group by slug, yield one
record per biographical slug.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator


def _is_biographical(slug: str, chunks_for_slug: list[dict], lite_entry: dict | None) -> bool:
    """Filter: True iff any chunk has 'd' OR lite has dh/dc/bp/fn/mz."""
    for ch in chunks_for_slug:
        if ch.get("d", "").strip():
            return True
    if lite_entry:
        for k in ("dh", "dc", "bp", "fn", "mz"):
            if lite_entry.get(k):
                return True
    return False


def extract(input_paths: list[Path]) -> Iterator[dict]:
    chunks_path = next(p for p in input_paths if p.name == "dia_chunks.json")
    lite_path = next(p for p in input_paths if p.name == "dia_lite.json")
    xref_path = next(p for p in input_paths if p.name == "dia_alam_xref.json")

    print(f"[extract] loading {chunks_path.name} ({chunks_path.stat().st_size // 1024} KB)...")
    with chunks_path.open(encoding="utf-8") as fh:
        chunks = json.load(fh)
    with lite_path.open(encoding="utf-8") as fh:
        lite = json.load(fh)
    with xref_path.open(encoding="utf-8") as fh:
        xref = json.load(fh)

    # Group chunks by slug
    chunks_by_slug: dict[str, list[dict]] = defaultdict(list)
    for ch in chunks:
        chunks_by_slug[ch["s"]].append(ch)
    # Sort each slug's chunks by 'c' (chunk index) for stable concat
    for s in chunks_by_slug:
        chunks_by_slug[s].sort(key=lambda c: (c.get("c") or 0, c.get("_id") or 0))

    lite_by_slug = {e["id"]: e for e in lite}
    dia_to_alam = xref.get("dia_to_alam", {}) if isinstance(xref, dict) else {}

    n_total = 0
    n_kept = 0
    n_skipped_non_bio = 0
    for slug, slug_chunks in chunks_by_slug.items():
        n_total += 1
        lite_entry = lite_by_slug.get(slug)
        if not _is_biographical(slug, slug_chunks, lite_entry):
            n_skipped_non_bio += 1
            continue
        n_kept += 1

        # First chunk's 'd' wins (most authoritative)
        d_value = next((c["d"] for c in slug_chunks if c.get("d", "").strip()), None)

        yield {
            "slug": slug,
            "title": (slug_chunks[0].get("n") or "").strip(),
            "name_ar": next((c["a"] for c in slug_chunks if c.get("a", "").strip()), None),
            "death_paren": d_value,
            "n_chunks": len(slug_chunks),
            "chunks_text_concat": " ".join(c.get("t", "") for c in slug_chunks if c.get("t")),
            "lite": lite_entry or {},
            "alam_id": dia_to_alam.get(slug),
        }

    # Also handle lite-only slugs (no chunks at all) — Note: per analysis chunks_only=0,
    # so we only need to handle chunk-backed slugs above. But for robustness include
    # any lite entries that have biographical signals and are NOT in chunks_by_slug.
    # (Per analysis: 435 lite-only entries exist but were not in chunks; treat as bios
    # too if signals present.)
    chunks_slugs = set(chunks_by_slug.keys())
    for slug, le in lite_by_slug.items():
        if slug in chunks_slugs:
            continue
        if not (le.get("dh") or le.get("dc") or le.get("bp") or le.get("fn") or le.get("mz")):
            continue
        n_kept += 1
        yield {
            "slug": slug,
            "title": (le.get("t") or "").strip(),
            "name_ar": le.get("ar"),
            "death_paren": None,
            "n_chunks": 0,
            "chunks_text_concat": le.get("ds") or "",
            "lite": le,
            "alam_id": dia_to_alam.get(slug),
        }

    print(f"[extract] DİA slugs scanned: {n_total:,}; kept (biographical): {n_kept:,}; skipped non-bio: {n_skipped_non_bio:,}")
