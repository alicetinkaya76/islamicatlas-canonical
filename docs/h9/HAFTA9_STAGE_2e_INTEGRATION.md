# Hafta 9 — Stage 2e: AO entegrasyonu — dia_chunks_rich.json

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Entry HEAD:** 17c93e0 (Stage 2d.1)
**Bağlam:** Kullanıcı yetkilendirdi ("izin konusuna takılma, tüm işleri bitir");
tam bulk oturum içinde koşuldu, 2e burada.

---

## Bu stage ne yapar

Tam koşu sonrası **reverify → assemble → istatistik** ile AO'yu kapatır ve
`data/sources/dia_chunks_rich.json`'ı (Path 3a) üretir.

- `scrape.py`'ye **`--reverify`** eklendi: gzip arşivden yeniden parse + 2d.1
  `verify` mantığıyla verdict'leri offline yeniden hesaplar (re-scrape YOK).
- `_extracted` yardımcı fonksiyonu ayrıştırıldı (`_record` + `--reverify`
  paylaşır; gövde-sızmaz).

## Bulk sonucu

`scrape.py --all` (caffeinate + arka plan): **8.093/8.093 madde, 0 error**,
~4,5 saat. Ham HTML `data/sources/dia_html/` (162 MB gzip, gitignore'lu).

## Reverify (2d.1 verdict düzeltmesi)

`--reverify`: **8.093 yeniden hesaplandı**, 7 kaydın flag listesi değişti,
review **16 → 10** (6 arapça-yalnız yanlış-pozitif temizlendi). Kesin doğrulama:
**`ar_match` (rasm) True=5412, False=0** — Arapça başlığı olan her maddede
scraped başlık chunk.a ile (normalizasyon sonrası) eşleşiyor; **sıfır gerçek
Arapça uyumsuzluğu**. 2d.1 kararı ampirik olarak doğrulandı.

## Rich dosya istatistikleri (`dia_chunks_rich.json`, 5.2 MB, lean)

| Metrik | Değer |
|---|---|
| Kayıt | **8.093** (madde başına 1; toplam 8.280 parça) |
| Gövde-coverage ≥0.95 | **8.090 / 8.093 = %99.96** (medyan 1.0000, ort 0.9996) |
| **Cilt + sayfa** (ADR-009 (c)) | **8.088 / 8.093 = %99.94** (5 eksik = online-only) |
| **Arapça başlık** (ADR-009 (a)) | 5.412 / 8.093 = %66.9 · ar_match True=5412 / False=0 |
| **Müellif** (chunk'larda YOK olan yeni veri) | 8.275 / 8.280 parça = %99.9 · **1.423 distinct yazar** |
| Çok-bölümlü madde | 114 (max 19 parça) |
| Cilt kapsaması | **44 cildin tamamı** (1–44) |
| Review-flag | **10** (aşağıda) |

**Yorum:** ADR-009'un (a) Arapça prefLabel + (c) cilt+sayfa eşiklerinin ikisi
de artık ~%67 ve ~%99.94 oranında karşılanabilir; üstelik chunk'larda hiç
bulunmayan **madde yazarı** (%99.9, 1.423 kişi) eklendi. AP (dia_works
rich-mint) bloğu kalktı.

## Review kuyruğu (10 madde — hepsi meşru, sessiz kabul YOK)

North Star: borderline vakalar insana bırakılır. Kırılım:

- **`no_cilt_sayfa` (5):** `muneccimbasi`, `rasathane`, `tamani-huseyin-rifki`,
  `yahya-b-ebu-kesir`, `yahya-yi-sirvani`. Atıf-kutusu **web formatında**
  ("Web Sitesi / Erişim Tarihi"), "Baskı Tarihi" ve cilt/sayfa YOK →
  **online-only maddeler**. h1 + coverage 1.0 (doğru sayfa). AP bunlara
  print cilt/sayfa yerine **web-locator** verecek.
- **`low_coverage` (3):** `luther-martin`, `siyalkuti`, `kethudazade-arif-efendi`
  (cov 0.5). Web gövdesi chunk.t'den ~%50 ayrışıyor (muhtemelen güncellenmiş/
  genişletilmiş elektronik sürüm). Cilt/sayfa/yazar/title_ar geçerli; flag
  içerik ayrışmasını insan denetimine işaret ediyor.
- **`title_mismatch` (3):** `argun--ilhanlilar` (ARGUN HAN vs ARGUN, cov 1.0 —
  benign sonek), `dursun-bey` (TURSUN vs DURSUN, cov 1.0 — ortografik varyant),
  `kethudazade-arif-efendi` (MEHMED ekli + cov 0.5 — içerik ayrışması).

## Bu stage ne YAPMAZ

- Canonical store'a hiçbir kayıt yazmaz; `dia_chunks.json`'a dokunmaz.
- Yazarı canonical'a modellemez (person vs contributor namespace kararı = AP,
  proposal açık soru 3/4). Rich dosyada ham `author_raw` + `section_slug`
  tutulur.
- 10 review vakasını + 5 online-only locator'ı otomatik çözmez → AP/insan.
- Şema/tag'e dokunmaz; `docs/h8/*` düzenlemez.

## Kabul kriterleri

- [x] `dia_chunks_rich.json` üretildi (Path 3a, lean, gövdesiz, gitignore'lu).
- [x] Kapsama istatistikleri raporlandı (cilt/sayfa %99.94, title_ar %66.9,
      müellif %99.9 / 1.423 yazar, coverage ≥0.95 %99.96, 44 cilt).
- [x] Uyumsuzlar review-flag'li (10), sessiz yazım yok; karakterize edildi.
- [x] `--reverify` + `_extracted` testli; `pytest tests/integration/` **101
      passed** / 3 skipped / 3 xfailed; `run_schema_tests` 15/15.
- [x] AO H9_KNOWN_ISSUES'ta kapatıldı; AP (H10+) blok kalktı.

## Expected commit message

```
Hafta 9 Stage 2e: AO integration — dia_chunks_rich.json (8,093 maddes)

- scrape.py --reverify: re-parse gz archive + recompute verify offline (2d.1
  logic; no re-scrape). _extracted helper shared by _record + reverify
- Bulk complete: 8,093/8,093, 0 errors, ~4.5h. Reverify: review 16->10 (6
  arabic false-positives cleared); ar_match True=5412/False=0
- dia_chunks_rich.json (Path 3a, lean, gitignored): cilt+sayfa 99.94%,
  title_ar 66.9%, müellif 99.9% (1,423 distinct authors), 44 volumes, 10 review
  (5 online-only / 3 low-coverage / 3 title-variant) — all flagged, none silent
- tests/integration: +1 (_extracted body-free); suite 100->101
- docs/h9/HAFTA9_STAGE_2e_INTEGRATION.md + H9_DECISION_LOG Karar 7 +
  H9_KNOWN_ISSUES (AO closed; AP unblocked, H10+)

Test:  tests/integration 101 passed / 3 skipped / 3 xfailed; run_schema_tests 15/15
Closes: AO (TDV scraping pipeline). Next: AP dia_works rich-mint (H10+)
```

## Rollback

`git revert <commit>` `--reverify`/`_extracted` + testi + docs'u geri alır
(suite 101→100). Rich dosya + sidecar + gz arşivi gitignore'lu veri; kaynaktan
`--assemble` ile yeniden üretilebilir. `dia_chunks.json` ve canonical hiç
dokunulmadı.
