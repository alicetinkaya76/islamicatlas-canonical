#!/usr/bin/env python3
"""Nedensellik inceleme verisini arayüze yansıtır (H37).

NEDEN AYRI BİR ADIM: sidecar (`data/sources/causal/causal_links.json`) veri
tarafının doğrusu, ama tarayıcı `web/public/view-data/` altını okur. H37'de bu
kopya ELLE yapılmıştı → tam olarak H33'te kapattığımız "sessiz bayatlama"
sınıfına giren bir borç. Artık `make view-data` zincirinin bir halkası.

NE TAŞIR: kayıtların kendisi + inceleme için gereken kalite alanları.
NE TAŞIMAZ: karar. Kararlar tarihçinin; bu script onları ÜRETMEZ, yalnız
halihazırda işlenmiş olanları (`review.verdict`) arayüze taşır ki ekran neyin
karara bağlandığını gösterebilsin.

Çıktı: web/public/view-data/causal_review.json
Determinizm: kitap+seq sıralı, timestamp yok.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "data" / "sources" / "causal" / "causal_links.json"
OUT = REPO / "web" / "public" / "view-data" / "causal_review.json"
LINKS_OUT = REPO / "web" / "public" / "view-data" / "causal_reader_links.json"


def main() -> None:
    if not SRC.is_file():
        print(f"atlandı: {SRC.relative_to(REPO).as_posix()} yok (H36 hattı koşulmamış)")
        return

    doc = json.loads(SRC.read_text(encoding="utf-8"))
    records = sorted(
        doc["records"],
        key=lambda r: (r.get("book_pid") or "", r.get("seq") if r.get("seq") is not None else 0),
    )

    decided = sum(1 for r in records if r.get("review", {}).get("verdict"))
    approved = sum(1 for r in records if r.get("review", {}).get("verdict") == "approve")

    out = {
        "_doc": ("Nedensellik ONAY KUYRUĞU — kaynağın Arapça asılda kendi kurduğu "
                 "sebep–sonuç bağları. Hiçbiri iddia değil; tarihçi onayı olmadan "
                 "atlas/analiz görünümlerine GİRMEZ. Üretici: build_causal_review.py"),
        "_provenance": doc.get("_provenance"),
        "counts": {
            "records": len(records),
            "decided": decided,
            "approved": approved,
            "pending": len(records) - decided,
        },
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kb = OUT.stat().st_size // 1024
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | kayıt: {len(records)} "
          f"| karara bağlanan: {decided} (onay {approved}) | KB: {kb}")

    # ── Okuyucu köprüsü: YALNIZ ONAYLANANLAR, kitap→bölüm indeksinde ────────
    # Onay kapısının anlamı, onaylanan bağın METNİN YANINDA görünmesi. Bu indeks
    # kitap okunurken "kaynak bu bölümde şu sebep-sonucu kuruyor" rozetini besler.
    # ONAYSIZ HİÇBİR BAĞ BURAYA GİRMEZ — kapı veri düzeyinde uygulanır, UI'da değil.
    by_book: dict[str, dict[str, list]] = {}
    for r in records:
        if (r.get("review") or {}).get("verdict") != "approve":
            continue
        sec = r.get("sec")
        if sec is None:
            continue
        by_book.setdefault(str(r["book_pid"]), {}).setdefault(str(sec), []).append({
            "seq": r.get("seq"), "page": r.get("page"), "date_text": r.get("date_text"),
            "connector_ar": r.get("connector_ar"), "quote_ar": r.get("quote_ar"),
            "cause_tr": r.get("cause_tr"), "effect_tr": r.get("effect_tr"),
            "link_type": r.get("link_type"), "place_pid": r.get("place_pid"),
        })
    links_out = {
        "_doc": ("Okuyucuda gösterilen ONAYLANMIŞ nedensel bağlar (kitap → bölüm). "
                 "Onaysız bağ bu dosyaya GİRMEZ. Üretici: build_causal_review.py"),
        "counts": {"books": len(by_book),
                   "sections": sum(len(v) for v in by_book.values()),
                   "links": sum(len(x) for v in by_book.values() for x in v.values())},
        "by_book": by_book,
    }
    LINKS_OUT.write_text(json.dumps(links_out, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    c = links_out["counts"]
    print(f"yazıldı: {LINKS_OUT.relative_to(REPO).as_posix()} | onaylı bağ: {c['links']} "
          f"| {c['books']} kitap · {c['sections']} bölüm")


if __name__ == "__main__":
    main()
