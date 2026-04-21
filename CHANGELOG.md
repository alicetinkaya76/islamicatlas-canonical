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

---

## [Unreleased]

### Added
- (burada aktif değişiklikler listelenecek)

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
