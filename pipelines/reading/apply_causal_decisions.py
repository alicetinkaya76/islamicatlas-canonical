#!/usr/bin/env python3
"""Tarihçi kararlarını nedensellik katmanına işler (H37 — döngünün kapanan ucu).

AKIŞ
    ⚖️ Nedensellik Onayı ekranı → "Kararları indir" → causal_review_decisions.json
    → BU SCRIPT → data/sources/causal/causal_links.json güncellenir
    → make view-data → ekran neyin karara bağlandığını gösterir.

Bu script olmadan indirilen karar dosyası hiçbir yere gitmiyordu; araç ölü uçta
bitiyordu. Onay kapısının anlamı, kararın veriye DÖNMESİ.

KURALLAR (bu katmanın doktrini)
  - Karar YALNIZ dışarıdan gelir. Script hiçbir bağı kendi kararına bağlamaz.
  - `needs_human_review` yalnız KARARA BAĞLANAN kayıtta False olur; reddedilen
    kayıt SİLİNMEZ — `verdict: reject` ile durur (neyin neden elendiği,
    kabul edilenler kadar kayda değer bir bulgudur).
  - Eşleşmeyen karar anahtarı SESSİZ GEÇİLMEZ, sayılıp bildirilir.
  - Önceki kararın üzerine yazmadan önce uyarır (`--force` ister).

Kullanım:
    python3 pipelines/reading/apply_causal_decisions.py ~/Downloads/causal_review_decisions.json
    python3 pipelines/reading/apply_causal_decisions.py <dosya> --dry-run
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LINKS = REPO / "data" / "sources" / "causal" / "causal_links.json"

VALID = {"approve", "reject"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("decisions", help="ekrandan indirilen causal_review_decisions.json")
    ap.add_argument("--dry-run", action="store_true", help="yazma, yalnız raporla")
    ap.add_argument("--force", action="store_true", help="mevcut kararların üzerine yaz")
    a = ap.parse_args()

    dec_doc = json.loads(Path(a.decisions).read_text(encoding="utf-8"))
    decisions = dec_doc.get("decisions", dec_doc)     # ham sözlük de kabul
    doc = json.loads(LINKS.read_text(encoding="utf-8"))

    by_key = {f"{r['book_pid']}:{r['seq']}": r for r in doc["records"]}

    applied = overwritten = skipped_same = deferred = 0
    unmatched: list[str] = []
    invalid: list[str] = []

    for key, d in decisions.items():
        verdict = (d or {}).get("verdict") if isinstance(d, dict) else d
        if verdict not in VALID:
            # 'skip' KARAR DEĞİLDİR — tarihçi "şimdi karar vermiyorum" demiştir;
            # kayıt insan kuyruğunda KALIR. Hata değil, sayılır.
            if verdict in (None, "skip"):
                deferred += 1
            else:
                invalid.append(f"{key}={verdict}")
            continue
        rec = by_key.get(key)
        if rec is None:
            unmatched.append(key)
            continue
        prev = rec.get("review", {}).get("verdict")
        if prev == verdict:
            skipped_same += 1
            continue
        if prev and not a.force:
            print(f"  ! {key}: mevcut karar '{prev}' → '{verdict}'; --force gerekiyor")
            continue
        if prev:
            overwritten += 1
        rec["review"] = {
            "verdict": verdict,
            "at": (d or {}).get("at") if isinstance(d, dict) else None,
            "by": dec_doc.get("reviewer") or "historian",
            "source": dec_doc.get("source", "web CausalReview (H37)"),
        }
        # Karara bağlandı → artık insan kuyruğunda değil. Reddedilen kayıt da
        # karara bağlanmıştır; SİLİNMEZ, elenmiş olarak durur.
        rec["needs_human_review"] = False
        applied += 1

    total = len(doc["records"])
    decided = sum(1 for r in doc["records"] if r.get("review", {}).get("verdict"))
    approved = sum(1 for r in doc["records"] if r.get("review", {}).get("verdict") == "approve")
    rejected = decided - approved
    doc["counts"] = {**doc.get("counts", {}), "decided": decided,
                     "approved": approved, "rejected": rejected,
                     "pending": total - decided}

    print(f"karar dosyası : {Path(a.decisions).name}  ({len(decisions)} girdi)")
    print(f"  işlenen     : {applied}" + (f" (üzerine yazılan {overwritten})" if overwritten else ""))
    print(f"  zaten aynı  : {skipped_same}")
    if deferred:
        print(f"  ertelenen   : {deferred} (⏭ atlandı — kuyrukta kalır)")
    if unmatched:
        print(f"  EŞLEŞMEYEN  : {len(unmatched)} → {unmatched[:5]}{' …' if len(unmatched) > 5 else ''}")
    if invalid:
        print(f"  GEÇERSİZ    : {len(invalid)} → {invalid[:5]}")
    print(f"katman durumu : {total} bağ | onay {approved} · red {rejected} · bekleyen {total - decided}")

    if a.dry_run:
        print("(--dry-run: yazılmadı)")
        return
    if applied == 0:
        print("değişiklik yok; dosya yazılmadı.")
        return
    LINKS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {LINKS.relative_to(REPO).as_posix()}")
    print("sıradaki: python3 pipelines/frontend/build_causal_review.py  (veya make view-data)")


if __name__ == "__main__":
    main()
