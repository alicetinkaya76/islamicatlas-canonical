# Phase 0 Closeout — kalan işlerin tek, sıralı listesi

**Yazılış:** 2026-07-07 (H9 Stage 5). **Amaç:** "Faz 0'ı bitirmek" için kalan
her işi TEK dokümanda, sahip + blokör + sıra ile tutmak. Şimdiye dek bu liste
6+ dokümana dağılmıştı (H9_KNOWN_ISSUES, H8_MASTER_PLAN_REVISION_PATCH,
ADR-009/013/014, HAFTA9_STAGE_2e, CHANGELOG). ADR-013'ün atıf yaptığı ama
hiç yazılmamış "Faz 0.5 roadmap" da budur. Her kalem kapandıkça burada
işaretlenir; yeni iş çıkarsa buraya eklenir.

**Durum özeti (H9 Stage 5 sonu):** schema set v0.3.0 · canonical 46,702 kayıt
· suite 147 passed (`make test`) / iç döngü ~9 sn (`make test-fast`) ·
`full_reindex --dry-run` 46,702/46,702 · AO tamam, `dia_chunks_rich.json`
hazır · CI gerçek suite'i koşuyor.

---

## 0. H9 kapanışı (sıradaki oturum; ~0.5 oturum) — sahip: Claude+Ali

