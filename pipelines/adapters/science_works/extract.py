"""
extract.py — Read science_layer.json and yield each work-like entry
(key_works[] entries + filtered discoveries[]), shape-normalized so
canonicalize.py can be source-agnostic.

Two yielded record types:
  - kind="key_work":  one record per (scholar_id, key_work_idx) pair
  - kind="discovery": one record per discovery (filtered to written works only)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator


# Discovery filter — only mint as work if name strongly suggests a written
# work (not a conceptual discovery / discipline founding / instrument
# invention). Conservative: keep false-negatives (drop borderline cases),
# they go to sidecar science_works_discovery_drops for Hafta 6 review.
_WRITTEN_WORK_HEAD_PATTERNS = re.compile(
    r"^(?:"
    r"kit[āaâā]b|"          # Kitāb / Kitāb / Kitap
    r"ris[āaâā]l[ae]|"      # Risāla / Risāle
    r"maq[āaâā]l[ae]|"      # Maqāla
    r"d[īiî]w[āaâā]n|"      # Dīwān / Dîvân
    r"t[āaâā]r[īiî]kh|"     # Tārīkh / Târîh
    r"muʿjam|mu['c]jam|mu[čc]em|"   # Muʿjam / Mucam / Mucem (transliteration variants)
    r"siyar|"               # Siyar
    r"book |"               # English "Book of ..."
    r"treatise |"
    r"compendium |"
    r"encyclopedia |"
    r"الكتاب|كتاب|رسالة|مقالة|ديوان"  # Arabic-script openers
    r")",
    re.IGNORECASE,
)


def _name_looks_like_work_title(name) -> bool:
    """Triage check: does this discovery `name` look like the title of a
    written work, vs a concept / discipline / theorem name?

    Multilingual `name` dict (en/tr/ar) — match if ANY language's name
    matches a work-title pattern.
    """
    if not name:
        return False
    if isinstance(name, str):
        return bool(_WRITTEN_WORK_HEAD_PATTERNS.search(name))
    if isinstance(name, dict):
        for lang in ("en", "tr", "ar"):
            v = name.get(lang)
            if isinstance(v, str) and _WRITTEN_WORK_HEAD_PATTERNS.search(v):
                return True
    return False


def extract(input_paths: list[Path]) -> Iterator[dict]:
    """Yield work-like records from science_layer.json.

    Iteration order:
      1. All key_works first (authoritative, every entry is a written work)
      2. Then filtered discoveries (heuristic-passed only)

    Discovery dropouts are written to sidecar via the canonicalize side
    effect; this extractor only emits records that pass the filter.
    """
    p = input_paths[0]
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)

    scholars = data.get("scholars", [])
    discoveries = data.get("discoveries", [])

    # 1. key_works entries
    for sc in scholars:
        scholar_id = sc.get("id")
        if not scholar_id:
            continue
        kw_list = sc.get("key_works") or []
        if not isinstance(kw_list, list):
            continue
        for idx, kw in enumerate(kw_list):
            if not isinstance(kw, dict):
                continue
            yield {
                "raw": kw,
                "kind": "key_work",
                "scholar_id": scholar_id,
                "scholar_name": sc.get("name"),         # multilingual dict
                "scholar_full_name": sc.get("full_name"),  # multilingual dict
                "scholar_death_year": sc.get("death_year"),
                "kw_idx": idx,
                "source_id": f"{scholar_id}:kw_{idx}",
            }

    # 2. discovery entries (filtered)
    # Build a scholar lookup so we can cross-reference scholar_id
    scholar_by_id = {sc.get("id"): sc for sc in scholars if sc.get("id")}

    for disc in discoveries:
        if not isinstance(disc, dict):
            continue
        disc_id = disc.get("id")
        if not disc_id:
            continue
        passed = _name_looks_like_work_title(disc.get("name"))
        # We yield BOTH passed and dropped — canonicalize handles the
        # dropped ones by writing to the science_works_discovery_drops
        # sidecar but NOT producing a record. Pass passed flag through.
        sc = scholar_by_id.get(disc.get("scholar_id"))
        yield {
            "raw": disc,
            "kind": "discovery",
            "scholar_id": disc.get("scholar_id"),
            "scholar_name": (sc or {}).get("name"),
            "scholar_full_name": (sc or {}).get("full_name"),
            "scholar_death_year": (sc or {}).get("death_year"),
            "passed_filter": passed,
            "source_id": disc_id,
        }
