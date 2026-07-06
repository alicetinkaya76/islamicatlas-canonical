# Hafta 9 — Stage 2b: dia-tdv-scrape scaffold + hijyen

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Entry HEAD:** 83b006a ("Hafta 9 Stage 2a: AO compliance gate + Phase-0 …")
**Gate:** 2a YEŞİL (ADR-014) → 2b açık.

---

## Bu stage ne yapar

AO scraper'ının iskeletini kurar (canlı toplu/pilot koşu YAPMADAN) ve
parser'ı offline testlerle sabitler:

1. `pipelines/adapters/dia_tdv_scrape/` adapter klasörü (source-üreten;
   `run_adapter.py`'ye bağlı DEĞİL).
2. Saf/deterministik `parse.py` + 8 offline unit test (sentetik fixture).
3. Nezaketli, resume'lu `scrape.py` CLI (fetch→parse→verify→gzip arşiv→
   checkpoint; `--assemble` ile rich dosya projeksiyonu).
4. Registry kaydı (`dia-tdv-scrape`, priority 330, enabled:false).
5. `.gitignore` hijyeni: `data/sources/dia_html/` + `data/sources/dia_chunks_rich.json`.
6. Checkpoint sidecar tasarımı: `data/_state/h9_scrape_progress.json` (zaten gitignore'lu).

## Mimari karar (Karar 3 — ADR-006 sapması)

Proposal §Phase 2 "manifest+extract+resolve+canonicalize dört dosya" der; bu
bir scraper için **literal gerçekleştirilemez**: (a) `extract.py` sözleşmesi
*"No network calls; deterministic"* der, (b) `run_adapter.py` `target_namespaces`
+ şema + `data/canonical/<ns>/` yazımı zorunlu kılar — AO ise ağ isteği yapan,
canonical değil **source** (`dia_chunks_rich.json`) üreten bir iştir. Çözüm:

- Klasör ADR-006 **lokalitesi** için var; iş bağımsız **`scrape.py`** CLI'ında.
- `parse.py` ağdan ayrık (offline test edilebilir); ağ + nezaket + checkpoint
  yalnız `scrape.py`'de.
- `manifest.target_namespaces: []` **bilinçli** → `run_adapter.py --id
  dia-tdv-scrape` "target_namespaces is empty" ile reddeder (kazayla
  çağrılmaya karşı guard).
- `dia_chunks_rich.json`, ileride **AP (dia_works, H10+)** için bir *source*
  olur — tıpkı `dia_chunks.json`'un `dia`/`v8` adapter'larına kaynak olması gibi.

## Files (touched)

| Path | Change |
|---|---|
| `pipelines/adapters/dia_tdv_scrape/parse.py` | Yeni — saf HTML→alan; `verify()` coverage metriği |
| `pipelines/adapters/dia_tdv_scrape/scrape.py` | Yeni — resume'lu polite CLI + `--assemble` |
| `pipelines/adapters/dia_tdv_scrape/manifest.yaml` | Yeni — source-üreten; politeness+verification config |
| `pipelines/adapters/dia_tdv_scrape/README.md` | Yeni — compliance + DOM sözleşmesi + kullanım |
| `pipelines/adapters/dia_tdv_scrape/__init__.py` | Yeni — boş paket |
| `pipelines/adapters/dia_tdv_scrape/tests/fixtures/*.html` | Yeni — 3 sentetik fixture (sahte içerik) |
| `tests/integration/test_dia_tdv_scrape_parse.py` | Yeni — 8 offline parser testi |
| `pipelines/adapters/registry.yaml` | dia-tdv-scrape kaydı (330, false) |
| `.gitignore` | dia_html/ + dia_chunks_rich.json |

## Doğrulama metriği (2a bulgusu → koda geçti)

Scraped `.m-content`, `dia_chunks.t`'yi **kapsar ama daha uzundur** (dipnot/
bibliyografya) → simetrik edit-ratio yanıltır. Gate: `chunk.t` token'larının
scraped gövdeye **coverage ≥ 0.95** + `h1==chunk.n` + `arabic==chunk.a`. Herhangi
bir sapma → `verify.flags` → kayıt `review` işaretlenir, ASLA sessiz kabul.

