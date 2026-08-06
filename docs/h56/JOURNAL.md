# H56 — Olay/kurum/hanedan denetimi: "veri bilmiyor, ekran biliyormuş gibi davranıyor"

**Tarih:** 2026-08-04/05
**Durum:** birinci dalga kapandı (uydurma sınıfı) — kalan maddeler aşağıda
**Commit:** `65bc4f73`

Kişi (H44–H50), yer (H51–H54) ve eser (H55) eksenlerinden sonra hiç
denetlenmemiş üç namespace: **event (9.956), institution (5.423),
dynasty (186)**. Üç namespace × iki mercek = 6 bağımsız denetçi, ardından her
bulgu için ayrı bir **çürütücü**. **48 bulgu → 45'i çürütmeden sağ çıktı.**

---

## Manşet: aynı kalıbın beş ayrı vakası

Sağ çıkan bulguların en ağır sınıfı tek bir cümlede toplanıyor:
*veri bir şey bilmiyor, ekran biliyormuş gibi çiziyor.* Beşi de onarıldı,
hiçbirinde doğru değer tahmin edilmedi.

### 1. Savaş sonucu varsayılanı "zafer"

`getOutcomeType`'ın son satırı `return 'win'` idi — ve fonksiyon **üç dosyada**
kopyalanmıştı (`BattleView`, `BattleSidebar`, `BattleCard`).

Ölçüldü: 100 savaşın **39'unda** sonuç metni yok (`battle_meta.js` 65'ini
kapsıyor). Ekrandaki 82 "✓ zafer" rozetinin **%48'i** veriden değil
varsayılandan geliyordu. İkisi doğrudan **tarihsel olarak yanlıştı**:

- **Tarain Savaşı (Birinci, 1191)** — Gurluların *yenilgisi*, ekranda ✓
- **Belgrad Muhasarası (1456)** — Osmanlı *yenilgisi*, ekranda ✓

Yani varsayılan yalnız bilgisizliği gizlemiyordu; **aktif olarak yanlış tarih
anlatıyordu.** Tek otorite `data/battleOutcome.js`, varsayılan `'unknown'`,
rozet basılmıyor. **39 → 0.** Ayrıca `outcomeClass` ölü koddu (tanımlı,
hiç çağrılmıyor) ve gövdesinde *"default, overridden by specific logic below"*
yazıyordu — o mantık hiç yazılmamış. Silindi.

### 2. İmkânsız yıl aralığı çıplak basılıyordu

186 hanedanın **9'unda** aralık imkânsız. İslam takvimi 622'de başlar:

| id | hanedan | v1 | sorun |
|---|---|---|---|
| 30 | Eyyûbîler | 1169 – 15 | başlangıç > bitiş |
| 51 | Âl-i Cülandâ | 7 – 9 | ikisi de < 622 |
| 89 | Hârezmşahlar | 7 – 1231 | başlangıç < 622 |
| 132 | Çağataylılar | 1227 – 15 | başlangıç > bitiş |

…ve 5 tanesi daha. **Dördü haritada hiçbir yılda çizilmiyor** — sebebi bir
filtre kararı değil, bozuk veri. Değerler büyük olasılıkla hicrî yüzyıl
numarası; **ama bu bir tahmindir ve veriye yazılmadı.**

Ayrı 7 kayıtta `end = 2025` bir *nöbetçi* değer ve bunu canonical
`temporal.end_ce: null` **bağımsız olarak doğruluyor** (Âl Suûd, Brunei
Sultanları, Yogyakarta…). Dolayısıyla "devam ediyor" yazmak yorum değil, iki
kaynağın ortak ifadesi.

Arayüz artık **"kaynakta tutarsız (10 – 1550)"** ve **"1735 – devam ediyor"**
yazıyor; ham değer parantezde kalıyor (veriyi saklamak da bir tür sahtelik
olurdu). 9 kayıt `data/review_queue/dynasty_temporal.jsonl` ile insan
kuyruğuna alındı.

### 3. Haritanın merkezî görseli uydurma

186 hanedan dikdörtgeninin **185'i veriden gelmiyor.** `dynBbox()` başkenti
alıp editöryel bir *"önem"* etiketine göre sabit derece ekliyor:

```
Kritik 8° · Yüksek 5° · Normal 3° · aksi 1,5°
```

Gerçek sınır kutusu (`bn/bs/bw/be`) taşıyan **tek** hanedan: Endülüs Emevîleri.

Şekil **korundu** — v1'in görsel kimliği bu. Ama artık şematik olanlar kesikli
kenarla ve düşük dolgu opaklığıyla çiziliyor, popup açıkça diyor:
*"Şematik yayılım — ölçülmüş sınır değil; başkent çevresinde temsilî alan."*

