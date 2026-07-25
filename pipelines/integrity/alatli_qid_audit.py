#!/usr/bin/env python3
"""alatli_qid_audit.py — Alatlı tarih-teyitli QID'leriyle store QID'lerini denetle (H25).

islamicatlas'ın bilinen %33,7 FP-QID sorununa (H10 S11) kanıt-güdümlü katkı:
Alatlı'nın 564 QID'i korpus/TDV + Wikidata çift-kaynaklı (date-corroborated).
Store'da AYNI QID farklı bir kişide/tarihte duruyorsa → muhtemel FP (ya da
store'un tarih hatası). Bulgular QID-temizlik oturumuna worklist olur.

ÜRETİR (data/review_queue/, gitignored → reproducible):
  alatli-qid-audit.jsonl  — QID∩QID tarih-çelişkileri (>25 yıl)
NOT: otomatik düzeltme YOK — worklist. Doğru olanı tarihçi seçer.
"""
from __future__ import annotations
import glob, json, os
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
ALATLI = Path.home() / "Desktop" / "alev_alatlı" / "corpus_json" / "timeline" / "timeline_final.json"


def main():
    if not ALATLI.exists():
        print(f"Alatlı kaynağı yok: {ALATLI}"); return
    P = json.load(open(ALATLI, encoding="utf-8"))["people"]
    # Alatlı QID -> (tarih-teyitli yıl, ad). Aynı QID birden çok Alatlı kaydında
    # olabilir → en iyi (tarihli) olanı tut.
    alatli_q = {}
    for p in P:
        q = p.get("qid"); ay = p.get("death") or p.get("birth")
        if q and ay:
            alatli_q.setdefault(q, (ay, p["name"]))

    # TÜM store QID-taşıyıcılarını tara (QID başına ilk değil, HEPSİ — Q39619'un
    # 6 kaydı gibi; her taşıyıcı ayrı ayrı denetlenir).
    conflicts = []
    for f in glob.glob(str(R / "data" / "canonical" / "person" / "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        dt = d.get("death_temporal") or d.get("birth_temporal") or d.get("floruit_temporal") or {}
        sy = dt.get("start_ce")
        if sy is None:
            continue
        lab = d.get("labels", {}).get("prefLabel", {}) or {}
        for x in d.get("authority_xref", []):
            if x.get("authority") != "wikidata":
                continue
            q = x.get("id")
            if q not in alatli_q:
                continue
            ay, aname = alatli_q[q]
            if abs(ay - sy) > 25:
                conflicts.append({
                    "qid": q, "store_pid": d["@id"],
                    "store_year": sy, "store_label": lab.get("en") or lab.get("tr"),
                    "alatli_name": aname, "alatli_year": ay,
                    "delta_years": abs(ay - sy),
                    "verdict": "store QID muhtemel FP ya da store tarih hatası — tarihçi karar",
                })
    conflicts.sort(key=lambda c: -c["delta_years"])
    out = R / "data" / "review_queue" / "alatli-qid-audit.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in conflicts) + "\n",
                   encoding="utf-8")
    print(f"[alatli_qid_audit] Alatlı QID'i: {len(alatli_q)} | store taşıyıcı "
          f"tarih-çelişkisi (>25y, HER taşıyıcı ayrı): {len(conflicts)} -> {out.name}")
    for c in conflicts[:8]:
        print(f"  {c['qid']:11} {c['alatli_name'][:20]:22} Alatlı {c['alatli_year']} "
              f"vs store {c['store_year']} (Δ{c['delta_years']}) [{c['store_label']}]")


if __name__ == "__main__":
    main()
