#!/usr/bin/env python3
"""
postprocess_book_layer.py — jenerik kitap-katmanı son-işlemi (H14).

İbn Cübeyr runbook'unun olay/yapı türlerine genellemesi. Sahip kararı
(2026-07-16): çıkarımlar DOĞRUDAN yayınlanır; confidence/geo_note alanları
veride kalır (dürüstlük veri düzeyinde).

Kullanım:
  --pid 00001293 --kind events --records-key events --input raw.json \\
  [--center lat,lon --radius 120]   (şehir-yapıları politikası)
Çıktı: web/public/reading/<pid>/layer.json  {metadata, kind, records}
        + data/sources/book-layers/<pid>_<kind>.json (repo kopyası)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.reading.book_geo import link_records  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", required=True, help="pidnum (00001293)")
    ap.add_argument("--kind", required=True, choices=["events", "structures", "routes", "entries"])
    ap.add_argument("--records-key", default=None)
    ap.add_argument("--input", required=True)
    ap.add_argument("--center", default=None, help="lat,lon (şehir politikası)")
    ap.add_argument("--radius", type=float, default=120.0)
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    key = args.records_key or args.kind
    records = raw[key] if isinstance(raw, dict) else raw
    records = [r for r in records if r.get("sec") is not None]
    records.sort(key=lambda r: (r["sec"],))
    for i, r in enumerate(records):
        r["seq"] = i + 1

    center = tuple(float(x) for x in args.center.split(",")) if args.center else None
    stats = link_records(records, name_key="place_ar" if args.kind == "events" else "name_ar",
                         center=center, radius_km=args.radius)

    manifest = json.loads((REPO_ROOT / "web/public/reading" / args.pid / "manifest.json")
                          .read_text(encoding="utf-8"))
    layer = {
        "metadata": {
            "kind": args.kind,
            "source_work": manifest["pid"],
            "book": manifest.get("name_tr"),
            "extraction": "Claude bölüm-bazlı yapılandırılmış çıkarım + "
                          "book_geo 3-kademeli bağlama (H14 runbook)",
            "status": "PUBLISHED — sahip kararıyla doğrudan (2026-07-16); "
                      "confidence/geo_note alanları veride",
            "n_records": len(records),
            "n_geocoded": stats["linked"],
        },
        "kind": args.kind,
        "records": records,
    }
    (REPO_ROOT / "web/public/reading" / args.pid / "layer.json").write_text(
        json.dumps(layer, ensure_ascii=False), encoding="utf-8")
    out = REPO_ROOT / "data/sources/book-layers"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.pid}_{args.kind}.json").write_text(
        json.dumps(layer, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{manifest.get('name_tr','?')[:30]}] {args.kind}: kayıt={len(records)} "
          f"koordinatlı={stats['linked']} şüpheli={stats['suspect']} "
          f"koordinatsız={stats['unlinked']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
