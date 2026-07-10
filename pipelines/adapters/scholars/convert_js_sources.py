#!/usr/bin/env python3
"""
convert_js_sources.py — one-off, deterministic JS-literal → JSON conversion
for the scholars source (H10 Stage 3).

The upstream files (scholar_identity.js, scholar_meta.js, scholar_links.js,
isnad_chains.js) are JavaScript object/array literals (unquoted keys, single
quotes, comments) written for a browser app — not JSON. This script evaluates
each in Node (available: v22) and dumps a single canonical JSON,
data/sources/scholars/scholars_converted.json, which the adapter's extract.py
then consumes with zero runtime Node dependency. The output is committed to
git AS the source-of-record derivative; rerunning is idempotent (same input →
same output; a `_meta` block records the conversion).

Usage: python3 pipelines/adapters/scholars/convert_js_sources.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "data" / "sources" / "scholars"
OUT = SRC / "scholars_converted.json"

FILES = {  # js filename → (const name, output key)
    "scholar_identity.js": ("SCHOLAR_IDENTITY", "identity"),
    "scholar_meta.js": ("SCHOLAR_META", "meta"),
    "scholar_links.js": ("SCHOLAR_LINKS", "links"),
    "isnad_chains.js": ("ISNAD_CHAINS", "isnad_chains"),
}

NODE_SNIPPET = """
const fs = require('fs');
let src = fs.readFileSync(process.argv[1], 'utf8');
// Browser-module tails (`export default X;` / `export { X };`) are illegal
// inside new Function() — strip them; the const declaration stays.
src = src.split('\\n').filter(l => !l.trimStart().startsWith('export ')).join('\\n');
const name = process.argv[2];
const fn = new Function(src + `; return ${name};`);
process.stdout.write(JSON.stringify(fn()));
"""


def main() -> int:
    out: dict = {}
    for fname, (const_name, key) in FILES.items():
        path = SRC / fname
        r = subprocess.run(["node", "-e", NODE_SNIPPET, path.as_posix(), const_name],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERROR converting {fname}: {r.stderr[:400]}", file=sys.stderr)
            return 1
        out[key] = json.loads(r.stdout)
        n = len(out[key])
        print(f"  {fname} → {key}: {n} entries")

    csv_rows = (SRC / "scholars.csv").read_text(encoding="utf-8").count("\n")
    out["_meta"] = {
        "converted_from": sorted(FILES),
        "converter": "pipelines/adapters/scholars/convert_js_sources.py (node eval)",
        "note": ("scholars.csv is consumed directly by extract.py "
                 f"({csv_rows - 1} rows); this JSON covers only the JS literals."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
