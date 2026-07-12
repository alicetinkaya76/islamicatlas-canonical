# Hafta 10 — Stage 14: Final-review remediation (46-ajanlık inceleme)

**Date:** 2026-07-12 · **Entry:** Stage 12+13 (`daebcf5`) üstüne.
H10'un tüm diff'i (76c2d14..HEAD) 4-dilimli inceleme + 2-refuter doğrulamadan
geçti: **17 onaylı bulgu** (4 çürütüldü, 16 low). Hepsi ya düzeltildi ya
belgeli-ertelendi.

## Veri onarımları (h10_003; hepsi idempotent, history'li)

| Onarım | Sayı | Ne |
|---|---:|---|
| R1 doğum-ölüm karışımı | **58** | EI1 bc-fallback'i doğum yılını death_temporal'a yazmıştı (Barhebraeus sınıfı) → birth_temporal'a taşındı |
| R2 AN çok-slug çakışması | **9 kayıt / 18 slug** | Yanlış-kişi bulaşması kanıtlıydı (Nûh II ← Mansûr b. Nûh) → AN katkıları GERİ ALINDI, slug'lar collisions kuyruğunda |
| R3 ei1 çok-olay çakışması | **14 kayıt / 32 olay** | Adaş-merge şüphesi (5166: Osmanlı I. Mahmud ↔ Malwa Mahmud'ları) → ei1 katkıları geri alındı, kuyruğa |
| R4 mükerrer yer mintleri | **8 silindi** | Koşu-içi indeks-tazeliği bug'ı: Rihle'nin tekrar-uğrayışları ("Kûlam (Dönüş)") ayrı mint olmuştu; 1 vs-store + 7 ibn-içi; sınır-vakalar (İhmîm↔Aḫmīm 80, Sehwan↔Sadūsān 77) SİLİNMEDİ → borderline_review |
| R5 evliya temporal backfill | **469** | voyage başlangıç yılından temporal_coverage (kaynakta yıl taşıyan seferler) |

Store: 52.385 → **52.377** · reindex 52.377/52.377.

## Kod düzeltmeleri

- **HARD_YEAR_BLOCK yalnız person** (yerlerde tanıklık-yılı varoluş sanılıyordu
  — R4'ün kök nedeni).
- **decision_cache lookup.sqlite'tan AYRILDI** → `data/_state/decision_cache.sqlite`
  (index --rebuild artık idempotency hafızasını silmiyor); v2 şema tier+queue_id
  taşır (replay kanıt zinciri); `_review_enqueue` rid-dedup guard'ı (re-run
  kuyruk şişirmez).
- **run_adapter preserve** genişledi: teachers/students/kunya/nisba/laqab +
  derived_from_layers BİRLEŞİMİ + provenance.created/record_history/
  derived_from applier-katkıları korunur (re-run H10 augment'larını silemez).
- ei1 `_temporal` kaynak-anahtarı taşır (bc→birth, dc→death; resolver'a yalnız
  ölüm yılı gider); `apply_an_cat_b` + `apply_ei1_augments` çok-eşleşme
  guard'ları (otomatik uygulamaz → collisions kuyruğu).
- `resolver_weights` sızdırmaz-kontrat (eksik anahtar=0; YAML bozulursa SESLİ
  in-code default'a düşüş); `_score` **optional:false** (Typesense
  default_sorting_field'ı optional REDDEDER — canlı-blocker) + test assert'i;
  test_i ters-yön denetimi (disk→index) + dedup-rezerv kategorisi.

## Belgeli-ertelenenler (PHASE0_CLOSEOUT'a işlendi)

Review-karar geri-beslemesi (cli.py→cache; tasarım işi), koşu-içi indeks
tazeliği için genel çözüm (adapter'lara in-run mint-cache), sidecar
queue_id/tier retro-onarımı (rid-join), ei1 dc-kopyası geniş taraması.

## Kabul
- [x] 17/17 bulgu ele alındı (13 fix + 4 belgeli-erteleme değil — 13 fix
      sınıfı + 4 erteleme); make test 158; reindex 52.377/52.377; onarımlar
      idempotent.
