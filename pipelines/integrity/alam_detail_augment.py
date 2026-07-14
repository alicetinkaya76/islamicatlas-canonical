#!/usr/bin/env python3
"""
alam_detail_augment.py — el-Aʿlâm detay katmanı → kişi zenginleştirme
(H11 S10; data.zip envanterinin en büyük kazanımı).

alam_detail.json (13,940) alam_lite ile id-for-id aynı evren; store'daki
11,379 `el-alam:<id>` curie'sine eşlenir. GAP-FILL ONLY (append-only,
mevcut değer asla ezilmez):

  ne  (ALA-LC tam isim zinciri)  → labels.transliteration["ar-Latn-x-alalc"]
  nt  (TR tam isim zinciri)      → labels.altLabel.tr  (+= benzersizse)
  fn  (AR tam isim zinciri)      → labels.altLabel.ar  (+= benzersizse)
  de  (EN kısa tanım)            → labels.description.en   (yoksa)
  dt  (TR kısa tanım)            → labels.description.tr   (yoksa)
  ku  (künye)                    → kunya                    (yoksa)

MINT YOK. wk (11,412 başlıklı eser; tarihsiz/yazar-tek) ADR-009 gereği
eser olarak MINT EDİLMEZ → alam_works_pending.json. bp/dp (doğum/ölüm yeri
adları) + mc (koordinatlı yer-anılmaları) kişi-yer bağlama aşaması için
alam_places_pending.json'a düşer (dia_geo ile birlikte tek Tier-2 koşusu).
dia URL alanı KULLANILMAZ: küratörlü dia_alam_xref.json ile %54 çelişiyor
(H11 S9 profil taraması) — otorite küratörlü dosyada kalır.

Idempotent: history'de "alam-detail augment" notu görülen kayıt atlanır.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
MARKER = "alam-detail augment"


def main() -> int:
    detail = json.loads((REPO_ROOT / "data/sources/el-alam/alam_detail.json")
                        .read_text(encoding="utf-8"))
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
    curie_to_pid = dict(conn.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE 'el-alam:%'"))
    conn.close()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"applied": 0, "already": 0, "unmatched": 0, "no_gap": 0}
    works_pending: dict[str, list] = {}
    places_pending: dict[str, dict] = {}
    unmatched: list[str] = []

    for alam_id, det in sorted(detail.items()):
        pid = curie_to_pid.get(f"el-alam:{alam_id}")
        if not pid:
            stats["unmatched"] += 1
            unmatched.append(alam_id)
            # eşleşmese de eser/yer bilgisi pending'e gitsin (id anahtarıyla)
            if det.get("wk"):
                works_pending[f"el-alam:{alam_id}"] = det["wk"]
            continue

        # pending toplama marker'dan ÖNCE: idempotent yeniden-koşu pending
        # dosyalarını daraltıp EZMESİN (H11 S10 ilk koşuda kanıtlandı —
        # 4.251 works-pending 485'e inmişti).
        if det.get("wk"):
            works_pending[pid] = det["wk"]
        pp = {k: det[k] for k in ("bp", "dp", "mc") if det.get(k)}
        if pp:
            places_pending[pid] = pp

        path = REPO_ROOT / "data/canonical/person" / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        hist = rec.get("provenance", {}).get("record_history", [])
        if any(MARKER in (h.get("note") or "") for h in hist):
            stats["already"] += 1
            continue

        labels = rec.setdefault("labels", {})
        changed = []

        ne = det.get("ne")
        if ne:
            translit = labels.setdefault("transliteration", {})
            if not translit.get("ar-Latn-x-alalc"):
                translit["ar-Latn-x-alalc"] = ne[:500]  # şema kalıbı ^[a-z]{2,3}-Latn(-x-...)$
                changed.append("translit")
        for lang, key in (("tr", "nt"), ("ar", "fn")):
            v = det.get(key)
            if v:
                alt = labels.setdefault("altLabel", {}).setdefault(lang, [])
                pref = (labels.get("prefLabel") or {}).get(lang)
                if v not in alt and v != pref and len(alt) < 8:
                    alt.append(v[:500])
                    changed.append(f"alt.{lang}")
        desc = labels.setdefault("description", {})
        for lang, key in (("en", "de"), ("tr", "dt")):
            v = det.get(key)
            if v and not desc.get(lang):
                desc[lang] = v[:2000]
                changed.append(f"desc.{lang}")
        if det.get("ku") and not rec.get("kunya"):
            rec["kunya"] = det["ku"][:200]
            changed.append("kunya")

        if not changed:
            stats["no_gap"] += 1
            continue

        hist.append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": f"{MARKER} (H11 S10): gap-fill {'+'.join(sorted(set(changed)))} "
                    f"from alam_detail.json el-alam:{alam_id}.",
        })
        rec["provenance"]["modified"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        stats["applied"] += 1

    (REPO_ROOT / "data/_state/alam_works_pending.json").write_text(
        json.dumps({"_doc": "ADR-009: başlık-tek eserler mint edilmez; Faz 2 "
                            "eser-eşleme girdisi.", "works": works_pending},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (REPO_ROOT / "data/_state/alam_places_pending.json").write_text(
        json.dumps({"_doc": "bp/dp (yer adı) + mc (koordinatlı anılma) — "
                            "kişi-yer bağlama aşaması (dia_geo ile birlikte).",
                    "persons": places_pending}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"[alam_detail_augment] applied={stats['applied']} "
          f"already={stats['already']} no-gap={stats['no_gap']} "
          f"unmatched={stats['unmatched']} "
          f"works-pending={len(works_pending)} places-pending={len(places_pending)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
