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


if __name__ == "__main__":
    main()
