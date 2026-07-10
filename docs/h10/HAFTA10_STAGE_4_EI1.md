# Hafta 10 — Stage 4: EI1 adapter'ı (7.568 giriş; tek-namespace mint + çok-namespace augment)

**Date:** 2026-07-10 · **Entry:** Stage 3 (`c5d560a`) üstüne.
**Kaynak:** Encyclopaedia of Islam 1st ed. (Brill 1913-1936; telif dışı),
OCR-türevi `ei1_lite.json` + geo/works yan dosyaları.

## Tasarım

- **Tek-yield-namespace:** yalnız PERSON mint edilir (run_adapter tek şemaya
  doğrular). geography/dynasty track'leri augment/review-only; "new"leri
  MINT EDİLMEZ (Yâqūt gazetteer'i zaten kapsıyor; koordinatsız OCR-yeri
  haritaya değer katmaz) — sayıları sidecar'da.
- **Tarihsiz yeni-person mint edilmez** (dia emsali, P0.2 temporal kuralı).
- **Work başlıkları mint edilmez** — ei1_works yalnız başlık-listesi =
  ADR-009'un yasakladığı sig-mint; augment payload'ında kanıt olarak durur.
- concept (203) / unknown (1.270) / cross_reference (467) → sınıf-atlaması
  (kanonik ev yok; triage insan işi).

## Sonuçlar (muhasebe: 5.628 yönlendirilen + 1.940 sınıf-atlanan = 7.568 ✓)

| Track | Sayı |
|---|---:|
| match → augment (person+place+dynasty) | **242 olay → 224 kayıt** (applier idempotent) |
| person mint (tarihli yeni) | **964** (0 validasyon hatası) |
| person yeni-tarihsiz (mint yok) | 2.119 |
| place/dynasty yeni (mint yok) | 729 |
| review (kuyruk) | **1.574** |

Augment gap-fill: description.en/tr/ar + altLabel.en + (place) layers +
`ei1:<id>` provenance (cilt+sayfa locator'lı). Spot-check eşleşmeler: hepsi
1.0 (Ibn Bakr, al-Balkhī, Ibn Bandār...).

**person: 21.946 → 22.910 · store: 50.004 kayıt · reindex 50.004/50.004.**

## Dürüst notlar

- Match oranı (242) düşük: EI1 adları Latin-OCR translit, store tr/ar ağırlıklı
  — recall kuyruğa aktı (1.574 review, aday listeli). OCR gürültüsü ("BA GH
  DAD") tasarım gereği match'i bozmak yerine review/new-dateless'e düşüyor.
- Bekçi facet-testi yeni `ei1` katmanını yakaladı → facets+prefix_map ilan.
- 2.119 tarihsiz + 729 yer/hanedan-yeni + 1.940 sınıf-atlanan = gelecekteki
  triage havuzu; hiçbiri sessizce yutulmadı, sidecar'da sayılı.

## Kabul
- [x] make test 156 passed · reindex 50.004/50.004 · applier 224/224 idempotent.
