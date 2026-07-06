# Hafta 9 — Stage 2d: bulk-run teslimi (koşu kullanıcıda)

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Entry HEAD:** 84fae1c ("Hafta 9 Stage 2c: dia-tdv-scrape pilot …")
**Gate:** 2c pilot %100 geçti.

---

## Bu stage ne yapar

Tam koşu için **kendi kendine devam eden** araçları teslim eder ve **gece
başlatma komutunu** verir. **Bulk koşuyu OTURUM İÇİNDE BAŞLATMAZ** — kullanıcı
çalıştıracak (handoff §4/§5).

Teslim edilenler:
- `scrape.py --all` — resumable CLI (2b'de kuruldu, 2c'de 100 slug'la doğrulandı).
- `scrape.py --status` — **yeni**; sidecar'dan ilerleme özeti (done/remaining/
  coverage/flags), network'süz — 4.5 saatlik koşuyu izlemek için.
- `run_bulk.sh` — **yeni**; `caffeinate -i` (uyku engelle) + `nohup` (detach) +
  `logs/h9_scrape.log`; resumable; başlat/izle/durdur talimatlarını basar.

## Kapsam ve süre (ölçek düzeltmesi)

Handoff/proposal "~19.742 madde / ~11 saat" der; bu **chunk** sayısıdır. Fetch
birimi **madde = distinct slug = 8.093** → **~4,5 saat** (1 istek/2 sn). Pilotun
100 slug'ı sidecar'da "ok" → `--all` bunları atlar, **kalan 7.993 ≈ 4,4 saat**.
(`--status`: universe=8093, done=100, remaining=7993.)

## Gece başlatma — kullanıcı komutu

```bash
cd ~/Desktop/islamicatlas_canonical
bash pipelines/adapters/dia_tdv_scrape/run_bulk.sh
```

Eşdeğer ham tek-satır (script yerine):

```bash
caffeinate -i nohup python3 pipelines/adapters/dia_tdv_scrape/scrape.py --all \
    >> logs/h9_scrape.log 2>&1 &
```

**İzleme:**
```bash
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --status   # done/remaining/coverage
tail -f logs/h9_scrape.log                                     # canlı log (her 25 slug)
```
**Nazik durdurma (checkpoint + çıkış; yeniden başlatınca kaldığı yerden):**
```bash
pkill -INT -f dia_tdv_scrape/scrape.py
```
**Koşu bitince (2e için):**
```bash
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --assemble  # → dia_chunks_rich.json
```

## Dayanıklılık garantisi

- Checkpoint her 25 slug + koşu sonu, **atomik** (`os.replace`). Sert kill son
  checkpoint'ten bu yana ≤24 slug'ı yeniden fetch ettirir; nazik SIGINT'te
  kayıp 0.
- `--all` her çalıştırıldığında tamamlananları atlar (resume 2c'de kanıtlandı).
- Ham HTML gzipli + gitignore'lu; nezaket ADR-014 (1/2 sn, tanımlayıcı UA,
  Retry-After, cease-on-request).

## Bu stage ne YAPMAZ

- **Bulk koşuyu başlatmaz** (kullanıcı çalıştırır).
- Canonical/şema/`dia_chunks.json`'a dokunmaz.
- git invoke etmez; tag atmaz; `docs/h8/*` düzenlemez.

## Kabul kriterleri

- [x] Kendi kendine devam eden CLI + başlatma talimatı teslim edildi
      (`run_bulk.sh` + tek-satır + izleme/durdurma/assemble).
- [x] `--status` izleme aracı; `run_bulk.sh` `bash -n` temiz.
- [x] Süre/kapsam dürüstçe düzeltildi (8.093 slug ≈ 4,5 saat, 19.742/11 saat
      değil).
- [x] Kod değişikliği additive → `pytest tests/integration/` **98 passed** /
      3 skipped / 3 xfailed; `run_schema_tests` 15/15.

## Önerilen commit sekansı

```
git add pipelines/adapters/dia_tdv_scrape/scrape.py \
        pipelines/adapters/dia_tdv_scrape/run_bulk.sh \
        pipelines/adapters/dia_tdv_scrape/README.md \
        docs/h9/HAFTA9_STAGE_2d_BULK_READY.md docs/h9/H9_DECISION_LOG.md
git commit   # mesaj: "Expected commit message" (aşağıda)
```

### Expected commit message

```
Hafta 9 Stage 2d: dia-tdv-scrape bulk-run delivery (run kept to user)

- run_bulk.sh: overnight launcher (caffeinate -i + nohup + logs/h9_scrape.log;
  self-resuming); prints monitor/stop/assemble instructions
- scrape.py --status: progress summary from checkpoint sidecar (no network)
- README: bulk launch + --status + graceful-stop docs
- Scope/duration corrected: 8,093 distinct slugs (not 19,742 chunks) ≈ 4.5 h;
  pilot's 100 already done → 7,993 remaining. Bulk NOT started in-session.
- docs/h9/HAFTA9_STAGE_2d_BULK_READY.md + H9_DECISION_LOG Karar 5

Test:  tests/integration 98 passed / 3 skipped / 3 xfailed; run_schema_tests 15/15
Next:  2e (after user's bulk run): assemble + coverage stats + journal
```

## Rollback

`git revert <commit>` `--status` + `run_bulk.sh` + README/docs'u geri alır. Kod
additive; suite 98'de kalır (bu stage test eklemez, yalnız CLI kolaylıkları).
