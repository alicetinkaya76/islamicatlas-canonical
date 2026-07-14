#!/usr/bin/env python3
"""
h11_002 — dia_relations ts-yön düzeltmesi: YANLIŞ yönle uygulanmış 7,965
kenarın geri alınması (H11 S11 doğrulama süpürmesi, KRİTİK bulgu).

Eski koşu ts=[a,b]'yi [hoca,talebe] sandı; popülasyon kanıtı [talebe,hoca]
gösterdi. Bu migrasyon eski algoritmanın ürettiği kümeleri AYNEN yeniden
hesaplar ve alanlardan çıkarır; eski marker notunu düşürür. Ardından
düzeltilmiş dia_relations_edges.py taze koşulur.

Koruma: çıkarılan pid, doğru-yön kümesinde de varsa (karşılıklı çift —
teorik olarak çift-yönlü elemesi yüzünden boş olmalı) raporlanır; başka
katmandan gelmiş olup tesadüfen çakışan girdi sayısı da raporlanır.
"""
import json, sqlite3, sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
rel = json.loads((REPO_ROOT / "data/sources/dia/dia_relations.json").read_text(encoding="utf-8"))
conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
slug_to_pid = {}
for prefix in ("dia:", "dia-chunks:"):
    for sid, pid in conn.execute("SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?", (prefix + "%",)):
        slug_to_pid.setdefault(sid.split(":", 1)[1], pid)
conn.close()

ts = rel["ts"]
pair_set = {(a, b) for a, b, *_ in ts}
conflict_set = {tuple(sorted((a, b))) for a, b, *_ in ts if a != b and (b, a) in pair_set}

wrong_teachers, wrong_students = defaultdict(set), defaultdict(set)
corr_teachers, corr_students = defaultdict(set), defaultdict(set)
for a, b, *_ in ts:
    if a == b or tuple(sorted((a, b))) in conflict_set:
        continue
    pa, pb = slug_to_pid.get(a), slug_to_pid.get(b)
    if not pa or not pb:
        continue
    wrong_students[pa].add(pb); wrong_teachers[pb].add(pa)   # eski (hatalı) yön
    corr_teachers[pa].add(pb);  corr_students[pb].add(pa)    # doğru yön

MARKER = "dia-relations edges"
stats = {"records": 0, "removed": 0, "kept_would_readd": 0}
for pid in sorted(set(wrong_teachers) | set(wrong_students)):
    path = REPO_ROOT / "data/canonical/person" / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for field, wrong, corr in (("teachers", wrong_teachers.get(pid, set()), corr_teachers.get(pid, set())),
                               ("students", wrong_students.get(pid, set()), corr_students.get(pid, set()))):
        cur = rec.get(field) or []
        keep = [p for p in cur if p not in wrong]
        stats["removed"] += len(cur) - len(keep)
        stats["kept_would_readd"] += len([p for p in cur if p in wrong and p in corr])
        if keep != cur:
            changed = True
            if keep:
                rec[field] = keep
            else:
                rec.pop(field, None)
    hist = rec.get("provenance", {}).get("record_history", [])
    new_hist = [h for h in hist if not ((h.get("note") or "").startswith(MARKER)
                                        and "rev" not in (h.get("note") or ""))]
    if len(new_hist) != len(hist):
        rec["provenance"]["record_history"] = new_hist
        changed = True
    if changed:
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stats["records"] += 1
print(f"[h11_002] reverted: records={stats['records']} removed-entries={stats['removed']} "
      f"wrong∩correct(çift-yön kalıntısı, beklenen 0)={stats['kept_would_readd']}")
