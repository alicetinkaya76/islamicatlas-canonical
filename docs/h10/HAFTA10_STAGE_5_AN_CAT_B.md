# Hafta 10 — Stage 5: AN — Cat B/C çözümü (4.784 slug)

**Date:** 2026-07-10 · **Entry:** Stage 4 (`135cf69`) üstüne.
ADR-011 v1.1'in ertelediği iş; motor = H10 Stage 1 Tier-2.

## Sonuçlar (muhasebe 4.784 tam)

| Sınıf | Sayı | Ne oldu |
|---|---:|---|
| match (conf hepsi 1.0) | **2.261** | mevcut person'a bağlandı (çoğu el-alam/bosworth-tohumlu; DiA slug'ı haritasızdı). Apply: `dia-chunks:<slug>` provenance + web locator; gap-fill: +22 prefLabel.ar, +1 desc.tr (el-alam zaten doldurmuştu — dürüst sayım), idempotent 2.261/2.261 |
| review | **1.889** | `an-cat-b.jsonl` kuyruğunda aday listeleriyle (tarihçi) |
| unmatched (triage) | **634** (257 tarihli) | MINT YOK — kişi/yer/kavram ayrımı otomatikleştirilmez (Cat C karışımı); `an_cat_b_resolution.json`'da ipuçlarıyla |

**AP kazanımı:** matches = fiilen 2.261 girişlik ek slug→pid haritası
(`an_cat_b_resolution.json`); AP author-linkage'ı Cat-A (3.309) + bu haritayı
birlikte tüketebilir. ADR-011'in AM-B hedefi (≥%50 match) %47 auto + %40
review-aday olarak gerçekleşti — otomatik bandı şişirmek yerine kuyruk tercih
edildi (North Star).

## Kabul
- [x] make test 156 · reindex 50.004/50.004 · applier idempotent.
