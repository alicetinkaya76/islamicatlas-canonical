# Hafta 10 — Stage 12+13: work-provenance düzeltmesi + scholar kenarları

**Date:** 2026-07-10 · **Entry:** Stage 11 (`44f1057`) üstüne.

## S12 — h10_002: 9.330 work'ün jenerik pipeline_name düzeltmesi

H5 registry-id uyuşmazlığının kalıntısı (`canonicalize_work` fallback'i)
source_id önekinden gerçek ada çevrildi: openiti→canonicalize_work_openiti,
science-works→canonicalize_work_science. **9.330 fixed / 1 already-ok
(Hassâf) / 0 unknown**; idempotent; her düzeltme record_history'li.

## S13 — scholar kenarlarının uygulanabilir alt kümesi

163 kenar (teacher 24 · influence 98 · isnad 39 · debate 2) + 46'lık
`_id_to_pid`: **yalnız 3 teacher kenarı iki-ucu-eşli** → `teachers[]`/
`students[]` gap-append (yön künyeyle doğrulandı: Mâlik→Şâfiî→Ahmed b.
Hanbel). Kalan **160 kenar + 10 isnad zinciri** `scholar_edges_pending.json`'a
— 252 yetim kart (v1 db.json — Ali) gelince ve P1 graf katmanında işlenir.
influence/debate şemasız (alan yok) → bilinçli pending.

## Kabul
- [x] İkisi de idempotent · make test 158 · kararsız kuyruk BOŞALDI.
