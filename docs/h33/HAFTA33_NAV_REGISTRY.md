# Hafta 33 — Tek deklaratif navigasyon kaydı

H27 denetiminin **1 numaralı önerisi**. O turda semptomları düzeltmiştim
(çift-Kütüphane, gruplama, mobil parite); asıl refactor duruyordu.

## Sorun (ölçüldü)
Aynı sekme listesi **beş** yerde tekrarlıydı: `VALID_TABS` (22),
`SWIPE_TAB_ORDER` (11), masaüstü Kaynaklar/Analiz açılırları, mobil çekmece
(21 `role="tab"`), `BottomTabBar` (21 id). Yeni görünüm = ~8 dokunuş; biri
unutulunca **sessiz** kırılıyordu (kanıt: #visits mobilde hiç erişilemiyordu;
çekmece ile BottomTabBar khitat/cityatlas'ta anlaşmıyordu).

## Çözüm
`web/src/config/navRegistry.js` — her sekme **bir kez** tanımlanır:
`{id, icon, label{tr,en,ar}, group, navs[], preload?, countKey?}`.
Türetilenler: `VALID_TABS`, `SWIPE_TAB_ORDER`, Kaynaklar ▾ (grup başlıklarıyla),
Analiz ▾, `BottomTabBar` (PRIMARY/SECONDARY).

**Davranış korundu — iki bilinçli karar:**
- **Kaydırma sırası kayıt sırasından TÜRETİLMEDİ.** v1'deki dizilim kasıtlı
  olarak `SWIPE_SEQUENCE` ile sabit tutuldu (kayıt sırası farklı bir sıra
  veriyordu). Registry'de olmayan id süzülür → iki kaynak ayrışamaz.
- **Etiketlerde i18n önceliklidir** (`t.tabs[id]`); registry etiketi yedektir.
  Böylece mevcut çeviriler aynen çalışır.

**Kapsam sınırı:** App.jsx'in 45 dallı render ternary zinciri BU TURDA
DEĞİŞTİRİLMEDİ (yüksek risk, ayrı iş). Bunun yerine guard test registry ↔
dispatch tutarlılığını kilitler.

## Guard (4 test)
1. registry boş/yinelenmiş değil;
2. App.jsx listeleri registry'den türetir (elle dizi geri gelirse kırmızı);
3. BottomTabBar registry'den beslenir;
4. **registry'deki her sekmenin render dalı var** — menüde olup ekranı olmayan
   sekme = sessiz kırık.

## Doğrulama (canlı)
- **Masaüstü:** Kaynaklar 14 öğe + 2 bölüm başlığı + rozetler
  (13.844 / 8.491 / 7.538); Analiz 4 öğe. 0 konsol hatası.
- **Mobil:** alt çubuk *Harita · Pano · el-A'lâm · DİA · Daha*; "Daha" 17 öğe —
  Kütüphane, **Seyahatnâmeler**, Şehir Atlası dahil.
- Gate **167 passed**.

## Bundan sonra yeni görünüm eklemek
`navRegistry.js`'e **bir satır** + bir render dalı. Diğer dört nav kendiliğinden
güncellenir; bir yer unutulursa guard kırmızıya döner.

## Not (süreç)
Bu journal ilk yazımda bozulmuştu: `cat > … <<'EOF'` heredoc'u `mkdir -p` ile
`||` zincirine girince dosyaya commit komutunun kendisi yazıldı. Dosya yeniden
yazıldı; ders: journal'ı heredoc yerine doğrudan dosya yazımıyla oluştur.