- [ ] H9 close-state dokümanı (H8 kalıbında) + `hafta9-close` tag'i.
- [ ] `hafta5-work-namespace` → `main` merge (CONTRIBUTING notu gereği;
      24+ commit'lik fark — fast-forward değil, merge commit önerilir).
- [ ] LaCie klonu kararı: sil ya da salt-okunur arşiv etiketle (iki sapmış
      kopya riski — H9 Stage 3'te bayat `__pycache__` bundan çıktı).

## 1. AP — dia_works rich-mint (H10; 1-1.5 oturum) — sahip: Claude, karar: Ali

**Girdi hazır:** `dia_chunks_rich.json` + `adr009_rich_gate()` (testli) +
PidMinter `session()` + work-PID state onarımı (h9_001). **Tam kickoff dokümanı
+ karar çerçevesi: [`docs/h10/HAFTA10_AP_KICKOFF.md`](h10/HAFTA10_AP_KICKOFF.md).**

**Kapsam düzeltmesi (H9 close bulgusu):** AP **toplu-mint DEĞİL, sınırlı-mint.**
AO (c) cilt+sayfa locator'ını her âlim için verdi; ama per-work (a) çok-dilli
başlık + (b) açıklama 42.449 DiA-only başlık için YOK (audit bantları:
42.449 `dia_only`, 37 `moderate_validated`). Zengin-mint edilebilir küme =
dış-eşleşmeli alt küme (~1.519); 42K DiA-only başlık ADR-009 gereği mint
edilmez (doğrulanmamış atıf yok garantisi). Detay kickoff'ta.

Kickoff'ta KARAR gereken maddeler (Ali):
- [ ] **ADR-009 v1.1 revizyonu:** (a) eşiği — title_ar'sız ~%33 madde için
      "ar yoksa tr+en (DiA başlığı + transliterasyon) yeterli mi, yoksa
      mint-dışı mı?" K-hedefi bu karara göre koddan sayılır (~5.4K vs ~8K).
      ADR-009'un kendi revisit-tetiği zaten doldu.
- [ ] **Yazar modellemesi (proposal Q3/Q4):** 1,423 TDV katkıcısı person
      namespace'e mi, ayrı `iac:contributor-*` namespace'e mi? (Rich dosyada
      ham `author_raw`+`section_slug` hazır; çok-bölümlü maddelerde bölüm-başı
      yazar korunmuş.)
- [ ] **5 online-only madde** (`muneccimbasi`, `rasathane`,
      `tamani-huseyin-rifki`, `yahya-b-ebu-kesir`, `yahya-yi-sirvani`):
      print locator yok → tarihli web-locator formatı onayı
      (`adr009_rich_gate` ikisini de kabul edecek şekilde yazıldı).
- [ ] **10 review-flagged kayıt** insan incelemesi (3 low-coverage, 3
      title-varyant, 5 online-only) — journal'a kayıt.

Uygulama (Claude): `pipelines/adapters/dia_works/` (ADR-006 dört-dosya, bu
kez gerçek canonical-mint adapter'ı); gate'i geçemeyenler review sidecar'ına;
Hassâf `iac:work-00009331`'e idempotent `dia-rich:hassaf` augment; Phase-5
cross-validation testleri (dia-chunks ↔ dia-rich slug tutarlılığı);
`attributed_to` doldurma H8'in bıraktığı boşluğu kapatır. Şema değişikliği
beklenmez (work.schema'da `dia_slug` alanı mevcut); zorunlu olursa ADR-013
prosedürüyle v0.4.0 set bump.

## 2. Kısa onarım koşuları (AP ile aynı hafta; ~0.5 oturum) — sahip: Claude

Stage 3'ün kod düzeltmeleri davranışı ileriye dönük düzeltti; mevcut
kayıtlara yansıtmak için birer idempotent koşu gerekir (hepsi journal'lı):

- [ ] **el-alam re-run** (`--id el-alam`): Track-A fix'i sonrası 20 kayıp
      Ziriklī kişisi Track B'den basılır (~15 dk; idempotency probe'u eskileri
      atlar). Öncesinde `--dry-run`la sayı teyidi. Sayı ayrıntısı (2026-07-09,
      koddan yeniden üretildi): Track-A disk-guard'ı 22 alam kaydını Track
      B'ye düşürüyor = 20 benzersiz dia_slug (`ibn-zekvan` ve `nesib` 2'şer
      kayıt); 22'nin 1'i (alam_id=4800, Âtike bint Abdülmuttalib — hd/md/c
      hepsi None) temporal-eligibility skip'ine düşer → 21 kayıt basılır.
      El_alam mint-erteleme fix'i (aşağıdaki madde) sayesinde 4800 artık
      phantom PID üretmez.
- [ ] **Phantom PID denetimi — genel "indexte var, diskte yok" taraması:**
      kapsam yalnız 361 `person:dia:*` DEĞİL. Aynı mint-before-skip deseni
      el_alam Track B'de de vardı (2026-07-09'da dia'daki fixin aynısıyla
      düzeltildi: mint, temporal-eligibility skip'inin arkasına taşındı) ve
      **1.249 phantom `person:el-alam:*`** girdisi bırakmış durumda. Genel
      `person:*` taraması (2026-07-09, koddan yeniden üretildi): toplam
      **2.779 phantom** = 361 dia + 1.249 el-alam + 1.167 openiti + 2
      bosworth-nid (openiti/bosworth sınıflarının nedeni henüz teşhis
      edilmedi — ayrıca incelenecek). Tam liste
      `data/_state/phantom_pids_audit.json`'a; AP author linkage'ı yalnız
      disk-doğrulamalı PID kullanır (el_alam guard'ı örnek). Index temizliği
      journal'lı ayrı koşudur; canonical kayıtlara dokunulmaz.
- [ ] **9,330 work kaydının jenerik provenance'ı** (`canonicalize_work`):
      registry id düzeltmesi ileriye dönük çözüldü; mevcutlar için mini
      migration (source_id önekinden gerçek pipeline_name) — düşük öncelik,
      Faz 0.5'e kayabilir.

## 3. AN — Cat B fuzzy match (H10.5-H11; 1 oturum) — sahip: Claude

4,784 slug'lık dia_chunks Cat B kümesi (kişi olmayan/fuzzy adaylar).
Altyapı notu (Stage 3 incelemesinden): `entity_resolver.py` Tier-2 stub
(`kind='new'` sabit) → gerçek blocking+similarity yazılacak (fingerprint +
death-bucket blocklama; rapidfuzz eklenirse requirements'a girer); Tier-3
review kuyruğu (`_review_enqueue`) hazır ama bugün erişilemez durumda.
Borderline eşleşmeler `needs_human_review` — asla otomatik merge.

## 4. Faz 0.5 — yayın hazırlığı (H11+; 2-3 oturum) — sahip: Ali+Claude

- [ ] **İSAM izin belge referansı** → ADR-014 §Koşul (SAHİP: ALİ — tek sert
      dış blokör; merci+tarih+kapsam+belge kimliği. Kapsam "yeniden dağıtım
      hakkı"nı içermiyorsa AP çıktısının yayın stratejisi yeniden kurgulanır).
- [ ] **Ontoloji/context bakımı** (w3id blokörü): `iac:Place` tanımsız;
      context'te person/work terimleri yok; `iac:Tabaqa` ikili tanım (E78 vs
      Work altsınıfı — work.schema enum'uyla çakışıyor; çözüm muhtemelen
      genre sınıfını yeniden adlandırıp v0.4.0 set bump'ına bağlamak).
- [ ] **w3id.org PR** (ADR-001): v0.3.0 (ya da o günkü etiket) yolları.
- [ ] **Schema set v1.0.0** atomik bump (ADR-013 R2-R4; AP'nin şemaya
      dokunup dokunmadığına göre v0.3.0/v0.4.x'ten).
- [ ] **Canlı Typesense yolu:** `typesense_schema_emit` + `full_reindex
      --live` + upsert (bugün tümü yok; NDJSON hazır). İqlim facet'i ya
      backfill'le doldurulur ya kapsamdan çıkarılır (şimdilik kapalı).
- [ ] **QID audit + display-gate gevşetme** (H7'nin H8'e vaadi, hiç
      yapılmadı): H4 recon 517 + yaqut auto-accept 1,001 QID örneklem
      denetimi (ADR-002 ≤%5 yanlış-pozitif hedefi); OpenITI seed'in
      doğrulanmış-yanlış QID'leri temizliği.
- [ ] **check_all davranışı:** bayraksız çağrının store'a yazması (resolve)
      footgun — `--resolve` opt-in'e çevirme kararı (runbook'larla birlikte).
- [ ] **Zenodo dump + DOI** (CHANGELOG 1.0.0 tanımı): ADR-014 belge referansı
      olmadan YAYIN YOK.

## 5. Sürekli disiplin

Her stage = 1 commit + journal + karar-logu girdisi. `make test` haftalık
kapı (CI aynısını koşar); `make test-fast` iç döngü. Şema seti donuk
(ADR-013); canonical'a sadece adapter'lar yazar; borderline → insan.