### 4. 830 hükümdar 133 noktaya çakışıyor

830 hükümdarın **830'unun** koordinatı kendi hanedanının başkentinden
kopyalanmış. Popup artık *"Konum hanedanın başkentinden devralındı — hükümdara
özgü bir yer kaydı yok"* diyor.

### 5. Elle yazılmış sayı

`MapView` katman rozeti `'5.618'`i sabit taşıyordu — üstelik Arapça dalı yoktu.
`canonical_overview.json`'dan okunuyor, üç dil de var.

---

## Birleştirmenin kendi amacına aykırı yan etkisi

H49/H50 kaybeden kayıtları yumuşak-sildi. Ama üzerlerindeki **kaynak izleri**
(curie'ler) orada kaldı ve havuzda görünmedikleri için ekrandan düştüler.
Yani **birleştirme, birleştirmek istediği zenginliği kaybetti.**

Ölçüldü: **1.976 curie yetim**, **1.382 kazanan kişi** etkileniyor. İzler
kazanana taşındı:

```
a 11.465→12.496 · d 7.041→7.379 · bc 5.215→5.549 · sc 228→270
e 1.104→1.136 · s 134→149 · ba 215→233 · by 813→826
el-A'lâm ∩ DİA:  1.209 → 2.327   (+1.118 kişi artık İKİ kaynağı da gösteriyor)
```

H46 güvencesi **korundu**: DİA slug'ının pid eşitliği hâlâ şart; yalnız
karşılaştırmanın *iki tarafı da* kazanana çevriliyor. Yanlış ret 520 → 415.

---

## Kapı kendi kendini ikinci kez yakaladı

Yeni kapı ilk koşusunda **yanlış alarm** verdi: onarımı açıklayan yorum
(*"elle yazılmıştı '5.618'"*) onarılmamış kod sanıldı. Bu oturumda ikinci kez —
H55'te de JSDoc içindeki örnek bir `import` gerçek sanılmıştı.

**Ders: kusurun ADI kusurun KENDİSİ değildir.** Yanlış alarm veren kapı,
görmezden gelinen kapıdır. İki kapıda da yorumlar taramadan çıkarıldı.

**Beş kusurun beşi de mutasyonla doğrulandı** — kusur geri konunca ilgili test
kızarıyor, geri alınınca yeşile dönüyor.

---

## Doğrulama (tarayıcı, canlı)

- 10 aktif hanedanın **10'u** kesikli çiziliyor, popup şematik notunu basıyor
- Arama: **"Kilva Sultanları (kaynakta tutarsız (10 – 1550))"**
- Emevî Halifeleri: **"661 – 750"** (sağlam kayıt etkilenmiyor)
- Konsol hatası: yok · `vite build`: yeşil

**Test 234 → 247.**

## Ajan raporunda düzelttiğim iki nokta

Denetçilere körü körüne güvenilmedi:

1. Haritadaki 13 adet `U` işaretini bozuk render sandım — kaynağa baktım,
   **UNESCO rozeti** (`LayerManager.js:53`). Rapor edilmedi.
2. Bir bulgu "21 kurum Mısır merkezine **bayraksız** çakılı" diyordu.
   Ölçtüm: bayrak **var** — `note` içinde *"Koordinat düşük güvenilirlikli
   (v1 geocoding)"*. Yani kusur "bayrak yok" değil, **"bayrak note'ta hapis"**
   (62 kayıt; `grep web/src` → 0 isabet). Farklı kusur, farklı onarım.

---

## Kalan — bu turda YAPILMADI

**Otomatik onarılabilir, sıradaki dalga:**
- Olay katmanında **iki bağımsız kesme üst üste**: üreticide `CAP=25`, arayüzde
  `slice(0,12)`. 9.956 olayın 2.616'sı ekranda; Bağdat marker'ı **388 yazıp 12
  satır gösteriyor** ve "+N daha" bağının **hiçbir hedefi yok**.
- **Koordinat belirsizliği yayına hiç taşınmıyor**: 5.618 olayın %27,8'i
  centroid/approximate koordinat üzerinde, 613'ü **250 km** hassasiyetli — hepsi
  100 m hassasiyetli şehirlerle aynı görsel kesinlikte. Mekanizma zaten var
  (`yaqut_lite.geo_confidence`, HeatmapLayer bunu kullanıyor).
- Kurum `note`'unda hapis zenginlik: 62 kayıtta koordinat güven işareti, 1.343
  dönem, 1.020 durum, 5.399 v1 kategori — **hiçbiri ekranda**.
- maqrizi katmanının **801 kaydının 801'ine** sabit `located_in = Kahire`;
  53'ü Kahire'den 50 km'den, 31'i 200 km'den uzakta.
- 29 olay **yumuşak-silinmiş 4 place**'e bakıyor (Kudüs'te sayı bölünmesi).

