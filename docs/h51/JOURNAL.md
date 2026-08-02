# H51 — Yerler ekseni denetimi: arama onarımım yarım kalmış

**Tarih:** 2026-08-02
**Durum:** ilk dalga kapandı (kalan maddeler aşağıda)

Âlimler eksenindeki 6 eksenli denetimin aynısı **yerler** eksenine uygulandı:
**84 bulgu, 37 kritik**. En ağır bulgu benim eksik işim çıktı.

## H44'teki "arama onarıldı" iddiam yarım doğruydu

H44'te `bookkit/normalize.js`'i onardım ve "arama onarıldı" dedim. **Kopyaları
taramamışım.** Kırık Arapça sınıfı **10 dosyada** canlı kalmış:

`SearchBar` (global arama) · `AlamView` · `DiaView` · `KhitatView` ·
`LeStrangeView` · `RihlaView` · `SalibiyyatView` · `muqaddasi/constants` ·
`ei1Constants` · `data/placeBooks`

Ölçüm: global aramada 12.935 Yâkût Arapça adının **%99,6'sı** boşa düşüyordu;
MuqaddasiView'da 2.049'un %94,7'si. Yalnız `YaqutView` kurtulmuştu — çünkü
bookkit'i import ediyordu.

**Ders:** tek kaynağı onarmak yetmez; **kopyaları aramak da onarımın parçasıdır.**
10 kopya silindi, hepsi `bookkit/normalize`'a bağlandı. `GlossaryModal`'ın
TR-only kopyası da (harf yemiyordu ama kopyaydı) aynı otoriteye alındı.

## "Bu yeri kitaplarda oku" köprüsü H18'den beri tamamen ölüymüş

`placeBooks.js`'in `normAr`'ı **tek** hareke aralığı kullanıyordu; üretici
(`extract_book_mentions.py`, `build_place_index.py`) **iki** aralık kullanıyor.
Sonuç: `normAr('بغداد') === ''` → `place_index`in 4.595 adının **hiçbiri**
eşleşmiyordu.

**4.566 yer / 102.984 anılma** kurulduğu günden beri hiç çizilmemiş. Ölçüm:
db.json'ın 80 şehrinden eşleşen **0 → 21**.

Acı ironi: `build_place_index.py` dosyasının başında *"normalizasyon kuralı
burada KOPYALANMAZ — sürüklenme olmasın"* uyarısı var. Kopyalanmış ve
sürüklenmiş. `placeBooks.js`'in kendi docstring'i de *"üreticideki norm_ar ile
aynı normalizasyon"* diyordu — değildi.

## Uydurma koordinat sabitleri — deponun en sert kuralının ihlali

`SearchBar.jsx`'te dört satır:

```js
lat: b.lat || 30, lon: b.lon || 45          // Yâkût
lat: parseFloat(e.lat) || 30, ...           // Makdisî
lat: e.lat ?? 30.05, lon: e.lon ?? 31.26    // Hıtat (Kahire)
```

Koordinatsız kayıt sessizce tek bir noktaya çakılıyordu — yalnız Yâkût kolunda
**1.483 kayıt** — ve kullanıcı bunu "bilinen konum" sanıyordu. `SalibiyyatCompare`'de
de `cluster.lat ?? 33` vardı. Ayrıca `|| 30` kalıbı geçerli `lat=0` değerini de
yutuyordu.

Sabitler kaldırıldı: koordinat yoksa `null` kalır, `handleSelect` **uçmaz**
(kaydı seçer, harita yerinde kalır), koordinatsız küme çizilmez.

## Guard testleri (3) — mutasyonla sınandı

- Hiçbir dosyada silme aralığı Arap harf bloğuyla (U+0620–U+064A) kesişemez.
  Test sınıfları **kod noktası düzeyinde çözer** — görsel karşılaştırma bidi
  yüzünden güvenilmez (bu denetimde ajan da bir kez yanlış okudu).
- `normalize` tek yerde tanımlı olmalı.
- `lat/lon` sabit sayıya düşemez.

## Doğrulama
- `make test` → **211 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: global aramada `بغداد` → 11 sonuç, `دمشق` → 2, `bagdat` → 11.
  Önce üçü de sıfırdı. Konsol temiz.

## Denetimden kalan (bu tura girmedi)
1. **80 şehir popup'ı "(undefined)" basıyor** — âlimlerdeki hatanın yer eşi.
2. **Canonical yer alanlarının hiçbiri arayüzde yok** (`place_subtype`,
   `located_in`, `temporal_coverage`, `authority_xref`, `yaqut_id` → grep 0).
3. **`note` alanı deponun en zengin yer katmanı ve string olarak hapis:**
   geo_type 6.999 · modern ülke 11.237 · etimoloji 6.000 · DİA bağlantısı 6.776.
   Yapısal alanlarla çakışma ölçüldü: geo_type taşıyan kayıtların %100'ünde
   `place_subtype` BOŞ.
4. **`place_subtype` 3 kaba değerde**, 69 ince yer tipi note'ta bekliyor
   (mountain 1.214, water 704, valley 342…) — canonical bu boyutta v1'den fakir.
5. **Yer derin linkleri ada göre** (`#yaqut?search=`), pid %100 mevcutken.
6. **2.481 aktif yer hiçbir görünümde yok**; darphane katmanının 3.381 kaydında
   pid alanı hiç yok.
