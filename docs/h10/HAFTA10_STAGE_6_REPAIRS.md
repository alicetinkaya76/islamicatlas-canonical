# Hafta 10 — Stage 6: Onarım koşuları (PHASE0_CLOSEOUT §2)

**Date:** 2026-07-10 · **Entry:** Stage 5 (`46cd14d`) üstüne.

## 1. el-alam kayıp-21 onarımı — `repair_el_alam_lost.py`

TAM re-run BİLİNÇLİ reddedildi: `run_adapter --id el-alam` 12.5K mevcut kaydı
taze timestamp'le yeniden yazardı (provenance.created gerçeği bozulur).
Hedefli script: extract filtrelenir (dia_slug'lu ama diskte kaydı olmayan) →
yalnız kayıp sınıf gerçek adapter canonicalize'ından geçer. Sonuç: **21 mint**
(öngörüyle birebir: 22 aday − 1 temporal-skip), idempotent (2. koşu 0),
şema-valid. person 22.910 → **22.931**; store **50.025**.

## 2. Phantom-PID denetim sidecar'ı — `phantom_pid_audit.py`

`data/_state/phantom_pids_audit.json` (salt-okur): **2.782 phantom** =
1.249 el-alam + 1.167 openiti + 361 dia + 3 darp-rezerv + 2 bosworth.
**openiti teşhisi:** work-mint değil — H5 yazar-placeholder mint'lerinin
kısmî yazımı (index'te var, record alt kümesi diske inmiş; örneklem:
0001AwsIbnHajar diskte yok, komşuları var). Yeniden-üretimi AP-öncesi ayrı
onarım. Politika: index temizliği YOK (ordinal determinizmi + rezerv
kategorisi); tüketiciler disk-doğrulamalı lookup kullanır.

## 3. Çapraz-kaynak dublör taraması — `dedup_scan_persons.py`

H10 Karar 3'ün işi: 22.931 person kendine-karşı Tier-2'den (≥0.95 +
çift-sinyal, öz-eşleşme hariç) → `person_dedup_candidates.json` aday
çiftleri. STORE'A YAZMAZ; merge ADR-008 Tier-3 insan kararı. (Sonuç sayısı
koşu bitince bu dosyanın altına işlenir.)

### Tarama sonucu (2026-07-10, koddan)
- **22.931 tarandı → 3.199 aday çift** (`person_dedup_candidates.json`).
- Örneklem şüphesiz gerçek dublörler: Ebû Bekir, ʿUthmān, ʿAlī, el-Mansûr,
  el-Mehdî... (bosworth-rulers/science-layer ↔ dia/el-alam çift-tohumları) —
  H4-H5'in Tier-2'siz dönemi ölçekte görünür oldu (~%14'lük kesişim).
- Merge İNSAN kararı (ADR-008 Tier-3): dosya skor-sıralı aday listesidir;
  onaylanan çiftler ileride ADR-008 append-only merge semantiğiyle birleşir
  (ayrı, journal'lı iş — Faz 0.5 öncesi önerilir, arama dublör gösteriyor).

## Kabul
- [x] 21/21 onarım idempotent; audit sidecar yazıldı; make test 156; index tazelendi.
