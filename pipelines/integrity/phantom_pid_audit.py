#!/usr/bin/env python3
"""
phantom_pid_audit.py — pid_index'te olup diskte kaydı olmayan PID'lerin
denetim sidecar'ı (PHASE0_CLOSEOUT §2). SALT-OKUR; index temizliği ayrı,
journal'lı bir karardır (ordinal determinizmi + rezerve-PID kategorisi).

Çıktı: data/_state/phantom_pids_audit.json — namespace+önek kırılımı,
bilinen sınıf etiketleri (dia/el-alam mint-before-skip; darp review-rezerv;
openiti = H5 yazar-placeholder kısmî yazımı — teşhis notuyla).

Usage: python3 pipelines/integrity/phantom_pid_audit.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "data" / "_state" / "phantom_pids_audit.json"

KNOWN = {
    "person:dia:": "mint-before-temporal-skip (H9 S3'te ileri-dönük düzeltildi)",
    "person:el-alam:": "Track-B mint-before-skip (H9 S3-ek'te düzeltildi)",
    "person:openiti:": ("H5 yazar-placeholder mint'lerinin kısmî yazımı — "
                        "records yalnız bir alt küme için diske indi; "
                        "yeniden-üretim AP-öncesi ayrı onarım"),
    "place:darp-islam:": "pilot→review rezerve PID (test_i'de belgeli-mazur)",
}


def main() -> int:
    idx = json.loads((REPO_ROOT / "data/_state/pid_index.json").read_text(encoding="utf-8"))
    phantoms: dict[str, list] = {}
    by_prefix: Counter = Counter()
    for key, pid in idx.items():
        ns = key.split(":", 1)[0]
        path = (REPO_ROOT / "data" / "canonical" / ns /
                f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json")
        if path.exists():
            continue
        prefix = ":".join(key.split(":", 2)[:2]) + ":"
        by_prefix[prefix] += 1
        phantoms.setdefault(prefix, []).append(key)

    OUT.write_text(json.dumps({
        "_meta": {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "total": sum(by_prefix.values()),
                  "by_prefix": dict(by_prefix.most_common()),
                  "known_classes": KNOWN,
                  "policy": ("index temizliği YAPILMAZ (ordinal determinizmi; "
                             "rezerve kategorisi); tüketiciler disk-doğrulamalı "
                             "lookup kullanır (el_alam guard deseni)")},
        "phantoms": {k: sorted(v) for k, v in phantoms.items()},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[phantom_audit] total={sum(by_prefix.values())} by_prefix={dict(by_prefix.most_common())}")
    print(f"[phantom_audit] → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
