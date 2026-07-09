# Hafta 9 — Stage 4: Test altyapısı + CI + geliştirici araç katmanı

**Date:** 2026-07-07
**Branch:** hafta5-work-namespace
**Entry:** Stage 3 remediation'ının üstüne; aynı incelemenin test/CI bulguları.

---

## Bu stage ne yapar

### A. Suite hızlandırma (ölçüm-temelli)

- **`tests/integration/conftest.py`** (yeni): `lru_cache`'li paylaşılan
  yükleyiciler — person store 3×, place store ~9× diskten yükleniyordu
  (modül-scope fixture'lar paylaşamaz); artık süreç başına 1×. Modül
  fixture'ları ince delegasyona çevrildi (dia_pilot, work_pilot, v8_pilot).
- **Multiprocessing DENENDİ ve REDDEDİLDİ** (dürüst mühendislik kaydı):
  tüm-store validasyonunun 8-worker spawn fan-out'u benchmark'landı — macOS
  spawn'da worker-başı interpreter + jsonschema import maliyeti person
  geçişini suite içinde 5.5 s → 7.3 s'ye YAVAŞLATTI. Sıralı + cache'li
  `validate_all()` kaldı; karar conftest docstring'inde.
- **`slow_fullstore` marker'ı** (pytest.ini'de kayıtlı): 3 tüm-store
  validasyon testi işaretli → **iç döngü `make test-fast` ≈ 8-10 sn**
  (önce tek seçenek 31 sn'lik tam suite'ti). Tam kapı `make test`.
- Bayat `__pycache__` temizliği (pyc'ler LaCie klonundan derlenmişti —
  traceback'ler 2 commit geride dosya gösteriyordu).

### B. Sessiz/ölü kapsamın açılması

- `test_schema_fixtures.py` (yeni): run_schema_tests'in 15 fixture kontrolü
  artık pytest İÇİNDE de (tek komut; CLI script duruyor, mantık kopyalanmadı).
- `test_dia_chunks_rich.py` (yeni, 4): AP'nin tek girdisinin invariant'ları
  (8.093 sayımı, ADR-014 §4 gövde-sızmazlığı, kapsama tabanları, 5
  online-only'nin flag'li kalması). Dosya yoksa temiz skip.
- `test_truncate_sentence_boundary.py` (yeni, 3): H8 postmortem'li fonksiyonun
  H8'den beri açık test TODO'su — seed=42'li 500-girdili fuzz ile
  `len(out) <= max_len` invariant'ı (production'da patlayan buydu).
- `test_g3` skip→xfail (eski skip+assert-True HİÇBİR koşulda kırmızı olamayan
  ölü testti); c1/e3 xfail gerekçeleri "Hafta 6" bayatlığından güncel
  milestone'lara (AP/H10+) güncellendi — eşikler ESNETİLMEDİ.
- `test_bosworth_pilot.py` (pytest'in toplamadığı script): person/place/work
  store doluyken `data/_state`'i (46K kaydın PID state'i!) silen rmtree'ye
  `--force-clean` guard'ı. Pytest'e dönüştürme Faz 0.5 kalemi.
- `test_yaqut_pilot.pipeline_state`: store eksikse 3 adapter'ı OTOMATİK koşan
  fixture → `pytest.skip` (eski davranış `IAC_TEST_BOOTSTRAP=1` ile opt-in).
  Test artık veri mutasyona uğratmaz; taze clone'da dakikalarca koşu yok.
- `test_dia_pilot.py`: store yokken 8 hard-fail → modül-düzeyi `skipif`
  (CI/taze clone yeşil; lokalde davranış aynı).
- DH-1 sertleştirmesi: `count_files` varsayılanı `iac_*.json`; a2 AppleDouble
  ayrımı; conftest `record_files()` desen-güvenli.

### C. CI + araçlar

- **`.github/workflows/ci.yml` yeniden yazıldı.** Eski workflow çifte
  bozuktu: `smoke-test-audit` var olmayan `scripts/week1_audit.py`'yi çağırıyor
  (her push kırmızı), şema adımı boş `schema/canonical/*` glob'uyla 0 dosya
  doğrulayıp YEŞİL görünüyordu (üstelik Draft7 ile — set 2020-12) ve yalnız
  `main`'i dinliyordu (iş `hafta*`'da). Yenisi: `hafta*` + main tetikleyicisi,
  `pip install -r requirements.txt`, **`make test`** (lokalle tek doğruluk
  kaynağı); ruff ayrı advisory job (gerçek yollara).
- **`requirements.txt`** (yeni; kökte hiç yoktu) + **`Makefile`**
  (test / test-fast / schema / reindex-dry / scrape-status) + **`pytest.ini`**.
- `CODEOWNERS`: var olmayan `/schema/canonical|vocab/` → `/schemas/`.
- `.gitignore` += `tmp/` (oturum karalamaları `git status`'u kirletiyordu).

## Ölçümler (önce → sonra)

| Metrik | Önce | Sonra |
|---|---|---|
| `pytest tests/integration` | 101 passed / 3 skipped / 3 xfailed · ~31 sn | **147 passed / 2 skipped / 3 xfailed · ~21-35 sn** |
| İç döngü | yok (tek mod) | **`make test-fast` ~9 sn** |
| CI | her push kırmızı (bozuk job) + sahte-yeşil şema adımı | gerçek suite; taze-clone yeşili guard'larla |
| Store disk yükleri | person 3×, place ~9× | süreç başına 1× |

147'nin dökümü: 101 eski + 15 schema-fixture + 16 lib (2'si diff-review sonrası
session istisna/deadlock kilidi) + 6 search/ui + 4 rich + 3 truncate + 1 PE2.5
(Stage 5'in newline bekçisi) + b2 (xfail→passed);
skip 3→2 (g3 artık xfail), xfail 3 (c1, e3, g3).

## Kabul

- [x] `make test` uçtan uca yeşil (schema 15/15 + projector 3/3 + resolver
      5/5 + pytest 147).
- [x] Suite hiçbir testte zayıflatılmadı: eşik esnetme yok; skip→xfail
      dönüşümleri görünürlüğü ARTIRIR; tüm eski testler korunur.
- [x] CI tarifinin storeless-yeşil olduğu guard'larla sağlandı (dia_pilot
      skipif + yaqut skip + rich skip).

## Rollback

Tek revert; conftest delegasyonları modül fixture'larının eski gövdeleriyle
birlikte döner (aynı commit). Davranışsal risk: yalnız test katmanı + CI.
