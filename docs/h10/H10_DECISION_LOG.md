# Hafta 10 — Karar Logu

Yapı H8/H9 karar loglarıyla aynıdır: Bağlam / Karar / Gerekçe / Sonuç.

---

## Karar 1 — H10 sıralaması: Tier-2 resolver öne alındı (kullanıcı direktifi); AP, Ali'nin kararlarını bekliyor

**Tarih:** 2026-07-09
**Stage:** 1
**İlgili:** ADR-008, docs/h10/HAFTA10_AP_KICKOFF.md, PHASE0_CLOSEOUT §1/§3

### Bağlam

H9 close AP'yi (dia_works) H10'un ana gövdesi olarak bırakmıştı; ama AP
Ali'nin iki kararına (ADR-009 (a) eşiği + katkıcı namespace) bloklu. Kullanıcı
hedefi netleştirdi: islamicatlas.org **v2 canlı ürün** — ve dönüştürülmemiş
9 kaynağın profillemesi (9-ajanlık fan-out), 5 kaynağın (ei1 ~5.600, evliya
5.444, darp-islam ~3.381, ibn-battuta 317+7, scholars ~285) ortak blokörünün
**fuzzy entity-resolution** olduğunu gösterdi: mevcut 37K person+place'e
dublör üretmeden eklenemiyorlar.

### Karar

H10 Stage 1 = ADR-008 §8.2 Tier-2'nin gerçek implementasyonu (karar
gerektirmeyen, mint'siz, saf altyapı). AP kickoff dokümanı hazır bekliyor;
Ali'nin kararları gelince AP araya girebilir.

### Sonuç

Tier-2 canlı ve kalibre (Karar 2); AN'in motoru ve 5 kaynağın blokörü açıldı.

## Karar 2 — person auto-accept eşiği 0.90 → 0.95 (veri-kalibreli); isim-tek-başına asla auto-match

**Tarih:** 2026-07-09
**Stage:** 1
**İlgili ADR:** ADR-008 (eşik semantiği), CLAUDE.md North Star (borderline → insan)

### Bağlam

250 alam↔dia ground-truth çifti (Track A xref'leri = bilinen-doğru eşleşme)
canlı 46.702-kayıtlık indekse karşı koşuldu; eşik taraması yapıldı
(tablo journal'da). 0.90'da auto bandı 9 gerçek yanlış taşıyor (yakın-tarihli
adaşlar: İbn el-Alkami 0.902, Muʿizz ed-Devle 0.942...); 0.95'te 1
(precision %99.2). Düşen vakalar kaybolmuyor — review kuyruğuna iniyor.

### Karar

(1) `resolver_weights.yaml` yazıldı: person auto=0.95 (kalibreli), diğerleri
ADR-008 varsayılanı (kalibrasyonları kendi ilk tüketicileriyle yapılacak).
(2) Koda North-Star guard'ı: skoru ne olursa olsun **tek-özellikli** (yalnız
isim) aday auto-match olamaz — review'a düşer. (3) Sert yıl-bloku: iki taraf
tarihli ve fark >150 yıl → aday elenir (adaş bastırma).

### Gerekçe

Bu korpusta adaş normdur; "isim + tarih" çift-sinyal şartı ve 0.95 eşiği,
otomatik banda yalnız savunulabilir eşleşmeleri bırakır. Tarihçi onayı
gereken sınır vakalar tam da tasarlandığı yere (Tier-3 kuyruk) akar.

### Sonuç

precision(auto) %99.2 · recall(auto+review-adayda) %84.4 · 20 ms/resolve.
Yan bulgu: Karar 3.

## Karar 3 — Yan bulgu: store-içi çapraz-kaynak person dublör adayları → closeout kalemi

**Tarih:** 2026-07-09
**Stage:** 1

### Bağlam

Kalibrasyonda "yanlış" görünen auto-match'lerin 21/30'u aynı isim + ölüm yılı
±5 + skor ≥0.95 ile BAŞKA bir kayda gitti (ör. İbn Rüşd: dia kaydı beklenirken
conf 1.0 ile başka PID) — bunlar büyük olasılıkla resolver hatası değil,
store'da hâlihazırda yaşayan dia↔science-layer/el-alam **çapraz-kaynak
dublörleri** (H4-H5 seed'leri Tier-2'siz koşmuştu).

### Karar

Bu iterasyonda store'a dokunulmaz (North Star: merge insan onayıyla).
PHASE0_CLOSEOUT §2'ye yeni kalem: "çapraz-kaynak person dedup taraması" —
Tier-2 artık var; tüm person store'u kendi kendine karşı koşturup ≥0.95
çiftleri review kuyruğuna çıkarmak ~1 saatlik makine işi + tarihçi onayı.

### Sonuç

Örneklemdeki oran (21/250 ≈ %8'i alam-xref'li kesitin) evrene doğrusal
genellenemez; gerçek sayı taramada koddan sayılacak.

## Karar 4 — darp-islam: iki-track mint + küratör-sinyalli demotion; place 15.239→17.577

**Tarih:** 2026-07-10
**Stage:** 2
**İlgili:** ADR-006 v1.1 (resolve aşaması), ADR-008, ADR-010 (digital_corpus)

### Bağlam

v2'nin harita katmanı için ilk kaynak dönüşümü: DarpIslam 3.381 geokodlu
darphane. İlk kez bir adapter Tier-2 resolver'a bağlanıyor; darphane
şehirlerinin çoğu Yâqūt'ta zaten var → dublör riski asıl tasarım problemi.

### Karar

(1) İki-track: match → augment-sidecar (le-strange deseni; apply_darp_augments
uygular), new → mint, review → kuyruk + MINT YOK. (2) Pilot bulgusu üzerine
**hinted-new demotion**: küratör yakut-ipucu taşıyan ama resolver'ın
bulamadığı 119 mint review'a (mint edilseydi dublör olurdu). (3) İndeks yoksa
adapter reddeder. (4) 3 pilot-kalıntısı "rezerve PID" bilinçli tutuldu
(onay gelirse aynı PID); test_i bu kategoriyi belgeli-şartla tanır.

### Sonuç

3.381 = 706 augment-olayı (621 yer) + 2.338 yeni + 337 review; 0 validasyon
hatası; full_reindex 49.040/49.040; make test 156 passed. Sağlama örnekleminde
tüm auto-match'ler 0-3 km / conf ≥0.97. Kuyruktaki 337 vaka tarihçiye.

## Karar 5 — scholars: 49 çekirdek âlim augment-ağırlıklı dönüştü; 252 yetim kart kaynak-temini kalemi

**Tarih:** 2026-07-10
**Stage:** 3

### Bağlam / Karar / Sonuç

v1 uygulamasının scholars katmanı (JS-literal) node-eval'li determinist
türevle JSON'a çevrildi (commit'li). 49 isimli âlim Tier-2'den geçti:
**46 augment** (EN açıklama + kunya/nisba/laqab gap-fill; applier idempotent)
+ 0 mint + 3 review. identity'nin 252 kartı isim-otoritesiz (kayıp db.json)
→ İŞLENMEDİ; PHASE0_CLOSEOUT'a kaynak-temini kalemi (Ali). Hoca-talebe
kenarları (163+10 isnad) Stage-3b'ye — `_id_to_pid` haritası sidecar'da
hazır. Bekçi facet-testi yeni prefix'i yakaladı → `scholars` facet değeri
ilan edildi. `make test` 156 passed.

