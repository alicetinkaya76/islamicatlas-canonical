# Hafta 10 — Stage 7: Evliyâ Çelebi atlas katmanı (yerleşim alt kümesi)

**Date:** 2026-07-10 · **Entry:** Stage 6 + dedup-notu (`df92c03`) üstüne.
**Kaynak:** Seyahatnâme atlas katmanı v2.0.0 — 5.444 geokodlu konum
(tr/en/ar ad + anlatı + kategori + sefer bağı), 10 sefer.

## Kategori yönlendirmesi (dürüst kapsam)

| Sınıf | Kategoriler | Sayı | Ne oldu |
|---|---|---:|---|
| YERLEŞİM → place | şehir, kasaba, köy, kale, liman, ada | 2.568 | iki-track Tier-2 |
| YAPI → institution-bekleyen | cami, türbe, hamam, tekke, han, saray, medrese, mescit, köprü, kilise, çeşme, bedesten | **2.608** | MINT YOK — konya/maqrizi ile aynı ADR-006 §6.4 havuzu (Ali kararı) |
| DOĞAL/BİLİNMEYEN → triage | dağ, göl, nehir, bilinmeyen | 268 | insan triage |
| SEFERLER → event-bekleyen | 10 voyage | 10 | event-aktivasyonu (Ali) |

## Sonuçlar (2.568 yerleşimde; muhasebe 5.444 tam)

- match → augment: **160 olay / 158 yer** (`derived_from_layers += evliya-celebi`;
  applier idempotent) · new → **2.232 mint** (0 validasyon hatası) ·
  review → **176** kuyrukta.
- Düşük match oranı BEKLENEN: Evliyâ 17.yy Osmanlı Balkan/Anadolu coğrafyası;
  Yâqūt 13.yy Arap-doğu — kesişim yalnız büyük şehirler.
- **2.232 Osmanlı yerleşimi = v2 haritasının yeni katmanı** (17.yy).
- place 17.577 → **19.809** · store **52.257** · reindex 52.257/52.257 ·
  test_a1 bandı 19-21K'ya belgeli genişletildi.

## Kabul
- [x] make test 156 · applier 158/158 idempotent · index tazelendi.
