# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Phase 0 için bir sürüm stratejisi:

- `0.1.x` — Week 1 audit + initial schemas (pre-ER)
- `0.2.x` — Week 3-4 Entity Resolution complete
- `0.3.x` — Week 5 Canonical store + ETL complete
- `0.4.x` — Week 6 API + derivative builder
- `0.5.x` — Week 7-8 Search + tests
- `1.0.0` — Phase 0 complete, DOI'li Zenodo dump

> **Not (H9 Stage 5):** Yukarıdaki proje-sürümü ekseni, **schema-set etiketi**
> (ADR-013; şu an v0.3.0) ile AYRI eksenlerdir — schema-set etiketi 11 şema
> dosyasının `$id`'lerini sürümler, proje release'ini değil. Haftalar fiilen
> plan tablosundan hızlı ilerledi; aşağıdaki [Unreleased] retrospektifi
> gerçekleşeni hafta-hafta kaydeder (sayılar journal'lardan; SHA'lar commit
> grafiğinden).

---

## [Unreleased] — H2→H9 retrospektifi (Phase 0 gövdesi)

### Hafta 2-3 — dynasty + place seed
- Bosworth NID adapter'ı: 186 dynasty (`hafta2` dizisi).
- Yâqūt (12,954) + Muqaddasī (2,070) + Le Strange augment → 15,239 place;
  iki-geçişli integrity (parent/capital backfill).

### Hafta 4 — person seed (`5fb02a7` main tepesi)
- DİA (~7,3K) + el-Aʿlām two-track (~12,5K yeni) + science-layer (182) +
  Bosworth rulers fix-up → person namespace; Wikidata recon cache + seed.

### Hafta 5-7 — work seed + ER + QID hijyeni (`hafta7-close` = `8833ec0`)
- OpenITI + science-works → 9,330 work + Hassâf elle rich-mint (9,331.
  kayıt); ADR-008 resolver, ADR-009 rich-mint doktrini (dia_works sığ mint
  YASAK); H7 QID audit + frontend display-gate.
- work.schema $id v0.2.0'a bump (PE-2 driftinin doğuşu — H9'da kapandı).

### Hafta 8 — PE-1 + dia_chunks person enrichment (`a41642d`, `hafta8-close`)
- ADR-010 `digital_corpus` enum + ADR-012 description maxLength 50K.
- `dia-person-enrichment-v8`: 3,309 Cat A kişi tam anlatı upgrade'i
  (%76.5 description büyümesi); truncate marker bug'ı bulunup düzeltildi.
- ADR-011 v1.1 (`a` alanı = Arapça başlık düzeltmesi); AO/AP planı yazıldı.

### Hafta 9 — PE-2 + AO scraper + review remediation (`89cfd79` → …)
- Stage 1 (`89cfd79`): 11 dosyalık şema seti atomik **v0.3.0** + ADR-013
  (set-düzeyi semver, test-pinli).
- Stage 2a-2e (`83b006a`→`12dc460`): **AO** — ADR-014 compliance gate (İSAM
  yazılı izni; robots `Allow:/`), dia-tdv-scrape adapter'ı, 8,093 madde
  (~4,5 saat, 0 hata) → `dia_chunks_rich.json`: cilt+sayfa %99.94, Arapça
  başlık %66.9, **1,423 madde yazarı** (chunk'larda yoktu); 10 kayıt insan
  incelemesine işaretli. AP (dia_works) bloğu kalktı.
- Stage 3-5: 56-ajanlık repo incelemesinin remediation'ı — work-PID state
  onarımı (9331 çakışma bombası), recon offline-TTL, el-alam Track-A kaybı,
  projector @id-tabanlı tip çıkarımı (46,702/46,702 projeksiyon), suite
  101→147 test + `make test-fast` (~9 sn), CI'ın gerçek suite'i koşması,
  kök dizin arşivi, bu retrospektif. Ayrıntı: `docs/h9/` + PHASE0_CLOSEOUT.

---

## [0.1.0] — 2026-04-21

İlk commit. Phase 0 kickoff paketi.

### Added
- **Planning docs**
  - `docs/phase0-canonical-data-foundation.md` — 8 haftalık master plan
  - `docs/fatima-kickoff.md` — co-lead onboarding
  - `docs/meeting-01-agenda.md` — ilk toplantı gündemi
  - `docs/meeting-01-notes.template.md` — toplantı sonrası notlar template
  - `docs/setup-github.md` — adım adım GitHub kurulum rehberi (label'lar, milestone'lar, kanban, ilk issue'lar, Fatıma davet)
  - `docs/canonical_scope.md` — Week 1 Ali deliverable: 47 dosyanın in-scope / auxiliary / backup-delete / defer kategorilere ayrımı
- **Ready-to-paste GitHub issues**
  - `issues/001-week1-audit.md` — Fatıma için audit koşusu
  - `issues/002-canonical-scope.md` — Ali için scope kararı
  - `issues/003-adr-001-review.md` — ikimize ADR review
  - `issues/README.md` — GH CLI toplu açma komutları
- **Architecture Decision Records**
  - `docs/decisions/ADR-template.md`
  - `docs/decisions/ADR-001-canonical-attestation-model.md`
- **Canonical schemas (JSON Schema draft-07)**
  - `schema/canonical/place.schema.json`
  - `schema/canonical/person.schema.json`
  - `schema/canonical/work.schema.json`
  - `schema/canonical/event.schema.json`
  - `schema/canonical/dynasty.schema.json`
  - `schema/canonical/route.schema.json`
  - `schema/canonical/source.schema.json`
  - `schema/canonical/attestation.schema.json`
- **Scripts**
  - `scripts/week1_audit.py` — veri katmanı audit (standart kütüphane)
  - `scripts/requirements.txt` (Phase 0 süresince güncellenecek)
  - `scripts/README.md`
- **Repo infra**
  - `CONTRIBUTING.md` — Conventional Commits + branch + PR + review rehberi
  - `pyproject.toml` — ruff / mypy / pytest config
  - `.github/CODEOWNERS`
  - `.github/pull_request_template.md`
  - `.github/ISSUE_TEMPLATE/` — phase0-task, bug-report, adr
  - `.github/workflows/ci.yml` — lint + JSON Schema validation + smoke test
- **Example audit output**
  - `audit_output_example/` — scriptin gerçek veri üzerinde koşturulmuş çıktısı (47 katman)

### Bulgular (ilk audit koşusu)
- 47 dosya, 105.802 tahminî kayıt, 129.3 MB toplam
- Yinelenen ID tespiti: `ei1_geo.json` (47), `konya.json` (2), `ibn_battuta_atlas_layer.json` (8)
- Yedek/prod'da görünmemesi gereken dosyalar: `salibiyyat_atlas_layer_backup.json`, `App.jsx.bak`, vd.
- Koordinat alan adı heterojenliği: `lat/lon`, `lat/lng`, `latitude/longitude` üçü de kullanılıyor
