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
