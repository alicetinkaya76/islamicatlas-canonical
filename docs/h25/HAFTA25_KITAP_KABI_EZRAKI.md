# Hafta 25 — Kitap Kabı dikey dilimi: Ezrakî → Mekke Şehir Atlası

## Bağlam
Kullanıcı "iki farklı arayüz var, kaynaşmamışlar; Ezrakî #cityatlas'ta Mekke
atlası olmalıydı ama sadece kütüphaneye kondu" dedi (5-ajan workflow üç iddiayı
da doğruladı; kök neden: H17 "Kitap Kabı" yalnız ŞEMA, UI bileşeni hiç
yazılmadı). Kullanıcı **dikey dilim** seçti: önce Ezrakî'yi uçtan uca göster.
Bu belge dilimin **1. adımını** (Mekke şehir atlasını gerçekle) kaydeder.

## Kritik dürüstlük bulgusu (H25 Karar-1)
**Ezrakî Konya gibi sokak-iğne-haritası OLAMAZ.** Kanıt:
- Canonical 633 institution kaydının **koordinatı yok** — yalnız `located_in`
  Mekke (place-00011505); Ezrakî GÖRELİ tarif eder ("Safâ tarafında, mescit
  duvarına bitişik; aralarında ~7 zirâ"). Bu ortaçağ göreli topografyası,
  modern koordinat değil.
- Kitabın okuma-katmanındaki 808 özellikten yalnız **199'u** bir canonical
  place'e çözülüp koordinat aldı; bunların da yalnız **109'u Mekke bölgesine**
  düşüyor (90'ı aynı adlı homonim, dünyanın başka yerine çözülmüş = yanlış),
  ve "yakın" olanlar bile sokak hassasiyetinde değil (Ebû Kubeys ~40 km sapmış).
- **Modern iğne zorlamak = sahte hassasiyet = projenin kaçındığı tam da bu**
  (CLAUDE.md north star: "never fabricate a count/coordinate").

## Dürüst tasarım
`build_mecca_atlas.py` (→ `view-data/city-atlas/mecca.json`, gitignored,
build'de üretilir): kitabın okuma-katmanı atlasından 808 özellik →
CityAtlas kayıt şeması. **Kod/bileşen DEĞİŞMEDİ** — CityAtlasView/Detail
mecca.json'u konya/cairo gibi okur (koordinatsız kaydı zaten zarif karşılıyor).
- **HARİTA:** yalnız Mekke bölge kutusundaki ~109 koordinat iğnelenir; konum
  "varlık-çözümlü, yaklaşık" etiketli. Kutu-dışı 90 koordinat İĞNELENMEZ
  (kayıt listede kalır, koordinatsız).
- **LİSTE:** 808'in tamamı; koordinatsız 609 kayıt Ezrakî'nin göreli tarifi +
  Arapça pasaj + bölüm künyesiyle görünür.
- **Registry altbaşlığı farkı AÇIKÇA söyler:** "göreli topografya, modern
  ölçüm değil" → okur Konya'nın saha-ölçümüyle karıştırmaz.

## Sonuç (tarayıcı-doğrulamalı)
- #cityatlas sekmeleri: **Konya 583 · Kahire 801 · 🕋 Mekke 808** (kardeş şehir).
- Mekke atlası yüklüyor: 11 kategori (Diğer 179 · Ev/Konut 165 · Kuyu 111 ·
  Dağ 106 · Mescid 53 · …), harita gerçek Mekke bölgesinde (MECCA/MINA/ARAFAT).
- Detay paneli **Ezrakî'nin gerçek Arapçasını** gösteriyor (Kâbe kaydı: göreli
  inşa anlatısı + "وأنه بناه من خمسة أجبل في لبنان وطور وطور سينا…"). Konsol hatası yok.
- Gate 160; mecca.json bayt-bayt deterministik.

## Dilim-2: birleşik Kitap Kabı yüzü (kullanıcı "devam" dedi)
Ezrakî artık TEK Kitap Kabı yüzünde açılıyor; şehir atlası kabın bir **yetenek
sekmesi**. UI'daki kanıt (tarayıcı-doğrulamalı):
- Okuyucu sekmeleri: **Metin | 🗺 Mekke Atlası (808) | 🗺 Kitap Haritası (221) |
  🏛 Yapılar (808) | 📊 İstatistik** — kullanıcının önizlemesindeki sıra.
- "🗺 Mekke Atlası" sekmesi, o cilalı CityAtlas görünümünü **kabın içine gömer**
  (tam genişlik; bölüm-ağacı + künye sütunları o modda gizlenir); altbaşlık
  dürüstlük notu, 109 iğne, kategori filtreleri, 808 liste hepsi çalışıyor.
- "←" düğmesi metne döndürür. Konsol hatası yok.

**Nasıl (kod, minimal + veri-güdümlü):**
- `cityAtlasRegistry.js` mecca girişine `bookPidnum: '00001848'` — kitap↔atlas bağı.
- `CityAtlasView.jsx`: `embedded` + `lockCityId` propları (şehir seçici gizli,
  tek şehre kilitli, "✕"→"←" metne dön); `.city-atlas--embedded { height:100% }`.
- `LibraryView.jsx`: `cityAtlas = REGISTRY.find(c=>c.bookPidnum===book.pidnum)`;
  varsa `mode='cityatlas'` sekmesi + gömülü render; atlas modunda grid tek sütun,
  yan sütunlar gizli. **Regresyon kontrolü:** şehir atlası olmayan kitap (İdrîsî)
  bu sekmeyi GÖSTERMEZ (veri-güdümlü) — doğrulandı.

**Neden LibraryView'i genişlettim, yeni bileşen yazmadım:** LibraryView zaten
"yarı-doğmuş kap" (3 bölme + mode-sekmesi deseni); atlas'ı bir yetenek sekmesi
olarak eklemek en az riskli ve tüm çekirdek kitaplara ölçeklenebilir yol.

## Bu dilimde YAPILMAYAN (bilerek, sonraki adımlar)
- Kap sekmelerinin `books/index.json` manifest `capabilities`'inden sürülmesi
  (şu an mode-sekmeleri reading dosyalarının varlığından; atlas sekmesi
  registry'den). Jenerik manifest-güdümlü kap = tüm kitaplara ölçekleme adımı.
- Ters köprü: #cityatlas Mekke detayından "kitapta oku" derin-linki.
- Frontend→Typesense mağaza bağlantısı (ana #map hâlâ db.json).

## Değişen dosyalar
- `pipelines/frontend/build_mecca_atlas.py` (yeni; üretici)
- `web/src/data/cityAtlasRegistry.js` (mecca girişi + 11 kategori)
- `Makefile` (view-data hedefine mecca üretimi)
- `scripts/start_local.sh` (3. adıma mecca üretimi)
- `web/public/view-data/city-atlas/mecca.json` (üretilen; gitignored)
