# Phase 0 Closeout — kalan işlerin tek, sıralı listesi

**Yazılış:** 2026-07-07 (H9 Stage 5). **Amaç:** "Faz 0'ı bitirmek" için kalan
her işi TEK dokümanda, sahip + blokör + sıra ile tutmak. Şimdiye dek bu liste
6+ dokümana dağılmıştı (H9_KNOWN_ISSUES, H8_MASTER_PLAN_REVISION_PATCH,
ADR-009/013/014, HAFTA9_STAGE_2e, CHANGELOG). ADR-013'ün atıf yaptığı ama
hiç yazılmamış "Faz 0.5 roadmap" da budur. Her kalem kapandıkça burada
işaretlenir; yeni iş çıkarsa buraya eklenir.

**Durum özeti (H22 kova-A, 2026-07-20 — HEPSİ KODDAN ÖLÇÜLDÜ):** schema set
**v0.4.0** (ADR-015) · canonical **67,833 kayıt** (person 22,935 · place
19,929 · event 9,956 · work 9,404 · institution 5,423 · dynasty 186) ·
bunların **399'u yumuşak-silinmiş** (`provenance.deprecated=true`: place 241
[H22 #4 dublet birleştirme, 0a2a14c] + person 158 [27'si H22 #1 EI-1 hayaleti,
140366f; kalanı önceki haftaların emeklileri]) → **aktif 67,434** · suite
**160 passed, 2 skipped, 3 xfailed** (28,7 sn) · reverse-lookup index
`data/_index/lookup.sqlite`: entity_bracket 67,833 · label 211,800 ·
label_fts 211,800 · source_curie 75,161 · authority_xref 11,923.

Sayı düzeltmeleri (bu güncellemede ölçülüp doğrulandı):
- **Mağaza 57,177 → 67,833.** Eski özet H11 S11 tarihliydi ve H12-H21'i hiç
  görmemiş. Fark +10,656 = ağırlıklı olarak event (854 → 9,956; kitap-katmanı
  olayları H14-H16) + institution (3,942 → 5,423) + work (9,331 → 9,404).
  person/place/dynasty sayıları H11'den beri değişmedi (22,935 / 19,929 / 186)
  — H12+ işi ağırlıklı olarak *katman ve arayüz* üretti, yeni kişi/yer değil.
- **Phantom PID: 2,779 → 1,615.** Ayrıntı ve mutabakat §2'de.

**H12-H21'de ne oldu (özet; ayrıntı `docs/h12/`…`docs/h21/` journallerinde):**
H12 v1 React kabuğu v2 önyüzüne taşındı (b216fd1) · H13 OpenITI Kütüphanesi +
Çekirdek Külliyat parti-1, 10 kitap site içinde okunur (c49b415…810abb1) ·
H14-H16 jenerik kitap-katmanı boru hattı, iki parti okuma verisi, coğrafya
klasikleri (3be80df…bfcc377; mağaza 67,833'e burada çıktı) · H17-H21 beş
"dalga": bookkit çekirdeği + Yer Grafı onarımı (1a94260), kitap kabı üreticisi
+ arama 31,992 kayıt (a58ac46, e32ad8d), kişi köprüsü (aca5a5d), **Ulema
Havuzu canlı — 22,935 kişi** (3e66f67), durak modeli + EI-1 triyajı ve dalga
planı kapanışı (890ac60, cee94a0).

**Kalan işler** iki sınıf: (a) Ali-kapılı kararlar (İSAM izin yazısı — yalnız
yayın öncesi; hosting/DNS; tarihçi oturumları: dup-merge
[dia_travel_pending'deki Mekke×8 kanıt listesiyle], borderline-QID, review
kuyrukları), (b) yayın/akademik paket ve Faz 2 teknik kalemleri (ontoloji +
w3id kalıcı adresler + v1.0.0 + Zenodo DOI + veri indirme/API + data paper;
kişi-yer bağlama [dia_geo+alam_places], contemporaries, ei1 68 kenar,
muqaddasi_xref, salibiyyat boundaries/routes frontend, TR-ekzonim alias).

> **Arşiv — H11 S11 tarihli özet (2026-07-14; BAYAT, silinmedi).** Sayıları
> yukarıdaki ölçümle geçersizleşti; kayıt için aynen korunuyor:
>
> > schema set **v0.4.0** (ADR-015) · canonical **57,177 kayıt** (person
> > 22,935 · place 19,929 · work 9,331 · institution 3,942 · event 854 ·
> > dynasty 186) · suite **160 passed** · `full_reindex --dry-run`
> > 57,177/57,177 · **yerel Typesense CANLI** (docker, 57,177 upsert fail=0) ·
> > **web/ arayüz v0 ÇALIŞIYOR** (arama + facet + varlık sayfası + harita) ·
> > hoca-talebe ağı person kayıtlarında (7,965 kenar) · H9 kapanış maddeleri
> > ve H10-H11 aşamaları için `docs/h10/`+`docs/h11/` journalleri. Aşağıdaki
> > eski bölümlerin durumu: §0 KAPANDI (H9 close + merge + LaCie arşivlendi);
> > §1 AP → H11 S1'de A1+B3 augment-only icra edildi (30 locator; 1,489
> > kuyruk); event+institution aktivasyonu TAMAM (H11 S2/S5-S6); data.zip
> > bonus katmanları TAMAM (H11 S9-S11).

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

- [x] **el-alam onarımı (H10 S6; hedefli script, 21 mint — tam re-run provenance bozardı)** (`--id el-alam`): Track-A fix'i sonrası 20 kayıp
      Ziriklī kişisi Track B'den basılır (~15 dk; idempotency probe'u eskileri
      atlar). Öncesinde `--dry-run`la sayı teyidi. Sayı ayrıntısı (2026-07-09,
      koddan yeniden üretildi): Track-A disk-guard'ı 22 alam kaydını Track
      B'ye düşürüyor = 20 benzersiz dia_slug (`ibn-zekvan` ve `nesib` 2'şer
      kayıt); 22'nin 1'i (alam_id=4800, Âtike bint Abdülmuttalib — hd/md/c
      hepsi None) temporal-eligibility skip'ine düşer → 21 kayıt basılır.
      El_alam mint-erteleme fix'i (aşağıdaki madde) sayesinde 4800 artık
      phantom PID üretmez.
