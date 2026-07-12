#!/usr/bin/env python3
"""
repair_el_alam_lost.py — H9 Stage 3 el_alam Track-A fix'inin veri onarımı:
mint-yerine-lookup + disk-guard sonrası Track-B'ye düşen (eski kodda augment
sidecar'ına gömülüp KAYBOLAN) Ziriklī kişilerini hedefli mint eder.

TAM re-run BİLİNÇLİ yapılmıyor: `run_adapter --id el-alam` 12.5K mevcut
kaydı taze timestamp'lerle yeniden yazar (provenance.created gerçeğini
bozar). Bu script extract'i filtreler: yalnız "dia_slug'lu ama canonical
kaydı diskte olmayan" alam kayıtları canonicalize'a girer (~22 kayıt; 1'i
temporal-skip → ~21 mint). İdempotent: kayıt diske gelince aday kümesi boşalır.

Usage: python3 pipelines/integrity/repair_el_alam_lost.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

from pipelines._lib.pid_minter import PidMinter, filename_for_pid  # noqa: E402
from pipelines.adapters.el_alam import extract as ex  # noqa: E402
from pipelines.adapters.el_alam import canonicalize as cz  # noqa: E402

PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"


def _validator():
    reg = Registry()
    for sp in (REPO_ROOT / "schemas").rglob("*.schema.json"):
        s = json.loads(sp.read_text(encoding="utf-8"))
        if s.get("$id"):
            reg = reg.with_resource(uri=s["$id"], resource=Resource.from_contents(s))
    target = json.loads((REPO_ROOT / "schemas/person.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(target, registry=reg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    minter = PidMinter(REPO_ROOT / "data" / "_state")
    inputs = [REPO_ROOT / "data/sources/alam_lite.json",
              REPO_ROOT / "data/sources/dia_alam_xref.json",
              REPO_ROOT / "data/sources/yaqut_alam_crossref_enriched.json"]

    def losts():
        for rec in ex.extract(inputs):
            slug = rec.get("dia_slug")  # el_alam H4-era shape: flat, not raw_data-wrapped
            if not slug:
                continue
            pid = minter.lookup("person", f"dia:{slug}")
            if pid and (PERSON_DIR / filename_for_pid(pid)).exists():
                continue  # gerçek Track A — dokunma
            yield rec    # kayıp sınıf: Track B'ye düşecek

    options = {"strict_mode": True, "namespace": "person",
               "pipeline_name": "canonicalize_person_el_alam",
               "pipeline_version": "v0.1.0", "sidecars": {}}
    validator = _validator()
    n_written = 0
    for record in cz.canonicalize(losts(), minter, None, options):
        errs = list(validator.iter_errors(record))
        if errs:
            print(f"  FAIL {record.get('@id')}: {errs[0].message[:160]}", file=sys.stderr)
            return 1
        out = PERSON_DIR / filename_for_pid(record["@id"])
        if out.exists():
            continue  # idempotent
        if not args.dry_run:
            out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
        n_written += 1
        print(f"  minted {record['@id']}  {list(record['labels']['prefLabel'].values())[0][:40]}")
    print(f"[repair_el_alam] written={n_written}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