## Smoke-test kanıtı (2 slug; kalıcı koşu değil, iskelet doğrulaması)

`--slugs hassaf,abaka` → `ok=2`; hassaf `verify` coverage=1.0 flags=[]
(cilt 16 / sayfa 395 / baskı 1997 / müellif ABDÜLVEHHAB ÖZTÜRK). Tekrar koşu →
`2 already done · 0 to fetch` (**resume idempotent**). `--assemble` → 2-kayıtlı
lean rich dosya (0 review-flag). Tüm run-artifact'ları gitignore'lu (`git
status`'ta yok) ve stage sonunda temizlendi.

## Bu stage ne YAPMAZ

- Toplu/pilot koşu (8.093) YAPMAZ ve kalıcı progress bırakmaz — o 2c/2d.
- Canonical store'a hiçbir şey yazmaz; `dia_chunks.json`'a, şemalara dokunmaz.
- Yazarı canonical'a modellemez (person vs contributor namespace kararı AP/H10+).
- git invoke etmez (orchestrator konvansiyonu); önerilen sekans aşağıda.
- Tag atmaz. `docs/h8/*` düzenlemez.

## Kabul kriterleri

- [x] `pipelines/adapters/dia_tdv_scrape/` + registry girdisi (330, false).
- [x] `.gitignore` dia_html/ + dia_chunks_rich.json kapsıyor; `git status`'ta
      büyük blob staged değil (smoke run-artifact'ları gitignore doğrulandı).
- [x] `pytest tests/integration/` → **93 passed** (85+8 additive), 3 skipped,
      3 xfailed, 0 failed; `run_schema_tests` 15/15 değişmedi.
- [x] Parser gerçek örneklemde de doğru (hassaf 16/395, ahidname 2-parça,
      muhammed 19-parça — hepsi flags=[], coverage≈1.0).

## Önerilen commit sekansı (git'i orchestrator invoke etmez)

```
git add pipelines/adapters/dia_tdv_scrape/ \
        tests/integration/test_dia_tdv_scrape_parse.py \
        pipelines/adapters/registry.yaml .gitignore \
        docs/h9/HAFTA9_STAGE_2b_SCAFFOLD.md docs/h9/H9_DECISION_LOG.md
git commit   # mesaj: "Expected commit message" (aşağıda)
```

### Expected commit message

```
Hafta 9 Stage 2b: dia-tdv-scrape scaffold + hijyen — parser + resumable CLI

- pipelines/adapters/dia_tdv_scrape/: source-producing adapter (NOT run_adapter;
  target_namespaces:[] guard). parse.py (offline, deterministic; coverage-based
  verify), scrape.py (polite 1/2s, conditional GET, checkpoint/resume, gzip HTML
  archive, --assemble → dia_chunks_rich.json), manifest, README, __init__
- tests/integration/test_dia_tdv_scrape_parse.py: 8 offline parser tests vs
  synthetic fixtures (no TDV HTML committed; ADR-014). Suite 85→93 passed
- registry.yaml: dia-tdv-scrape (priority 330, enabled:false, compliance ADR-014)
- .gitignore: data/sources/dia_html/ + data/sources/dia_chunks_rich.json
- docs/h9/HAFTA9_STAGE_2b_SCAFFOLD.md + H9_DECISION_LOG Karar 3 (ADR-006
  deviation rationale; lean rich sidecar; coverage≥0.95 gate; scope 8,093 slugs)

Gate:  2a GREEN (ADR-014). Smoke (2 slugs) validated fetch/resume/assemble
Test:  tests/integration 93 passed / 3 skipped / 3 xfailed; run_schema_tests 15/15
Next:  2c pilot (50–100 slugs; coverage≥95%, resume test, integration tests)
```

## Rollback

`git revert <commit>` adapter klasörünü + registry satırını + gitignore
satırlarını + testi + docs'u birlikte geri alır. Suite 93→85'e döner (test
additive). Kod/veri/canonical dokunulmadığı için yan etkisiz.
