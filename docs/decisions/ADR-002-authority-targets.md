# ADR-002 — Authority Reconciliation Hedefleri (Phase 0)

| Alan | Değer |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-03 |
| **Decision-maker** | Ali Çetinkaya (solo) |
| **Supersedes** | — |
| **Superseded by** | (Phase 1'de yeni ADR — GeoNames + OpenITI dahil edildiğinde) |
| **Related** | ADR-001 (URI Scheme), ADR-003 (Ontology Stack) |
| **Affects** | `pipelines/reconcilers/`, `schemas/_common/authority_xref.schema.json`, `crossrefs/by_authority/` |

---

## 1. Context

Authority reconciliation = kanonik entity'leri tanınmış otorite dosyalarındaki (Wikidata, VIAF, Pleiades, GeoNames, vd.) ID'lere bağlama süreci. Bu bağlantı LOD ekosisteminin lingua franca'sıdır: Pelagios indexer'ları, Linked Pasts harvester'ları, Wikidata API'si — tümü external authority ID'leri üzerinden çalışır.

Tam reconciliation hedefi (15+ otorite dosyası) bu repo için son hedef. Ama Phase 0'ın 8 haftalık solo penceresi, hangi otoritelere **şimdi** bağlanılması gerektiğine dair sert bir önceliklendirme zorluyor:

- Her otorite için bir reconciliation pipeline yazmak ~5-10 saat.
- Manuel review queue + gold standard kontrolü her otorite için ~3-5 saat ek.
- Düşük confidence eşleşmeler için domain bilgisi gerektiren editorial decisions (delege edilemez).

Bu ADR, Phase 0'da hedeflenecek otoriteleri sabitliyor; geri kalanları sonraki fazlara explicit olarak erteliyor.

---

## 2. Decision

### 2.1 Phase 0 hedefleri (zorunlu)

**Sadece iki otorite Phase 0 scope'unda:**

| Authority | Namespace | Hedef oran | Niye Phase 0 |
|---|---|---|---|
| **Wikidata** | place + dynasty | place ≥ %40, dynasty ≥ %90 | Reconciliation API açık + OpenRefine kolaylığı + en yüksek coverage |
| **Pleiades** | place (subset) | pre-1500 places ≥ %30 | Pelagios Network'e katılım için **mutlak şart**, alternatifi yok |

### 2.2 Phase 0.2 hedefleri (ertelendi)

| Authority | Namespace | Niye ertelendi |
|---|---|---|
| **VIAF** | person | Phase 0'da person namespace zaten yok; VIAF'ın varlık nedeni ortadan kalkıyor |
| **OpenITI URI** | source | Source namespace Phase 0.2'de doğacak; OpenITI URI'leri o namespace'in xref hedefi |

### 2.3 Phase 1 hedefleri

| Authority | Namespace | Gerekçe |
|---|---|---|
| **GeoNames** | place (modern subset) | Modern coğrafya araması için yararlı; Yâkût'un %70'i modern coğrafyaya tetkik edilebilir değil — sınırlı fayda |
| **TGN (Getty Thesaurus of Geographic Names)** | place | Sanat tarihi ekosistemi için; akademik bibliography integration |

### 2.4 Phase 2+ hedefleri

LCNAF, ISNI, OCLC FAST, Index Islamicus, Brill bibliographic IDs, GND (German National Library), BNF authorities — hepsi person ve source namespace'leri olgunlaştıktan sonra Phase 2-3'te.

---

## 3. Sub-decisions (Hafta 0'da finalize edilen 3 alt nokta)

### 2.1 OpenITI URI'ları Phase 0'a almalı mıyız?

**Karar: Schema'da yer açılır (forward compatibility), reconciliation Phase 0'da yapılmaz.**

**Detay:**
- `schemas/_common/authority_xref.schema.json` opsiyonel field olarak `openiti_uri` içerir.
- Phase 0'da hiçbir entity bu field'ı doldurmaz (place ve dynasty için OpenITI URI'leri irrelevant).
- Phase 0.2 source namespace doğduğunda OpenITI URI dynasty narrative source'larıyla bağlanmaya başlar (örn. Tabari Tarih, İbnü'l-Esir Kâmil, Bosworth bibliyografisi).

**Gerekçe:**
- Schema'ya field eklemek şimdi bedava (sadece JSON Schema'da bir property). Sonra eklemek = backward compatibility migration.
- Reconciliation pipeline yazmak = 5-8 saat — Phase 0 budget'ı zaten sıkı.
- Çetinkaya'nın enrichment pipeline'ından gelen OpenITI URI'leri zaten "elde" — Phase 0.2'de import quick win olur.

