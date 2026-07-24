#!/usr/bin/env python3
"""h25_001_alatli_qid_quarantine.py — Alatlı audit'inin kanıtladığı FP QID'leri
quarantine et (H25). h11_001 desenini izler: SİLME DEĞİL taşıma, geri alınabilir.

Kanıt: Alatlı çift-kaynaklı (korpus/TDV + Wikidata tarih-teyitli) diyor ki QID X'in
öznesi Z yılında; store'da AYNI QID Y yıllı bir kişide (Δ=|Z-Y|). GÜVENLİK EŞİĞİ
Δ≥80: bir ömür <100y olduğundan (doğum/ölüm ekseni karışması dahil) Δ≥80 aynı
kişinin İMKÂNSIZ olduğunu kanıtlar → store xref FP → quarantine. Δ<80 tarihçide.

Kaynak worklist: data/review_queue/alatli-qid-audit.jsonl (alatli_qid_audit.py üretir)
Kullanım: python3 pipelines/migrations/h25_001_alatli_qid_quarantine.py [--dry-run]
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
AUDIT = R / "data" / "review_queue" / "alatli-qid-audit.jsonl"
QUAR = R / "data" / "_state" / "qid_quarantine.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
# Δ≥100: hiçbir ömür 100+ yıl değil → aynı kişinin doğum/ölüm ekseni karışması
# İMKÂNSIZ. Δ<100 tarihçide (dry-run'da Abdülhak Hâmid Δ85 = 1852 doğum/1937 ölüm,
# store etiketi Alatlı ile birebir → aynı kişi, FP DEĞİL; eşiği bu kanıt yükseltti).
DELTA_MIN = 100


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conflicts = [json.loads(l) for l in AUDIT.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = json.loads(QUAR.read_text(encoding="utf-8")) if QUAR.exists() else {"quarantined": []}
    already = {(q["pid"], q["qid"]) for q in existing.get("quarantined", [])}

    n_q = n_skip_delta = n_noxref = n_already = 0
    new_items = []
    for c in conflicts:
        pid, qid = c["store_pid"], c["qid"]
        if (pid, qid) in already:
            n_already += 1
            continue
        if c["delta_years"] < DELTA_MIN:
            n_skip_delta += 1
            print(f"  SKIP Δ<{DELTA_MIN} (tarihçide): {c['alatli_name']} {qid} Δ{c['delta_years']}")
            continue
        path = R / "data" / "canonical" / "person" / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        if not path.exists():
            n_noxref += 1
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        xrefs = rec.get("authority_xref") or []
        hit = [x for x in xrefs if x.get("id") == qid and x.get("authority") == "wikidata"]
        if not hit:
            n_noxref += 1
            print(f"  WARN xref yok: {pid} {qid}")
            continue
        rec["authority_xref"] = [x for x in xrefs if x not in hit]
        if not rec["authority_xref"]:
            rec.pop("authority_xref", None)
        rec.setdefault("provenance", {}).setdefault("record_history", []).append({
            "change_type": "update", "changed_at": NOW,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"QID {qid} quarantine (H25 Alatlı audit): store ö.{c['store_year']} "
                     f"vs Alatlı date-corroborated ö.{c['alatli_year']} (Δ{c['delta_years']}) "
                     f"— aynı kişi imkânsız, xref FP; kanıt qid_quarantine.json."),
        })
        rec["provenance"]["modified"] = NOW
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        new_items.append({
            "pid": pid, "qid": qid, "ns": "person", "name_sim": None, "km": None,
            "death_rec": c["store_year"], "death_wd": c["alatli_year"],
            "rec_label": [c.get("store_label")], "wd_label": [c["alatli_name"]],
            "source": "alatli_audit_h25", "delta_years": c["delta_years"],
            "quarantined_at": NOW, "restorable": True,
        })
        n_q += 1
        print(f"  QUARANTINE {qid} {c['alatli_name'][:20]:22} store ö.{c['store_year']} "
              f"(Δ{c['delta_years']}) [{c.get('store_label')}]")

    if new_items and not args.dry_run:
        QUAR.write_text(json.dumps({
            "_meta": {**existing.get("_meta", {}), "updated": NOW,
                      "policy": existing.get("_meta", {}).get("policy",
                          "silme değil taşıma; tarihçi geri alabilir"),
                      "total": len(existing.get("quarantined", [])) + n_q},
            "quarantined": existing.get("quarantined", []) + new_items,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n[h25_001] quarantine={n_q} skip-Δ<{DELTA_MIN}={n_skip_delta} "
          f"already={n_already} xref-yok={n_noxref}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
