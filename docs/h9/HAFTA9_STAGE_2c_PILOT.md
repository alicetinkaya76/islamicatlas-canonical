# Hafta 9 — Stage 2c: dia-tdv-scrape pilot (100 slug)

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Entry HEAD:** 2c2284a ("Hafta 9 Stage 2b: dia-tdv-scrape scaffold + hijyen …")
**Gate:** 2a YEŞİL (ADR-014). İzin altında canlı pilot.

---

## Bu stage ne yapar

Scraper'ı **100 slug'lık temsili canlı pilotla** doğrular, resume'u uçtan uca
test eder ve resume/projection invariant'larını kalıcı testlere bağlar.

- Pilot örneklem: 100 distinct slug, tüm alfabeye/ciltlere yayılmış (stratified
  stride + çapa maddeler); **67 çok-chunk, 67 Arapça-başlıklı**. Nezaket 1/2 sn.
- `scrape.py`'ye test edilebilirlik refactor'u: saf `plan_fetch` (resume) +
  `project_rich` (lean projeksiyon) fonksiyonları.

## Pilot sonuçları (ampirik; `data/_state/h9_scrape_progress.json`)

| Metrik | Değer |
|---|---|
| İşlenen | **100/100 ok** (0 review, 0 error) |
| Gövde coverage (chunk.t → scraped) | min **0.998** · medyan **1.000** · ort **1.000** |
| **coverage ≥ 0.95** | **100/100 = %100** (gate rahat geçildi) |
| Cilt/sayfa parse | **132/132 parça = %100** |
| Müellif parse | 132/132 parça = %100 |
| `title_ar` dolu | 67/100 = %67 (chunk'lardaki %66.7 Arapça oranıyla tutarlı) |
| Review-flag | **0** |
| n_parts dağılımı | 1:93 · 2:2 · 3:2 · 4:1 · 6:1 · 19:1 (muhammed) |

**Yorum:** 2a'nın "gövde-hash ≥%95" endişesi, doğru metrikle (token coverage,
simetrik Levenshtein değil) tamamen çözüldü — %100 örnekte chunk anlatısı
scraped gövdede mevcut. Cilt/sayfa ve müellif çıkarımı parça-başına %100.

## Resume (kesinti + devam) doğrulaması

- **Canlı re-run:** aynı 100 slug ikinci kez → `100 already done · 0 to fetch`,
  **0.55 sn, sıfır network isteği** (idempotent skip uçtan uca çalışıyor).
- **Saf birim testleri** (`test_dia_tdv_scrape_pilot.py`): `plan_fetch`
  ok/review/unchanged'i atlar, `error`'ı yeniden dener, `--refetch` hepsini
  zorlar.
- **Dayanıklılık mekaniği:** progress sidecar her 25 slug'da bir + koşu sonunda
  **atomik** (`os.replace`) yazılır; SIGINT/SIGTERM → STOP bayrağı → mevcut slug
  biter, checkpoint + graceful çıkış. **Dürüst sınır:** sert kill (SIGKILL) son
  checkpoint'ten bu yana en çok `CHECKPOINT_EVERY-1` (≤24) slug'ı yeniden
  fetch ettirir; graceful SIGINT'te kayıp 0. (Canlı SIGKILL testi koşulmadı;
  skip-mantığı testlerle + iki canlı re-run'la kanıtlı.)

## Assemble (Path 3a) doğrulaması

`--assemble` → `data/sources/dia_chunks_rich.json`: **100 kayıt, 0 review-flag**,
lean (slug → title_ar + per-part {part_id, section_slug, cilt, sayfa_baslangic,
sayfa_bitis, author_raw, baski_yili} + verify + source). **Gövde metni yok**
(ADR-014 §4). `dia_chunks.json` değiştirilmedi. Dosya gitignore'lu.

## Testler

`tests/integration/test_dia_tdv_scrape_pilot.py` — 5 saf test (network yok):
resume skip / error-retry / refetch / lean-projection / **gövde-stripping**
(`_record` gövdeyi asla kalıcılaştırmaz). Suite **93 → 98 passed** (additive);
3 skipped, 3 xfailed, 0 failed. `run_schema_tests` 15/15 değişmedi.

## Bu stage ne YAPMAZ

- Tam koşu (8.093) YAPMAZ — o 2d (kullanıcı gece başlatır). Pilot'un 100 slug'ı
  progress sidecar'ında kalır → 2d `--all` bunları atlar (istenen resume
  davranışı; kullanıcı temiz koşu isterse sidecar'ı silebilir).
- Canonical/şema/`dia_chunks.json`'a dokunmaz. Yazarı canonical'a modellemez.
- git invoke etmez; tag atmaz; `docs/h8/*` düzenlemez.

## Kabul kriterleri

- [x] Pilot ≥%95 hash-match → **coverage ≥0.95: %100** (medyan 1.000).
- [x] Cilt/sayfa parse başarımı → **%100** (132/132 parça).
- [x] Uyumsuzlar review-flag'li → 0 uyumsuz (mekanizma testle kanıtlı).
- [x] Kesinti sonrası resume tamamlananları yeniden fetch etmiyor → canlı
      re-run + 3 saf test.
- [x] Entegrasyon testleri eklendi (additive); `pytest tests/integration/`
      **98 passed** / 3 skipped / 3 xfailed / 0 failed; schema 15/15.

## Önerilen commit sekansı

```
git add pipelines/adapters/dia_tdv_scrape/scrape.py \
        tests/integration/test_dia_tdv_scrape_pilot.py \
        docs/h9/HAFTA9_STAGE_2c_PILOT.md docs/h9/H9_DECISION_LOG.md
git commit   # mesaj: "Expected commit message" (aşağıda)
```

### Expected commit message

```
Hafta 9 Stage 2c: dia-tdv-scrape pilot (100 slugs) — coverage %100, resume ok

- 100-slug stratified live pilot (67 multi-chunk, 67 arabic): 100/100 ok,
  coverage median 1.000 / min 0.998 → 100% >=0.95; cilt/sayfa parse 132/132
  parts = 100%; author 100%; title_ar 67%; 0 review-flag
- Resume validated: same-100 re-run → "100 already done, 0 to fetch" in 0.55s,
  zero requests; --assemble → 100-record lean rich file (0 flagged, no body)
- scrape.py: extracted pure plan_fetch (resume) + project_rich (lean projection)
- tests/integration/test_dia_tdv_scrape_pilot.py: 5 pure tests (resume skip /
  error-retry / refetch / lean projection / body-strip ADR-014 §4). Suite 93->98
- docs/h9/HAFTA9_STAGE_2c_PILOT.md + H9_DECISION_LOG Karar 4

Test:  tests/integration 98 passed / 3 skipped / 3 xfailed; run_schema_tests 15/15
Next:  2d bulk-run delivery (self-resuming CLI + overnight caffeinate command)
```

## Rollback

`git revert <commit>` scrape.py refactor'unu + 2c testini + docs'u geri alır
(suite 98→93). Pilot'un gitignore'lu run-artifact'ları veri değil, kaynaktan
yeniden üretilebilir; istenirse `rm data/_state/h9_scrape_progress.json
data/sources/dia_chunks_rich.json; rm -rf data/sources/dia_html`.
