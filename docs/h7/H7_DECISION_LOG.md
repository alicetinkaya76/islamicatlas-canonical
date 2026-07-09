# H7 Karar Günlüğü (Decision Log)

> H6'nın handoff DECISION_LOG.md formatında. H7 oturumunda yapılan
> önemli yargıların kayıt altına alınması.

---

## Karar 1 — Path C (hybrid), 4-6 saat budget

**Bağlam**: H7 oturumu açıldığında 3 yol vardı: Path A (Stream 2 bulk
mint, volume-first), Path B (QID quality audit + cleanup, quality-first),
Path C (hibrit, küçük QID temizlik + sınırlı Stream 2). Saat budget'ı
açık değildi; "sen seç" tarzı karar verildi.

**Karar**: Path C, 4-6 saat budget. Stage 1 (QID temizlik), Stage 2
(frontend gate), Stage 3 (sınırlı Stream 2), Stage 4 (test), Stage 5
(close).

**Gerekçe**: Path A "Stream 2 mint'leri yanlış author'lara bağlanır"
diye uyarılmıştı, ama empirik gözlem: dia_slug→PID mapping
`dia_slug_to_pid.json`'dan geliyor, QID seed'den değil — yani saf Path
A'nın author resolution riski sanıldığı kadar yüksek değil. Saf Path
B 4-6 saatte 607 QID'i tam audit edemez (Wikidata API rate limits +
manuel review yükü); Path C QID temizliğinin **görünür kısmını**
(4 confirmed-wrong) açar, frontend'i bu farkındalıkla kapatır
(Bölüm 2.4 gate), Stream 2'nin sınırlı versiyonunu yapar.

**Sonuç**: Path C uygulandı; Stage 3 ADR-009 ile kapsam değiştirdi
ama Path C'nin omurgası (QID temizlik + frontend gate + close)
korundu.

---

## Karar 2 — 4 confirmed-wrong QID için "flag, sil değil" semantiği

**Bağlam**: Stage 1'de Khwarizmi/Q9438, al-Qāsim/Q9458, Badr/Q36533610,
'Alī II/Q719449 person record'larında confirmed-wrong wikidata xref'i
nasıl ele alınmalı? İki seçenek:
1. **Sil**: `authority_xref` listesinden tamamen çıkar.
2. **Flag**: `confidence: 0.0`, `reviewed: false`, `note: "h7_audit_..."`
   ile kaydı koru ama disable et.

**Karar**: Flag (Seçenek 2).

