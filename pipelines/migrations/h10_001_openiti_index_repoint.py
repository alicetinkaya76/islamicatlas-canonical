#!/usr/bin/env python3
"""
h10_001_openiti_index_repoint.py — openiti phantom sınıfının kök çözümü
(H10 Stage 9).

Teşhis (koddan doğrulandı): 1.167 `person:openiti:<oid>` index girdisi, H5'in
İLK geçişinde mint edilmiş ama aynı koşuda Tier-2 eşleşmesine çözülünce HİÇ
YAZILMAMIŞ pid'lere işaret ediyor. Varlıklar `openiti_author_resolution.json`
map_pid'lerinde yaşıyor; 9.331 work kaydının HİÇBİRİ phantom'lara referans
vermiyor (tarandı). Tek tutarsızlık index'in kendisi: gelecekte
`lookup("person", "openiti:<oid>")` çağıran her kod YANLIŞ (kayıtsız) pid alır.

Onarım (idempotent): her phantom girdi, resolution map'in pid'ine REPOINT
edilir. pid_counter DOKUNULMAZ (ordinal delikleri kalır — belgeli); hiçbir
canonical kayıt değişmez. Doğrulama: repoint sonrası person:openiti:* phantom
sayısı 0 olmalı ve her girdinin pid'i diskte kayıtlı olmalı.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import PidMinter  # noqa: E402

PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"


def _exists(pid: str) -> bool:
    return (PERSON_DIR / f"iac_person_{pid.rsplit('-', 1)[1]}.json").exists()


def main() -> int:
    res = json.loads((REPO_ROOT / "data/_state/openiti_author_resolution.json")
                     .read_text(encoding="utf-8"))
    minter = PidMinter(REPO_ROOT / "data" / "_state")

    with minter._exclusive_lock():
        index = minter._load_index()
        n_repointed = n_ok = n_unfixable = 0
        for key, pid in list(index.items()):
            if not key.startswith("person:openiti:"):
                continue
            if _exists(pid):
                n_ok += 1
                continue
            oid = key.split(":", 2)[2]
            target = (res.get(oid) or {}).get("pid")
            if target and _exists(target):
                index[key] = target
                n_repointed += 1
            else:
                n_unfixable += 1
                print(f"  WARN unfixable: {key} → {pid} (map: {target})")
        if n_repointed:
            minter._save_index(index)

    # verify
    index = json.loads((REPO_ROOT / "data/_state/pid_index.json").read_text(encoding="utf-8"))
    still = [k for k, p in index.items()
             if k.startswith("person:openiti:") and not _exists(p)]
    print(f"[h10_001] repointed={n_repointed} already-ok={n_ok} "
          f"unfixable={n_unfixable} | verify: kalan openiti-phantom={len(still)}")
    return 0 if not still and n_unfixable == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