**Reject:**
- Reconciliation'ı Phase 0'a sıkıştırmak: scope creep + place/dynasty'ye fayda yok.
- Schema'dan field'ı çıkarmak: gelecek migration zorluğu.

### 2.2 Reconciliation oranı düşerse plan B?

**Karar: Üç-aşamalı graceful degradation.**

Eğer Hafta 5 sonu Wikidata reconciliation oranı %40 hedefine ulaşmazsa:

| Senaryo | Aksiyon | Paper raporlaması |
|---|---|---|
| %30 ≤ oran < %40 | Confidence eşiği 0.85 → 0.70'e düşürülür; ek 5-10 puan kazanılır | Limitation cümlesi: "Auto-reconciled at confidence ≥ 0.70 with manual review queue" |
| %20 ≤ oran < %30 | + Manual review queue ad-hoc delege; 0.50-0.70 confidence range gözle değerlendirilir | Methods sub-section: confidence calibration prosedürü detaylı raporlanır |
| oran < %20 | Hedef "%40" değil "anlamlı kapsam" olarak yeniden ifade edilir; release kesilmez | Limitations bölümünde explicit "lower than hoped" beyan; future work list |

**Anti-pattern (kaçınılacak):**
- Hedefi tutturmak için confidence threshold'u 0.50'nin altına çekmek → **false positive** kontaminasyonu.
- Release'i geciktirmek → motivasyon zinciri kırılır, doçentlik takvimi sıkışır.
- Hedefi gizlemek/yumuşatmak → akademik dürüstlük zafiyeti.

**Gerekçe:**
- Düşük oran bir başarısızlık değil, bir bulgu (finding). Yâkût coğrafyasının Wikidata'da ne kadar kapsandığı kendi başına bir araştırma sorusu — paper'da limitation değil, contribution olarak çerçevelenebilir.
- "Iterate vs declare and move on" trade-off'unda solo modda her zaman declare and move on lehine.

### 2.3 Pleiades pre-1000 cut-off makul mu?

**Karar: Cut-off "pre-1500 CE / pre-900 AH" olarak gevşetilir; metric "matched / pleiades-eligible" olarak tutulur.**

**Detay:**
- Pleiades'in resmi scope'u Greco-Roman + Late Antiquity (~1000 BCE – 600 CE), ama topluluk recent yıllarda erken İslam coğrafyasına genişlemiş (Pelagios içerikleri).
- Yâkût'un kayıtlarının çoğu **antik öncülü olan** yerlerdir: Halep = Beroia (Helenistik); Damaskus = Damaskos (Roma); Mısr = Memphis/Babylon Fortress. Bu yerlerin Pleiades record'u var; Yâkût'un yer kaydı pre-1000 olmasa da Pleiades match'i mümkün.
- Pre-1000 cut-off bu match'leri yanlışlıkla dışlardı.

**Implementation:**
- Filter: `temporal_coverage.end_ce ≤ 1500 OR temporal_coverage.start_ce ≤ 600` (yani ya pre-modern pre-Mongol ya da antik öncülü açıkça pre-Roma).
- Hedef oran: "**Pleiades-eligible** subset'in ≥ %30'u match"; eligibility filter'ı yukarıdaki bool predicate.
- Eligible-olmayan place'ler (post-1500 modern foundations) Pleiades reconciliation'a tabi tutulmaz; metric'ten dışlanır.

