"""
review_queue/cli.py — Interactive resolution-decision review tool.

Reads pending review entries from data/review_queue/<adapter_id>.jsonl,
shows each one to the maintainer with candidate alternatives, captures
the decision, and appends to data/review_decisions.jsonl. The adapter's
next run picks up these decisions from the cache and applies them.

Usage:
    python3 pipelines/review_queue/cli.py --adapter dia
    python3 pipelines/review_queue/cli.py --adapter dia --limit 50
    python3 pipelines/review_queue/cli.py --adapter dia --skip-decided
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE_DIR = REPO_ROOT / "data" / "review_queue"
DECISIONS_PATH = REPO_ROOT / "data" / "review_decisions.jsonl"
INDEX_PATH = REPO_ROOT / "data" / "_index" / "lookup.sqlite"


def load_decided_queue_ids() -> set[str]:
    if not DECISIONS_PATH.exists():
        return set()
    decided = set()
    with DECISIONS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    decided.add(json.loads(line)["queue_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return decided


def fetch_pid_summary(conn: sqlite3.Connection | None, pid: str) -> dict:
    """Return labels + entity_type + temporal bracket for display."""
    if conn is None:
        return {}
    summary: dict = {"pid": pid}
    row = conn.execute(
        "SELECT entity_type, century_ce_bucket, iqlim, start_year_ce, end_year_ce "
        "FROM entity_bracket WHERE pid = ?",
        (pid,),
    ).fetchone()
    if row:
        summary["entity_type"] = row[0]
        summary["century_bucket"] = row[1]
        summary["iqlim"] = row[2]
        summary["start_ce"] = row[3]
        summary["end_ce"] = row[4]
    rows = conn.execute(
        "SELECT lang, text FROM label WHERE pid = ? AND kind = 'pref'", (pid,)
    ).fetchall()
    summary["prefLabels"] = {lang: text for lang, text in rows}
    return summary


def display_entry(entry: dict, conn: sqlite3.Connection | None) -> None:
    print()
    print("=" * 78)
    print(f"queue_id           : {entry.get('queue_id')}")
    print(f"adapter            : {entry.get('adapter_id')}")
    print(f"extracted_record_id: {entry.get('extracted_record_id')}")
    print(f"deferred_at        : {entry.get('deferred_at')}")
    print()
    print("--- Extracted record summary ---")
    summary = entry.get("extracted_summary", {}) or {}
    if "labels" in summary and summary["labels"]:
        pref = (summary["labels"].get("prefLabel") or {})
        for lang, text in pref.items():
            print(f"  prefLabel.{lang}: {text}")
    if "temporal" in summary and summary["temporal"]:
        t = summary["temporal"]
        print(f"  temporal: start_ce={t.get('start_ce')}, end_ce={t.get('end_ce')}, "
              f"start_ah={t.get('start_ah')}, end_ah={t.get('end_ah')}")
    if "coords" in summary and summary["coords"]:
        c = summary["coords"]
        print(f"  coords: lat={c.get('lat')}, lon={c.get('lon')}")
    print()
    print("--- Candidates ---")
    candidates = entry.get("candidates", []) or []
    for i, cand in enumerate(candidates):
        letter = chr(ord("a") + i)
        info = fetch_pid_summary(conn, cand["pid"])
        labels_str = ", ".join(f"{l}={t}" for l, t in (info.get("prefLabels") or {}).items())
        print(f"  [{letter}] {cand['pid']:<28} score={cand['score']:.2f}  {labels_str}")
        feat = cand.get("feature_scores") or {}
        if feat:
            feat_str = ", ".join(f"{k}={v:.2f}" for k, v in feat.items())
            print(f"        features: {feat_str}")
    print(f"  [n] new entity (mint new PID)")
    print(f"  [s] skip (decide later)")


def write_decision(decision: dict) -> None:
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECISIONS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(decision, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, help="Adapter ID (matches data/review_queue/<id>.jsonl)")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N decisions (0 = all).")
    parser.add_argument("--skip-decided", action="store_true",
                        help="Skip queue entries already decided in review_decisions.jsonl.")
    args = parser.parse_args()

    queue_path = QUEUE_DIR / f"{args.adapter}.jsonl"
    if not queue_path.exists():
        print(f"No review queue for adapter '{args.adapter}' (expected: {queue_path})")
        return 0

    decided = load_decided_queue_ids() if args.skip_decided else set()
    conn = sqlite3.connect(INDEX_PATH) if INDEX_PATH.exists() else None

    n_processed = 0
    with queue_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("queue_id") in decided:
                continue
            if args.limit and n_processed >= args.limit:
                break

            display_entry(entry, conn)
            print()

            while True:
                choice = input("Choice [a-z/n/s/q to quit]: ").strip().lower()
                if not choice:
                    continue
                if choice == "q":
                    print("Bye.")
                    if conn: conn.close()
                    return 0
                if choice == "s":
                    print("  → skipped")
                    break
                if choice == "n":
                    note = input("Note (optional): ").strip()
                    write_decision({
                        "queue_id": entry["queue_id"],
                        "decision": "new",
                        "matched_pid": None,
                        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                        "decided_by": "https://orcid.org/0000-0002-7747-6854",
                        "note": note,
                    })
                    print("  → new entity")
                    n_processed += 1
                    break
                # candidate letter
                idx = ord(choice) - ord("a")
                cands = entry.get("candidates", []) or []
                if 0 <= idx < len(cands):
                    matched_pid = cands[idx]["pid"]
                    note = input("Note (optional): ").strip()
                    write_decision({
                        "queue_id": entry["queue_id"],
                        "decision": "match",
                        "matched_pid": matched_pid,
                        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                        "decided_by": "https://orcid.org/0000-0002-7747-6854",
                        "note": note,
                    })
                    print(f"  → match {matched_pid}")
                    n_processed += 1
                    break
                print("  ?")

    if conn: conn.close()
    print()
    print(f"Reviewed {n_processed} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
