# Hafta 10 — Stage 8: İbn Battûta Rihle durakları

**Date:** 2026-07-10 · **Entry:** Stage 7 (`0546d26`) üstüne.
**Kaynak:** 317 geokodlu durak (tr/en/ar + CE/AH varış + Rihla sayfa-locator +
anlatı/alıntı), 7 sefer, 1 gezgin (zaten person store'da: dia).

## Sonuçlar (muhasebe 317 tam)

| Track | Sayı |
|---|---:|
| match → augment | **148 olay / 124 yer** (rota şehirleri — beklenen yüksek oran; applier idempotent) |
| new → mint | **128** Settlement (varış-yılı temporal'lı; Rihla s.X locator'lı; 0 validasyon hatası) |
| review | **41** kuyrukta |
| sefer/rota | 7 (+GeoJSON) event-aktivasyonu bekliyor |

place 19.809 → **19.937** · store **52.385** · reindex 52.385/52.385.

## Yenilik: jenerik applier

`apply_layer_augments.py` — darp/evliya applier'larının üçüncü kopyası yerine
parametrik tek script (`--layer --sidecar --namespace`); sonraki tüm
layer-augment kaynakları bunu kullanır. İdempotent 124/124.

## Kabul
- [x] make test 156 · band 19-21K içinde · index tazelendi.
