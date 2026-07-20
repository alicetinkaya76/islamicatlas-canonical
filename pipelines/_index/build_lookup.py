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
    python3 pipelines/_index/build_lookup.py [--rebuild] [--out PATH]

Idempotency (H22): a run WITHOUT --rebuild is now equivalent to a run WITH it.
Previously `label`/`label_fts` used a bare INSERT while the other four tables
used INSERT OR REPLACE, so every re-run appended a complete second copy of
every label row. Measured on the live index 2026-07-20: 635,257 label rows for
211,800 distinct (pid,lang,kind,text) tuples — i.e. three accumulated passes,
423,457 pure duplicate rows (~3x FTS bloat on the hot Tier-2 scoring path).
Labels are now cleared per-PID before re-insert, and rows whose PID no longer
has a file under data/canonical/ are pruned at the end of the walk (stale-row
GC — a deleted/superseded record used to keep its index rows forever).

NOT a phantom-PID source: this script only ever writes PIDs it read off disk.
The 1,615 phantoms in data/_state/phantom_pids_audit.json are pid_index.json
(mint-ledger) reservations; none of them has ever had a row here — verified
0/1615 across all five tables. See docs/PHASE0_CLOSEOUT.md §2.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

_PID_RE = re.compile(r"^iac:([a-z]+)-[0-9]{8}$")

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
-- H10 Stage 1: Tier-2 scoring fetches labels per candidate PID (~200/resolve);
-- without this index each fetch scanned all label rows (measured 467 ms/resolve).
CREATE INDEX IF NOT EXISTS label_pid_idx ON label(pid);

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


def prune_stale(conn: sqlite3.Connection, live_pids: set[str]) -> dict[str, int]:
    """Drop rows whose PID no longer has a canonical file on disk.

    Without this, a record that is deleted, merged away or superseded keeps its
    labels/bracket/CURIEs in the index forever, and only `--rebuild` clears
    them. Derivative index only — no source data is touched.
    """
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _live(pid TEXT PRIMARY KEY)")
    conn.execute("DELETE FROM _live")
    conn.executemany("INSERT OR IGNORE INTO _live(pid) VALUES (?)",
                     ((p,) for p in live_pids))
    removed: dict[str, int] = {}
    for table in ("authority_xref", "source_curie", "label", "entity_bracket"):
        cur = conn.execute(
            f"DELETE FROM {table} WHERE pid NOT IN (SELECT pid FROM _live)")
        if cur.rowcount > 0:
            removed[table] = cur.rowcount
    return removed


def rebuild_fts(conn: sqlite3.Connection) -> int:
    """Regenerate label_fts wholesale from the (already-correct) label table.

    label_fts declares `pid UNINDEXED`, so a per-PID `DELETE ... WHERE pid = ?`
    costs a full scan of the FTS content table — 67.8K of those made a re-run
    take >10 min (measured). One truncate + one bulk re-insert is O(n) and also
    repairs the drifted FTS row counts (multiplicities of 6 and 9 observed on
    the live index, where label showed 3), since the two tables were previously
    written by independent statements and could not be kept in step.
    """
    conn.execute("DELETE FROM label_fts")
    conn.execute("INSERT INTO label_fts(pid, text) SELECT pid, text FROM label")
    return conn.execute("SELECT COUNT(*) FROM label_fts").fetchone()[0]


def index_one(conn: sqlite3.Connection, record: dict) -> None:
    pid = record.get("@id")
    if not pid:
        return

    # Idempotency: `label` has no primary key, so a bare INSERT on a re-run
    # appends a duplicate copy of every row (measured 3x on the live index).
    # Clear this PID's label rows before re-inserting. Uses label_pid_idx, so
    # it is cheap. The other tables are INSERT OR REPLACE, already idempotent.
    # label_fts is NOT written here — it is regenerated from `label` in one
    # bulk pass at the end of the run (see rebuild_fts).
    conn.execute("DELETE FROM label WHERE pid = ?", (pid,))
    # entity_type from @id — authoritative per ADR-001 (H10 Stage 1 fix: the
    # old @type[0] read mis-bracketed the 768 subtype-first person records,
    # e.g. ["iac:Scholar","iac:Person"] → 'scholar' → invisible to Tier-2
    # blocking by entity_type='person'; same bug class as the H9 projector fix).
    m = _PID_RE.match(pid)
    if m:
        entity_type = m.group(1)
    else:
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
    for lang, arr in (labels.get("altLabel", {}) or {}).items():
        if isinstance(arr, list):
            for t in arr:
                conn.execute(
                    "INSERT INTO label(pid, lang, kind, text) VALUES (?, ?, 'alt', ?)",
                    (pid, lang, t),
                )
    for scheme, t in (labels.get("transliteration", {}) or {}).items():
        if isinstance(t, str):
            conn.execute(
                "INSERT INTO label(pid, lang, kind, text) VALUES (?, ?, 'translit', ?)",
                (pid, scheme, t),
            )

    # 4. entity_bracket
    coords = record.get("coords") or {}
    lat, lon = coords.get("lat"), coords.get("lon")
    # H10 Stage 1 fix: person records carry death_/floruit_/birth_temporal —
    # none of which the old list read, leaving every person bracket-less
    # (century blocking dead for 21,946 records). Death year is the primary
    # bracket for persons (ADR-008 §8.2 blocking key).
    temporal = (
        record.get("temporal")
        or record.get("temporal_coverage")
        or record.get("composition_temporal")
        or record.get("dating_temporal")
        or record.get("founded_temporal")   # institution (H11 S6, ADR-015)
        or record.get("death_temporal")
        or record.get("floruit_temporal")
        or record.get("birth_temporal")
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
    parser.add_argument("--out", type=Path, default=INDEX_PATH,
                        help="Write to an alternate index path (default: "
                             "data/_index/lookup.sqlite). Used to build a "
                             "shadow index for before/after comparison without "
                             "disturbing readers of the live one.")
    args = parser.parse_args()

    index_path = args.out
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if args.rebuild and index_path.exists():
        index_path.unlink()

    conn = sqlite3.connect(index_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    conn.commit()

    n = 0
    live_pids: set[str] = set()
    for path, record in iter_canonical():
        try:
            index_one(conn, record)
            pid = record.get("@id")
            if pid:
                live_pids.add(pid)
            n += 1
        except Exception as exc:
            print(f"  WARN: {path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)

    # Stale-row GC. Skipped after --rebuild (the file was just recreated) and
    # skipped if the walk produced nothing, so a mis-pointed CANONICAL_DIR can
    # never empty a good index.
    removed: dict[str, int] = {}
    if live_pids and not args.rebuild:
        removed = prune_stale(conn, live_pids)

    # FTS mirrors `label`; regenerate it after the walk and the prune so the
    # two can never drift (they did on the live index — see rebuild_fts).
    fts_rows = rebuild_fts(conn)
    conn.commit()

    if not args.quiet:
        print(f"Indexed {n} canonical records into {index_path}")
        if removed:
            print(f"  pruned stale rows (PID no longer on disk): {removed}")
        for table in ("authority_xref", "source_curie", "label", "entity_bracket", "decision_cache"):
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")
        print(f"  label_fts: {fts_rows} rows (regenerated from label)")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
