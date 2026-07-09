# Hafta 9 — Stage 3: Tüm-repo incelemesi remediation'ı (veri güvenliği + AP-hazırlık + arama katmanı)

**Date:** 2026-07-07
**Branch:** hafta5-work-namespace
**Entry HEAD:** 12dc460 (Stage 2e — AO kapanışı)
**Trigger:** Kullanıcı talebi ("tüm projeyi incele ve iyileştir; daha smart ve
hızlı bitirmemi sağla") → 56-ajanlık çok-yönlü inceleme (6 paralel okuyucu ×
derinlik + her bug/perf bulgusuna 2 bağımsız çürütücü): **81 ham bulgu → 16
doğrulanmış bug/perf + 56 diğer; 9 çürütüldü ve elendi.**

---

## Bu stage ne yapar

Doğrulanmış bulguların **kod** ayağını kapatır (test altyapısı Stage 4'te,
hijyen/docs Stage 5'te). Tüm düzeltmeler ileriye dönüktür; canonical store'a
tek onarım dokunuşu vardır ve o da state'tir (aşağıda, h9_001).

### A. Veri güvenliği / AP-blocker düzeltmeleri

| Bulgu (doğrulanmış) | Düzeltme |
|---|---|
| **CANLI DRİFT: `iac:work-00009331`** (H6 Hassâf elle mint'i) pid_index/pid_counter dışında → AP'nin ilk work mint'i aynı PID'i yeniden basıp kaydı ezecekti | `pipelines/migrations/h9_001_work_pid_state_repair.py` (idempotent; koşuldu): index += `work:tdv_dia:hassaf:title_2`, counter.work 9330→9331. Doğrulama: counter==index==disk==9331. Bekçi: `test_b2` xfail'i kaldırıldı + düz index formatını okuyacak şekilde düzeltildi |
| PidMinter her mint'te 2.7 MB index'i okuyup yeniden yazıyor (ölçülen 31.3 ms/mint → AP'de ~10-15 dk saf I/O) | `session()` batch API'si: blok boyunca kilit + bellekte mint + çıkışta tek atomik yazım. Ölçüm: **0.001 ms/mint** (bloktaki davranış birebir; 3 yeni test) |
| `wikidata_reconcile._cache_get` 30 günlük TTL'i offline modda da uyguluyor — 11.217 satırlık cache'in tamamı 2026-06'dan beri expired → bugünkü bir re-run QID'leri sessizce düşürür | Offline modda TTL yok sayılır (offline'da cache = doğruluk kaynağı; refetch yolu yok). Ek: manifest'te bildirilen seed dosyası yoksa/parse edilemiyorsa artık stderr'e WARNING |
| `run_adapter` overwrite-preserve listesi yalnız place/dynasty alanları — person re-run'ı `authored_works`/`birth_place`/`death_place`/`active_in_places` backfill'lerini siler | Listeye person alanları + `had_ruler` + `authority_xref` (yeni kayıt boşsa koru) eklendi. Ayrıca strict modda @id'siz kayıt artık sessiz değil (FAIL satırı + özet her modda) |
| `el_alam` Track A `mint()` çağırıyor (lookup değil) → güvenlik ağı ölü kod, 20 Ziriklī kişisi sessizce augment-sidecar'a gömülü | `lookup()` + disk-varlık guard'ı (phantom index girdilerine karşı); PID yoksa Track B'ye düşer. **Re-run bu stage'de YAPILMADI** (canonical yazımı ayrı, journal'lı koşu — PHASE0_CLOSEOUT §2) |
| `dia` adapter'ı PID'i temporal-skip'ten ÖNCE basıyor → 361 phantom `person:dia:*` index girdisi | mint, eligibility kontrolünden sonraya taşındı (mevcut phantom'ların denetimi PHASE0_CLOSEOUT §2'de) |

### B. AP-hazırlık (work_canonicalize)

- **`build_work_type_array` ölü kodu dirildi:** erken `return ["iac:Work"]`
  kaldırıldı; `WORK_SUBTYPES` donuk v0.3.0 enum'una yeniden yazıldı (H5
  taslağındaki LegalManual/Commentary/Translation... enum'a hiç girmemişti);
  cap 4→3 (şema maxItems). Enum driftine karşı test.
- **`adr009_rich_gate()` eklendi:** ADR-009 (a)/(b)/(c) eşiklerinin pre-write
  kontrolü — AP'nin zorunlu kapısı; print cilt+sayfa VEYA tarihli web-locator
  (Stage 2e'nin 5 online-only maddesi için) kabul eder. 3 testle kilitli.
- **Title fingerprint düzeltmeleri** (AP/AN dedup'unun temeli): (1) `w`
  düşürülüp `v` düşürülmüyordu → Hayawān↔Hayevân, Wafayāt↔Vefeyât ayrışıyordu;
  simetrik `v`-drop. (2) Arapça stopword kontrolü prefix-strip'ten ÖNCE
  ("في"→"ي" çöp token'ı). (3) ʾ/ʿ/kıvrık tırnak apostrof-eşdeğeri AYIRICI
  sınıfına alındı ("aʿyān"↔"a'yân"). (4) Token-başı proclitic soyma
  al/el/il'e daraltıldı — eski liste kökleri parçalıyordu (Fihrist→hrist,
  Bidāya→daya, Wafayāt→fayat). 4 çeviri-yazı çifti + negatif testlerle kilitli.
  NOT: H5-H7 sidecar'ları (work_same_as_clusters vb.) eski normalizer'la
  üretilmişti; AP/AN taze hesaplar — eski sidecar'lar audit arşividir.
- `try_resolve_author_pid`'in var-olmayan `pid_minter._index` fallback'i
  silindi (hem attribute yok hem anahtar şeması yanlıştı).

### C. Arama katmanı (bugün kırıktı)

- **`projector._infer_entity_type` artık @id'den** (PID deseni ADR-001 gereği
  namespace taşır): subtype-first `@type` dizili **768 person kaydı** "No
  projection rule for entity_type=scholar" ile düşüyordu. `_d_subtypes` de
  sıradan bağımsız (supertype hariç tümü). **Ölçüm: `full_reindex --dry-run`
  = 46.702/46.702, 0 fail, 18 sn** (önce: exit 1).
- `_d_source_layers` prefix_map + `facets.yaml` senkronu: science-works,
  el-alam, dia/dia-chunks-v8/dia-rich/tdv_dia eklendi (AP'nin `tdv_dia`
  katmanı artık görünür); iqlim facet'i veri gelene dek kapalı (0/15.239
  kayıtta alan var); facets başlığındaki "projector doğrular" yanlış iddiası
  düzeltildi. `full_reindex`'in "Hafta 6" bayat mesajları güncellendi.
- `ui_contract/entity_page.meta.schema.json` `$schema` anahtarına izin
  (6/6 tarif kendi meta-şemasını geçemiyordu) — artık testli.
- `dia_tdv_scrape/scrape.py`: progress-meta merge sırası (eski meta yenileri
  eziyordu) + Retry-After HTTP-date biçimi (RFC 9110) desteği.

### Çürütülen bulgular (uygulanMAdı — kayıt için)

9 bulgu 2'şer bağımsız çürütücüyle elendi; öne çıkanlar: "OpenITI seed 8/15
halüsinasyon QID", "Tier-1 'identifier' alan adı bug'ı", "pipeline_version
hardcode", "304/unchanged resume tuzağı". Ayrıntı inceleme çıktısında; QID
kalitesi Faz 0.5 audit kalemi olarak PHASE0_CLOSEOUT'ta.

## Testler

Yeni: `test_work_canonicalize_lib.py` (14), `test_search_ui_contract.py` (6),
`test_work_pilot.py::test_b2` (xfail→passed). `pytest tests/integration/` bu
stage sonunda: eski 101'in tamamı + yenilerle birlikte YEŞİL (kümülatif sayım
Stage 4 journal'ında; suite düzeni orada değişiyor). `run_schema_tests` 15/15.

## Kabul

- [x] 16/16 doğrulanmış bug/perf bulgusunun kod ayağı kapalı (2 tanesi —
      el-alam re-run + phantom audit — bilinçli olarak koşu-aşamasına
      devredildi, PHASE0_CLOSEOUT §2).
- [x] `full_reindex --dry-run` 46.702/46.702 · 0 fail.
- [x] h9_001 idempotent + doğrulamalı; canonical KAYIT dokunulmadı (yalnız
      data/_state onarımı).
- [x] Suite yeşil; şema seti v0.3.0 değişmedi.

## Rollback

Kod düzeltmeleri tek `git revert` ile döner (test'ler de aynı commit'te —
yetim kırmızı test kalmaz). h9_001 state onarımı revert'le GERİ DÖNMEZ
(gitignored state); geri almak isteyen pid_counter.work'ü 9330'a, index'ten
hassaf anahtarını silmeli — ama bu PID çakışma bombasını yeniden kurar,
önerilmez.
