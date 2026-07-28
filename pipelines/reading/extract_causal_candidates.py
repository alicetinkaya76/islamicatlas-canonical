#!/usr/bin/env python3
"""Nedensellik adaylarını ayıklar (H36 — kaynak-tanıklı nedensellik, adım 1/2).

İLKE (bu katmanın en kritik kuralı):
    Nedensellik bir YORUMDUR. Bu hat, tarihsel neden-sonuç İDDİASI ÜRETMEZ.
    Yalnız **kaynağın kendisinin, Arapça asılda kurduğu** nedensel ifadeyi
    birebir pasajıyla yakalar. Çıkarım/yorum/tahmin yapılmaz.

ADIM 1 (bu script): ucuz filtre — 7 kroniğin 11.253 olayından Arapça nedensel
işaret taşıyanları ayıklar ve GÜÇ SINIFINA ayırır:
    ar_strong   415  — açık ta'lîl (وذلك أن، لأن، بسبب…) veya mef'ûlün leh
                       (خوفا، طمعا، عصبية…). Asıl değerli küme.
    ar_weak   2.288  — çok anlamlı (فلما، حتى، إذ…): zaman/gaye de olabilir;
                       çıkarım adımı bunları VARSAYILAN OLARAK REDDEDER.
    (atlanan)   195  — Türkçe özette nedensellik var, Arapça asılda YOK.

ADIM 2 (ayrı): yapılandırılmış çıkarım — sebep/sonuç ifadesi + bağlaç + pasaj.

DENETİM DERSİ (pilot sonrası, bu sürümün varlık sebebi): ilk sürüm Türkçe
özete de bakıyordu ve pilot kabullerinin çoğu fa-lammâ ZAMAN çerçevesini sebep
sanıyordu. Denetçi "bu haliyle ölçeklenmemeli" dedi; filtre Arapça asıla
taşındı, güç sınıfı eklendi. Ayrıntı: docs/h36/.

Çıktı: data/_state/causal_candidates.json
Determinizm: kitap+seq sıralı, timestamp yok.
"""

import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
READING = REPO / "web" / "public" / "reading"
OUT = REPO / "data" / "_state" / "causal_candidates.json"

# ── DÖNGÜSELLİK ONARIMI (denetim bulgusu, H36) ───────────────────────────────
# İlk sürüm Türkçe `summary_tr`'ye de bakıyordu. Ama summary_tr ÖNCEKİ BİR LLM
# ADIMININ ürünüdür → "kaynağın kurduğu bağ" ölçütü pratikte "önceki LLM'in
# kurduğu bağ"a dönüşüyordu (havuzun %58,3'ü yalnız TR işaretle giriyordu).
# KANIT: seq 13'ün Türkçe özeti "…yüzünden… bunun üzerine…" diyor, Arapça asılda
# yalnız "من … حتى" var. Artık KANIT YALNIZ ARAPÇA ASILDAN gelir; Türkçe işaret
# tek başına aday YAPMAZ, yalnız `tr_hint` olarak kaydedilir.
#
# Ayrıca işaretler GÜÇ SINIFINA ayrıldı — denetim, en güçlü kanıt tipinin
# (açık ta'lîl / mef'ûlün leh) havuz DIŞINDA kaldığını ölçtü (1.054 kayıt).

# A) Açık ta'lîl — kaynağın doğrudan gerekçe bildirmesi (en güçlü kanıt)
MARKERS_AR_STRONG = ["وذلك أن", "لأن", "بسبب", "من أجل", "لأجل", "مما أدى",
                     "فترتب", "على إثر", "نتيجة", "لعلة", "بعلة"]
# B) Mef'ûlün leh — eylemin gerekçesini bildiren mansûb masdar (güçlü)
MARKERS_AR_MOTIVE = ["خوفا", "طمعا", "عصبية", "رغبة في", "كراهية", "حرصا",
                     "طلبا", "انتقاما"]
# C) Zayıf/çok anlamlı — TEK BAŞINA nedensellik kanıtı DEĞİL (zaman/gaye olabilir);
#    aday yapar ama çıkarım adımı bunları varsayılan olarak REDDEDER.
MARKERS_AR_WEAK = ["فلما", "ولما", "لما", "حتى", "إذ", "حيث", "بعد أن",
                   "فأدى", "لذلك", "فلذلك", "إثر"]

