"""
extract.py — Cat A filter + per-slug aggregation for dia_person_enrichment_v8.

Reads dia_chunks.json (19,742 chunks) and data/_state/dia_slug_to_pid.json
(envelope structure: .slug_to_pid). Filters chunks to slugs in slug_to_pid
(Cat A), aggregates per slug via dia_enrichment_lib.aggregate_chunks_by_slug
(matches H4 adapter's join semantics), yields one record per Cat A slug.

Yields dicts with shape:
    {
        "source_record_id": "<slug>",
        "raw_data": {
            "slug": "<slug>",
            "resolved_pid": "iac:person-NNNNNNNN",
            "n_chunks": int,
            "t_total": str,           # space-joined narrative
            "primary_n": str,         # uppercase Turkish title
            "primary_a": str,         # Arabic-script title (may be empty)
            "primary_d": str,         # death-paren raw string (may be empty)
            "primary_sec": str,       # section marker (rare; may be empty)
        }
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

# Hoist _lib (mirror le-strange / other adapters' pattern)
_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "_lib"
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib.dia_enrichment_lib import aggregate_chunks_by_slug  # noqa: E402


def _repo_root_from(chunks_path: Path) -> Path:
    """Derive repo root from data/sources/dia_chunks.json path."""
    return chunks_path.parent.parent.parent


def _load_slug_to_pid(repo_root: Path) -> dict[str, str]:
    """Load slug→PID map from data/_state/dia_slug_to_pid.json envelope."""
    path = repo_root / "data" / "_state" / "dia_slug_to_pid.json"
    if not path.exists():
        print(
            f"[extract] WARN: {path.relative_to(repo_root)} not found; "
            f"yielding zero records (Stage 3 cannot resolve PIDs).",
            file=sys.stderr,
        )
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    s2p = data.get("slug_to_pid")
    if not isinstance(s2p, dict):
        print(
            f"[extract] WARN: {path.name} has no .slug_to_pid dict; "
            f"envelope structure changed?",
            file=sys.stderr,
        )
        return {}
    return s2p


def extract(input_paths: list[Path]) -> Iterator[dict]:
    chunks_path = next(p for p in input_paths if p.name == "dia_chunks.json")
    repo_root = _repo_root_from(chunks_path)

    print(
        f"[extract] loading {chunks_path.name} "
        f"({chunks_path.stat().st_size // (1024 * 1024)} MB)..."
    )
    with chunks_path.open(encoding="utf-8") as fh:
        chunks = json.load(fh)
    print(f"[extract] {len(chunks):,} chunks loaded.")

    slug_to_pid = _load_slug_to_pid(repo_root)
    print(f"[extract] {len(slug_to_pid):,} slug\u2192PID mappings loaded.")

    aggregated = aggregate_chunks_by_slug(chunks)
    print(f"[extract] {len(aggregated):,} distinct slugs aggregated.")

    n_cat_a = 0
    n_cat_bc = 0
    for slug in sorted(aggregated):
        agg = aggregated[slug]
        pid = slug_to_pid.get(slug)
        if not pid:
            n_cat_bc += 1
            continue
        n_cat_a += 1
        yield {
            "source_record_id": slug,
            "raw_data": {
                "slug": slug,
                "resolved_pid": pid,
                **agg,
            },
        }

    print(
        f"[extract] yielded {n_cat_a:,} Cat A records; "
        f"skipped {n_cat_bc:,} Cat B/C slugs (deferred per ADR-011 v1.1)."
    )
