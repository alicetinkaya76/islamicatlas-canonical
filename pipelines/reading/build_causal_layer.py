#!/usr/bin/env python3
"""Nedensellik katmanını sidecar'a yazar (H36 — adım 3/3).

GİRDİ  : çıkarım koşusunun ham çıktısı (workflow task output JSON)
ÇIKTI  : data/sources/causal/causal_links.json   (SIDECAR — canonical DEĞİL)

NEDEN SIDECAR, NEDEN CANONICAL DEĞİL
    Şemadaki `causes`/`consequences` alanları **olay→olay PID bağı** bekler
    (`^iac:event-\\d{8}$`). Buradaki bağlar ise **kayıt-içi**: tek bir kronik
    kaydının içinde kaynağın kurduğu sebep–sonuç ("tâun çıktı → halk kaçtı").
    Bunları `causes` alanına yazmak şemanın semantiğini bozar ve yanlış veri
    üretir. Bu yüzden sidecar'da tutulur; `causes` ancak sebep ifadesi başka bir
    canonical olayla EŞLEŞTİRİLİRSE (tarihçi onayıyla) dolar.

YAYIN KURALI
    Her kayıt `needs_human_review: true` ile yazılır. Bu katman **iddia değil
    kayıttır**; tarihçi onayı olmadan atlas/analiz görünümüne BAĞLANMAZ.

KALİTE ALANLARI (iki denetim turunun ürünü)
    link_type            explicit_talil | motive_reported | fa_consequential
                         | onomastic | state_description
    cause_is_proposition sebep bir ÖNERME mi, yoksa çıplak ad/konu mu
    evidence_complete    sebep VE sonuç ikisi de alıntının içinde mi
    effect_realized      realized | intent_only | rejected | unclear
    asserted_by          chronicler | chronicler_with_isnad | quoted_actor | hedged

Çalıştırma:
    python3 pipelines/reading/build_causal_layer.py --input <task_output.json>
"""

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAND = REPO / "data" / "_state" / "causal_candidates.json"
OUT = REPO / "data" / "sources" / "causal" / "causal_links.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True,
                    help="çıkarım koşusunun ham çıktısı (JSON)")
    a = ap.parse_args()

    raw = json.loads(a.input.read_text(encoding="utf-8"))
    # Workflow task çıktısı sonucu `result` altına sarabiliyor (str veya dict).
    if "accepted" not in raw and "result" in raw:
        r = raw["result"]
        raw = json.loads(r) if isinstance(r, str) else r
    accepted = raw.get("accepted") or []
    stats = raw.get("stats") or []

    # Aday havuzundan bağlam (kitap adı, bölüm, sayfa, tarih) eşle
    cands = {}
    if CAND.is_file():
        for r in json.loads(CAND.read_text(encoding="utf-8"))["records"]:
            cands[(r["book_pid"], r["seq"])] = r

    out = []
    for a_ in accepted:
        key = (a_.get("book_pid"), a_.get("seq"))
        c = cands.get(key, {})
        out.append({
            "book_pid": a_.get("book_pid"),
            "book": c.get("book"),
            "seq": a_.get("seq"),
            "sec": c.get("sec"),
            "page": c.get("page"),
            "date_text": c.get("date_text"),
            "place_pid": c.get("place_pid"),
            "link_type": a_.get("link_type"),
            "connector_ar": a_.get("connector_ar"),
            "cause_tr": a_.get("cause_tr"),
            "effect_tr": a_.get("effect_tr"),
            "quote_ar": a_.get("quote_ar"),
            "cause_is_proposition": a_.get("cause_is_proposition"),
            "evidence_complete": a_.get("evidence_complete"),
            "effect_realized": a_.get("effect_realized"),
            "asserted_by": a_.get("asserted_by"),
            "confidence": a_.get("confidence"),
            # YAYIN KAPISI — istisnasız
            "needs_human_review": True,
        })
    out.sort(key=lambda x: (x["book_pid"] or "", x["seq"] or 0))

    def dist(field):
        return dict(Counter(x.get(field) for x in out).most_common())

    doc = {
        "_doc": ("Kaynak-tanıklı nedensellik bağları — kronik kaydının İÇİNDE, "
                 "kaynağın kendisinin kurduğu sebep–sonuç. İDDİA DEĞİL KAYIT: "
                 "her bağ needs_human_review=true; tarihçi onayı olmadan "
                 "atlas/analiz görünümüne bağlanmaz."),
        "_why_not_canonical": ("Şemadaki causes/consequences olay→olay PID bağı "
                               "bekler; bu bağlar kayıt-içidir. Şemayı zorlamak "
                               "yanlış veri üretirdi (bkz. docs/h36)."),
        "_provenance": ("Kaynak: 7 kronik okuma katmanı (11.253 olay) → "
                        "extract_causal_candidates.py (Arapça asılda kelime-sınırlı "
                        "işaret; 195 ar_strong aday) → LLM yapılandırılmış çıkarım "
                        "(iki denetim turunun kurallarıyla)."),
        "counts": {
            "examined": raw.get("total_examined"),
            "accepted": len(out),
            "by_link_type": dist("link_type"),
            "by_confidence": dist("confidence"),
            "by_effect_realized": dist("effect_realized"),
            "evidence_complete_true": sum(1 for x in out if x["evidence_complete"] is True),
            "cause_is_proposition_true": sum(1 for x in out if x["cause_is_proposition"] is True),
            "per_batch_stats": stats,
        },
        "records": out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = doc["counts"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  incelenen : {c['examined']} · kabul: {c['accepted']}")
    print(f"  link_type : {c['by_link_type']}")
    print(f"  güven     : {c['by_confidence']}")
    print(f"  sonuç     : {c['by_effect_realized']}")
    print(f"  kanıt tam : {c['evidence_complete_true']}/{c['accepted']}")
    print(f"  sebep önerme: {c['cause_is_proposition_true']}/{c['accepted']}")
    print("  TÜMÜ needs_human_review=true (yayın kapısı)")


if __name__ == "__main__":
    main()
