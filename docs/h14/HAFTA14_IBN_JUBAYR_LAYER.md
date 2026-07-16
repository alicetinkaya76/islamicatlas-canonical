# Hafta 14 — İbn Cübeyr katmanlaştırma: v1 süreci, bizim boru hattımızla

**Tarih:** 2026-07-16 · **Kullanıcı direktifi:** "var olan kitapları ben
Claude'a yükledim, o çıkarım yapmıştı — aynı süreçleri bizim kitaplara da
yapalım, kitap kitap yavaş gidelim ama yapalım."

## Süreç (v1'in disiplinli sürümü)

1. **Çıkarım:** 25 paralel Claude ajanı, 75 okuma bölümünü (91,7K kelime)
   yapılandırılmış durak şemasıyla taradı (İbn Battûta katmanı kalıbı:
   üç dilli ad, metindeki tarih İFADESİ aynen + normalize hicrî, birebir
   Arapça pasaj + sayfa çapası, kişiler+roller, is_stay, confidence).
   Katı kurallar: tarih tahmini YASAK; yalnız bizzat gidilen yer durak;
   sadece anılan uzak yerler durak DEĞİL. → 218 ham durak.
2. **Son-işlem (postprocess_ibn_jubayr.py):** ardışık aynı-yer birleştirme
   (218→208) · koordinat: 3 kademeli, hepsi koşu-kanıtlı —
   (a) birebir AR-etiket + tip-öneki/parantez/honorifik varyantları,
   (b) mağaza-mükerrer kümeleri (Mekke×8): adaylar <50 km ise en belirgine
   bağla + dup-cluster notu,
   (c) dağınık adaylar: "en belirgin" DEĞİL **rota-bağlamı** (komşu
   duraklara en yakın aday; >800 km ise bağlama) — Mansûra vakası:
   belirginlik kuralı İspanya dönüş durağını Orta Asya adaşına bağlamıştı.
   + süreklilik süpürmesi: iki komşuya da >800 km → geo_suspect (7 kayıt;
   taslak haritada gizli, kuyrukta görünür).
3. **North Star:** 208 kaydın TAMAMI needs_human_review; onay kuyruğu
   data/review_queue/ibn-jubayr-stops.jsonl. Taslak, UI'da her popup'ta
   "⚠ TASLAK — onay bekliyor" rozetiyle işaretli. Onaysız canonical'a
   HİÇBİR ŞEY yazılmadı.

## Sonuç

**208 durak · 167'si tarihli (%80) · 125 koordinatlı · her durakta birebir
pasaj + sayfa atfı.** UI: Kütüphane→Rihle→"🧭 Rota (taslak)" — altın
kesikli rota Gırnata→Sebte→İskenderiye→Nil→Hicaz→Bağdat→Şam→Akkâ→
Sicilya→Kartacena; numaralı duraklar; popup'tan "bölümü oku §N".
Tarayıcı doğrulamalı. Örnek kalite: Gırnata çıkışı "8 Şevval 578, Perşembe
ilk saat" birebir pasajla; deniz geçişleri is_stay=false.

## Sonraki kitaplar (aynı runbook)

Fütûh (olay şeması: fetih+yer+tarih+pasaj) → Ezrakî (yapı şeması: Mekke
Hıtat'ı) → Meğâzî (sefer olayları) → ... Onay akışı: Ali kuyruk dosyasını
(veya ileride onay ekranını) işledikçe taslak→canonical terfisi ayrı
adapter koşusuyla yapılır.

## Karar (2026-07-16): doğrudan yerleştirme

Kullanıcı inceleme kapısını bekletmeden doğrudan yerleştirme talimatı verdi
("human review gerek[mez] direk olarak yerleştir") — v1'deki kendi süreciyle
tutarlı sahip kararı. Uygulanan:
- Taslak → ibn_jubayr_atlas_layer.json (status: PUBLISHED, sahip kararı
  kayıtlı); confidence/geo_note/geo_candidates alanları veride KORUNDU
  (dürüstlük veri düzeyinde sürer).
- UI'dan 'taslak' rozetleri kalktı; rota kitap sayfasının birinci-sınıf
  özelliği.
- 107 bağlı yer kaydına canonical iz: derived_from_layers += ibn-jubayr
  (jenerik applier; ibn-battuta deseni) + facet değeri; place şeması
  derived_from_layers enum'una 'ibn-jubayr' (geriye-uyumlu genişletme,
  ADR-013 bump gerektirmez).
- Onay kuyruğu dosyası kapatıldı (git geçmişinde durur); geo_suspect 7
  nokta haritada gizli kalmaya devam eder.
