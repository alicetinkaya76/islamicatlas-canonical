#!/usr/bin/env python3
"""
dia_relations_edges.py — DİA hoca-talebe ağı → person.teachers/students
(H11 S11; data.zip dönüşümünün kenar ayağı).

dia_relations.json: ts 8,127 kenar [talebe_slug, hoca_slug, w] + co 3,390
çağdaşlık çifti. YÖN DÜZELTMESİ (H11 S11 doğrulama süpürmesi, KRİTİK):
v1 kodu DiaIdCard.jsx `[teacher, student]` diye AÇAR ama verinin kendisi
bunu çürütür — TÜM meşhur çiftlerde pozisyon-0 tarihsel TALEBEDİR:
[gazzali, cuveyni], [ebu-yusuf, ebu-hanife], [safii, malik-b-enes],
[ahmed-b-hanbel, safii], [buhari, ahmed-b-hanbel], [ibn-kayyim,
ibn-teymiyye], [sehavi, ibn-hacer], [watt, bell]. v1 SİTESİNİN KENDİSİ
yönü ters gösteriyormuş (H10 S11 dersi: popülasyon ölçümü nihai hakem;
kod adlandırması kanıt değildir). ts[0] = TALEBE, ts[1] = HOCA.

Uygulama (append-only, gap-fill):
  talebe.teachers += hoca_pid      hoca.students += talebe_pid
  (uniqueItems — mevcut girdi korunur, mükerrer eklenmez)

Gürültü doktrini:
  - öz-döngü (3) atlanır;
  - ÇİFT-YÖNLÜ ts çiftleri (a→b VE b→a; ~83) çelişkidir → İKİSİ DE
    uygulanmaz, conflict listesine düşer (yön kararı tarihçiye);
  - co (çağdaşlık) şemasız → contemporaries_pending (Faz 2).

Slug→pid: source_curie 'dia:<slug>' + 'dia-chunks:<slug>'.
Idempotent: teachers/students uniqueItems doğal koruma; history notu kayıt
başına bir kez (marker).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
MARKER = "dia-relations edges"


def main() -> int:
    rel = json.loads((REPO_ROOT / "data/sources/dia/dia_relations.json")
                     .read_text(encoding="utf-8"))
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
    slug_to_pid: dict[str, str] = {}
    for prefix in ("dia:", "dia-chunks:"):
        for sid, pid in conn.execute(
                "SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?",
                (prefix + "%",)):
            slug_to_pid.setdefault(sid.split(":", 1)[1], pid)
    conn.close()

    ts = rel["ts"]
    pair_set = {(a, b) for a, b, *_ in ts}
    conflicts = sorted({tuple(sorted((a, b))) for a, b, *_ in ts
                        if a != b and (b, a) in pair_set})
    conflict_set = set(conflicts)

    # pid başına eklenecek kenarlar
    add_teachers: dict[str, set] = defaultdict(set)
    add_students: dict[str, set] = defaultdict(set)
    stats = {"applied_edges": 0, "self_loop": 0, "conflict": 0,
             "unresolved": 0, "records_touched": 0}
    unresolved_slugs: set[str] = set()

    for a, b, *_ in ts:
        if a == b:
            stats["self_loop"] += 1
            continue
        if tuple(sorted((a, b))) in conflict_set:
            stats["conflict"] += 1
            continue
        pa, pb = slug_to_pid.get(a), slug_to_pid.get(b)
        if not pa or not pb:
            stats["unresolved"] += 1
            unresolved_slugs.update(s for s, p in ((a, pa), (b, pb)) if not p)
            continue
        add_teachers[pa].add(pb)   # a TALEBE → hocaları (yön: popülasyon kanıtı)
        add_students[pb].add(pa)   # b HOCA  → talebeleri
        stats["applied_edges"] += 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    touched_pids = sorted(set(add_teachers) | set(add_students))
    for pid in touched_pids:
        path = REPO_ROOT / "data/canonical/person" / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for field, additions in (("teachers", add_teachers.get(pid)),
                                 ("students", add_students.get(pid))):
            if not additions:
                continue
            cur = rec.get(field) or []
            new = [p for p in sorted(additions) if p not in cur]
            if new:
                rec[field] = cur + new
                changed = True
        if not changed:
            continue
        hist = rec.setdefault("provenance", {}).setdefault("record_history", [])
        if not any(MARKER in (h.get("note") or "") for h in hist):
            hist.append({
                "change_type": "update", "changed_at": now,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": f"{MARKER} (H11 S11 rev): teachers/students from "
                        f"dia_relations.json ts=[talebe,hoca] (yön popülasyon "
                        f"kanıtıyla düzeltildi; çift-yönlüler uygulanmadı).",
            })
        rec["provenance"]["modified"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        stats["records_touched"] += 1

    out = {
        "_doc": "dia_relations dönüşüm artıkları (H11 S11).",
        "direction_conflicts": [list(c) for c in conflicts],
        "unresolved_slugs": sorted(unresolved_slugs),
        "contemporaries_co": rel.get("co", []),
    }
    (REPO_ROOT / "data/_state/dia_relations_pending.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[dia_relations_edges] edges-applied={stats['applied_edges']} "
          f"records-touched={stats['records_touched']} "
          f"conflict-pairs={len(conflicts)} (kenar={stats['conflict']}) "
          f"self-loop={stats['self_loop']} unresolved={stats['unresolved']} "
          f"co-pending={len(rel.get('co', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
