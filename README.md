# islamicatlas-canonical

> Phase 0: Canonical Data Foundation for [islamicatlas.org](https://islamicatlas.org)

Pleiades + Perseus seviyesinde bir dijital İslam medeniyeti araştırma altyapısının canonical veri modeli.

---

## Ne işe yarıyor?

[islamicatlas.org](https://islamicatlas.org) bugün 13 heterojen veri katmanında ~58.000 entity'ye ulaştı — Yâkût'un *Muʿcamü'l-Büldân*'ı, Ziriklî'nin *al-Aʿlām*'ı, DİA, Brill EI-1, Le Strange, Muqaddasî, Maqrizi'nin *Khitat*'ı, Salibiyyat (Haçlı seferleri), Science Layer, DarpIslam, şehir atlasları ve daha fazlası. Her katmanın kendi ID uzayı, kendi şeması, kendi koordinat alan adları var.

Bu repo o dağınık veri katmanını **Pleiades + Perseus modelinden uyarlanan canonical entity + attestation mimarisine** taşıyor:

- **Stable URI:** her entity'nin değişmez adresi (`islamicatlas.org/place/baghdad`)
- **Entity-level citation:** araştırmacı tek bir varlığa atıf yapabiliyor
- **Source transparency:** her bilgi kırıntısının hangi kaynağa dayandığı görünür
- **Linked Open Data:** Wikidata, VIAF, GeoNames bağlantıları
- **FAIR ilkeleri:** Findable, Accessible, Interoperable, Reusable

---

## Durum

**Phase 0 · Week 1 (aktif):** Audit & Inventory

| Hafta | Çıktı | Durum |
|---|---|:-:|
| 1 | Veri katmanı audit + inventory | 🟡 aktif |
| 2 | Canonical schema (8 dosya) + Pydantic + vocab | ⚪ bekliyor |
| 3-4 | Entity resolution pipeline + manuel doğrulama | ⚪ bekliyor |
| 5 | PostgreSQL+PostGIS + ETL + Source registry | ⚪ bekliyor |
| 6 | FastAPI + derivative builder + URL scheme | ⚪ bekliyor |
| 7-8 | Typesense + regression tests + Zenodo dump | ⚪ bekliyor |

Detaylı plan: [`docs/phase0-canonical-data-foundation.md`](docs/phase0-canonical-data-foundation.md)

---

## Ekip

| | Rol | Uzmanlık |
|---|---|---|
| **Dr. Ali Çetinkaya** | Lead, domain authority | Islamic studies, DH, Arabic/Ottoman NLP |
| **Fatıma Zehra Nur Balcı** | Engineering co-lead | Python, PostgreSQL, systems engineering |

İletişim için GitHub issues kullanılır. Karar niyetiyle açılan tartışmalar **ADR** (Architecture Decision Record) olarak dokümante edilir — bkz. [`docs/decisions/`](docs/decisions/).

---

## Repo yapısı

```
islamicatlas-canonical/
├── README.md                            ← buradasınız
├── CONTRIBUTING.md                      ← PR / commit / review rehberi
├── CHANGELOG.md
├── LICENSE                              ← MIT (kod) + CC-BY-4.0 (veri)
├── pyproject.toml                       ← ruff / mypy / pytest config
├── .gitignore
│
├── .github/
│   ├── CODEOWNERS                       ← otomatik review ataması
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── phase0-task.md
│   │   ├── bug-report.md
│   │   └── adr.md
│   └── workflows/
│       └── ci.yml                       ← lint + schema validation
│
├── docs/
│   ├── phase0-canonical-data-foundation.md  ← master plan
│   ├── setup-github.md                      ← repo kurulum adımları (Ali)
│   ├── fatima-kickoff.md                    ← onboarding (Fatıma)
│   ├── meeting-01-agenda.md                 ← ilk toplantı gündemi
│   ├── meeting-01-notes.template.md         ← toplantı sonrası notlar
│   ├── canonical_scope.md                   ← Week 1 Ali deliverable (Issue #2)
│   └── decisions/
│       ├── ADR-template.md
│       └── ADR-001-canonical-attestation-model.md
│
├── issues/                              ← ilk 3 GitHub issue'nun gövdeleri
│   ├── README.md
│   ├── 001-week1-audit.md
│   ├── 002-canonical-scope.md
│   └── 003-adr-001-review.md
│
├── schema/
│   ├── README.md                        ← model açıklaması
│   └── canonical/
│       ├── place.schema.json
│       ├── person.schema.json
│       ├── work.schema.json
│       ├── event.schema.json
│       ├── dynasty.schema.json
│       ├── route.schema.json
│       ├── source.schema.json
│       └── attestation.schema.json
│
├── scripts/
│   ├── README.md                        ← scriptlerin kullanımı
│   ├── requirements.txt
│   └── week1_audit.py                   ← veri katmanı audit scripti
│
└── audit_output_example/                ← Week 1 örnek çıktı (reference)
    ├── README.md
    ├── summary.md
    ├── summary.json
    ├── cross_reference.md
    ├── duplicates.md
    └── <layer_name>.md × 47
```

---

## Hızlı başlangıç

### 1. Repo'yu klonla

```bash
git clone git@github.com:alicetinkaya76/islamicatlas-canonical.git
cd islamicatlas-canonical
```

### 2. Python ortamı

```bash
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows

pip install -r scripts/requirements.txt
```

### 3. Ana atlas repo'sunu referans olarak yanına klonla

```bash
cd ..
git clone git@github.com:alicetinkaya76/islamicatlas.git    # veya mevcut yolunu kullan
cd islamicatlas-canonical
```

### 4. Week 1 audit scriptini koş

```bash
python3 scripts/week1_audit.py \
    --data-dir ../islamicatlas/public/data \
    --csv-dir  ../islamicatlas/data \
    --extra    ../islamicatlas/public/data/city-atlas \
    --out      ./audit_output
```

Çıktı `audit_output/` altında (git'e commit edilmez, her lokal kullanıcı kendi çıktısını üretir).

### 5. Sonraki adımlar

- [`docs/phase0-canonical-data-foundation.md`](docs/phase0-canonical-data-foundation.md) — tam plan
- [`docs/fatima-kickoff.md`](docs/fatima-kickoff.md) — Fatıma için brifing
- [`schema/README.md`](schema/README.md) — model açıklaması
- GitHub Issues — aktif iş

---

## Canonical model — 30 saniyelik özet

```
            ┌────────────────────┐
            │    Place           │   canonical — islamicatlas otoritesi
            │  plc_baghdad       │
            │  coords: 33.3,44.4 │
            └─────────▲──────────┘
                      │
          ┌───────────┼───────────┬───────────┐
          │           │           │           │
    ┌─────┴─────┐┌────┴────┐┌─────┴─────┐┌────┴────┐
    │Attestation││Attestation││Attestation││Attestation│
    │ src=yaqut ││ src=lestr││ src=dia   ││ src=sal  │
    │ p.456     ││ p.30-35  ││ "BAĞDAT"  ││ evt_1191 │
    └───────────┘└──────────┘└───────────┘└──────────┘
```

**Anahtar kural:** Canonical entity (Place/Person/Work/Event/Dynasty/Route) bilgisi doğrudan taşımaz — bilgi **Attestation**'lardan gelir. Canonical kayıt attestation'ların konsolide edilmiş hâlidir.

Detay: [ADR-001](docs/decisions/ADR-001-canonical-attestation-model.md)

---

## Phase 0'da **YAPILMAYACAK** (scope disiplini)

- Frontend redesign
- Yeni veri katmanı eklenmesi
- SPARQL endpoint kurulumu
- 3D/Mapbox geçişi
- Crowdsource/annotation UI

Bunlar Phase 1+'a aittir.

---

## Lisans

- **Kod** (scripts/, schema/): MIT
- **Veri** (seed data, Source registry, vocab): CC-BY-4.0
- **Dokümantasyon** (docs/): CC-BY-4.0

Atıf: Çetinkaya, A., & Balcı, F. Z. N. (2026). *Islamic Atlas Canonical Data Foundation* (v0.1.0) [Software]. https://github.com/alicetinkaya76/islamicatlas-canonical

---

## İlgili yayınlar

- (Planlanıyor, Week 7-8): "Canonical data infrastructure for Islamic civilization digital humanities: a methodology paper" — hedef: ACM JOCCH / DSH

## İlgili kaynaklar

- [Pleiades Gazetteer](https://pleiades.stoa.org/) — referans model (ancient Mediterranean)
- [Perseus Digital Library](http://www.perseus.tufts.edu/hopper/) — referans model (classical philology)
- [Syriaca.org](https://syriaca.org/) — referans model (Syriac prosopography)
- [OpenITI](https://openiti.org/) — İslam metin korpusu (potansiyel gelecek entegrasyon)
- [CIDOC-CRM](https://www.cidoc-crm.org/) — kültürel miras ontolojisi
