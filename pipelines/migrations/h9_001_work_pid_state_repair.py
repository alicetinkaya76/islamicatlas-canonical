#!/usr/bin/env python3
"""
h9_001_work_pid_state_repair.py — one-time repair of the work-namespace PID
state drift discovered by the H9 Stage 3 review.

Drift (measured 2026-07-07):
    pid_counter.work            9330
    pid_index work:* entries    9330 (max ordinal 9330)
    on-disk work records        9331 — iac_work_00009331.json exists

iac:work-00009331 is the H6 Stream-1 one-off rich mint (al-Khaṣṣāf, Kitāb
al-Ḥiyal; commit 564f1c8) whose PID was hand-assigned WITHOUT going through
PidMinter, so neither the counter nor the index ever learned about it. The
next work mint (AP dia_works, H10+) would re-allocate iac:work-00009331 and
OVERWRITE the Hassâf record.

Repair (idempotent):
    1. pid_index  += {"work:<source_id of the record>": "iac:work-00009331"}
       — key derives from provenance.derived_from[0].source_id
       ("tdv_dia:hassaf:title_2"), mirroring the "<namespace>:<source-CURIE>"
       convention every adapter uses.
    2. pid_counter.work = max(counter, 9331) so ordinal 9331 is never reissued.

Verification: counter == index-max == on-disk count == 9331, and the guard
test tests/integration/test_work_pilot.py::test_b2_pid_index_consistent
(un-xfail'ed in the same commit) keeps this class of drift red forever.

No canonical record is touched — this edits only data/_state (gitignored,
regenerable state), consistent with h8_001/h8_002's "state evidence" pattern.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import PidMinter  # noqa: E402

HASSAF_PID = "iac:work-00009331"
HASSAF_ORDINAL = 9331


def main() -> int:
    state_dir = REPO_ROOT / "data" / "_state"
    record_path = REPO_ROOT / "data" / "canonical" / "work" / "iac_work_00009331.json"
    if not record_path.exists():
        print("[h9_001] iac_work_00009331.json not found — nothing to repair "
              "(fresh clone without canonical store?). Exiting 0.")
        return 0

    with record_path.open(encoding="utf-8") as fh:
        record = json.load(fh)
    source_id = record["provenance"]["derived_from"][0]["source_id"]
    index_key = f"work:{source_id}"

    minter = PidMinter(state_dir)
    with minter._exclusive_lock():
        counter = minter._load_counter()
        index = minter._load_index()

        changed = False
        existing = index.get(index_key)
        if existing is None:
            index[index_key] = HASSAF_PID
            changed = True
            print(f"[h9_001] index += {index_key!r} -> {HASSAF_PID}")
        elif existing != HASSAF_PID:
            print(f"[h9_001] ERROR: {index_key!r} already maps to {existing!r} "
                  f"(expected {HASSAF_PID}). Refusing to overwrite.", file=sys.stderr)
            return 1
        else:
            print(f"[h9_001] index entry already present (idempotent no-op).")

        if counter.get("work", 0) < HASSAF_ORDINAL:
            print(f"[h9_001] counter.work {counter.get('work')} -> {HASSAF_ORDINAL}")
            counter["work"] = HASSAF_ORDINAL
            changed = True
        else:
            print(f"[h9_001] counter.work already >= {HASSAF_ORDINAL} (idempotent no-op).")

        if changed:
            minter._save_counter(counter)
            minter._save_index(index)

    # ---- verification ----------------------------------------------------
    # Idempotent ALSO after later mints (review catch): assert the repair's
    # own invariants (hassaf indexed, ordinal fenced), not a frozen snapshot —
    # a strict ==9331 check would start failing the moment AP mints work 9332.
    counter = json.loads((state_dir / "pid_counter.json").read_text())
    index = json.loads((state_dir / "pid_index.json").read_text())
    work_pids = {v for k, v in index.items() if k.startswith("work:")}
    ondisk = len(list((REPO_ROOT / "data" / "canonical" / "work").glob("iac_work_*.json")))
    ok = counter["work"] >= HASSAF_ORDINAL and HASSAF_PID in work_pids
    print(f"[h9_001] verify: counter.work={counter['work']} (>= {HASSAF_ORDINAL}) "
          f"indexed={len(work_pids)} on-disk={ondisk} "
          f"hassaf-indexed={HASSAF_PID in work_pids} -> {'OK' if ok else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
