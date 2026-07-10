#!/usr/bin/env python3
"""
dedup_scan_persons.py — person store'unun kendine-karşı Tier-2 taraması
(H10 Karar 3'ün işi): H4-H5 seed'lerinin (Tier-2'siz dönem) bıraktığı
çapraz-kaynak dublör adaylarını çıkarır. STORE'A YAZMAZ — çıktı:
data/_state/person_dedup_candidates.json (pair'ler skor+kanıtla) →
tarihçi onayı; merge ADR-008 Tier-3 insan kararıdır.

Aday kriteri: kayıt kendi-dışı bir PID'e ≥0.95 skor + çift-sinyal (Tier-2'nin
auto-match bandı) veriyorsa (A,B) çifti adaydır. Çiftler normalize edilir
(A<B), tek sefer raporlanır.

Usage: python3 pipelines/integrity/dedup_scan_persons.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402

OUT = REPO_ROOT / "data" / "_state" / "person_dedup_candidates.json"
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    resolver = EntityResolver(REPO_ROOT)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing.")
    weights = (resolver._weights or {}).get("person", {})
    auto_thr = float(weights.get("auto_accept_threshold", 0.95))

    paths = sorted(PERSON_DIR.glob("iac_person_*.json"))
    if args.limit:
        paths = paths[:args.limit]
    pairs: dict[str, dict] = {}
    n = 0
    for path in paths:
        rec = json.loads(path.read_text(encoding="utf-8"))
        pid = rec["@id"]
        labels = rec.get("labels") or {}
        temporal = rec.get("death_temporal") or rec.get("floruit_temporal") \
            or rec.get("birth_temporal") or {}
        q_t = {"start_ce": temporal["start_ce"]} if isinstance(
            temporal.get("start_ce"), int) else {}
        d = resolver._tier2_blocking_similarity(
            entity_type="person", labels=labels, temporal=q_t,
            coords={}, nisba=rec.get("nisba") or [], kunya=rec.get("kunya"))
        for c in d.candidates:
            if c.pid == pid or c.score < auto_thr:
                continue
            if int(c.feature_scores.get("n_features", 1)) < 2:
                continue
            key = "|".join(sorted((pid, c.pid)))
            if key not in pairs:
                pairs[key] = {"a": min(pid, c.pid), "b": max(pid, c.pid),
                              "score": c.score,
                              "label": next(iter((labels.get("prefLabel") or {}).values()), "?")}
        n += 1
        if n % 2000 == 0:
            print(f"  {n}/{len(paths)} tarandı; aday çift: {len(pairs)}")

    resolver.close()
    OUT.write_text(json.dumps({
        "_meta": {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "scanned": n, "candidate_pairs": len(pairs),
                  "threshold": auto_thr,
                  "policy": "merge = insan kararı (ADR-008 Tier-3); bu dosya salt aday listesi"},
        "pairs": sorted(pairs.values(), key=lambda p: -p["score"]),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[dedup_scan] scanned={n} candidate_pairs={len(pairs)} → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
