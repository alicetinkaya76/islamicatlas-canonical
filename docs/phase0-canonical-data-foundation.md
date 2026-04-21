# Phase 0: Canonical Data Foundation

**Proje:** islamicatlas.org  
**Faz:** 0 (Kanonik Veri Altyapısı)  
**Tahminî süre:** 6-8 hafta  
**Başlangıç:** Nisan 2026  
**Sorumlu ekip:** Dr. Ali Çetinkaya (lead) + Fatıma Zehra Nur Balcı (eng. co-lead)  
**Doküman sürümü:** v1.0 (2026-04-21)

---

## 1. Vizyon

islamicatlas.org bugün kendi alanında (İslam medeniyeti dijital atlası) en geniş kapsamlı çalışma; ancak mimari olarak **görselleştirme platformu** seviyesinde. Hedefimiz: **Pleiades (klasik antik çağ) ve Perseus (klasik filoloji) seviyesinde bir dijital araştırma altyapısına** dönüşmek.

Bu iki platformu ayırt eden şey güzel görsel değil — her ikisi de görsel olarak sade. Ayırt eden şey:

- **Stable URI** — her varlığın (yer/kişi) değişmez, atıf verilebilir adresi var
- **Entity-level citation** — araştırmacı tek bir varlığa atıf yapabiliyor, toplu veri kümesine değil
- **Linked Open Data** — veri Wikidata, VIAF, GeoNames gibi global ağlara bağlı
- **Source attestation modeli** — her bilgi kırıntısının hangi kaynağa dayandığı görünür
- **Federated SPARQL / API** — veri makine okunur formatta programatik erişilebilir
- **FAIR ilkeleri** — Findable, Accessible, Interoperable, Reusable

Bu beş sütunun hiçbiri mevcut islamicatlas mimarisinde tam olarak oturmuyor. Phase 0, bu sütunları inşa edecek veri altyapısını kurmaktır — görsel veya yeni özellik eklemez.

---

## 2. Mevcut Durumun Tanısı

Kaynak kod ve `public/data/` klasörünün sistematik taranması sonucu (bkz. `audit_output/summary.md`):

### 2.1 Şema heterojenliği

13 veri katmanının 13 farklı şeması var. Örnekler:

| Katman | ID alanı | Koordinat | Ad alanı |
|---|---|---|---|
| al-Aʿlām (Ziriklî) | `id: int` | `lat, lon` | `h, ht, he` |
| DİA | `id: slug` | yok (geo ayrı dosyada) | `t, ds` |
| Yâkût | `id: int` | `lat, lon` | `h, ht, he` |
| Le Strange | `id: int` | `latitude, longitude` | `name_ar, name_tr, name_en` |
| Konya City Atlas | `id: slug` | `location.lat, location.lng` | `name_tr, name_en, name_ar` |
| Science Layer | `id: slug` (scholar_0001) | `coordinates: [lat, lon]` | `name: {en, tr, ar}` |

Bu farklılık estetik değil, işlevsel bir sorun — her view bileşeni kendi adapter koduyla çalışıyor, bu yüzden `AlamView`, `YaqutView`, `DiaView`, `LeStrangeView` kodu **~%70 tekrar**.

### 2.2 Kimlik sistemi yokluğu

`"id": 1` Yâkût'ta bir yer, al-Aʿlām'da bir kişi, Science Layer'da "scholar_0001" formatında. Katmanlar arası ID çakışması var:

- **`ei1_geo.json`:** 47 yinelenen ID (otomatik audit bulgusu)
- **`muqaddasi_xref.json`:** 225 yinelenen ID
- **`yaqut_crossref.json`:** 2014 yinelenen ID (ancak bu dict-form xref kastı ile ilgili olabilir, doğrulanacak)
- **`konya.json`:** 2 yinelenen ID
- **`ibn_battuta_atlas_layer.json`:** 8 yinelenen ID

### 2.3 Varlık çözümleme (entity resolution) yapılmamış

