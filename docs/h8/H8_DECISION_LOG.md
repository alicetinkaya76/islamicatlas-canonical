# H8 Karar Günlüğü (Decision Log)

> H8 oturumunda yapılan önemli yargılar. H7 formatına uygun.

---

## Karar 1 — PE-1 için Option B1 (enum genişletme, no data mutation)

**Bağlam**: H7 close'da 2,262 person record (~%10) schema-invalid
durumda kalmış; üç remediation seçeneği var (B1 enum genişlet, B2
mass-rename tertiary_reference, B3 mass-rename primary_textual).

**Karar**: B1. Detaylar ADR-010'da.

**Gerekçe**: Tek değişiklik additive, geriye-uyumlu, zero data mutation;
B2/B3 yanlış semantic + 2,262 record_history append maliyeti +
H4-time data integrity izini bozar. Schema'nın vocabulary'sine eksik
olan kategori adımı eklenir.

**Sonuç**: 1 dosya schema patch + 1 ADR + 1 migration script (no-op data,
re-validation only) + 0 record mutation. Test suite 73→74 passed.

---

## Karar 2 — Schema $id bump'ı PE-1 yamasından ayrıştır (PE-2 olarak ertele)

**Bağlam**: PE-1 fix sırasında `_common/provenance.schema.json`'un
`$id`'sini de v0.1.0 → v0.2.1 bumplamak doğal görünüyordu (additive
enum revision sonuçta minor version bump). Ama H6 Stream 4'te yalnız
`work.schema.json` v0.2.0'a bumplanmış; diğer 9 dosya v0.1.0'da. Tüm
entity schemaları `$ref` ile `v0.1.0/_common/provenance.schema.json`'a
bakıyor. Tek başına provenance'in `$id`'sini bumplamak `referencing.
Registry`'de resolution kırar → full suite kırmızıya döner.

**Karar**: `$id` bumplanmadı. PE-1 sadece enum + description ekledi.
$id coherence ayrı tech-debt: H8_KNOWN_ISSUES.md'de **PE-2** olarak
kayda alındı, gelecek bir commit 10 dosyayı atomik olarak günceller.

**Gerekçe**: Hata yüzeyini ayrıştır. PE-1 30 dk'lık additive bir
yama; 10-dosya `$id` housekeeping pass'ini buna karıştırmak (a) commit
diff'ini şişirir, (b) PE-1'in gerçekten ne fix ettiğini gizler, (c)
PE-2'nin kendi başına hak ettiği "schema versioning policy" tartışmasını
gizler.

**Sonuç**: ADR-010 §"Schema versioning" bu kararın gerekçesini kayıtlı
tutar. PE-2 H8_KNOWN_ISSUES.md'de açık.

---

## Karar 3 — Yol C: dia_chunks → person enrichment + H9 TDV scraping spec

