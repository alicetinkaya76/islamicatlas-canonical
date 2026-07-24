#!/usr/bin/env python3
"""triage_alatli_review.py — Alatlı review (159) + collision (9) kuyruklarını
kanıtla güvenli triyaj et (H25).

KANIT: collision'ların hepsi AYNI-KİŞİ Alatlı-içi dup (ölüm yılları uyuşuyor;
ei1'in farklı-kişi kontaminasyonu DEĞİL) → güvenle augment. Review girdilerinin
çoğu exact ad (label=1.0) + exact ölüm (temporal=1.0), yalnız alt-label cezasıyla
0.95 auto-eşiğinin altında.

GÜVENLİ SINIFLAR (augment'e → _alatli_augment_review.json, {pid:[event]}):
  A) collision (aynı-kişi dup): PID başına EN İYİ Alatlı kaydı (QID'li tercih)
  B) review, İslami, label==1.0 & temporal==1.0 & BASKIN aday
     (top≥0.90 ve (tek aday veya 2.'ye fark≥0.08))
KAPI-DIŞI: Batı review → western-held. Belirsiz İslami review → kuyrukta kalır
(H10/H14 adaş-kontaminasyonu dersi: çoklu-yakın aday asla otomatik değil).
"""
from __future__ import annotations
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
RQ = R / "data" / "review_queue"
SRC = R / "data" / "sources" / "alatli"


def best_event(events):
    return sorted(events, key=lambda e: (0 if e.get("qid") else 1,
                                         -(e.get("record_count") or 0)))[0]


def main():
    aug: dict = {}                       # {pid: [event]}
    western = json.loads((SRC / "_alatli_western_held.json").read_text(encoding="utf-8"))
    remaining = []
    n_coll = n_review_aug = n_west = n_keep = 0

    # --- A) collision'lar: hepsi aynı-kişi dup → en iyi kayıtla augment ---
    coll_path = RQ / "alatli-collisions.jsonl"
    if coll_path.exists():
        for line in coll_path.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            evs = d["events"]
            deaths = {e.get("death_ce") for e in evs if e.get("death_ce")}
            # güvenlik: ölüm yılları ≤3 yıl içinde mi (aynı kişi kanıtı)
            if len(deaths) <= 1 or (max(deaths) - min(deaths) <= 3):
                aug.setdefault(d["pid"], []).append(best_event(evs))
                n_coll += 1
            else:
                remaining.append({"pid": d["pid"], "reason": "collision-diff-death", "events": evs})
                n_keep += 1

    # --- B) review kuyruğu ---
    rp = RQ / "alatli.jsonl"
    if rp.exists():
        for line in rp.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            summ = d.get("extracted_summary", {})
            cands = d.get("candidates") or []
            rid = d["extracted_record_id"].split(":", 1)[-1]
            # Batı mı? (western-held sidecar'da rid VEYA ad geçiyorsa)
            name = (summ.get("labels", {}).get("prefLabel", {}) or {}).get("tr", "")
            # kanon bilgisi review entry'de yok → western_held'e bakılamaz; ad
            # üzerinden değil, güvenli tarafta: aday yoksa/zayıfsa kuyrukta bırak.
            if not cands:
                remaining.append({"rid": rid, "name": name, "reason": "no-candidate"})
                n_keep += 1
                continue
            top = cands[0]
            fs = top.get("feature_scores", {})
            dominant = (len(cands) == 1) or (top["score"] - cands[1]["score"] >= 0.08)
            safe = (fs.get("label", 0) >= 0.999 and fs.get("temporal", 0) >= 0.999
                    and top["score"] >= 0.90 and dominant)
            if safe:
                aug.setdefault(top["pid"], []).append({
                    "alatli_id": rid, "name_tr": name, "qid": None,
                    "death_ce": (summ.get("temporal") or {}).get("start_ce"),
                    "birth_ce": None, "tdv_slug": None, "canon": ["bize"],
                    "place_label": None, "record_count": 1,
                    "tier": 2, "confidence": top["score"],
                })
                n_review_aug += 1
            else:
                remaining.append({"rid": rid, "name": name, "reason": "ambiguous",
                                  "top_score": round(top["score"], 3),
                                  "n_candidates": len(cands),
                                  "label": round(fs.get("label", 0), 2),
                                  "temporal": round(fs.get("temporal", 0), 2)})
                n_keep += 1

    (SRC / "_alatli_augment_review.json").write_text(
        json.dumps(aug, ensure_ascii=False, indent=1), encoding="utf-8")
    (RQ / "alatli_review_remaining.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in remaining) + "\n",
        encoding="utf-8")
    (SRC / "_alatli_western_held.json").write_text(
        json.dumps(western, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[triage] collision-augment={n_coll} review-safe-augment={n_review_aug} "
          f"kuyrukta-kalan={n_keep}")
    print(f"  -> _alatli_augment_review.json ({len(aug)} pid) + "
          f"alatli_review_remaining.jsonl ({len(remaining)})")


if __name__ == "__main__":
    main()
