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

## Karar 7 — Bulk run on full Cat A (3,309 records) under `--strict`

**Bağlam**: Stage 4 pilot (50 records, deterministic alphabetical
subset) emitted 7/7 AG green ve 0 validation failure. ADR-011 v1.1
patch shape ve ADR-012 schema bump pilot batch'te doğrulandı. Bulk
run önce `--lenient` (silent-skip on error) ya da `--strict` (halt-on-
first-error) modunda yapılabilirdi.

**Karar**: `--strict`. Bulk run komutu:
`python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --strict`

**Gerekçe**: (a) Pilot, lenient mode'un meşru gerekçesini ortadan
kaldırdı — record-level failure beklenmiyor; varsa silently
absorblamak yerine investigation tetiklenmeli. (b) `--strict` halt
ise, error surface'i tek bir record'da yoğunlaşır, debugging süresi
küçülür. (c) Stage 5 bulk için planlanan AM acceptance criterion
(≥ 2,647 enrichment) `--strict` altında verifiable bir contract olur.

**Sonuç**: Bulk run iki pasta hâline geldi (Karar 8 nedeniyle).
Pre-fix run 637 record yazdı, 638'inci (`efgani-cemaleddin`) maxLength
overflow nedeniyle halt etti. Post-fix resume yine `--strict` ile
çalıştı: `skip_idempotent=637`, `yielded=2,672`, validation failures
= 0. Toplam: 3,309 / 3,309 Cat A enriched (100% kapsama). AM hedefi
(≥ 2,647) %25 marjla aşıldı.

---

## Karar 8 — `truncate_at_sentence_boundary`: marker length'i search range'den rezerve et

**Bağlam**: Stage 5 strict bulk halt etti çünkü `efgani-cemaleddin`
(74,318-char aggregated narrative) için truncate işlemi 50,008-char
çıktı üretti — ADR-012 schema constraint'i (50,000) 8 char aştı. Root
cause: sentence-boundary search penceresi `[max_len-200, max_len]`
spanlıyordu, bu yüzden `cut_pos` en kötü ihtimalle `max_len`'e
ulaşıyordu. " […truncated]" marker'ı (15 char) sonradan eklenince
total length `max_len + marker_len`'e kadar çıkabiliyordu. Function's
contract (`len(result) ≤ max_len + marker_len`) açıktı ama ADR-012'nin
strict `maxLength: 50000`'i tolere etmiyordu.

**Karar**: Marker length'i search range'den rezerve et:
`search_end = max_len - marker_len`. `TRUNCATION_MARKER` top-level
constant olarak çıkar (test edilebilirlik için). Defensive clamp
ekle: `cut_pos = max(0, min(cut_pos, search_end))`. Degenerate
guard: `max_len ≤ marker_len` durumunda `TRUNCATION_MARKER[:max_len]`
döndür (production hit etmeyen edge case ama function total olur).

**Gerekçe**: (a) En basit fix — sadece search end'i yeniden hesapla,
diğer logic değişmez. (b) `len(result) ≤ max_len` invariant'ı artık
universal — tüm input'lar için geçerli, sadece typical'lar için
değil. (c) Constant'ı çıkarmak future property-based test için
zemin hazırlar. (d) Patch file (`apply_h8_stage5_truncate_fix.py`)
idempotent: TRUNCATION_MARKER constant'in varlığını probe ederek
re-run no-op olur.

**Sonuç**: Patch uygulandı, lib import sanity OK, efgani-cemaleddin
re-verify edildi (input=74,318 → output=49,999 ≤ 50,000 ✓). Stage 5
bulk resume sırasında previously-failed record başarıyla yazıldı.
Bug Stage 5 içinde kapatıldı; H9'a residual issue olarak taşınmıyor.

### Yan ders (postmortem note)

Alphabetically-sorted pilot tail conditions'i underrepresent ediyor:
50 alphabetic sample, narrative length p99 distribution'ı sample
etmez. Stage 4 pilot p<0% probability ile overflow rejimini
gözlemledi; randomized 50-sample p≈92% ile gözlemleyebilirdi. Future
pilot template'i hybrid sampling (alphabetical + random-by-attribute-
decile) önerir. Bu bir process improvement, formal karar değil —
`HAFTA8_STAGE_5_BULK.md` §"Why the pilot did not catch it"'te kayıtlı.

---

## Karar 9 — H8 close: tek ceremonial commit + `hafta8-close` tag + adapter enable

**Bağlam**: Stage 5 tamamlandı; H8 kapanışı için iki seçenek var:
**A** — Stage 6 close'u birden çok commit'e böl (bir close-state
doc commit, bir adapter-enable commit, bir tag commit). **B** —
Tek ceremonial commit: 5 dosya değişikliği + tag — H7 close pattern'i
ile uyumlu.

**Karar**: B. Tek commit:
1. `docs/h8/HAFTA8_STAGE_5_BULK.md` (NEW — bulk journal + postmortem).
2. `docs/h8/HAFTA8_CLOSE_STATE.md` (NEW — H8 close state).
3. `docs/h8/H8_DECISION_LOG.md` (APPEND — Karar 7, 8, 9 — bu girdiler).
4. `docs/h8/H8_KNOWN_ISSUES.md` (APPEND — H8 close footer; PE-2 unchanged,
   Stage 5 bug closed-within-H8).
5. `pipelines/adapters/registry.yaml` (FLIP — `dia-person-enrichment-v8`
   `enabled: false → true`).
6. Tag `hafta8-close` close commit'inde.

**Gerekçe**: (a) **Ceremoniality**: H7'nin pattern'ı (single close
commit + tag) audit trail'i okunabilir tutar — H8 close'un tek
SHA'ya bağlanması H9 retrospektif için clean entry point sağlar.
(b) **Atomicity**: 5 değişiklik mantıken atomic — close-state doc'un
adapter enable'siz tutarsız olur, journal'sız ise referans dangle eder.
(c) **Idempotency**: orchestrator (`apply_h8_stage6_close.py`)
re-runnable; dry-run + wet-run ayrımı tek commit cycle'da görünür.
(d) **Adapter enable**: registry flip ceremonial commit'in semantic
core'u — H8 kapanışıyla birlikte gelecek `run_all_adapters.py`
replay'leri bu adapter'i otomatik dahil eder. Flip pre-Stage-6
yapılsa, "enabled but not closed" bir window oluşurdu.

**Sonuç**: Tek close commit, 5 dosya değişikliği, `hafta8-close` tag.
H8 hesap-kapatması tamamlanır; H9 PE-2 (veya AO scraping) ile başlar.

<!-- Stages 3-6 kararları burada eklenecek -->


