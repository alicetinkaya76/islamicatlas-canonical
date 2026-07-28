# Hafta 35 — Kütüphane kürasyon rafı tek kaynağa bağlandı

H27 denetiminin **3 numaralı** bulgusu: `LibraryView`'daki "Kürasyonlu Atlas
Görünümleri" rafı **7 öğelik sabit diziydi** → yeni bir eser-türevi görünüm
eklenince raf güncellenmiyordu (oto-uyum boşluğu). Ayrıca kartlar kullanıcıyı
v1 hash'ine "fırlatıyordu" ve denetim bunu "birleşme vaadiyle çelişiyor" diye
KRİTİK işaretlemişti.

## Yapılan

**1) Raf artık `navRegistry`'den türer** (H33 tek-kaynak ilkesinin genişlemesi).
Kürasyon meta'sı (`ar`, `by`, `caps`, `name{tr,en}`) registry'de ilgili sekmenin
yanına `curated: {...}` olarak taşındı; `curatedItems()` yardımcısı raf için
süzer. Yeni eser-türevi görünüm eklemek = registry'de **bir alan**.

**2) "Fırlatma" sorununa dürüst çözüm — gizlemek yerine söylemek.**
Bu kartlar kabın *içinde* açılmaz; kendi tam-ekran atlas görünümlerine gider.
Bu **kasıtlıdır**: Yâkût'un 12.935 kayıtlık, harita+analitik+graf içeren
arayüzünü Kitap Kabı'na gömmek onu bozardı (Ezrakî'de gömülen CityAtlas
küçük ve tek amaçlıydı — burada durum farklı).
Çözüm: davranışı değiştirmek yerine **önceden bildirmek** → kart başlığında
`↗` işareti + `title`: *"… tam ekran atlas görünümüne gider"*.

## Doğrulama (canlı)
Kütüphane rafı: 2 bölüm başlığı korunuyor; **7 kürasyon kartı** registry'den
türedi (Mu'cemü'l-Büldân ↗ · Rihle ↗ 317 · el-Hıtat ↗ 801 …), rozetler doğru,
**0 konsol hatası**.

## Guard
`test_nav_registry_contract` → **5. test**: LibraryView rafı registry'den
türetmeli; `const curated` elle diziye dönerse **kırmızı**.

Gate **168 passed**.

## Not (kapsam kararı)
Kartların hedefini "kap içinde aç" yapmak reddedildi — gerekçe yukarıda.
Bu, denetimin önerisinden bilinçli bir sapmadır ve nedeni burada kayıtlıdır.