**Gerekçe:**
- Pelagios uyumluluğunu maksimize ediyor (eligibility filter'ı Pleiades'in fiili scope'una daha yakın).
- Metric sayısı "matched / total places" olsa düşerdi (~%5); "matched / pleiades-eligible" daha dürüst bir kapsam göstergesi.
- Solo modda implementation maliyeti aynı (filter expression bir satır).

**Reject:**
- Sert "pre-1000" cut-off: Pleiades match'lerinin yarısını kaçırırdı.
- Filter yok (tüm places Pleiades'e gönderilir): API rate limit yer; %3-5 oran gerçek hedefi gizler.

---

## 4. Reconciliation pipeline tasarımı (özet)

Detaylı specification → `docs/architecture/RECONCILIATION_PIPELINE.md` (Hafta 5'te yazılacak).

### Wikidata pipeline

- **Input:** Canonical place/dynasty entity dosyası.
- **Method:** OpenRefine Reconciliation API (https://wikidata.reconci.link/) + custom property hints (P31 Q486972 settlement / Q486972 archaeological site / Q3024240 historical region).
- **Disambiguation:** label match + language hint (ar/tr/en triangulation) + country hint (modern lat/lon ülke içi).
- **Output:** `crossrefs/by_authority/wikidata_qids.json` — `{"iac:place-00000123": {"qid": "Q5773", "confidence": 0.92, "method": "openrefine_v3", "reviewed": false}}`.
- **Caching:** Tüm API responses `cache/wikidata/` altında; idempotent re-run.

### Pleiades pipeline

- **Input:** Eligibility filter sonrası canonical place subset (~6000-8000 place tahmin).
- **Method:** Pleiades JSON API (https://pleiades.stoa.org/places/{id}/json); coordinate-distance match (radius 10 km) + label fuzzy match (Levenshtein > 0.85 + transliteration variants).
- **Disambiguation:** Multiple Pleiades match → temporal proximity (Pleiades record'unun "timePeriods" listesi Yâkût dönemine yakın olanı).
- **Output:** `crossrefs/by_authority/pleiades_pids.json`.

---

## 5. Consequences

### Pozitif

- **Pelagios Network'e katılım yolu açık** (Pleiades reconciliation tamamlanırsa).
- **Wikidata back-feed:** Phase 0 release'i Wikidata WikidataIntegrator ile dış push yapılabilir (binlerce yer entity'sinin "described in" property'si islamicatlas.org URI'sine işaret edebilir).
- **Forward compatibility:** Schema'da yer açtığımız `openiti_uri`, `viaf`, `geonames` field'ları Phase 0.2+ için sürtünmesiz açılır.

### Negatif / kabul edilen risk

- **Person reconciliation (VIAF) yok** → A'lâm + DİA biyografi entity'leri Phase 0 release'inde external linkage'sız kalır. Paper'da limitation.
- **GeoNames yok** → modern şehir adlarıyla arama (örn. "Aleppo Turkey" diye GeoNames over query gelirse) match yok. Phase 1'de eklenecek.
- **Düşük Wikidata coverage riski:** Yâkût'un %50-60'ı (toponim, küçük yerleşimler, vadiler) Wikidata'da yok. %40 hedef hayli iddialı; Plan B explicit (alt-karar 2.2).
- **API rate limit + downtime:** Wikidata reconci.link servisi açık kalmazsa Hafta 5 bloke. Mitigation: tüm responses cached, retry exponential backoff.

### İzlenecek metrikler

- Hafta 5 sonu: `crossrefs/by_authority/wikidata_qids.json` içindeki entry sayısı; gold standard 200 manuel review'da false positive oranı (≤ %5 hedef).
- Hafta 6 sonu: Pleiades match'lerinin rastgele 50 örneğinde manuel doğrulama (≤ %10 false positive).
- Phase 0 sonu: Toplam coverage raporu `docs/reports/wikidata_recon_v0_1_0.md` ve `docs/reports/pleiades_recon_v0_1_0.md`.

---

## 6. Implementation checklist (Hafta 5-6)

- [ ] `pipelines/reconcilers/wikidata_reconciler.py`
- [ ] `pipelines/reconcilers/pleiades_reconciler.py`
- [ ] `pipelines/reconcilers/utils/cache.py` (HTTP response cache)
- [ ] `pipelines/reconcilers/utils/eligibility.py` (Pleiades-eligibility filter)
- [ ] Gold standard test set: `tests/fixtures/gold_standard/` — top 200 place + 50 dynasty manuel mapping
- [ ] Reconciliation report templates (`docs/reports/_templates/`)

---

## 7. References

- Wikidata. [Reconciliation API documentation](https://wikidata.reconci.link/).
- Pleiades. [Place data API](https://pleiades.stoa.org/help/api).
- Pelagios Network. [Linked Data Practices](https://pelagios.org/linked-data-practices).
- VIAF. [About VIAF](https://viaf.org/) — Phase 0.2'de.
- OpenRefine. [Reconciliation service standard](https://reconciliation-api.github.io/specs/latest/).

---

**Versiyon:** 1.0 (Accepted)
**Son güncelleme:** 03 Mayıs 2026
