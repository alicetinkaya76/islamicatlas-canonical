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

<!-- Sonraki H11 kararları burada eklenecek -->