# Türkçe işaretler: KANIT DEĞİL, yalnız ipucu (türev metinden gelir).
MARKERS_TR = ["sebebiyle", "yüzünden", "sonucunda", "neden oldu", "yol açtı",
              "bunun üzerine", "dolayısıyla", "bu sebeple", "bu yüzden",
              "sebep oldu"]


def hits(blob_ar: str, blob_tr: str) -> dict:
    """Arapça asıldan KANIT, Türkçe özetten yalnız İPUCU toplar."""
    strong = [m for m in MARKERS_AR_STRONG if m in blob_ar]
    motive = [m for m in MARKERS_AR_MOTIVE if m in blob_ar]
    weak = [m for m in MARKERS_AR_WEAK if m in blob_ar]
    low = blob_tr.lower()
    tr_hint = [m for m in MARKERS_TR if m in low]
    if strong or motive:
        tier = "ar_strong"
    elif weak:
        tier = "ar_weak"
    elif tr_hint:
        tier = "tr_only"          # ADAY DEĞİL — yalnız kayıt için işaretlenir
    else:
        tier = None
    return {"tier": tier, "strong": strong, "motive": motive,
            "weak": weak, "tr_hint": tr_hint}


def main():
    shelf = json.loads((READING / "core_shelf.json").read_text(encoding="utf-8"))
    out = []
    tr_only_skipped = []
    scanned = 0
    for b in shelf["books"]:
        lp = READING / b["pidnum"] / "layer.json"
        if not lp.is_file():
            continue
        layer = json.loads(lp.read_text(encoding="utf-8"))
        if layer.get("kind") != "events":
            continue
        for r in layer["records"]:
            scanned += 1
            # KANIT yalnız Arapça asıldan (quote_ar). summary_ar da türev
            # olabileceği için kanıt setine ALINMAZ.
            ar = r.get("quote_ar") or ""
            tr = (r.get("summary_tr") or "") + " " + (r.get("title_tr") or "")
            h = hits(ar, tr)
            if h["tier"] in (None, "tr_only"):
                # tr_only: Türkçe özet nedensellik ima ediyor ama Arapça asılda
                # işaret YOK → aday DEĞİL (döngüsellik önlemi). Sayımı raporlanır.
                if h["tier"] == "tr_only":
                    tr_only_skipped.append({"book": b["name_tr"], "seq": r.get("seq")})
                continue
            out.append({
                "book_pid": b["pidnum"],
                "book": b["name_tr"],
                "seq": r.get("seq"),
                "sec": r.get("sec"),
                "page": r.get("page"),
                "title_tr": r.get("title_tr"),
                "date_text": r.get("date_text"),
                "event_type": r.get("event_type"),
                "place_pid": r.get("place_pid"),
                "trigger_tier": h["tier"],          # ar_strong | ar_weak
                "markers_strong": h["strong"] + h["motive"],
                "markers_weak": h["weak"],
                "tr_hint": h["tr_hint"],            # yalnız bilgi, kanıt değil
                "quote_ar": r.get("quote_ar"),
                "summary_tr": r.get("summary_tr"),
            })
    out.sort(key=lambda x: (x["book_pid"], x["seq"] if x["seq"] is not None else 0))
    doc = {
        "_doc": ("Nedensellik ADAYLARI — kaynağın kendi nedensel ifadesini taşıyan "
                 "kronik olayları. İDDİA DEĞİL, aday havuzu; yapılandırılmış "
                 "çıkarım ayrı adımda. Üretici: extract_causal_candidates.py"),
        "counts": {
            "scanned": scanned,
            "candidates": len(out),
            "ar_strong": sum(1 for x in out if x["trigger_tier"] == "ar_strong"),
            "ar_weak": sum(1 for x in out if x["trigger_tier"] == "ar_weak"),
            "tr_only_skipped": len(tr_only_skipped),
        },
        "records": out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  taranan olay : {scanned}")
    print(f"  aday         : {len(out)}")
    print(f"    ar_strong (açık ta'lîl/mef'ûlün leh): {doc['counts']['ar_strong']}")
    print(f"    ar_weak   (zaman/gaye — varsayılan RED): {doc['counts']['ar_weak']}")
    print(f"  TR-only ATLANDI (döngüsellik önlemi)     : {len(tr_only_skipped)}")
    from collections import Counter
    per = Counter(x["book"][:28] for x in out)
    for k, v in per.most_common():
        print(f"    {k:<30} {v:>5}")


if __name__ == "__main__":
    main()
