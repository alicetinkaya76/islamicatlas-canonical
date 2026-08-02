# H52 — Yer popup'ı, yer derin linki ve gizli bir çökme

**Tarih:** 2026-08-02
**Durum:** kapandı

H51 denetiminin kalan maddelerinden üçü.

## 1. 80 şehir popup'ının hepsi "(undefined)" basıyordu

`buildCityPopup` şunu üretiyordu:

```
Nüfus: 1.000.000 (undefined)
```

Kod `c.yr` okuyordu; db.json'da bu adda alan **yok** (0/80). Bu, âlim
popup'ındaki `s.field`/`s.sub` hatasının (H44) birebir aynısı: **kod ile veri
arasında ad sürüklenmesi.**

Veride `pop` ve `peak_pop` var, **yıl yok**. Bu yüzden yıl iddiası tümüyle
kaldırıldı — olmayan bir bilgiyi parantez içinde uydurmaktansa hiç göstermemek
doğru. Zirve nüfus ayrı ve dolu bir alan olduğu için gösteriliyor:
`1.000.000 · zirve 1.200.000`.

**Tüm popup üreticileri sistematik tarandı** (dinasti, savaş, olay, âlim, eser,
şehir, rota): koşulsuz basılan alanların hepsi veride dolu. Sözleşme guard'a
bağlandı.

## 2. Yer derin linkleri ada göre kuruluyordu

`#yaqut?search=<ad>` — oysa `yaqut_lite`'ın 12.935 satırının **%100'ünde pid
var**. Ad araması çok-adaylı olup kullanıcıyı yanlış kayda ya da boş listeye
düşürebiliyordu; kişi tarafında aynı kusur H43'te onarılmıştı.

`#yaqut?pid=iac:place-XXXXXXXX` eklendi; `?search=` geriye dönük uyumluluk için
duruyor. SearchBar pid varsa onu kullanıyor.

## 3. …ve bu, gizli bir çökmeyi ortaya çıkardı

pid ile doğrudan açılışta ekran **tamamen çöküyordu**:

```
⚠️ Bir hata oluştu — Error: Invalid LatLng object: (NaN, NaN)
```

Sebep: Leaflet uçuş eğrisini konteyner boyutundan hesaplıyor; harita henüz
0×0 iken `flyTo` çağrılınca `unproject(NaN, NaN)` atıyor. Normal akışta
(kullanıcı listeden seçer) harita çoktan hazır olduğu için kusur hiç
görünmüyordu — **pid ile doğrudan açılış onu ilk kez tetikledi.**

H17'de AlamMap'te tam bu ders alınmıştı ("gizli konteyner flyTo → NaN, setView
kullan"); YaqutMap'te tekrarlanmış. Boyut yoksa animasyonsuz `setView`.

**Not:** bu çökme, pid rotasını eklemeseydim bulunamayacaktı. Yeni bir giriş
yolu açmak, eski yolların hiç sınamadığı durumları açığa çıkarıyor.

## Guard testleri (+2, toplam 5)
- Popup üreticileri veride **bulunmayan** alan adı okuyamaz (koşulsuz satırlar
  veriye karşı doğrulanır) — "undefined basma" sınıfını kalıcı kapatır.
- `flyTo` öncesi konteyner boyutu kontrol edilmeli.

## Doğrulama
- `make test` → **213 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: `#yaqut?pid=iac:place-00002027` → Bağdat kaydı açılıyor, çökme yok,
  konsol temiz.

## Kalan (H51 denetiminden)
- Canonical yer alanları arayüzde yok (`place_subtype`, `located_in`,
  `authority_xref`, `temporal_coverage` → grep 0)
- `note` alanı yapısal alana dönüştürülmedi (geo_type 6.999 ayrıştırılabilir
  ölçüldü; `place_subtype` 3 kaba değerde, 69 ince tip note'ta bekliyor)
- 2.481 aktif yer hiçbir görünümde yok; darphanenin 3.381 kaydında pid yok
