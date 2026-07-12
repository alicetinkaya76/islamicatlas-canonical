# Hafta 11 — Karar Logu

## Karar 1 — AP kararları KULLANICI DEVRİYLE alındı: A1+B3, augment-only

**Tarih:** 2026-07-12 · **Stage:** 1
**Devir:** Kullanıcı "sen karar ver devam et" dedi (2026-07-12); kickoff'taki
A/B seçenekleri açık sayılarla sunulmuştu.

### Karar

**A1:** ADR-009 DEĞİŞMEZ — katı kalır; 42.449 DiA-only başlık mint edilmez.
**B3:** katkıcı-namespace ERTELENİR (şema v0.3.0 donuk kalır; 1.423 müellif
ham halde rich dosyada). **AP = augment-only:** H5 audit'inin başlık
eşleşmeleri BUGÜNKÜ yazar haritasıyla (Cat-A + AN) yeniden doğrulanır;
tek-aday + yazar-doğrulamalı eşleşmeler work'e dia_slug + AO cilt/sayfa
locator'ı olarak işlenir; gerisi kuyruğa.

### Gerekçe

A1 en savunulabilir (doğrulanmamış atıf sıfır); B3 tek şema-değişikliksiz
seçenek; augment-only, ADR-009'un yasakladığı sig-mint'e hiç yaklaşmaz.
Bu üçlü, "kendi başıma karar verebilir" sınırının içindeki tek kombinasyon —
diğerleri şema/namespace işi (Ali/v0.4.0).

### Sonuç

30 work DiA-yüzü kazandı (dia_slug + "TDV DİA cilt N, s. M" locator +
altLabel.tr). Kuyruk: 1.457 yazar-uyuşmazlığı (audit'in misattribution
sınıfı — DOĞRU dışarıda) + 23 scholar-çözümsüz + 9 slug-çakışması.
**Keşif:** hassaf:title_2 çakışması el-mint 9331 ↔ openiti-Hiyal 3591'in
AYNI ESER olduğunu ifşa etti → work-dublör adayı kuyruğa (merge insan
kararı); guard eklendi (key-sahipliyse augment yok). make test 158.

## Karar 2 — EVENT NAMESPACE AKTİVASYONU (kullanıcı devriyle): battles+events ilk 100 olay

**Tarih:** 2026-07-12 · **Stage:** 2

### Karar + Gerekçe

event.schema v0.3.0 setinde ZATEN tanımlı (iac:Battle/Founding/Disaster...
enum'u, projeksiyon kuralı ve UI-tarifi dahil) — aktivasyon şema değişikliği
gerektirmiyor, geri alınabilir (kayıtlar silinebilir), ADR-005 faz sırasının
(P0.3) veri-hazır öne alınışı. "Sen karar ver" devri kapsamında en düşük
riskli aktivasyon buydu; institution AKTİVE EDİLMEDİ (yeni şema = v0.4.0
set-bump = Ali).

### Sonuç

100 olay mint (50 savaş → iac:Battle; kategoriler → Founding/Composition/
Disaster/Event); location Tier-2 place-çözümü: 40 bağlı, 60 çözümsüz (boş
bırakıldı — koordinattan place mint edilmez); 214 yerel-kenar (causes/
related) sidecar'da PID-bağlama koşusunu bekliyor. Store 52.477; reindex
52.477/52.477; make test 158. v2'nin zaman-çizelgesi katmanı ilk verisini
aldı. Seferler (17) + monuments/diplomacy/trade_routes bilinçli-beklemede.

## Karar 3 — QID karantinası (kullanıcı devriyle): 388 aşikâr-çöp taşındı; H7 tombstone doktrini karantina altında birleşti

**Tarih:** 2026-07-12 · **Stage:** 3

### Karar

SİLME DEĞİL TAŞIMA: denetimin MISMATCH sınıfından sim<70 + doğrulayıcı-
sinyalsiz olanlar (dynasty <85 — reviewed=true display-gate'i aştığı için)
kayıtlardan çıkarılıp kanıtlarıyla `qid_quarantine.json`'a; her kayıtta
history izi; tarihçi geri alabilir. 653 sınır-vakası kayıtta kaldı
(display-gate zaten gizliyor) → review. H7'nin 4 insan-onaylı yanlış-hedefi
(Hârizmî→Thomas Aquinas...) tombstone deseninden karantinaya BİRLEŞTİRİLDİ;
test_h7_1 artık iki meşru biçimi tanır (tombstone VEYA kanıtlı-karantina).

### Sonuç

388 karantina = 24 dynasty (Safevîler→Spartacus League sınıfı) + 51 person +
313 place. Yayın yüzünde kanıtlanmış-yanlış iddia kalmadı; make test 158;
reindex temiz. Sınır bandının nihai kararı tarihçi oturumuna.

## Karar 4 — db.json teslimi: scholars evreni 49→450; kenarlar bağlandı

**Tarih:** 2026-07-12 · **Stage:** 4

Kullanıcı v1 sitesinin tam verisini (data.zip) + `src/data/db.json`'ı teslim
etti (450 âlim: üç-dilli ad + doğum/ölüm + koordinat + üç-dilli anlatı).
H10 S3'ün "252 yetim kart" sınırı KALKTI. Extract db.json-otoriteli yeniden
yazıldı (sözleşme aynı — 49'luk eski koşu idempotent kaldı). Sonuç: 450 =
354 augment (232 kayıt yeni gap-fill: prefLabel.ar + desc en/tr/ar) + 4 mint
+ 92 review; kenar geçişi tam haritayla 11 hoca-talebe bağı daha uyguladı
(Ebû Hanîfe.students ✓); 150 kenar (influence/isnad — şema alanı yok) P1-graf
havuzunda. Zip envanterinden gelecek işler: salibiyyat olay katmanı,
dia_travel/relations, yaqut_detail, alam_detail (7.6MB) — sıraya not edildi.

<!-- Sonraki H11 kararları burada eklenecek -->