## Karar 6 — EI1: tek-namespace mint + çok-namespace augment; OCR recall'ı kuyruğa

**Tarih:** 2026-07-10 · **Stage:** 4

person 21.946→22.910 (+964 tarihli yeni); 242 eşleşme-olayı → 224 kayıtta
EN/TR/AR özet gap-fill; 1.574 review (OCR-translit recall'ı insan şeridinde);
tarihsiz-yeni (2.119), yer/hanedan-yeni (729), concept/unknown/xref (1.940)
MINT EDİLMEDİ — tümü sidecar'da sayılı. Work başlıkları ADR-009 gereği
mint dışı. Store 50.004; make test 156.

## Karar 7 — AN: 2.261 Cat-B eşleşmesi bağlandı; 1.889 kuyruk; 634 triage — mint sıfır

**Tarih:** 2026-07-10 · **Stage:** 5

Cat B/C (4.784) Tier-2'den geçirildi: eşleşenler DiA provenance+locator aldı
(zenginleştirme el-alam'ca doyurulmuştu — dürüst sayım: +22 ar, +1 desc);
kuyruk/triage havuzları sayılı. Kişi/yer/kavram ayrımı OTOMATİKLEŞTİRİLMEDİ.
AP'ye yan ürün: +2.261 slug→pid haritası (an_cat_b_resolution.json).

## Karar 8 — Onarımlar: hedefli mint (tam re-run reddi), phantom politikası, dedup taraması

**Tarih:** 2026-07-10 · **Stage:** 6

(1) el-alam kayıp-21 HEDEFLİ script'le mint'lendi — tam re-run 12.5K kaydın
provenance.created'ını bozacağı için reddedildi. (2) Phantom denetimi sidecar'a
(2.782; openiti sınıfı teşhis edildi: H5 placeholder kısmî yazımı); index
temizliği bilinçli YOK — tüketiciler disk-doğrulamalı. (3) Person dedup
taraması başlatıldı; adaylar dosyaya, merge insan kararına.

## Karar 9 — Evliyâ: yerleşim alt kümesi dönüştü (2.232 mint); yapılar institution-havuzuna

**Tarih:** 2026-07-10 · **Stage:** 7

5.444 konumun kategori yönlendirmesi: 2.568 yerleşim iki-track'ten (160
augment / 2.232 mint / 176 review); 2.608 YAPI (cami/türbe/hamam...) MINT
EDİLMEDİ — konya/maqrizi ile birlikte tek institution-karar havuzunda
(ADR-006 §6.4, Ali); 268 doğal/bilinmeyen triage; 10 sefer event-bekleyen.
place 19.809; store 52.257; test bandı belgeli genişledi.

<!-- Sonraki H10 kararları burada eklenecek -->
