#!/usr/bin/env python3
"""
upsert.py — canonical projeksiyonunu canlı Typesense'e yükler
(H10 Stage 10; Faz 0.5 canlı-yol parçası).

Akış:
  1. TYPESENSE_URL + TYPESENSE_API_KEY env'den (yoksa NET hata — hosting
     kararı verilene dek canlı koşu bilinçli imkânsız; projeksiyon kapısı
     `full_reindex --dry-run` olmayı sürdürür).
  2. Koleksiyon yoksa typesense_schema_emit gövdesiyle oluşturur
     (--recreate ile önce siler).
  3. NDJSON'u (verilmezse projector'dan taze üretir) 1.000'lik parçalarla
     `documents/import?action=upsert`e basar; Typesense satır-satır sonuç
     döndürür — başarısızlar SAYILIR ve ilk 5'i raporlanır (sessiz kayıp yok).

Usage:
  TYPESENSE_URL=http://localhost:8108 TYPESENSE_API_KEY=xyz \\
      python3 pipelines/search/upsert.py [--ndjson path] [--recreate] [--batch 1000]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from search.typesense_schema_emit import emit  # noqa: E402


def _env() -> tuple[str, dict]:
    url = os.environ.get("TYPESENSE_URL", "").rstrip("/")
    key = os.environ.get("TYPESENSE_API_KEY", "")
    if not url or not key:
        print("ERROR: TYPESENSE_URL ve TYPESENSE_API_KEY env değişkenleri "
              "gerekli. Canlı indeksleme hosting kararıyla açılır "
              "(docs/PHASE0_CLOSEOUT.md §4); projeksiyon regresyon kapısı "
              "için `make reindex-dry` kullanın.", file=sys.stderr)
        raise SystemExit(2)
    return url, {"X-TYPESENSE-API-KEY": key}


def ensure_collection(url: str, headers: dict, recreate: bool) -> str:
    body = emit()
    name = body["name"]
    r = requests.get(f"{url}/collections/{name}", headers=headers, timeout=30)
    if r.status_code == 200 and recreate:
        requests.delete(f"{url}/collections/{name}", headers=headers,
                        timeout=60).raise_for_status()
        r = requests.get(f"{url}/collections/{name}", headers=headers, timeout=30)
    if r.status_code == 404:
        c = requests.post(f"{url}/collections", headers=headers,
                          json=body, timeout=60)
        c.raise_for_status()
        print(f"[upsert] koleksiyon oluşturuldu: {name} "
              f"({len(body['fields'])} alan)")
    elif r.status_code == 200:
        print(f"[upsert] koleksiyon mevcut: {name}")
    else:
        r.raise_for_status()
    return name


def iter_ndjson(path: Path | None):
    if path:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield line.rstrip("\n")
        return
    from search.projector import Projector
    proj = Projector(repo_root=REPO_ROOT)
    for doc in proj.project_all():
        yield json.dumps(doc, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ndjson", type=Path, default=None,
                    help="Hazır NDJSON (full_reindex --out çıktısı); "
                         "verilmezse projector'dan taze üretilir.")
    ap.add_argument("--recreate", action="store_true")
    ap.add_argument("--batch", type=int, default=1000)
    args = ap.parse_args()

    url, headers = _env()
    name = ensure_collection(url, headers, args.recreate)

    n_ok = n_fail = 0
    fails: list[str] = []
    batch: list[str] = []

    def flush():
        nonlocal n_ok, n_fail
        if not batch:
            return
        r = requests.post(
            f"{url}/collections/{name}/documents/import?action=upsert",
            headers={**headers, "Content-Type": "text/plain"},
            data=("\n".join(batch)).encode("utf-8"), timeout=300)
        r.raise_for_status()
        for line in r.text.splitlines():
            res = json.loads(line)
            if res.get("success"):
                n_ok += 1
            else:
                n_fail += 1
                if len(fails) < 5:
                    fails.append(res.get("error", "?")[:200])
        batch.clear()

    for line in iter_ndjson(args.ndjson):
        batch.append(line)
        if len(batch) >= args.batch:
            flush()
            if (n_ok + n_fail) % 10_000 < args.batch:
                print(f"  {n_ok + n_fail} yüklendi (fail={n_fail})")
    flush()

    print(f"[upsert] ok={n_ok} fail={n_fail}")
    if fails:
        print("  ilk hatalar:", *fails, sep="\n  ")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
