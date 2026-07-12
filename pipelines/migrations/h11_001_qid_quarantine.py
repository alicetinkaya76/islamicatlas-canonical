#!/usr/bin/env python3
"""
h11_001_qid_quarantine.py — H10 S11 QID denetiminin AŞİKÂR-ÇÖP katmanını
karantinaya alır (H11 Karar 3; kullanıcı "sen karar ver" devri).

SİLME DEĞİL TAŞIMA: kayıttan çıkarılan her xref, kanıtıyla birlikte
data/_state/qid_quarantine.json'a yazılır — tarihçi tek tek geri alabilir.

Kademeli kural (yalnız denetimin MISMATCH sınıfı):
  KARANTİNA: name_sim < 70 VE hiçbir doğrulayıcı sinyal yok (ölüm-yılı ±3
    değil, koordinat ≤25 km değil) — Safevîler→Spartacus League sınıfı;
    yanlışlığı tartışmasız.
  KALIR (review'da): sim 70-84 sınır bandı + herhangi bir sinyalli vaka —
    bunlar display-gate arkasında zaten gizli (reviewed=false) ya da
    denetim-gürültüsü olabilir; karar tarihçinin.
  İSTİSNA: dynasty xref'leri reviewed=true olduğundan display-gate'i AŞAR —
    dynasty MISMATCH'leri sim<85'te de karantinaya girer (kanıt: 24/25 çöp;
    yayında yanlış iddia bırakılamaz).

Usage: python3 pipelines/migrations/h11_001_qid_quarantine.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT = REPO_ROOT / "data/_state/qid_audit_report.json"
QUARANTINE = REPO_ROOT / "data/_state/qid_quarantine.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _corroborated(m: dict) -> bool:
    dr, dw = m.get("death_rec"), m.get("death_wd")
    if isinstance(dr, int) and isinstance(dw, int) and abs(dr - dw) <= 3:
        return True
    km = m.get("km")
    if isinstance(km, (int, float)) and km <= 25:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    existing = {"quarantined": []}
    if QUARANTINE.exists():
        existing = json.loads(QUARANTINE.read_text(encoding="utf-8"))
    already = {(q["pid"], q["qid"]) for q in existing.get("quarantined", [])}

    # H7'nin insan-onaylı yanlış-hedefleri (tombstone deseni) karantinaya
    # BİRLEŞTİRİLİR (H11 Karar 3): insan onayı en güçlü kanıt sınıfıdır;
    # eşik ne olursa olsun taşınır. test_h7_1 iki biçimi de tanır.
    H7_FORCED = [("iac:person-00000184", "Q9438"),
                 ("iac:person-00000115", "Q9458"),
                 ("iac:person-00020919", "Q36533610"),
                 ("iac:person-00000182", "Q719449")]

    n_q = n_keep = n_noop = 0
    new_items = []
    forced = [{"ns": "person", "pid": p, "qid": q, "name_sim": 0,
               "_h7_confirmed": True} for p, q in H7_FORCED]
    for m in forced + audit.get("mismatches", []):
        ns, pid, qid = m["ns"], m["pid"], m["qid"]
        sim = m.get("name_sim") or 0
        threshold = 85 if ns == "dynasty" else 70
        if not m.get("_h7_confirmed") and (sim >= threshold or _corroborated(m)):
            n_keep += 1
            continue
        if (pid, qid) in already:
            n_noop += 1
            continue
        path = (REPO_ROOT / "data" / "canonical" / ns /
                f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json")
        if not path.exists():
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        xrefs = rec.get("authority_xref") or []
        hit = [x for x in xrefs
               if x.get("authority") == "wikidata" and x.get("id") == qid]
        if not hit:
            n_noop += 1
            continue
        rec["authority_xref"] = [x for x in xrefs if x not in hit]
        if not rec["authority_xref"]:
            rec.pop("authority_xref", None)
        rec.setdefault("provenance", {}).setdefault("record_history", []).append({
            "change_type": "update", "changed_at": NOW,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"h11_001 QID karantinası: wikidata:{qid} kayıttan "
                     f"çıkarıldı (denetim MISMATCH, sim={round(sim)}, "
                     f"doğrulayıcı sinyal yok; kanıt qid_quarantine.json)."),
        })
        rec["provenance"]["modified"] = NOW
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        new_items.append({"pid": pid, "qid": qid, "ns": ns, **{
            k: m.get(k) for k in ("name_sim", "km", "death_rec", "death_wd",
                                  "rec_label", "wd_label")},
            "quarantined_at": NOW, "restorable": True})
        n_q += 1

    if not args.dry_run:
        QUARANTINE.write_text(json.dumps({
            "_meta": {"updated": NOW,
                      "policy": ("silme değil taşıma; tarihçi geri alabilir. "
                                 "Kural: sim<70 + sinyalsiz (dynasty: <85 — "
                                 "reviewed=true display-gate'i aştığı için)"),
                      "total": len(existing.get("quarantined", [])) + n_q},
            "quarantined": existing.get("quarantined", []) + new_items,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"[h11_001] karantina={n_q} kalan-review'da={n_keep} noop={n_noop}"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
