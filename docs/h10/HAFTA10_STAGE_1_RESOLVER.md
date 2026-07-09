# Hafta 10 — Stage 1: Tier-2 fuzzy resolver (ADR-008 §8.2 gerçek implementasyon)

**Date:** 2026-07-09
**Branch:** hafta5-work-namespace
**Entry:** H9 close (`hafta9-close`, main'e merge edilmiş) üstüne; H10 Stage 1.
**Trigger:** Kullanıcı hedefi = islamicatlas.org v2; 9 dönüştürülmemiş kaynağın
profillemesi 5'inin ortak blokörünü fuzzy-resolution olarak gösterdi
(H10 Karar 1). AN'in motoru da budur.

---

## Bu stage ne yapar

H2'den beri stub duran (`kind="new"` sabit) `_tier2_blocking_similarity`,
ADR-008 §8.2'ye göre gerçek implementasyonla değiştirildi; indeks katmanındaki
iki gizli bug düzeltildi; eşikler canlı veriyle kalibre edildi.

### A. `build_lookup.py` düzeltmeleri (indeks katmanı)

| Bug | Etki | Fix |
|---|---|---|
| `entity_type = @type[0]` | 768 subtype-first person kaydı 'scholar' olarak bracket'leniyordu → Tier-2 blocklaması onları hiç göremezdi (H9 projector bug'ının aynı sınıfı) | @id'den türet (ADR-001 deseni), @type fallback |
| temporal listesi person alanlarını içermiyordu | 21.946 person'ın TAMAMI bracket'siz → yüzyıl blocklaması ölü | `death_/floruit_/birth_temporal` eklendi (ölüm yılı birincil — ADR-008 blocking anahtarı) |
| `label(pid)` indeksi yok | aday başına 115K satır tarama → **467 ms/resolve** | `label_pid_idx` → **20 ms/resolve** (23×) |

İndeks yeniden kuruldu (11 sn): 46.702 bracket · 115.016 label · 12.178
authority · 50.078 curie.

### B. Tier-2 implementasyonu (`entity_resolver.py`)

- **Blocking:** FTS5 token-OR (bm25 sıralı, ≤200 aday) ⋈ `entity_bracket`
  (entity_type filtresi). Sert yıl-bloku: iki taraf tarihli ve |Δ|>150 yıl →
  aday elenir (adaş bastırma).
- **Skorlama:** mevcut özellikler üzerinde ağırlıklı ortalama —
  `label` (aday prefLabel'ları üzerinde max token_set_ratio), `alt`
  (alt/translit), `temporal` (1−|Δyıl|/50), `spatial` (1−haversine/50km).
  Eksik özellik skoru SULANDIRMAZ (ağırlıklar yeniden normalize).
- **Karar:** skor ≥ auto eşiği **VE ≥2 bağımsız sinyal** → match(tier 2);
  ≥ review eşiği → review (top-5 aday kuyruğa); altı → new.
  **İsim-tek-başına asla auto-match** (North Star guard'ı — testli).
- `_normalize_name`: NFKD+TR-fold+noktalama; bilinçli olarak title-fingerprint'ten
  HAFİF (isimde 'Kitāb' düşürülmez); token-sıra/alt-küme işini rapidfuzz yapar.
- Tier-3 kuyruk (H2'den beri erişilemezdi) artık fiilen akıyor:
  `data/review_queue/<adapter>.jsonl` aday listeleriyle yazılıyor.

### C. Kalibrasyon (ampirik; tahmin yok)

**Yöntem:** 1.400 alam↔dia Track-A xref çifti = bilinen-doğru eşleşme evreni;
seed=42 ile 250 örneklem; canlı 46.702-kayıt indeksine karşı yalnız Tier-2
(authority/curie verilmeden). Ayrıca 150 Track-B kaydı (H4'te store'a mint
edilmişler) öz-eşleşme sağlaması olarak.

**Ground-truth sonuçları (n=250):** auto-match 169 = doğru 139 +
store-dublör-adayı 21 (aynı isim + ölüm ±5 + ≥0.95 → Karar 3) + gerçek-yanlış
9; review 67 (adayda-doğru 51); kaçan 14. **Track-B (n=150):** 134 öz-eşleşme
(=doğru), **0 çapraz-hata**, 13 review, 3 new.

**Eşik taraması (auto bandı):**

| eşik | auto | doğru | dublör-adayı | GERÇEK-YANLIŞ | prec (dublör=OK) |
|---:|---:|---:|---:|---:|---:|
| 0.90 | 169 | 139 | 21 | 9 | %94.7 |
| 0.93 | 147 | 122 | 21 | 4 | %97.3 |
| **0.95** | **119** | **97** | **21** | **1** | **%99.2** |
| 0.97 | 99 | 79 | 20 | 0 | %100 |

**Karar (H10 Karar 2):** person auto=0.95 → `resolver_weights.yaml`
(dosya artık gerçekten var; `_load_weights` bunu okur). 0.90-0.95 bandı
review'a iner — kayıp değil, insan şeridine devir. Nihai profil:
**precision(auto) %99.2 · recall(auto+review-adayda) %84.4 · 20 ms/resolve**
(ei1'in 7.568 kaydı ≈ 2.5 dk).

### D. Yan bulgu (Karar 3)

21 "yanlış" aslında store'daki muhtemel çapraz-kaynak dublörlerini ifşa etti
(H4-H5 seed'leri Tier-2'siz koşmuştu). Store'a DOKUNULMADI; dedup taraması
PHASE0_CLOSEOUT §2'ye kalem olarak eklendi.

## Testler

`tests/integration/test_entity_resolver_tier2.py` (yeni, 9): fixture-repo +
gerçek index-builder ile — auto-match (isim+yıl), uzak-transliterasyonun
review'a inişi (kalibre eşiğin belgelenmiş davranışı), isim-tek-başına
guard'ı, sert yıl-bloku, place spatial sinyali, kuyruk JSONL'i, ağırlık
renormalizasyonu, normalizer fold'ları. `tests/test_resolver.py` 5/5 korunuyor.
Suite: **147 → 156 passed** / 2 skipped / 3 xfailed; `make test` uçtan uca yeşil.

## Bu stage ne YAPMAZ

- Canonical store'a yazmaz; hiçbir adapter'ı resolver'a BAĞLAMAZ (ilk tüketici
  — scholars/ei1 adapter'ı veya AN — kendi stage'inde bağlar).
- place/work/dynasty eşiklerini kalibre etmez (ilk tüketicileriyle).
- AP'yi başlatmaz (Ali'nin 2 kararı — HAFTA10_AP_KICKOFF).
- data/_index gitignored — indeks her makinede `build_lookup.py`yle kurulur.

## Kabul

- [x] Tier-2 stub değil: blocking+scoring+karar ADR-008 §8.2'ye uygun, testli.
- [x] Eşikler ground-truth + taramayla kalibre; metodoloji + tablo bu journal'da.
- [x] İsim-tek-başına auto-match imkânsız (test); Tier-3 kuyruk akıyor (test).
- [x] `make test` 156 passed; smoke 5/5; storeless CI güvenli (importorskip +
      fixture-repo).

## Rollback

Tek revert: resolver + weights + index-builder düzeltmeleri + testler birlikte
döner (suite 156→147). data/_index yeniden kurulabilir state'tir.