**Bağlam**: H8 Stage 2 profilörü çıktısı dia_chunks.json'un yapısını
ortaya koydu: 19.742 kayıt, schema (s, n, t, d, a, sec, c, _id, id),
Arapça başlık YOK, cilt+sayfa YOK. Yani ADR-009'un üç eşiğinden (a) ve
(c) karşılanamıyor. Üç yol önümdeydi: A (eşik gevşet, dia_works mint),
B (dia_chunks'i person enrichment için kullan, dia_works ertele), C
(B + H9 TDV scraping spec). Önerim C idi.

**Karar**: Yol C. Detaylar ADR-011'de + H8_SCRAPING_PROPOSAL.md'de.

**Gerekçe**: (a) dia_chunks içeriği ontolojik olarak biographical/
encyclopedic, work değil — zorla works namespace'ine sokmak ADR-007
rich-page-contract'i bozar. (b) labels.description.tr zaten
multilingual_text.schema.json'da var, schema mutation gerekmiyor —
sıfır risk. (c) Fatıma'nın frontend'i için somut değer (~3.309
PersonCard zenginleşir). (d) ADR-009 disiplini korunur; dia_works
rich-mint H10+'ya gerçek-yol ile (scraping) bağlanır. (e) Master plan
"vague deferral" yerine "concrete deferral with spec" çerçevesine
geçer (AA.2 → H10+ gated on AO scraping pipeline).

**Sonuç**: ADR-011 + H8_MASTER_PLAN_REVISION_PATCH + H8_SCRAPING_PROPOSAL
yazıldı. Stage 2b analyzer Kategori A'nın gerçek sayısını ölçecek.
Stage 3'te dia_person_enrichment adapter yazılır.

---

## Karar 4 — description.tr 5000-char truncation, sentence-boundary aware

**Bağlam**: multilingual_text.schema.json'da `description.<lang>`
maxLength 5000 char/lang. Bazı DiA maddeleri (İbn Teymiyye, Gazzâlî,
Selçuklular) bu sınırı kolayca aşar.

Üç seçenek:
1. **Truncate to 5000 chars** at sentence boundary + provenance flag.
2. **Multi-field overflow**: ilk 5000 description.tr'ye, kalanı note'a.
3. **Schema bump**: description.<lang> maxLength → 50.000 char.

**Karar**: 1 (truncate, pilot default). Pilot sonrası gerekirse 3'e
geçilir (ADR-012 ile, PE-2 $id housekeeping ile koordineli).

**Gerekçe**: (a) MaxLength constraint zaten existing dataset için
çalışan bir invariant — bumping önce migration script gerektirir,
sonra all entity-typeları etkiler. (b) Truncation reversible:
`provenance.note="truncated_at_5000_chars"` flag'i olan recordlar
schema bump sonrası non-truncated halleriyle re-enrich edilebilir.
(c) Pilot batch (50 chunk) gerçek dağılımı gösterir — kaç madde
trunc'lanıyor, hangi kategori daha çok etkileniyor.

**Sonuç**: Adapter v1 truncation-with-flag uygulayacak. Stage 4
pilot inspection truncation oranını + bilgi kaybı materialitesini
ölçer, gerekirse ADR-012 yazılır.

---

## Karar 5 — Stage 2b analyzer v2 empirical refinements → ADR-011 v1.1

**Bağlam**: Stage 2 doctrine (ADR-011 v1) draft halinde yazıldıktan
sonra, Stage 2b analyzer v2 ground-truth ölçümler üretti. v1 doctrine
üç noktada veriyle çelişti:

1. `a` field interpretation: v1 "TDV contributor" → `provenance.attributed_to`.
   v2 sample inspection: `a='ابن النجّار البغدادي'` Arapça-script başlık,
   contributor değil. %68.4 Cat A slug arabic_primary.
2. Per-slug aggregation: v1 her chunk'ı bağımsız enrichment unit gibi
   ele aldı. v2: 19.742 chunks / 8.093 distinct slugs = 2.44 avg
   chunks/slug. Adapter slug bazlı aggregate etmeli.
3. Truncation: v1 "0% overflow" per-chunk idi (yanlış). v2 per-slug
   68.8% overflow. Karar 4 majority-case'i temsil ediyor, exception
   değil.

**Karar**: ADR-011 v1.1 yazıldı (v1 git'e commit edilmedi — clean
trajectory). Üç düzeltme entegre:
- Patch shape Step 4: `a` (arabic_primary) → `labels.prefLabel.ar`
- Patch shape Step 1: per-slug aggregation (sort by c, concat with \n)
- Patch shape Step 2: truncation now fires on >50K (ADR-012 sonrası),
  ~5% long-tail only

**Gerekçe**: (a) Veri gerçeği doctrine'e baskın olmalı (ADR-009'un
empirical-grounding tradition'ı). (b) v1 commit'lenmediği için
rewriting clean — H7'nin "H7_MASTER_PLAN_REVISION" pattern'i v1.1
gerekmemiş; trajectory dosyası (`H8_STAGE_2b_ANALYZER_FINDINGS.md`)
audit trail'i tutar. (c) Stage 3 adapter yanlış spec'e karşı
kodlanmasın.

**Sonuç**: ADR-011 v1.1 + ADR-012 (companion) + audit trail dosyası +
master plan v1.1 + h8_002 migration. Stage 2c iki commit halinde
push'lanır (2c.1 schema bump, 2c.2 doctrine).

---

## Karar 6 — ADR-012: description maxLength 5000 → 50000

**Bağlam**: Stage 2b analyzer v2 per-slug aggregated narrative
distribution: median 6.337, p95 20.450, max 318.213, mean 8.854. Karar
4'ün (5K-truncate-at-sentence-boundary) altındaki varsayım — "truncation
nadir bir durum" — empirik olarak yanlışlandı: %68.8 Cat A slug 5K'yı
aşıyor.

İki seçenek:
- **A**: Karar 4'ü koru, 5K limit'te kal, %68.8 truncate kabullen
- **B**: Schema bumpla (5K → 50K), %95 vakayı kapsa, long-tail (~%5)
  için Karar 4 fallback'i kalsın

**Karar**: B (ADR-012). 50K seçimi:
- p95 (20.450) için 2.5x headroom
- 50K char ≈ 10K kelime ≈ ~30-40 sayfa — tek encyclopedia entry için
  makul üst sınır
- 100K+ frontend pagination requirement'ı zorlar
- Round number, documentation-friendly

**Gerekçe**: (a) %99 truncation oranı ADR-011'in academic credibility
argümanını çürütür ("enrichment meaningful only if narrative
substantially preserved"). (b) Schema mutation **additive** — sıfır
veri mutation, mevcut tüm record valid kalır. (c) Long-tail truncation
(%5) bilinçli edge case olur, default değil. (d) PE-2 ($id housekeeping)
zaten ayrı tech-debt — bu bump ona ek bir divergence ekler ama
remediation aynı toplu commit'te toplanır.

**Sonuç**: ADR-012 yazıldı, schema patched, h8_002 migration script
hazır. Stage 2c.1 olarak ayrı commit (2c.2 doctrine'den önce, çünkü
ADR-011 v1.1 ADR-012'ye back-reference yapar).

---

<!-- Stages 3-6 kararları burada eklenecek -->


