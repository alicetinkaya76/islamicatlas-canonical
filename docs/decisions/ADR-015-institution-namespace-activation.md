# ADR-015: Institution namespace aktivasyonu + şema seti v0.4.0

**Status:** Accepted · **Date:** 2026-07-12 · **Phase:** 0 (H11 Stage 5)
**Decision-makers:** Ali Çetinkaya (onay: "Yapılar için evet", 2026-07-12);
uygulama kararları kullanıcı devriyle Claude.
**Related:** ADR-005 (faz aktivasyonu), ADR-006 §6.4 (yeni varlık tipi
runbook'u), ADR-013 (set-versiyonlama — bu bump onun R2-R4 prosedürünün ilk
gerçek icrası)

## Bağlam

H10-H11 dönüşümleri ~4.800 yapı-sınıfı kaydı (Evliyâ 2.608 + Konya 583 +
Kahire 801 + Makrîzî 801 + monuments 40) "institution şeması yok" kapısında
biriktirdi. Yapılar Place'e sokulamaz (yerleşim ≠ yapı; INVENTORY de ayrı
tip ister). Kullanıcı kategoriyi onayladı.

## Karar

1. `schemas/institution.schema.json` eklendi: @id `iac:institution-NNNNNNNN`;
   @type `iac:Institution` (+ Mosque/Madrasa/Shrine/Hammam/Caravanserai/
   Palace/Bridge/Church/Fountain/Market/Tekke/Library/Hospital/Observatory);
   `located_in` (place-PID, Tier-2 çözümlü — asla tahmin edilmez),
   `founded_temporal`, `patron_person/dynasty`, coords, provenance.
2. **Set v0.3.0 → v0.4.0 ATOMİK** (ADR-013 R2-R4): 38 `$id`/`$ref` URI'si
   tek commit'te yeniden yazıldı; `EXPECTED_SET_VERSION` + `EXPECTED_FILES`
   (11→12) aynı commit'te; 2 yeni fixture (17/17).
3. Arama/UI zinciri aynı commit'te: projection rule, facet değeri, sayfa
   tarifi (7/7), projector skoru.

## Sonuçlar

+ 4.800 bekleyen yapı dönüştürülebilir (adapter'lar ayrı stage).
− v0.4.0, Faz 0.5 w3id yayın yollarını v0.4.0 olarak günceller (zaten
  yayınlanmamıştı; ilk yayın bu etiketle olur). Ontoloji iac:Institution
  sınıfı Faz 0.5 ontoloji bakımına eklendi.

**Revision history:** 2026-07-12 ilk sürüm (H11 S5).
