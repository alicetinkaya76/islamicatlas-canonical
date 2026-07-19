# Hafta 15 — Kitap-katmanları canonical mağazada (mağaza 58,744)

**Tarih:** 2026-07-16 · **Bağlam:** H14 çıkarımlarının olgun alt-kümeleri
birleşik dizine mint edildi — kitap sayfası katmanları artık ana arama/
facet/harita vatandaşı.

## Mint'ler

- **book-events (264 olay):** Fütûh+Meğâzî+Sîre'nin TARİHLİ alt-kümesi
  (şema temporal ister; 1,437 tarihsiz kayıt kitap-içi katmanda yaşamaya
  devam eder — bilinçli sınır). 176'sı yer-bağlı (location). Arapça pasaj
  description.ar'da; sayfa çapası locator'da; kaynak eser PID'i edition'da.
  19 kayıt yıl-parse hatasıyla atlandı (date_h biçimsiz).
- **book-structures (1,230 yapı):** Ezrakî→Mekke (633, located_in
  iac:place-00011505) + Hatîb→Bağdat (597, iac:place-00002027) —
  Konya/Kahire CityAtlas'larına iki kardeş şehir. 305'i öz-koordinatlı;
  dağ/şüpheli 210 kayıt mint dışı. Alt-tip muhafazakâr (987 'other' —
  kapı/mahalle/katî'a enum'da yok; v1 türü note'ta).
- **bakri-mucjam place augment:** İLK deneme 7 yanlış bağ üretti ve GERİ
  ALINDI — yapısal kısayolun dersi: Bekrî başlıkları çoğunlukla
  harf-bölümü ("الهمزة والدال"); bileşik-ad bölme varyantı bunları 7 pid'e
  mıknatısladı (birine 43 bağ). Bozuk katman kaldırıldı; düzgün LLM madde
  çıkarımı (54 ajan) fırlatıldı — sonuçla yeniden bağlanacak.

## Kayıt

5 yeni kaynak-katmanı facet'i (futuh-buldan, maghazi, sira, azraqi-makka,
tarikh-baghdad) + prefix_map; place şeması enum += bakri-mucjam.
Gate 160 · projeksiyon 58,744/58,744 · Typesense 58,744 fail=0.

## Bekrî gazetteer — düzgün çıkarımla geri geldi (H15b)

Yapısal kısayolun çöküşünden sonra 55 ajanlık madde çıkarımı (2 tur + 2
boşluk retry; toplam ~3M token, API 529'lar journal-birikimi + hedefli
retry ile toparlandı): **3,697 toponim maddesi** (harekeleme tarifi +
bölge ipucu + birebir pasaj), SIKI birebir bağlamayla **1,853 koordinatlı**
(İbn Cübeyr'den sonra en zengin katman). 1,834 ayrık yere place augment
(madde başına 1.0 bağ — mıknatıs yok). UI popup'ında 🔤 harekeleme +
🧭 bölge ipucu. Ders pekişti: sözlük-tipi kitaplarda yapısal kestirme
YOK — LLM çıkarımı şart. Tarayıcı-doğrulamalı; Arabistan yoğunluklu
1,817 nokta.
