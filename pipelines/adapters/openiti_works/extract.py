"""
extract.py — Read corpus_works.json (and optionally corpus_genres.json
for a subject join) and yield each work-like entry.

Shape tolerance:
  - corpus_works.json may be either a list-of-dicts OR a dict-of-dicts
  - corpus_genres.json maps URI (or work_id) to genre annotation dict
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def _load_optional_genres(path: Path | None) -> dict:
    """Load corpus_genres.json into a dict keyed by URI for fast join."""
    if not path:
        return {}
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}

    # Tolerate dict-keyed-by-URI OR list-with-uri-field
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        out = {}
        for item in data:
            if isinstance(item, dict):
                key = item.get("uri") or item.get("primary_uri") or item.get("work_id")
                if key:
                    out[key] = item
        return out
    return {}


def extract(input_paths: list[Path]) -> Iterator[dict]:
    """Yield one record per work entry, joined with genre annotation if
    present.

    First input path: corpus_works.json (required).
    Second input path: corpus_genres.json (optional).
    """
    if not input_paths:
        return
    works_path = input_paths[0]
    genres_path = input_paths[1] if len(input_paths) > 1 else None

    genre_index = _load_optional_genres(genres_path)

    with works_path.open(encoding="utf-8") as fh:
        works_raw = json.load(fh)

    # Tolerate dict OR list shape
    if isinstance(works_raw, dict):
        works_iter = list(works_raw.values())
    elif isinstance(works_raw, list):
        works_iter = works_raw
    else:
        return

    for w in works_iter:
        if not isinstance(w, dict):
            continue

        # Identify primary URI / work_id
        work_id = (w.get("work_id") or w.get("uri") or
                   w.get("primary_uri") or w.get("id"))
        if not work_id:
            continue

        # Genre join — try multiple candidate keys
        genre_entry = (genre_index.get(work_id) or
                       genre_index.get(w.get("primary_uri") or "") or
                       genre_index.get(w.get("uri") or "") or
                       {})

        yield {
            "raw": w,
            "genre_data": genre_entry,
            "source_id": work_id,
            "author_id": w.get("author_id") or w.get("author"),
        }
