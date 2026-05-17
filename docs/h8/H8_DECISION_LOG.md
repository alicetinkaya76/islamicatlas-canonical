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

<!-- Stages 2-6 kararları burada eklenecek -->
