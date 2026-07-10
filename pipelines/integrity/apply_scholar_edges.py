#!/usr/bin/env python3
"""
apply_scholar_edges.py — scholars Stage-3b: hoca-talebe kenarlarının
uygulanabilir alt kümesi (H10 Stage 13).

scholar_links (163 kenar; teacher/influence/isnad/debate) + scholars
adapter'ının `_id_to_pid` haritası (46 eşlenmiş âlim):
  * type=teacher VE iki ucu eşli → person.teachers[]/students[] gap-append
    (şema alanları; yön: source=hoca → target=talebe; künye örneklemiyle
    doğrulandı: Mâlik→Şâfiî→Ahmed b. Hanbel).
  * Geri kalan HER kenar data/_state/scholar_edges_pending.json'a — 252
    yetim kart (db.json) gelince ve/veya P1 graf katmanında işlenir.
İdempotent: pid zaten listedeyse dokunulmaz; history yalnız değişince yazılır.

Usage: python3 pipelines/integrity/apply_scholar_edges.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
PENDING = REPO_ROOT / "data" / "_state" / "scholar_edges_pending.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"


def _load(pid):
    p = PERSON_DIR / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
    return (p, json.loads(p.read_text(encoding="utf-8"))) if p.exists() else (p, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    conv = json.loads((REPO_ROOT / "data/sources/scholars/scholars_converted.json")
                      .read_text(encoding="utf-8"))
    side = json.loads((REPO_ROOT / "data/_state/scholars_augment_pending.json")
                      .read_text(encoding="utf-8"))
    i2p = side.get("_id_to_pid", {})

    applied = 0
    pending = []
    touched: dict[str, dict] = {}

    for link in conv.get("links", []):
        s, t, typ = str(link.get("source")), str(link.get("target")), link.get("type")
        if typ == "teacher" and s in i2p and t in i2p:
            t_pid, s_pid = i2p[s], i2p[t]   # source=hoca, target=talebe
            teacher_pid, student_pid = i2p[s], i2p[t]
            _, srec = touched.get(student_pid, (None, None)) if False else (None, None)
            spath, srec = _load(student_pid)
            tpath, trec = _load(teacher_pid)
            if not srec or not trec:
                pending.append({**link, "reason": "record-missing"})
                continue
            changed = False
            st = list(srec.get("teachers") or [])
            if teacher_pid not in st:
                st.append(teacher_pid)
                srec["teachers"] = st
                changed = True
            ts = list(trec.get("students") or [])
            if student_pid not in ts:
                ts.append(student_pid)
                trec["students"] = ts
                changed = True
            if changed:
                for rec, path, other, field in ((srec, spath, teacher_pid, "teachers"),
                                                (trec, tpath, student_pid, "students")):
                    rec.setdefault("provenance", {}).setdefault("record_history", []).append({
                        "change_type": "update", "changed_at": now,
                        "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                        "note": f"scholar_links teacher edge (H10 S13): {field} += {other}.",
                    })
                    rec["provenance"]["modified"] = now
                    if not args.dry_run:
                        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
                applied += 1
        else:
            pending.append({**link,
                            "reason": ("type-no-schema-field" if typ != "teacher"
                                       else "endpoint-unmapped (db.json bekliyor)")})

    isnad = conv.get("isnad_chains", [])
    if not args.dry_run:
        PENDING.write_text(json.dumps({
            "_meta": {"run_at": now, "applied_teacher_edges": applied,
                      "pending_edges": len(pending), "isnad_chains": len(isnad),
                      "note": "252 yetim kart (v1 db.json) gelince + P1 graf katmanında işlenir"},
            "pending": pending, "isnad_chains": isnad,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"[scholar_edges] applied={applied} pending={len(pending)} "
          f"isnad-chains={len(isnad)}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