- [x] **Phantom PID denetimi (H10 S6: sidecar yazıldı; openiti sınıfı teşhisli; temizlik bilinçli YOK) — genel "indexte var, diskte yok" taraması:**
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
- [x] **Phantom sayı çelişkisi ÇÖZÜLDÜ + sınıflandırma yapıldı (H22, 2026-07-20;
      ölçüm, tahmin değil).** Yukarıdaki madde **2.779** diyor, sidecar
      `_meta.total` ise **1.615** ve `by_prefix`'te openiti sınıfı YOK. İkisi de
      kendi tarihinde doğruydu; mutabakat birebir kapanıyor:

      | | kayıt |
      |---|---:|
      | H10 S6 taraması (yalnız `person:*`) | 2.779 |
      | − openiti (H10 S9'da REPOINT edildi, `h10_001_openiti_index_repoint.py`) | −1.167 |
      | + `place:darp-islam:` (person-only tarama bunu görmüyordu) | +3 |
      | **bugünkü sidecar toplamı** | **1.615** |

      Bugünkü kırılım: el-alam 1.249 · dia 361 · darp-islam 3 · bosworth-nid 2.
      Yani "openiti sınıfının nedeni teşhis edilmedi" notu ARTIK GEÇERSİZ —
      H10 S9'da hem teşhis hem tamir edildi (ilk-geçiş mint'leri, aynı koşuda
      Tier-2'ye çözülüp diske hiç yazılmamış; girdiler resolution map'in gerçek
      pid'ine repoint edildi, silinmedi).

      **Sınıflandırma (1.615 phantom, 67.833 canonical dosyanın tamamı ve
      lookup.sqlite'ın beş tablosu tarandı):**
      - **(a) index artığı — 1.595.** Hiçbir canonical kaydın hiçbir alanında
        geçmiyor; hiçbir aktif kayıt işaret etmiyor.
      - **(b) canlı referans — 0.** Kırık bağ YOK. Yani bugün itibarıyla
        phantom'lar yayımlanan grafta hiçbir kopukluk üretmiyor.
      - **(c) belirsiz — 20.** Yalnız *bekleyen kuyruk* dosyalarında hedef
        olarak geçiyor: `el_alam_augment_pending.json` (20) ve
        `el_alam_yaqut_xref_pending.json` (8), kesişimle 20 ayrık pid. Kuyruklar
        eritilirse bu 20 hedef "dosya yok" diye sessizce düşer — H22 #3'te
        (6b6477d) 1.193 augment'i kaybettiren sessiz-düşme deseninin aynısı.
        Kuyruk eritilirken atlama-oranı kapısı bunları yakalar.

      Tam liste + yöntem + mutabakat tablosu makine-okunur olarak
      `data/_state/phantom_pids_classification.json`'da (salt sınıflandırma
      sidecar'ı; hiçbir şeyi silmez, `phantom_pids_audit.json`'a dokunmaz).

      **BULGU: `build_lookup.py` phantom'ların kaynağı DEĞİL.** Bu iş kaleminin
      varsayımı ("indekste referansı var → indeks üretiminden düşür") ölçümle
      ÇÜRÜDÜ: 1.615 phantom'ın **0'ı** `lookup.sqlite`'ta bulunuyor (label,
      label_fts, entity_bracket, source_curie, authority_xref — beşi de temiz;
      phantom kaynak anahtarları `source_curie.source_id`'de de yok). Sebep
      yapısal: `build_lookup.py` yalnız **diskte gördüğü** kayıtları yazar,
      dolayısıyla diskte olmayan bir pid'i hiçbir zaman yazamaz.
      Phantom'lar `data/_state/pid_index.json`'da, yani **mint defterinde**
      yaşıyor — `PidMinter.session()` istisna yolunda bile rezervasyonu kalıcı
      yazdığı için (H9 S3'te review'la kararlaştırılan davranış: kullanılmamış
      rezervasyon zararsız, ama serbest bırakılan ordinal BAŞKA bir varlığa
      verilirse atıf istikrarı kırılır). **Sonuç: pid_index.json'dan silme
      YAPILMADI ve yapılmamalı** — sidecar'ın kendi `policy` alanı da bunu
      söylüyor. Doğru tamir deseni silme değil **repoint**'tir (H10 S9
      precedent'i); ancak dia/el-alam sınıfında repoint edilecek hedef yok
      (varlık hiç yaratılmadı), o yüzden rezervasyon olarak kalıyorlar.
- [x] **AMA gerçek bir indeks artığı bulundu ve düzeltildi (H22, `build_lookup.py`).**
      Phantom avı sırasında ölçülen asıl kusur: `label` ve `label_fts` bare
      INSERT kullanıyordu (diğer dört tablo INSERT OR REPLACE), dolayısıyla
      `--rebuild`siz her koşu **her etiket satırının tam bir kopyasını daha**
      ekliyordu. Canlı indekste ölçüldü: 211.800 benzersiz (pid,lang,kind,text)
      demeti için **635.257 satır** — üç birikmiş geçiş, 423.457 saf mükerrer.
      (Bu oturum sırasında canlı sayının 423.457 → 635.257'ye çıktığı
      gözlendi: paralel bir koşu tam da bu hatayı işlerken yakalandı.)
      Zarar yalnız şişkinlik değil **isabet kaybı**: Tier-2 blocking
      `label_fts MATCH ... LIMIT BLOCK_LIMIT*4` ile aday topluyor, mükerrer
      satırlar limiti aynı pid'in kopyalarıyla doldurduğu için etkin aday
      çeşitliliği ~1/3'e düşüyordu. Düzeltmeler: (1) etiketler pid başına
      silinip yeniden yazılıyor (idempotent), (2) `label_fts` koşu sonunda
      `label`'dan tek seferde yeniden üretiliyor — per-pid FTS silme
      `pid UNINDEXED` yüzünden tam tarama demek ve koşuyu >10 dk'ya çıkarıyordu;
      toplu üretim aynı işi 9,4 sn'de yapıyor (8dk25sn → 9,4sn), üstelik iki
      tablonun sayıları bir daha ayrışamaz (canlıda label 3x iken FTS'te 6x ve
      9x çokluklar da vardı), (3) diskte karşılığı kalmayan pid'lerin satırları
      koşu sonunda budanıyor (stale-row GC — silinen/birleştirilen kayıt eskiden
      indekste sonsuza dek kalıyordu; H22 #1/#4'ün yumuşak-silmeleri için önemli).
      Doğrulama: temiz kurulum 211.800; üzerine sahte bayat satır enjekte edilip
      tekrar koşuldu → 2 bayat satır budandı, label yine 211.800 (idempotent);
      canlı indekste tekrar koşu 211.800 → 211.800, değişiklik yok. Suite 160.
- [x] **9,330 work provenance düzeltildi (H10 S12, h10_002; history'li).**
- [x] **Çapraz-kaynak person dedup taraması (H10 S6: script + koşu; adaylar person_dedup_candidates.json'da) (H10 Karar 3 bulgusu):** Tier-2
      kalibrasyonu, H4-H5 seed'lerinin (Tier-2'siz koşmuşlardı) store'da
      bıraktığı muhtemel dublörleri ifşa etti (örneklemde 21/250: aynı isim +
      ölüm ±5 + skor ≥0.95, ör. İbn Rüşd çifti). İş: person store'u kendi
      kendine karşı Tier-2'den geçir, ≥0.95 çiftleri review kuyruğuna çıkar
      (~1 saat makine + tarihçi onayı). Merge İNSAN kararıyla (ADR-008 Tier-3).

## 3. AN — Cat B fuzzy match (H10.5-H11; ~0.5 oturum kaldı) — sahip: Claude

4,784 slug'lık dia_chunks Cat B kümesi (kişi olmayan/fuzzy adaylar).
- [x] **Motor hazır (H10 Stage 1):** Tier-2 blocking+similarity gerçek
      implementasyon (ADR-008 §8.2); rapidfuzz requirements'ta; Tier-3 kuyruk
      fiilen akıyor; person auto-eşiği ground-truth'la 0.95'e kalibre
      (precision %99.2, 20 ms/resolve — `resolver_weights.yaml` +
      HAFTA10_STAGE_1_RESOLVER.md).
- [x] **AN TAMAM (H10 S5):** 2.261 match (provenance+locator bağlandı; AP'ye
      +2.261 slug→pid haritası) · 1.889 review kuyruğu · 634 triage (mint yok).

## 3.5. Kaynak dönüştürme — v2 içerik katmanları (H11+; kaynak başına ~0.5-1 oturum)

9 dönüştürülmemiş kaynağın 9-ajanlık profillemesi (2026-07-09; sayılar koddan):
~17K potansiyel yeni entity. Sıra, bağımlılığa göre:

| Kaynak | Hedef ns | Entity | Blokör |
|---|---|---:|---|
| ~~darp-islam~~ | place | **✅ H10 S2: 2.338 mint + 621 augment + 337 review** | — |
| ~~evliya-celebi~~ | place | **✅ H10 S7: 2.232 mint + 158 augment + 176 review** | 2.608 yapı institution-havuzunda; 10 sefer event-bekliyor |
| ~~ibn-battuta~~ | place | **✅ H10 S8: 128 mint + 124 augment + 41 review** | 7 sefer+rotalar event-bekliyor |
| ~~scholars~~ | person | **✅ H10 S3: 46 augment + 3 review** (49 isimli) | **252 yetim kart: v1 app db.json GEREK (Ali — kaynak temini)**; kenarlar Stage-3b |
| ~~ei1~~ | person(+augments) | **✅ H10 S4: +964 mint, 224 augment, 1.574 review** | tarihsiz 2.119 + sınıflar triage havuzunda |
| battles-events | **event** | ~100+200 kenar | ~~event ns aktivasyonu~~ **ÇÖZÜLDÜ: event ns aktif** (H11 S2; store'da 9.956 event — H14-H16 kitap-katmanı olaylarıyla) |
| konya-city-atlas | **institution**/place | ~1.384 | ~~institution şeması yok~~ **ÇÖZÜLDÜ: ADR-015 institution ns aktivasyonu** (H11 S5-S6; store'da 5.423 institution) |
| maqrizi-khitat | **institution**/place | 801 | aynı — blokör kalktı |
| major-cities | place augment | ~0 | şemaya sığmayan alanlar — düşük öncelik |

**Not (H22, ölçüm):** iki "Ali-kapılı" blokör de H11'de kalkmış ama bu tablo
güncellenmemişti. Kaynakların kendisi hâlâ dönüştürülmedi — blokör artık
karar değil, sıra.

## 3.6. Alatlı füzyonu (H25; backend YAPILDI, UI kalanı) — sahip: Claude

Alev Alatlı "Tarihe Yön Veren Metinler" 9-cilt atlası (~/Desktop/alev_alatlı/
corpus_json/) → `alatli` adapter. **Detay + UI reçetesi: `docs/h25/HANDOVER_UI.md`**
(+ `ALATLI_QID_AUDIT.md`, `ALATLI_TELIF_KAPISI.md`).

- [x] **Adapter + füzyon:** 234 kişi `source_layer=alatli` (53 mint + 181 augment);
      registry+projector prefix_map+facets kayıtlı; integrity 0/0, şema 17/17.
- [x] **98 tarih-teyitli QID** mevcut kişilere (display-gate ardında, reviewed:false).
- [x] **QID audit → 34 FP quarantine** (Q39619 Halife Ali 6 yanlış taşıyıcı→0, Q9458→0;
      store'un %33,7 FP'sine katkı; `qid_quarantine.json` 387→421). Δ≥100 kuralı;
      ad-eşleşmesi güvenilmez dersi. Kalan Δ<100 (Abdülhak Hâmid axis-karışması vb.)
      tarihçide.
- [x] **7 aşırı-mint dedup** (ad-sırası farkı; provenance.deprecated + QID mevcut
      kişiye taşındı). build_view_data deprecated'ı zaten filtreliyor → otomatik düşer.
- [ ] **UI tazeleme (paralel H27 oturumu):** `make view-data` + `make upsert-live` —
      dedup/quarantine SONRASI şart; Kaynak facet doğrula.
- [ ] **Telif kapısı (yayın; §4 ile):** `source_layer=alatli` kamu CC-BY-SA dump'tan
      ÇIKAR (İSAM deseni; olgular yayınlanabilir, seçim izne-bağlı, düzyazı store'da yok).
- [ ] **FIRSAT — Track-3 senkronik timeline view** (Bize/Batıya yan yana zaman ekseni;
      Batı kanonu `_alatli_western_held.json` yan-tabloda). Ref: standalone atlas
      `timeline_standalone.html`. Opsiyonel; UI oturumunun alanı.

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
- [x] **Canlı Typesense yolu — KOD TAMAM (H10 S10):** emit + upsert +
      Makefile + sözleşme testleri; ilk canlı koşu HOSTING KARARINA bağlı
      (env-kilitli; 15-dk reçete Stage-10 journal'ında). İqlim facet'i
      kapalı (backfill ayrı kalem).
      **Güncelleme (H22):** frontend araması H18 S4'te 16.006 → **31.992**
      kayda çıktı (e32ad8d) ve gündelik kullanım bunun üzerinden gidiyor;
      **hosting/DNS kararı H21 sonunda hâlâ AÇIK** (`docs/h21/HAFTA21_DALGA4.md`
      son bölüm) — yani bu kalem kapanmadı, sadece beklerken yerel yol
      olgunlaştı.
- [x] **QID audit YAPILDI (H10 S11) — sonuç: gevşetme YOK, tam tersi.**
      TAM evren (3.073): %33.7 MISMATCH (dynasty %96; Safevîler→Spartacus
      League sınıfı kanıtlar). Display-gate KALICI. → YENİ kalem:
- [ ] **QID temizlik oturumu (Ali+Claude):** kademeli kural (aşikâr-çöp
      purge: sim<60+sinyalsiz; sınır-vakalar review'a); qid_audit_report.json
      kanıt listesi hazır. Temizlik olmadan QID yayını YOK.
- [ ] **check_all davranışı:** bayraksız çağrının store'a yazması (resolve)
      footgun — `--resolve` opt-in'e çevirme kararı (runbook'larla birlikte).
- [ ] **Zenodo dump + DOI** (CHANGELOG 1.0.0 tanımı): ADR-014 belge referansı
      olmadan YAYIN YOK.

## 4.5. H22 kova-A — kuyruk eritme (DEVAM EDİYOR) — sahip: Claude, karar: Ali

Ayrıntı ve karar defteri: [`docs/h22/KUYRUK_ERITME.md`](h22/KUYRUK_ERITME.md).

- [x] 27 EI-1 hayalet kaydı **yumuşak-silindi** (140366f) — PID korunur.
- [x] **KARAR H22-1:** kapsam yüzdesi vs crosswalk ayrımı (8ad0e43) — H20'de
      "Ali'ye" bırakılan kalem kanıtla kapandı; yüzde şişirilmedi.
- [x] xref kopukluğunun kök sebebi: **yarış koşulu** (6b6477d) — 1.193 augment
      geri kazanıldı; alam kapsamı %81,63 → %90,19; kişi köprüsü 67 → 1.260.
- [x] 241 birebir yer dubleti birleştirildi (0a2a14c) — yumuşak-silme.
- [x] Kuyruk hijyeni: inceleme yükü 5.561 → 3.865 (c37cf29) — hiçbir eşleşme
      kabul/ret edilmedi, hiçbir satır silinmedi.
- [x] Phantom PID sınıflandırması + `build_lookup.py` idempotency/GC onarımı
      (§2'deki iki yeni madde).
- [ ] Kalan inceleme yükü **3.865 satır** — tarihçi oturumu (Ali).

## 5. Sürekli disiplin

Her stage = 1 commit + journal + karar-logu girdisi. `make test` haftalık
kapı (CI aynısını koşar); `make test-fast` iç döngü. Şema seti donuk
(ADR-013); canonical'a sadece adapter'lar yazar; borderline → insan.
