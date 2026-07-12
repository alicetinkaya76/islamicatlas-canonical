# Hafta 10 — Stage 3: scholars adapter'ı (49 çekirdek âlim; augment-ağırlıklı)

**Date:** 2026-07-10
**Branch:** hafta5-work-namespace
**Entry:** H10 Stage 2 (`e3e87e8`) üstüne.
**Kaynak:** islamicatlas v1 uygulamasının scholars katmanı — scholars.csv (49
âlim; TR/EN anlatılar, tarihler, koordinatlar) + JS-literal kart dosyaları.

---

## Dönüşüm zinciri

1. **JS→JSON:** `convert_js_sources.py` (node eval; `export` satırları süzülür)
   → `data/sources/scholars/scholars_converted.json` (commit'li determinist
   türev): identity 296 kart · meta 67 · links 163 kenar · isnad 10 zincir.
2. **Adapter (darp deseninin person sürümü):** CSV ⋈ identity ⋈ meta →
   Tier-2 resolve → match=augment-sidecar / new=mint / review=kuyruk.
3. **Applier:** `apply_scholars_augments.py` — GAP-FILL-ONLY:
   `prefLabel.en`, `description.en/tr`, `kunya`, `nisba`, `laqab` yalnız
   BOŞSA; her uygulamada `derived_from += scholars:<id>` + record_history.
   İdempotency probe'u: `scholars:*` derived_from'da varsa no-op.

## DÜRÜST SINIR — 252 yetim kimlik kartı

`scholar_identity.js` 296 kart taşıyor ama id'ler repo'da OLMAYAN bir
`db.json` âlim dizisine işaret ediyor; **252 kartın isim otoritesi yok →
işlenemez.** Kapsam = 49 isimli CSV âlimi (44 kartlı, 47 metalı). Eksik
kaynak PHASE0_CLOSEOUT'a "kaynak-temini" kalemi olarak yazıldı (v1
uygulamasının db.json'ı — Ali). Sayılar sayıldı, tahmin edilmedi.

## Sonuçlar (49 kayıt; dry-run → gerçek koşu → applier)

| Track | Sayı | Not |
|---|---:|---|
| match → augment | **46** | applier 46/46, idempotent (2. koşu 0) |
| new → mint | **0** | meşhurların tümü store'da (beklenen) |
| review | **3** | scholars:3 (0.94), :24 (0.91), :37 (0.75) — kuyrukta |

Spot-check: scholars:1 → `iac:person-00002172` "Ebû Hanîfe" (ö. 767 ✓,
conf 0.96); augment sonrası kayıtta `description.en` + `kunya="Ebû Hanîfe"` +
`nisba=[Kûfî, Teymî (velâen)]` dolu. **En meşhur 46 âlim artık iki-dilli
açıklamalı** — v2 aramasının en yüksek trafikli kayıtları.

## Bekçi test yakalaması

Store-örnekleyen facet testi yeni `scholars:` prefix'ini ilanısız yakaladı
(tam da bunun için yazılmıştı) → prefix_map + facets.yaml'a açık `scholars`
katmanı ("Çekirdek Âlim Kartları (v1)") eklendi; bu sırada prefix_map'te
mükerrer `muqaddasi` anahtarı temizlendi.

## Stage-3b'ye devir (bu stage YAPMADI)

- **Hoca-talebe kenarları:** links 163 kenar + isnad 10 zincir → person
  `teachers/students` alanları (şemada VAR). Sidecar `_id_to_pid` haritası
  (46 giriş) hazır; kenar uçlarının 252 yetimden olanları db.json gelmeden
  çözülemez → birlikte ele alınacak.
- 3 review vakası tarihçiye.
- `madhab` doldurulamadı (şema concept-PID ister; namespace P1'de boş).

## Kabul

- [x] 49/49 muhasebe: 46+0+3. Applier idempotent. Reindex 49.040/49.040.
- [x] `make test` 156 passed / 2 skipped / 3 xfailed.
- [x] Yetim-252 sınırı belgeli (journal + PHASE0_CLOSEOUT).

## Rollback

Kod+docs tek revert. Augment'lar: derived_from'daki `scholars:*` girdisi +
record_history notu üzerinden alan-bazında geri alınabilir (gap-fill'ler
kayıt tarihçesinde adlandırılmış).