**Gerekçe**: (a) Git history'sinde tarih var ama runtime data'da flag
daha denetlenebilir; (b) Gelecek `verify_seed_qids.py --person-mode
--batch` audit pipeline'ı `confidence == 0.0 AND note startswith
"h7_audit_"` ile "biliyoruz, atlama" cache'i olarak kullanabilir, aynı
API çağrısını tekrarlamaz; (c) Frontend zaten gate filter'ı uygulayacak
(Bölüm 2.4), display sızıntısı engellenir.

**Sonuç**: 4 record flagged, 0 silindi. Yeni konvansiyon: pre-H7
canonical/person store'unda 0 record `confidence == 0.0` taşıyordu;
H7 sonrası 4 record. Konvansiyon ileri audit pipeline'larının cache
key'i olarak kullanılır.

---

## Karar 3 — `change_type: "update"` (mevcut konvansiyon)

**Bağlam**: H7 patch'inde person record'un `provenance.record_history`
array'ine yeni entry eklerken hangi `change_type` değeri kullanılmalı?
İlk denemede `"modify"` yazıldı, schema reddetti.

**Karar**: `"update"`.

**Gerekçe**: Schema enum: `["create", "update", "merge", "split",
"deprecate", "revive"]`. `"modify"` yok. Mevcut store'da: 21,946
`"create"` + 6,873 `"update"` + 0 başka değer. Konvansiyon zaten
kurulmuş, yeni varyant tanıtılmıyor.

**Sonuç**: Schema validate green, idempotent re-run'da konsistens
korunmuştur.

---

## Karar 4 — Frontend Wikidata gate KURALI (öneri değil, zorunluluk)

**Bağlam**: Stage 2 frontend spec patch'inde Wikidata QID display
politikası nasıl çerçevelenmeli? "Tavsiye" mi (Fatıma kendi karar verir)
yoksa "kural" mı (zorunlu, kickoff'ta predicate detayları konuşulur)?

**Karar**: "Phase 0b kuralı (zorunlu)" tonu. Predicate kod blok'u
verildi (`isWikidataXrefDisplayable`), gate'in nedenleri ve sonuçları
açık yazıldı.

**Gerekçe**: "Khwarizmi → Aquinas Wikipedia link" tarzı sızıntı academic
credibility'yi doğrudan vurur; öneri tonu Fatıma'ya "gate'siz alternatifi
düşün" alanı bırakır, oysa o alan zaten kapalı olmalı. Kickoff toplantısında
predicate refinement (badge styling, fallback endpoint) tartışılır, ama
"gate yapsam mı yapmasam mı" sorusu tartışılmaz.

**Sonuç**: Spec'te bölüm 2.4 mandatory rule olarak kayıt; F2 PersonCard
deliverable'ında gate enforcement done-when criterion'u; bölüm 6 açık
konular listesinde sadece H8 gate-relaxation soru'su (gate'in *kendisi*
değil).

---

## Karar 5 — Stage 3 scope: rich-mint-only, ADR-009

**Bağlam**: Stage 3'te dia_works adapter scope'u tartışıldı. Üç opsiyon:
- X: Hiç yeni record yapma, doğrudan Stage 4/5'e geç.
- Y: Sığ-ama-dürüst mint, ~10-25 record (kalın filtre).
- Z: Sadece SAME-AS cluster (yapısal olarak tutarsız, eliyor).

İlk önerim Y idi. Empirik keşif sonrasında (audit/dia_works.json sığlığı,
Hassâf'ın elle yazılma gerçeği), karar X'e döndü.

**Karar**: X (yeni record yok). Bu hafta-içi seçim, **kalıcı mimari
karar olarak ADR-009'a yükseltildi** (rich-mint-only doctrine).

**Gerekçe**: (a) ADR-007 rich-page-contract ile sığ-mint çelişir; (b)
H5 Decision 1 zaten "dia_works dropped, ham re-extraction gerek" demiş
ama H6'da bu unutulmuş — H7'de bu karar ADR olarak kalıcılaştırılarak
unutmaya kapatılır; (c) Marjinal kazanç (cluster +25) kalıcı borç
yaratıyordu; (d) H8'de ham veri pipeline'ı zaten gerek — sığ mint
o pipeline'da idempotent enrichment update'i demek, mint pass'i iki
misli, hata yüzeyi iki misli.

**Sonuç**: ADR-009 yazıldı (Accepted). H6 master plan AA/AB/AG
kriterleri formal olarak H8'e ertelendi (`H7_MASTER_PLAN_REVISION.md`).
Stage 3'ün enerjisi dökümantasyona yönlendirildi.

---

## Karar 6 — H6 handoff dosyalarını geriye dönük commit etme

**Bağlam**: H6'nın CLOSE_STATE, KNOWN_ISSUES, SESSION_PLAN, DECISION_LOG
dosyaları sadece kişisel zip'te (handoff_package), repo'da yok. H5
pattern'i (docs/h5/) bunu yapardı. H6 boşluğu, "neden Stream 2 ertelendi"
sorusunun cevabı sadece git commit message'larında ve kafamızda
tutulmasına yol açıyordu.

**Karar**: H6 handoff dosyalarını H7 close commit'iyle birlikte
`docs/h6_phase_0b/handoff/`'a geriye dönük commit et. Aynı zamanda H7
dökümantasyonunu `docs/h7/` altında **commit anında** yaz, H6 hatasını
tekrarlama.

**Gerekçe**: Repo özbakımı. Tarihi düzelt; aynı pattern'i H7'de kur;
H8 zaman geldiğinde "neden Stream 2 hâlâ kapalı?" sorusunun cevabı
ADR-009 + H7_CLOSE_STATE'te bulunur, bir başka zip'te değil.

**Sonuç**: 4 H6 dosyası `docs/h6_phase_0b/handoff/`'a kopyalandı; H7'nin
4 dosyası `docs/h7/`'ye yazıldı; ADR-009 `docs/decisions/`'a yazıldı.
Repo standalone okunabilir.
