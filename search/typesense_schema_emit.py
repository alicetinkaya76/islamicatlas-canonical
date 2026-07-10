#!/usr/bin/env python3
"""
typesense_schema_emit.py — annotated koleksiyon şemasından Typesense
create-collection gövdesi üretir (H10 Stage 10; Faz 0.5 canlı-yol parçası).

search/typesense_collection.schema.json PROJENİN kaynağıdır (comment'li,
$id'li); Typesense API'si yalnız kendi anahtarlarını kabul eder. Bu script
dokümantasyon anahtarlarını ($schema/$id/title/description/comment/
_typesense_settings) sıyırıp saf API gövdesini basar.

Usage:
  python3 search/typesense_schema_emit.py            # stdout
  python3 search/typesense_schema_emit.py --out p.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "search" / "typesense_collection.schema.json"

_COLLECTION_KEYS = ("default_sorting_field", "enable_nested_fields",
                    "token_separators", "symbols_to_index")
_FIELD_KEYS = ("name", "type", "facet", "optional", "index", "sort", "infix",
               "locale", "stem")


def emit() -> dict:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    body: dict = {"name": src["collection_name"]}
    for k in _COLLECTION_KEYS:
        if k in src:
            body[k] = src[k]
    body["fields"] = [
        {k: f[k] for k in _FIELD_KEYS if k in f}
        for f in src["fields"]
    ]
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    body = emit()
    text = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(body['fields'])} fields, "
              f"collection '{body['name']}')")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
