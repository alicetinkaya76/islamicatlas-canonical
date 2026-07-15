#!/usr/bin/env python3
"""
core_canon_augment.py — Çekirdek Külliyat kitaplarının canonical
zenginleştirmesi (H13 S-D D2).

Parti manifesti + editoryal tanıtımlar + okuma-verisi istatistikleri →
work kaydına gap-fill:
  labels.description.tr/en  (EDİTORYAL metin — DİA değil; ADR-014/İSAM)
  note += yapı istatistiği (bölüm/kelime; okuma verisinden sayılır) +
          atlas rolü cümlesi
Idempotent: marker. Kullanım: --batch 1
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
MARKER = "core-canon augment"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=1)
    args = ap.parse_args()
    bdir = REPO_ROOT / "data/sources/openiti/core_batches"
    batch = yaml.safe_load((bdir / f"batch_{args.batch:02d}.yaml").read_text(encoding="utf-8"))
    descs = yaml.safe_load((bdir / f"batch_{args.batch:02d}_descriptions.yaml")
                           .read_text(encoding="utf-8"))["descriptions"]

    uri_to_rec = {}
    for p in (REPO_ROOT / "data/canonical/work").glob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("openiti_uri"):
            uri_to_rec[rec["openiti_uri"]] = (p, rec)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n = already = 0
    for book in batch["books"]:
        uri = book["uri"]
        if uri not in uri_to_rec:
            print(f"✗ {uri}: canonical yok")
            continue
        path, rec = uri_to_rec[uri]
        hist = rec.setdefault("provenance", {}).setdefault("record_history", [])
        if any(MARKER in (h.get("note") or "") for h in hist):
            already += 1
            continue

        changed = []
        desc = rec.setdefault("labels", {}).setdefault("description", {})
        ed = descs.get(uri) or {}
        for lang in ("tr", "en"):
            if ed.get(lang) and not desc.get(lang):
                desc[lang] = ed[lang].strip()[:2000]
                changed.append(f"desc.{lang}")

        # okuma verisi istatistiği (varsa)
        pidnum = rec["@id"].rsplit("-", 1)[1]
        mf = REPO_ROOT / "web/public/reading" / pidnum / "manifest.json"
        note_bits = []
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            note_bits.append(f"Çekirdek Külliyat (parti {batch['batch']}): "
                             f"{m['n_sections']} bölüm · {m['total_words']:,} kelime "
                             f"· sürüm {m['version_file'].rsplit('.', 1)[0].split('.')[-1]}")
        if book.get("atlas_role"):
            note_bits.append(f"Atlas rolü: {book['atlas_role']}")
        if note_bits:
            note = rec.get("note") or ""
            tag = " · ".join(note_bits)
            if "Çekirdek Külliyat" not in note:
                rec["note"] = (note + (" · " if note else "") + tag)[:2000]
                changed.append("note")

        if not changed:
            continue
        hist.append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": f"{MARKER} (H13 S-D, parti {batch['batch']}): "
                    f"{'+'.join(changed)} — editoryal tanıtım (kendi metnimiz; "
                    f"DİA kullanılmadı) + okuma-verisi istatistiği.",
        })
        rec["provenance"]["modified"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        n += 1
        print(f"✓ {uri}: {'+'.join(changed)}")
    print(f"[core_canon_augment] applied={n} already={already}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