"Bağdat" şu an **dört ayrı varlık** olarak modellenmiş: Yâkût'taki kaydı, Le Strange'deki kaydı, DİA makalesi, Salibiyyat olaylarındaki geçişleri. Halbuki canonical modelde bunlar **tek bir `plc_baghdad`**'ın dört ayrı `Attestation`'ı olmalıdır.

Aynı şey el-Harezmî için: Science Layer'da `scholar_0001`, muhtemelen al-Aʿlām'da ayrı, DİA'da "HÂREZMÎ" makalesi — hiçbir köprü yok.

Mevcut cross-ref dosyaları (`dia_alam_xref.json`, `yaqut_crossref.json`, `le_strange_xref.json`, `muqaddasi_xref.json`) bu boşluğu kısmen kapatıyor ama:
- Tek yönlü, sözlük formlu, doğrulama mekanizması yok
- Kapsama oranı düşük: al-Aʿlām→DİA sadece 1400 eşleşme (toplam 13.940'ta, yani **%10**)
- Güven skoru taşımıyor — "bu eşleşme kesin mi, olası mı?" bilgisi yok

### 2.4 Dağıtım mimarisi limitleri

- `public/data/` toplam **129.3 MB**
- `dia_chunks.json` tek başına **69.5 MB** — ve doğrudan client'a gönderiliyor
- Mobil kullanıcı için bu fiilen erişilemez
- Tüm arama/filtreleme browser'da RAM'de yapılıyor — karmaşık sorgular (örn. "750-1000 arası Bağdat'ta yaşamış, DİA + al-Aʿlām çift kayıtlı, fıkıh alanında eser vermiş âlimler") bu mimaride **yapılamaz**

### 2.5 Yedek/tekrar dosyalar

- `src/App.jsx` ve `src/App.jsx.bak` — prod dizininde yedek
- `public/data/salibiyyat_atlas_layer_backup.json` (0.43 MB) — prod yükünde
- `public/data/darpislam_detail_*.json` (0-6 arası 7 shard, toplam ~4.6 MB)
- `src/data/ibn_battuta_atlas_layer.json` + `public/data/ibn_battuta_atlas_layer.json` — **aynı dosya iki yerde**
- `src/data/maqrizi_khitat_atlas_layer.json` + `public/data/maqrizi_khitat_atlas_layer.json` — aynı durum
- `alam_xrefs_backup.json` — src'de yedek

### 2.6 Veri sözlüğü kapsama eksikliği

`data/DATA_DICTIONARY.md` sadece CSV katmanı (hanedanlar) için yazılmış. 13 JSON katmanının **12'sinin formal şeması yok**. `c1` alanının ne anlama geldiği, `is`'nin "importance score" mı "is"fahan" mı olduğu — kod okunarak anlaşılıyor.

### 2.7 Kaynak attestation'ı modellenmemiş

"Bağdat 33.33°N" bilgisi hangi kaynağa göre? Yâkût mu söylüyor, Le Strange mi koordinatı düzeltiyor, modern geocoder mı? Şu anki modelde her katman kendi "doğrusu" gibi davranıyor, akademik bir araç için kabul edilemez.

---

## 3. Hedef Mimari

### 3.1 Canonical entity + attestation ayrımı

Pleiades'in devrimsel fikri: **kanonik varlık ≠ attestation**. Bir yer (Place) kendi başına bir kayıttır; onun bir kaynakta geçişi ayrı bir attestation kaydıdır.

```
            ┌────────────────────┐
            │    Place           │      (canonical — islamicatlas.org otoritesi)
            │  plc_baghdad       │
            │  coords: 33.3,44.4 │
            └─────────▲──────────┘
                      │
          ┌───────────┼───────────┬───────────┐
          │           │           │           │
    ┌─────┴─────┐┌────┴────┐┌─────┴─────┐┌────┴────┐
    │Attestation││Attestation││Attestation││Attestation
    │ src=yaqut ││ src=lestr││ src=dia   ││ src=sal 
    │ p.456     ││ p.30-35  ││ "BAĞDAT"  ││ evt_1191
    │ coords:   ││ coords:  ││ coords:—  ││ coords:—
    │  33.3,44.4││  33.5,44.2│
    └───────────┘└──────────┘└───────────┘└─────────┘
```

### 3.2 Canonical entity tipleri

`Place` · `Person` · `Work` · `Event` · `Dynasty` · `Route` · `Source` · `Attestation`

Her canonical entity taşır:
- Stable slug (URI-safe, değişmez)
- `sameAs` bağlantıları → Wikidata, VIAF, GeoNames, Pleiades
- `provenance` izi → hangi legacy kayıtlardan üretildi
- Version/revision tracking → kim, ne zaman, neden değiştirdi
- JSON-LD export yeteneği

### 3.3 Katmanlı altyapı

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (React/Leaflet) — değişmeden kalıyor     │
└───────────────────────▲─────────────────────────────┘
                        │ eski lite.json dosyaları
┌───────────────────────┴─────────────────────────────┐
│  DERIVATIVE LAYER — canonical'dan otomatik türev    │
│  • place-lite.json, person-lite.json...             │
│  • search indexes (Typesense)                        │
│  • API endpoints (/api/v1/...)                       │
│  • JSON-LD / RDF exports (Zenodo dump)              │
└───────────────────────▲─────────────────────────────┘
                        │ ETL
┌───────────────────────┴─────────────────────────────┐
│  CANONICAL STORE (PostgreSQL + PostGIS)             │
│  Places, Persons, Works, Events, Sources,           │
│  Attestations + Relations                            │
└───────────────────────▲─────────────────────────────┘
                        │ migration
┌───────────────────────┴─────────────────────────────┐
│  LEGACY LAYERS (mevcut JSON dosyaları)              │
│  Yâkût, al-Aʿlām, DİA, EI-1, Le Strange,           │
│  Muqaddasî, Evliya, Maqrizi, Salibiyyat,            │
│  Science, DarpIslam, Konya, Cairo, Ibn Battuta     │
└─────────────────────────────────────────────────────┘
```

### 3.4 Kapsam dışı (Phase 0'da **YAPILMAYACAK**)

- Frontend redesign (React view'ları değişmez)
- Yeni veri katmanı eklenmesi
- SPARQL endpoint kurulumu (Phase 2+)
- 3D/Mapbox geçişi
- Kullanıcı authentication / crowdsource
- AI chat geliştirmeleri

Bu scope disiplini kritik — Phase 0 bir backend/veri işidir. UI ve yeni özellik Phase 1 ve sonrası.

---

## 4. 8 Haftalık Takvim

### Week 1 — Audit & Inventory

**Hedef:** Mevcut durumun makine okunur raporu.

**Fatıma:** `scripts/week1_audit.py` koşar, her katmanın şema/kapsama/kalite profilini çıkarır. İlk koşunun çıktısı `audit_output/` altında — 47 dosya, 105.802 kayıt, 129 MB.

**Ali:** Raporları okuyarak her katman için "bu canonical'a neresi gidecek, neresi atılacak" kararını verir. 1-2 iş oturumu.

**Çıktılar:**
- [x] `scripts/week1_audit.py` (tamamlandı)
- [x] `audit_output/summary.md` + her katman için ayrıntılı rapor (ilk koşu tamamlandı)
- [ ] `docs/canonical_scope.md` — hangi katman canonical'a dahil, hangi kayıt dışarıda

### Week 2 — Canonical Schema Tasarımı

**Hedef:** Tip güvenli, versiyonlanabilir şemalar.

**Fatıma:**
- Kalan canonical schema'ları yaz: `work.schema.json`, `event.schema.json`, `dynasty.schema.json`, `route.schema.json`
- Her birinin Pydantic modelini `schema/pydantic/` altında çıkar
- URI üretici fonksiyon: Arapça/Osmanlı adı → slug (transliterasyon + diacritic + çakışma çözümü)
- JSON Schema validation pipeline (`scripts/validate.py`)

**Ali:**
- CIDOC-CRM ve schema.org mapping kararları (ADR-002)
- İslamic-studies özgü kavramlar (madhab, silsile, iqlim, nisba) için controlled vocabulary
- Transliterasyon standardı kararı: IJMES mi, DİN 31635 mi?

**Çıktılar:**
- [ ] `schema/canonical/*.schema.json` (7 dosya tamamlanmış — şu an 3/7)
- [ ] `schema/pydantic/*.py` (Python runtime doğrulama)
- [ ] `schema/vocab/*.json` (controlled vocabularies)
- [ ] `docs/decisions/ADR-002-ontology-mapping.md`
- [ ] `docs/decisions/ADR-003-transliteration-standard.md`
- [ ] `docs/decisions/ADR-004-uri-scheme.md`

### Week 3-4 — Entity Resolution

**Hedef:** Katmanlar arası varlık birleştirme — canonical'a giden yol.

Bu Phase 0'ın **en zor** adımı. Bir kişinin al-Aʿlām + DİA + Science Layer karşılıklarını, bir yerin Yâkût + Le Strange + Muqaddasî + DİA karşılıklarını birleştirmek.

**Fatıma:** Üç aşamalı ER pipeline:

1. **Blocking** — fuzzy name hashing (Arapça normalizasyonu + metaphone). Her kaydı olası bucket'a atar. O(n²) → O(n·k).
2. **Similarity scoring** — Jaro-Winkler (ad) + tarih uzaklığı + coğrafi yakınlık + alan örtüşmesi. Weighted score (0-1).
3. **LLM-assisted tiebreaker** — şüpheli orta-skor (0.6-0.9) eşleşmeleri Claude/GPT ile doğrular. Ali'nin OpenITI pipeline'ında denenmiş yöntem.

Manuel doğrulama UI: basit Streamlit — düşük skorlu eşleşmeler yan yana gösterilir, "✓ / ✗ / ?" butonları.

**Ali:**
- Top-500 en çok atıf alan entity (örn. Bağdat, Medine, el-Harezmî, İbn Sînâ) için manuel **gold label** üretir
- >0.9 güven skorlu eşleşmelerin örnek doğrulaması
- 0.6-0.9 arası eşleşmelerde karar

**Çıktılar:**
- [ ] `scripts/er_pipeline.py`
- [ ] `scripts/er_verify_ui.py` (Streamlit)
- [ ] `er_output/concordance_auto.csv` (silver, güven skorlu)
- [ ] `er_output/concordance_verified.csv` (gold, insan onaylı)
- [ ] `docs/er_methodology.md` (yayın hazırlığı — DSH/JOCCH paper'ına yol açacak)

### Week 5 — Canonical Store & Migration

**Hedef:** PostgreSQL+PostGIS'de yaşayan canonical veri.

**Fatıma:**
- Docker compose: PostgreSQL 16 + PostGIS 3.4
- JSON Schema → SQL migration (Alembic)
- ETL: her legacy katmanı → canonical tablolar (idempotent)
- Attestation kayıtlarının otomatik üretimi

**Ali:**
- Source registry'nin ilk populasyonu — 13 kaynak için tam bibliyografik kayıt (DOI/ISBN, editör, edition, kapsama)
- ETL sonrası doğrulama: al-Aʿlām'daki 13.940 biyografinin `per_*` kayıtlarına dönüşüm oranı?

**Çıktılar:**
- [ ] `infra/docker-compose.yml`
- [ ] `infra/migrations/` (Alembic)
- [ ] `etl/run.py` (idempotent ana akış)
- [ ] `canonical_db/` (seed data + Source registry)
- [ ] Populated canonical store (test instance)

### Week 6 — Derivatives & API

**Hedef:** Frontend'i bozmadan canonical'dan beslemek + API açmak.

**Fatıma:**
- Derivative builder: canonical store → eski `*_lite.json` formatları (backwards compat kritik)
- FastAPI: `/api/v1/place/{slug}`, `/api/v1/person/{slug}`, `/api/v1/search`
- JSON-LD response default, Accept header'a göre JSON/RDF
- Sitemap jeneratörü (her entity için URL)
- OpenAPI spec

**Ali:**
- URL şeması son kararı (`/place/{slug}` vs `/yer/{slug}` vs `/p/{id}`) — ADR-004
- Citation template: BibTeX, RIS, Chicago, APA (her entity sayfasında)

**Çıktılar:**
- [ ] `api/` (FastAPI app)
- [ ] `derivatives/build.py` (canonical → legacy-format dump)
- [ ] OpenAPI spec (`api/openapi.json`)
- [ ] `docs/api_guide.md`
- [ ] Çalışan frontend (eski view'lar canonical'dan besleniyor)

### Week 7-8 — Search, Integration Test & Publication Prep

**Hedef:** Arama + testler + yayın malzemesi.

**Fatıma:**
- Typesense kurulumu (Türkçe + Arapça analyzer)
- Canonical → Typesense indexer
- Facet kurgusu: type, period, region, madhab, field
- Regression test suite (her view için kayıt sayısı ve detay erişim)

**Ali:**
- Go/no-go kararı: Phase 0 tamamlandı mı?
- Zenodo dump hazırlığı: canonical dump + DOI başvurusu
- İlk CHANGELOG_v8.0.0.md
- Publication outline: "Canonical data infrastructure for Islamic civilization digital humanities" (hedef: JOCCH veya DSH)

**Çıktılar:**
- [ ] `infra/typesense/` (konfig + indexer)
- [ ] `tests/regression/` (pytest suite)
- [ ] Zenodo deposit (islamicatlas-v8.0.0-canonical)
- [ ] DOI
- [ ] `docs/publications/phase0_paper_outline.md`

---

## 5. Roller ve İşbölümü

### 5.1 Fatıma — Makine/Mühendislik Omurgası

**Skill match:** BilgMüh son sınıf öğrencisi olarak şu teknoloji setleri ya aşina ya bir haftada öğrenilebilir:
- Python (pandas, pydantic, fastapi)
- PostgreSQL / PostGIS, Docker Compose, Alembic
- JSON Schema, JSON-LD temelleri
- Git workflow, PR review, GitHub Actions
- Typesense veya Elasticsearch

**Phase 0 sorumlulukları:**
- Tüm otomasyon scriptleri (audit, ETL, ER, derivative build)
- Şemaların JSON Schema + Pydantic implementasyonu
- Docker compose, migration, CI/CD
- API endpoint'leri, arama indeksi
- Kod review (Ali'nin PR'larında)

### 5.2 Ali — Muhakeme ve Domain Otoritesi

**Skill match:** Kanonik kararların özü akademik bilgiyi gerektiriyor; bir CS öğrencisinin yapamayacağı değerlendirmeler.

**Phase 0 sorumlulukları:**
- Canonical şemada hangi alanlar zorunlu, hangi varlıklar aynıdır
- Source registry'de her kaynağın tam bibliyografisi
- Transliterasyon, dönem etiketleri, madhab doğrulaması
- Top-500 entity için manual gold label
- ER eşleşmelerinin manuel doğrulaması
- ADR'lar (architecture decision records) — domain kararlı olanlar
- Code review (Fatıma'nın PR'larında — mimari düzeyinde)

### 5.3 Ortak alanlar

| Alan | Fatıma yapar | Ali yapar |
|---|---|---|
| Şema tasarımı | JSON Schema / Pydantic implementasyonu | İçerik kuralları, zorunlu alanlar |
| ER pipeline | Algoritma, UI | Gold label + manuel doğrulama |
| Code review | Domain olmayan PR'lar | Domain/mimari PR'lar |
| Dokümantasyon | Tech docs (API, setup) | ADR'ler, methodology |
| Paper draft | Methods + evaluation sections | Intro, related work, domain discussion |

---

## 6. Çalışma Protokolleri

### 6.1 Repo

`alicetinkaya76/islamicatlas-canonical` (private, Phase 0 için ayrı repo). Ana atlas repo'sunu kirletmeden çalışmak kritik — Phase 0 bittiğinde canonical derivative'ları atlas'a merge edilir.

**Roller:**
- **Ali:** Owner + admin (repo sahibi, destructive aksiyonlar)
- **Fatıma:** Maintain rolü — PR yönetim, issue triage, label/milestone düzenleme. Destructive aksiyon (repo silme, visibility değiştirme) yok. Bu rol bir öğrenciye verilebilecek en üst seviye güven rolüdür ve sorumluluğu açık çerçeveler.

**Branch koruması:** `main` tamamen korumalı — doğrudan push yok, 1 approval zorunlu, **admin dahil** herkes için. Bu disiplin üst-alt ilişkisi değil, iki kişilik ekipte dördüncü göz oluşturma meselesi.

Detaylı kurulum adımları (label'lar, milestone'lar, kanban, ilk issue'lar): [`setup-github.md`](setup-github.md).

### 6.2 Branch ve PR disiplini

- `main` korumalı, direct push yok
- Her değişiklik feature branch'te → PR → karşılıklı review → merge
- En az 1 approving review (ikiniz varsınız, karşılıklı review zorunlu)
- CI zorunlu: lint (ruff), type check (mypy), schema validation, unit test

### 6.3 Issue tracker

GitHub Projects kanban:
- **Backlog** (tüm görevler)
- **This Week** (haftanın hedefi)
- **In Progress**
- **Review**
- **Done**

Her hafta Pazartesi kanban refresh, Cuma retro.

### 6.4 İletişim ritmi

- **Haftalık senkron:** 1 saat, Pazartesi sabahı. Gündem: geçen haftanın deliverable durumu + bu haftanın hedefleri + bloker varsa unblocking.
- **Async kanal:** Slack/Discord/WhatsApp. Kısa sorular için.
- **Büyük kararlar:** Issue veya PR yorumunda kalmalı, mesajlaşmada değil (arşivlenebilirlik).

### 6.5 ADR (Architecture Decision Records)

`docs/decisions/` altında her mimari karar için bir ADR. Format: `ADR-NNN-kisa-baslik.md`. İçerik: Context → Decision → Consequences. Bir kez yazılınca rarely değiştirilir — değiştirilirse yeni ADR "supersedes ADR-NNN" notuyla eklenir.

---

## 7. Başarı Kriterleri

Phase 0 tamamlandı sayılır eğer:

1. **Canonical store canlı:** PostgreSQL + PostGIS instance'ında ≥7 canonical entity tipi için seed data
2. **En az 5 katmanın migrate olması:** Yâkût + al-Aʿlām + DİA + Le Strange + Konya canonical'a çekilmiş
3. **API çalışır:** `/api/v1/place/{slug}`, `/api/v1/person/{slug}`, `/api/v1/search` endpoints live
4. **Search indeksi çalışır:** Typesense üzerinde ≥30K entity, facet araması dönüyor
5. **Frontend bozulmamış:** mevcut 18 view (`AlamView`, `YaqutView`, ...) regression test'ten geçiyor
6. **Source registry tam:** 13 kaynak için bibliyografik kayıt
7. **Entity resolution silver+gold:** ≥3 katman çifti arasında ≥%60 eşleşme oranı, ≥1000 gold-label
8. **Zenodo dump:** v8.0.0-canonical DOI'li
9. **Dokümantasyon:** 7+ ADR + API guide + schema README + methodology paper outline

---

## 8. Riskler ve Mitigasyonlar

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| ER doğruluğu düşük (<%70 gold) | Orta | Yüksek | Top-500 manuel, long-tail provisional olarak işaretle; Phase 1'de düzelt |
| Fatıma'nın süresi yetmez | Orta | Yüksek | Haftalık hedef revize; scope trim (Typesense Phase 1'e ertelenebilir) |
| Frontend regression | Düşük | Yüksek | Her view için snapshot test; derivative dump format-uyumlu |
| PostgreSQL performance (58K entity) | Düşük | Orta | Index planning Week 5'te; materialized view gerekirse |
| Ali'nin paper/doçentlik yükü | Yüksek | Orta | Fatıma'nın autonomy'si yüksek tutulsun; ADR review asenkron |
| Scope creep | Yüksek | Yüksek | `canonical_scope.md` sabit; yeni istek → Phase 1 backlog |
| Veri kalitesi bulguları Phase 0'ı uzatır | Orta | Orta | İlk audit bulgularına göre Week 1 sonunda timeline reforecast |

---

## 9. Phase 0 Sonrası (Yol Haritası)

Phase 0 bittiğinde temel atılmış olacak. Sıradaki fazlar:

- **Phase 1 (v8.1-8.3, ~8 hafta):** Frontend canonical'a göre redesign — her entity sayfasında attestation display, ihtilaf görünümü, LOD bağlantıları
- **Phase 2 (v9.0, ~6 hafta):** Prosopographical query builder (doçentlik publication hedefi)
- **Phase 3 (v9.1+):** Annotation/crowdsource katmanı, IIIF manifest desteği
- **Phase ∞:** SPARQL endpoint, OAI-PMH harvester, Jupyter notebook örnekleri

---

## 10. Yayın Perspektifi

Phase 0 iyi dokümante edildiğinde **infrastructure paper** çıkıyor. Hedef dergiler:

1. **ACM JOCCH** (Journal on Computing and Cultural Heritage) — Ali'nin zaten bir submission'ı var (JOCCH-26-0106)
2. **Digital Scholarship in the Humanities (DSH)** — EICD-B paper'ı şu an DSH-2026-0184'te
3. **ACM TALLIP** — Ottoman fatwa paper TALLIP-26-0165'te
4. **Digital Humanities Quarterly (DHQ)**

Paper outline Week 7-8'de yazılır. Fatıma'nın substantive teknik katkısı nedeniyle **ikinci yazar** olarak konumlandırılır — bu akademik olarak hem doğru hem ona karşı adil.

Ek olarak **Phase 0 metodolojisi** bir **data paper** olarak Zenodo dump ile birlikte yayımlanabilir — canonical dataset DOI'li + methodology makalesi.

---

## 11. Bu Haftanın Somut Adımları

1. **Repo kurulumu** ([`setup-github.md`](setup-github.md) rehberiyle) — Ali, toplantıdan önce yapar:
   - Private repo oluştur (`alicetinkaya76/islamicatlas-canonical`)
   - Local paketi push'la (`v0.1.0` initial commit)
   - Branch protection, labels, milestones, kanban
   - Fatıma'yı Maintain rolüyle collaborator ekle
2. **Fatıma ile ilk toplantı** ([`meeting-01-agenda.md`](meeting-01-agenda.md))
3. **Week 1 kickoff:** Fatıma `week1_audit.py`'yı kendi makinesinde koşar, çıktıyı inceler, Issue #1'de bulgularını yazar
4. **Canonical scope çerçevesi:** Ali, mevcut 47 veri dosyasını kategorize eder (`in-scope` / `backup-delete` / `auxiliary` / `defer-to-phase-1`) — Issue #2
5. **ADR-001 onayı:** Toplantı sonrası Fatıma ve Ali ADR-001'i birlikte gözden geçirir, onaylanırsa status `Proposed` → `Accepted` güncellenir — Issue #3

---

**İmzalar:**

- Dr. Ali Çetinkaya — _________________________ Tarih: ___________
- Fatıma Zehra Nur Balcı — _____________________ Tarih: ___________