**Yayın kapısından ÖNCE kapanmalı:**
- `search/projections/event.yaml:16-18` → `description_en: $.note`. 9.956
  dokümanın **%100'ü** üretim izi taşıyor (`Kaynak:` 9.102, `dup-cluster` 2.917,
  `Çıkarım güveni` 9.102). Bugün zarar yok (`upsert.py::_env()` env yoksa
  duruyor) ama **hosting açıldığı an** dahilî notlar kamuya çıkar.

**İnsan kararı (Ali/tarihçi kapısı):**
- 9 tutarsız hanedan yılı — kuyrukta, Bosworth'e bakılmalı
- 8.211 olaydaki 4.774 önder adının kişi çözümü (güvenli taban: 443 ad /
  1.672 geçiş tek adaylı)
- 2.238 çözülmemiş yer adının toponim çözümü (%88,5–91,5'i çok adaylı)
- `outcome` enum eşlemesi — **kusur değil**, `docs/h11`'de belgeli çekimserlik
- `PHASE0_CLOSEOUT.md:239` event ns'i "ÇÖZÜLDÜ" diye kapatmış; oysa şemanın
  kendi kuralı (*"an event without participants is a non-event"*) 9.956/9.956
  kayıtta ihlal ediliyor. Kapanış statüsü Ali'nin kararı.

**Faz-2:** `participants_persons`, `preceded_by/followed_by`, `authority_xref`.
`causes`/`consequences`'in boş olması **kusur değildir** —
`build_causal_layer.py:8-14` gerekçesini yazmış.

---

# H56 — İKİNCİ DALGA (2026-08-05, `416e368a`)

Birinci dalgada "kalan" diye yazılmış maddelerin çoğu kapandı.

## Sayı ile içerik çelişiyordu

İki bağımsız kesme üst üste biniyordu: üreticide `CAP = 25`, arayüzde
`slice(0, 12)`. Bağdat marker'ı başlıkta **"388 canonical olay"** yazıp listede
**12 satır** gösteriyor, sonra açılacak hiçbir hedefi olmayan *"+376 daha"*
satırı basıyordu.

Ölçüldü: 5.618 çözülen olayın yalnız **2.616'sı (%46)** ekrana ulaşıyordu.

Dağılımı ölçtüm — en yoğun yer 388 olay, toplam 720 marker — ve **kesmeyi
tamamen kaldırdım.** Payload %100 taşıyor, liste kaydırılabilir. Katman zaten
opsiyonel ve tembel yüklendiği için 968 KB → 1.445 KB maliyeti yalnız katmanı
açan kullanıcıya düşüyor. Kalan tavan (`SANITY = 2000`) kesme değil **kaçak
denetimi**; aşılırsa susulmuyor.

**Ekrana ulaşan olay: 2.616 → 5.618 (+%115).** Bağdat: count 388, payload 388.

## Yanlış kesinlik: koordinat belirsizliği yayına hiç çıkmıyordu

Kaynak place kaydı belirsizliğini **dürüstçe ilan ediyor** —
`coords.uncertainty` ve `precision_meters` 18.411 yerde dolu:
centroid 14.532 · approximate 2.456 · exact 1.423. Üretici hiçbirini
okumuyordu.

Sonuç: **250 km hassasiyetli 218 marker** (613 olay), 100 m hassasiyetli
Haleb ile birebir aynı görsel kesinlikte çiziliyordu. Artık payload `u`+`pm`
taşıyor; belirsiz marker kesikli kenarla çiziliyor, popup
*"üst yerin merkezinden · ±250 km"* diyor. Belirsiz koordinat üzerindeki olay:
**1.563 (%27,8)**.

## Zombi marker ve sahte alt tür

- Yer indeksinde `deprecated` denetimi yoktu; **Kudüs'te sayı bölünüyordu**
  (aktif kayıt 14 olay + emekli kayıt 1 olay, aynı koordinat). 29 olay halefe
  yönlendirildi, marker **721 → 720**.
- Alt türü olmayan olaya `"Event"` yazılıyordu — *"tür yok"* bir **tür** gibi
  görünüyordu (**1.838 kayıt**). Alan artık hiç yazılmıyor; arayüz
  "sınıflanmamış" diyor ve alt tür etiketlerini üç dile çeviriyor (eskiden
  TR/AR arayüzde de ham İngilizce sınıf adı basılıyordu).

## Yayın kapısındaki engel kalktı

`search/projections/event.yaml` `description_en: $.note` diyordu — yani
"İngilizce açıklama" adlı alan **Türkçe boru hattı iç kaydını** taşıyordu ve
`description_tr`/`description_ar` `~` ile kapalıydı.

Ölçüldü (`full_reindex --dry-run --namespace event`): **9.956 dokümanın
9.956'sında (%100)** en az bir üretim izi — `Kaynak:` 9.102, `Çıkarım güveni`
9.102, `dup-cluster` 2.917, `v1 tip:` 754. Hosting açıldığı an her olay
kartının özeti dahilî not gösterecekti.

Üç dil de doğru kaynağa bağlandı (diğer beş namespace zaten öyleydi).
**Üretim izi taşıyan doküman: 9.956 → 0.** `description_tr` 9.202,
`description_ar` 9.743 dolu; hiçbiri boş değil. `manuscript.yaml`'daki ikiz
kalıp da düzeltildi (o namespace'te henüz kayıt yok — canlı zarar yoktu).

## Kurum yayın katmanı

H54'ün kurum eksenindeki karşılığı: 5.423 kayıt.

En önemlisi **koordinat güven uyarısı** — 62 kayıt kendi `note`'unda
*"Koordinat düşük güvenilirlikli (v1 geocoding)"* diyor ve `grep web/src` bunun
için **sıfır** isabet veriyordu. 21'i tam olarak **(28.0, 31.0)** — Mısır'ın
geometrik merkezi — üzerinde ve hepsi manastır.

Türetilmiş olgu: **89 noktayı 3 veya daha çok kurum paylaşıyor** (557 kayıt).

*Denetim bunu "bayraksız kopyalanmış" diye raporlamıştı; ölçünce bayrağın
**canonical'da var ama note'ta hapis** olduğu görüldü — farklı kusur, farklı
onarım.*

**Dört kusur da mutasyonla doğrulandı. Test 247 → 259.**

---

## İkinci dalgadan sonra kalan

**Yapılmadı — join anahtarı yok:** `institution_facets.json` ÜRETİLDİ ama
arayüze **bağlanmadı**. Kurumları gösteren üç görünüm (KhitatView, Konya ve
Kahire city-atlas) v1'in canlı symlink'indeki dosyaları okuyor ve o dosyalarda
canonical institution pid'i **yok** — join anahtarı hiç mint edilmemiş.
Bağlamak için önce `build_book_city_atlas.py` ve v1 katmanlarının kaydın kendi
`institution` pid'ini yazması gerekiyor. Bu, v1 symlink sınırına dokunduğu için
ayrı bir turda ve Ali kapısıyla ele alınmalı.

**Yapılmadı — ölçüldü, sırada:**
- maqrizi katmanının **801/801** kaydına sabit `located_in = Kahire`; 53'ü
  Kahire'den 50 km'den, 31'i 200 km'den, en uzağı **482 km** uzakta.
- Canonical olayların tek kapısı hâlâ varsayılan kapalı bir toggle; derin link
  yok, `SearchBar` indeksi tamamen `db.json`'dan kuruluyor → **9.956 canonical
  olayın 0'ı aranabilir.**
- Evliyâ katmanında v1'in `category_confidence` değeri düşürülüyor: 321 kayıt
  <0,5 güvenle sert `@type` alıyor, izi note'ta bile yok.

**İnsan kapısı (değişmedi):** 9 tutarsız hanedan yılı · 4.774 önder adı ·
2.238 çözülmemiş yer adı · `PHASE0_CLOSEOUT` event kapanışının statüsü.

---

# H56 — ÜÇÜNCÜ DALGA (2026-08-05/06, `0d1e3cd0`)

## Merkezî defter aranabilir oldu

`SearchBar` indeksi tamamen v1'in `db.json`'ından ve beş "lite" dosyadan
kuruluyordu. Mağazadaki **9.956 olayın, 9.404 eserin ve 5.423 kurumun
aranabilir olanı sıfırdı.** Kullanıcı "Kâdisiye" yazınca v1'in 100 küratörlü
savaşını buluyor, defterdeki 9.956 kitap-türevi olayı bulamıyordu.

**Tek sert kural: yalnız gerçekten açılan hedefi olan kayıt indekslenir**
(H46 — sahte tıklanabilirlik, dürüst boşluktan kötüdür).

| | mağazada | indekslendi | neden dışarıda |
|---|---|---|---|
| olay | 9.956 | **9.102** (%91) | 854'ünde kitap+bölüm çapası yok |
| eser | 9.404 | **9.385** | 19'unda müellif yok |
| kurum | 5.423 | **0** | join anahtarı mint edilmemiş → hedef YOK |

**14.899 → 49.353 aranabilir kayıt.**

### Kritik ayrıntı: çip olmadan indeks işe yaramazdı

`doSearch` her sonucu `catMatch`'ten geçiriyor ve **tanımlı bir kategoriye
düşmeyen tip sessizce eleniyor.** 'canon' çipi eklenmeseydi 18.487 kayıt
indekse girip aramada hiç görünmeyecekti. Çip 'Kaynaklar' şemsiyesine
sokulmadı — o zaman *"havuzu büyütünce ne oluyor?"* sorusunun cevabı yine
gizli kalırdı.

### Uçtan uca doğrulama (canlı)

```
"Kadisiy"  →  49.353 kayıt arasında 7 canonical olay
tıkla: "Kâdisiye Savaşı — Rüstem'in öldürülmesi"
  →  #library?book=00001293&sec=58
  →  sec_0058.json çekildi
  →  açılan bölüm başlığı: يوم القادسية
```

Arama kutusundan kaynak metne kadar zincir çalışıyor.

## H51 süpürgesinden kaçan uydurma koordinat

`SearchBar`'ın bilim atlası dalı `lat: 30, lon: 45` sabitini **koşulsuz**
taşıyordu. Diğer dallardaki `lat || 30` kalıbı H51'de temizlendiği için bu
varyant grep'e takılmamıştı.

Ölçüldü: **182 bilim âlimi, kendi koordinatı olan 0** — hepsi tek noktaya
çakılıydı. `handleSelect` `#science`'e gittiği için tıklamada görünmüyordu,
ama **`handleRandom` o sahte noktaya uçuyordu** ve `onSelectEntity` onu
aşağıya "bilinen konum" diye geçiriyordu.

**Ders (üçüncü kez):** tek kaynağı onarmak yetmez, kopyaları aramak da
onarımın parçasıdır — ve arama, kalıbın **varyantlarını** da kapsamalı.
Depoda son örnekti; artık `lat: 30, lon: 45` yok ve kapı bunu kilitliyor.

## Doğrulama tuzağı (kod kusuru değil)

Doğrulama sırasında konsol `dynastyYearRange is not defined` gösterdi ve
`SearchBar` çöküyor sandım. Kaynakta import yerindeydi. Sebep: **geliştirme
sunucusu ölmüştü** ve tarayıcı, ölmeden önce alınmış bayat bir HMR modülünü
(`?t=…` sorgulu) servis ediyordu. `.claude/launch.json` statik bir
`python http.server`'ı işaret ediyordu; vite dev sunucusuna yöneltildi.

*Sunucunun canlı olduğunu doğrulamadan konsol hatasını kod kusuru saymak,
olmayan bir hatayı kovalamaktır.* Ağ kaydına bakmak (`sec_0058.json → 200`)
hem bunu hem de "bölüm 58 açılmıyor" yanılgımı çözdü — ekranda gördüğüm
"Bölüm 1" içindekiler listesinin ilk satırıydı, okuyucunun bulunduğu bölüm
değil.

**Üç kusur da mutasyonla doğrulandı. Test 259 → 270.**

---

## H56 sonrası kalan (üç dalga sonunda)

**Otomatik onarılabilir:**
- maqrizi katmanının **801/801** kaydına sabit `located_in = Kahire`; 53'ü
  50 km'den, 31'i 200 km'den, en uzağı **482 km** uzakta.
- Evliyâ katmanında v1'in `category_confidence` değeri düşürülüyor: 321 kayıt
  <0,5 güvenle sert `@type` alıyor, izi note'ta bile yok.
- Canonical olay katmanının tek kapısı hâlâ varsayılan kapalı bir toggle;
  `#map?canonical=1` gibi bir derin link yok. (Arama artık ayrı bir kapı
  açtığı için aciliyeti düştü.)

**Ali kapısı:**
- `institution_facets.json` üretildi ama **bağlanmadı** — join anahtarı için
  v1 görünüm dosyalarına canonical pid yazmak gerekiyor, bu v1 symlink
  sınırına dokunuyor.
- 9 tutarsız hanedan yılı (kuyrukta) · 4.774 önder adı · 2.238 çözülmemiş yer
  adı · `PHASE0_CLOSEOUT` event kapanışının statüsü.

**Faz-2:** ilişkisel katman (`participants_persons`, `preceded_by`,
`authority_xref`).

