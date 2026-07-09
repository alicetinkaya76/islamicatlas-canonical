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

<!-- Sonraki H10 kararları burada eklenecek -->
