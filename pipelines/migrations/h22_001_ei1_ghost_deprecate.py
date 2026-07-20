#!/usr/bin/env python3
"""
h22_001_ei1_ghost_deprecate.py — EI-1 artifact'lerinden mint edilmiş
HAYALET kişi kayıtlarını yumuşak-siler (H22 kuyruk eritme, kova A).

Bulgu (H21 S2, ei1_triage.json → _meta.magaza_kirlilik_denetimi):
mağazadaki 1.174 `ei1:*` curie'li kaydın 27'si gerçek kişi değil —
taranmış EI-1 sayfalarının artifact'lerinden mint edilmiş:
  Lxxxix (Roma rakamı) · Zdpv (dergi kısaltması) · G O W (yazar imzası)
  Ai-KArlSlVA  KADJAR (iki-maddebaşlı sayfa üstbilgisi) …
27'sinin tamamı ajan tarafından gözle doğrulandı, yanlış pozitif yok.

SİLME DEĞİL YUMUŞAK-SİLME (h11_001 karantina doktrininin kişi-kaydı
karşılığı): `provenance.deprecated = true` + gerekçe. Şema bunu zaten
"soft-delete" olarak tanımlıyor (place.schema.json @id açıklaması) ve
search/projector.py deprecated kayıtlara -100 skor cezası veriyor →
kayıt aramada dibe düşer ama PID asla yeniden atanmaz, geçmiş korunur.
Geri alma: data/_state/ei1_ghost_deprecated.json'daki liste + bu
script'in --restore bayrağı.

Usage:
  python3 pipelines/migrations/h22_001_ei1_ghost_deprecate.py [--dry-run]
  python3 pipelines/migrations/h22_001_ei1_ghost_deprecate.py --restore
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRIAGE = REPO_ROOT / "data/_state/ei1_triage.json"
LEDGER = REPO_ROOT / "data/_state/ei1_ghost_deprecated.json"
PERSON_DIR = REPO_ROOT / "data/canonical/person"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

REASON = ("h22_001 yumuşak-silme: EI-1 taranmış metin artifact'inden mint "
          "edilmiş hayalet kayıt (H21 triyajı; kural {kural}; kaynak başlık "
          "{etiket!r}). Gerçek bir kişiye karşılık gelmiyor. PID korunur, "
          "geri alınabilir: h22_001 --restore.")


def _path_of(pid: str) -> Path:
    return PERSON_DIR / (pid.replace("iac:", "iac_").replace("-", "_") + ".json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not LEDGER.exists():
            print("✗ geri alma defteri yok — yapılacak bir şey yok")
            return 1
        led = json.loads(LEDGER.read_text(encoding="utf-8"))
        n = 0
        for row in led["deprecated"]:
            p = _path_of(row["pid"])
            if not p.exists():
                continue
            rec = json.loads(p.read_text(encoding="utf-8"))
            prov = rec.setdefault("provenance", {})
            prov["deprecated"] = False
            prov.pop("deprecated_reason", None)
            prov.pop("deprecated_at", None)
            if not args.dry_run:
                p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            n += 1
        print(f"↩ geri alındı: {n} kayıt" + (" (DRY-RUN)" if args.dry_run else ""))
        return 0

    triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
    ghosts = triage["_meta"]["magaza_kirlilik_denetimi"]["artifact_kayitlari"]
    print(f"hayalet aday: {len(ghosts)}")

    done, skipped, missing = [], [], []
    for g in ghosts:
        p = _path_of(g["pid"])
        if not p.exists():
            missing.append(g["pid"])
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        prov = rec.setdefault("provenance", {})
        if prov.get("deprecated") is True:
            skipped.append(g["pid"])          # idempotent
            continue
        prov["deprecated"] = True
        # GEREKÇE record_history'ye yazılır: provenance şeması KAPALI
        # (_common/provenance.schema.json additionalProperties:false —
        # deprecated_reason/deprecated_at alanları yok). Şemayı bunun için
        # değiştirmedik; record_history zaten "ne oldu, neden" alanıdır.
        hist = prov.setdefault("record_history", [])
        marker = REASON.format(kural=g["kural"], etiket=g["magaza_etiketi"])
        if not any(h.get("note") == marker for h in hist):
            hist.append({"change_type": "deprecate", "note": marker,
                         "changed_at": NOW, "changed_by": ATTRIBUTED_TO})
        if not args.dry_run:
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
        done.append({"pid": g["pid"], "ei1_id": g["ei1_id"],
                     "kural": g["kural"], "etiket": g["magaza_etiketi"]})

    if not args.dry_run and done:
        LEDGER.write_text(json.dumps({
            "_doc": "H22 kova-A: EI-1 hayalet kayıtlarının yumuşak-silme defteri "
                    "(geri alma: h22_001 --restore).",
            "deprecated_at": NOW, "n": len(done), "deprecated": done,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"✓ yumuşak-silinen: {len(done)}"
          f" · zaten işaretli: {len(skipped)} · dosyası yok: {len(missing)}"
          + (" (DRY-RUN — yazılmadı)" if args.dry_run else ""))
    if missing:
        print("  eksik:", ", ".join(missing[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
