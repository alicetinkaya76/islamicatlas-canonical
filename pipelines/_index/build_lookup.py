"""
build_lookup.py — Build / rebuild the canonical-store reverse-lookup index.

Walks data/canonical/<namespace>/*.json, populates data/_index/lookup.sqlite
with five tables (see ADR-008 §8.3):
    authority_xref      — (authority, authority_id) → pid
    source_curie        — source_id → pid (from provenance.derived_from CURIEs)
    label               — pid, lang, kind, text  (+FTS5 virtual table)
    entity_bracket      — pid → century/iqlim/lat/lon for blocking
    decision_cache      — (adapter_id, extracted_record_id) → decision

Usage:
    python3 pipelines/_index/build_lookup.py [--rebuild]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_DIR = REPO_ROOT / "data" / "canonical"
INDEX_PATH = REPO_ROOT / "data" / "_index" / "lookup.sqlite"


SCHEMA = """
CREATE TABLE IF NOT EXISTS authority_xref (
  authority TEXT NOT NULL,
  authority_id TEXT NOT NULL,
  pid TEXT NOT NULL,
  PRIMARY KEY (authority, authority_id)
);

CREATE TABLE IF NOT EXISTS source_curie (
  source_id TEXT PRIMARY KEY,
  pid TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS label (
  pid TEXT NOT NULL,
  lang TEXT NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS label_text_idx ON label(text);

CREATE VIRTUAL TABLE IF NOT EXISTS label_fts USING fts5(pid UNINDEXED, text);

CREATE TABLE IF NOT EXISTS entity_bracket (
  pid TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  century_ce_bucket INTEGER,
  iqlim TEXT,
  lat REAL, lon REAL,
  start_year_ce INTEGER, end_year_ce INTEGER
);
CREATE INDEX IF NOT EXISTS entity_bracket_blocking_idx
  ON entity_bracket(entity_type, century_ce_bucket, iqlim);

CREATE TABLE IF NOT EXISTS decision_cache (
  adapter_id TEXT NOT NULL,
  extracted_record_id TEXT NOT NULL,
  decision_kind TEXT NOT NULL,
  matched_pid TEXT,
  confidence REAL,
  decided_at TEXT NOT NULL,
  PRIMARY KEY (adapter_id, extracted_record_id)
);
"""


def iter_canonical() -> Iterable[tuple[Path, dict]]:
    if not CANONICAL_DIR.exists():
        return
    for ns_dir in sorted(CANONICAL_DIR.iterdir()):
        if not ns_dir.is_dir():
            continue
        for path in sorted(ns_dir.glob("*.json")):
            with path.open(encoding="utf-8") as fh:
                yield path, json.load(fh)


def index_one(conn: sqlite3.Connection, record: dict) -> None:
    pid = record.get("@id")
    if not pid:
        return
    types = record.get("@type") or []
    entity_type = types[0].split(":", 1)[-1].lower() if types else "unknown"

    # 1. authority_xref
    for x in record.get("authority_xref", []) or []:
        a, aid = x.get("authority"), x.get("id")
        if a and aid:
            conn.execute(
                "INSERT OR REPLACE INTO authority_xref(authority, authority_id, pid) VALUES (?, ?, ?)",
                (a, aid, pid),
            )

    # 2. source_curie
    for entry in (record.get("provenance", {}).get("derived_from") or []):
        sid = entry.get("source_id")
        if sid:
            conn.execute(
                "INSERT OR REPLACE INTO source_curie(source_id, pid) VALUES (?, ?)",
                (sid, pid),
            )

    # 3. labels (prefLabel + altLabel + transliteration)
    labels = record.get("labels", {}) or {}
    for lang, text in (labels.get("prefLabel", {}) or {}).items():
        conn.execute(
            "INSERT INTO label(pid, lang, kind, text) VALUES (?, ?, 'pref', ?)",
            (pid, lang, text),
        )
        conn.execute("INSERT INTO label_fts(pid, text) VALUES (?, ?)", (pid, text))
    for lang, arr in (labels.get("altLabel", {}) or {}).items():
        if isinstance(arr, list):
            for t in arr:
                conn.execute(
                    "INSERT INTO label(pid, lang, kind, text) VALUES (?, ?, 'alt', ?)",
                    (pid, lang, t),
                )
                conn.execute("INSERT INTO label_fts(pid, text) VALUES (?, ?)", (pid, t))
    for scheme, t in (labels.get("transliteration", {}) or {}).items():
        if isinstance(t, str):
            conn.execute(
                "INSERT INTO label(pid, lang, kind, text) VALUES (?, ?, 'translit', ?)",
                (pid, scheme, t),
            )
            conn.execute("INSERT INTO label_fts(pid, text) VALUES (?, ?)", (pid, t))

    # 4. entity_bracket
    coords = record.get("coords") or {}
    lat, lon = coords.get("lat"), coords.get("lon")
    temporal = (
        record.get("temporal")
        or record.get("temporal_coverage")
        or record.get("composition_temporal")
        or record.get("dating_temporal")
        or {}
    )
    start_ce = temporal.get("start_ce")
    end_ce = temporal.get("end_ce")
    century_bucket = (start_ce // 100 * 100) if isinstance(start_ce, int) else None
    iqlim = None
    falls = record.get("falls_within_iqlim") or []
    if isinstance(falls, list) and falls:
        iqlim = falls[0]
    conn.execute(
        """
        INSERT OR REPLACE INTO entity_bracket
          (pid, entity_type, century_ce_bucket, iqlim, lat, lon, start_year_ce, end_year_ce)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (pid, entity_type, century_bucket, iqlim, lat, lon, start_ce, end_ce),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="Drop tables and rebuild from scratch.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.rebuild and INDEX_PATH.exists():
        INDEX_PATH.unlink()

    conn = sqlite3.connect(INDEX_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    conn.commit()

    n = 0
    for path, record in iter_canonical():
        try:
            index_one(conn, record)
            n += 1
        except Exception as exc:
            print(f"  WARN: {path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
    conn.commit()

    if not args.quiet:
        print(f"Indexed {n} canonical records into {INDEX_PATH.relative_to(REPO_ROOT)}")
        for table in ("authority_xref", "source_curie", "label", "entity_bracket", "decision_cache"):
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
