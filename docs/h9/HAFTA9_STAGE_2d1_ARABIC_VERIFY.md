# Hafta 9 — Stage 2d.1: Arapça başlık doğrulaması → advisory (rasm)

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Entry HEAD:** 2707ab3 (Stage 2d). Bulk koşusu sürerken keşfedildi.

---

## Tetikleyici

Bulk'ın ilk ~625 maddesinde 6 review-flag belirdi; **hepsi `arabic_mismatch`
ve hepsinde `h1_match=True` + `coverage=1.0`** — yani doğru madde çekilmiş,
başlık açıkça doğru (ör. `العبّاس` = ABBAS).

## Kök neden

`dia_chunks.a` (ör. `عباس بن احمد`) ile scraped `arabic_title`
(ör. `العبّاس بن أحمد`) **aynı ismin farklı normalizasyonu**: chunk formu
belirlilik takısı `ال`'siz + hamza indirgenmiş + harekesiz; DiA formu tam
harekeli + `ال`'li + hamza'lı. Ham string eşitliği (harekesi bile stripleyerek)
doğru sayfalarda bile sık sık başarısız → gürültülü review tetikleyicisi.

## Karar (bkz. H9_DECISION_LOG Karar 6)

Arapça başlık **advisory** yapıldı:
- **Review-blocking flag'ler** yalnız gerçek kuşkuyu gösterenler:
  `title_mismatch` (h1 ≠ chunk.n), `low_coverage` (chunk.t ⊄ scraped gövde),
  `no_cilt_sayfa`. Kimlik bunlarla kesinleşir.
- `ar_match` **rasm** (ünsüz iskelet: harekat/tatweel at, hamza/alif/ya/ta-marbuta
  katla, `ال` sıyır) ile hesaplanır ve **kaydedilir** (sonra elle spot-check
  için), ama h1 + coverage kimliği doğruluyorken review'a **sokmaz**.

North Star uyumu: flag = gerçek şüphe; yanlış sayfa zaten h1+coverage ile
yakalanır (arabic'ten bağımsız).

## Doğrulama

- 6 flagged kayıt gerçek gzip HTML'den yeniden parse edilip yeni `verify`'la
  hesaplandı → **hepsi `flags=[]`, `ar_match=True`** (rasm `ال`+hamza'yı
  katladı → aslında eşleşiyorlar).
- Parser testleri 8 → **10** (advisory davranışı + rasm birim testi).
- `pytest tests/integration/` 98 → **100 passed**; `run_schema_tests` 15/15.

## Koşan bulk üzerine etki

Koşan `--all` süreci parse.py'yi belleğe yüklemiş → **eski mantıkta devam
eder**; extracted VERİ (title_ar/cilt/sayfa/müellif) doğru, yalnız sidecar'daki
`verify.flags` arabic açısından bayat kalır. **2e** tüm verdict'leri yeni
mantıkla **offline yeniden hesaplar** (saklı title_tr/title_ar/parts +
gzip HTML'den coverage) — re-scrape YOK. Bulk kesintiye uğratılmadı.

## Bu stage ne YAPMAZ

- Bulk'ı durdurmaz/yeniden başlatmaz. Extracted veriyi değiştirmez. Canonical/
  şema/`dia_chunks.json`'a dokunmaz. Tag atmaz.

## Kabul kriterleri

- [x] Arabic advisory; review flag'leri title/coverage/cilt ile sınırlı.
- [x] 6 flagged kayıt yeni mantıkla temiz (flags=[]).
- [x] `pytest tests/integration/` 100 passed; schema 15/15.

## Expected commit message

```
Hafta 9 Stage 2d.1: Arabic-title verification -> advisory (rasm-normalized)

- parse.py: arabic_mismatch removed from review-blocking flags; ar_match now
  rasm-compared (drop harakat/tatweel, fold hamza/alif/ya/ta-marbuta, strip
  ال) and advisory only. Review flags = title_mismatch / low_coverage /
  no_cilt_sayfa (h1 + coverage are the identity guarantee)
- Root cause: dia_chunks `a` is a reduced normalization of the DiA vocalized
  title; string inequality is common for CORRECT pages (first 6 bulk flags all
  had h1_match + coverage 1.0)
- tests: +2 (advisory-not-review, rasm); suite 98->100. 6 real flagged records
  recompute to flags=[] ar_match=True
- Running bulk keeps old in-memory logic; 2e recomputes verdicts offline
- docs/h9/HAFTA9_STAGE_2d1_ARABIC_VERIFY.md + H9_DECISION_LOG Karar 6

Test:  tests/integration 100 passed / 3 skipped / 3 xfailed; run_schema_tests 15/15
```

## Rollback

`git revert <commit>` verify'ı eski (arabic-flags) davranışa döndürür; suite
100→98. Veri dokunulmadı.
