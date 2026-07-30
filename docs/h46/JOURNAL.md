# H46 — "Kitap/diğer" rozeti açıldı (ve bir kısmı bilerek kapalı bırakıldı)

**Tarih:** 2026-07-30
**Durum:** kapandı — H44 denetiminin son maddesi

`b` (Kitap/diğer) rozeti TEK bir kovaydı ve `href` **sabit `null`** döndürüyordu:
3.105 kişinin tek rozeti buydu ve hiçbiri tıklanamıyordu. Oysa ham curie öneki
hangi kaynağın izi olduğunu zaten biliyor.

## Alt-kodlar ve gerçek çözülme

| önek | kişi | alt-kod | hedef | çözülen |
|---|---|---|---|---|
| dia-chunks + v8 | 5.546 | `bc` | `#dia/<slug>` | **5.252** |
| bosworth-nid | 828 | `by` | `#dynasty/<id>` | **828** |
| openiti | 2.262 | `bo` | — | 0 |
| alatli | 227 | `ba` | — | 0 |
| (kalan) | 0 | `b` | — | 0 |

**6.080 kişi** ilk kez tıklanabilir bir hedefe sahip. `b` **tek** rozetlilerde
kazanç 763 (Bosworth); 2.303'ü (openiti 2.256 + alatli 47) hedefsiz kaldı.

## En büyük tuzak: 300 reddedilen hedef

dia-chunks slug'ının **300'ü BAŞKA bir pid'e bağlıydı**. Slug'a bakıp link
üretmek o kişilerde **kesinlikle yanlış DİA maddesini** açardı. Üretici hedefi
yalnız `slug2pid[loc] == pid` eşitliği sağlanınca yazıyor; reddedilenler
sayılıp raporlanıyor (`bc_reddedildi: 300`).

Guard testi mutasyonla sınandı: eşitlik kontrolü `if loc in slug2pid`'e
düşürülünce test kırmızı yandı.

## Hedefsiz kodlar — dürüst boşluk

`bo` ve `ba` için sitede açılabilir sayfa **yok**: OpenITI eserleri mağazada
kayıtlı ama okunabilir külliyat 17 kitap; Alatlı kişileri şeritte çizili ama
şerit kişiye derin link kabul etmiyor. Sahte hedef üretilmedi. Rozet artık
**neden** açılmadığını söylüyor:

> OpenITI külliyatı · sayfa yok
> *(başlık: "Eseri merkezî defterde kayıtlı, ama bu kitap sitede henüz
> okunabilir değil.")*

`by` etiketi de dürüst: **"Bosworth hanedanı"** — hedef hanedanı haritada açar,
kişinin kendi kaydını değil. "Kişi sayfası" izlenimi verilmedi.

## Kısmi uygulama yasağı

`meta.kaynak_basina` anahtar kümesi değişti (`b` → `bc/by/bo/ba/b`) ve filtre
çiplerini o besliyor. Üretici ile bileşen ayrı commit'lerde gitseydi çipler ya
sayısız görünür ya da hiçbir kişiyi süzemezdi. İkisi aynı commit'te; bir guard
testi (`test_havuz_kod_tablosu_ureticiyle_ayni`) `CODE_ORDER` ile `SRC_ORDER`
kümelerini karşılaştırarak ayrışmayı engelliyor.

## Doğrulama
- `make test` → **194 geçti**, 2 atlandı, 3 xfail (+3 guard, biri mutasyonla).
- Tarayıcı: Abū Bakr → `Bosworth hanedanı →` (`#dynasty/1`); IbnCasakir →
  `OpenITI külliyatı · sayfa yok`; çipler `DİA (madde parçası) 5.546 ·
  Bosworth hanedanı 828 · OpenITI külliyatı 2.262`.

## H44 denetimi kapandı
Dört maddenin dördü de bitti (H45'te üçü, burada dördüncü). Geriye **kimlik
tekilliği** kaldı: "22.824" bir kişi sayısı değil kayıt sayısı; denetim tekil
tavanı ≤20.956 ölçtü. Bu otomatik çözülmez — Ali'nin dup-merge oturumuna bağlı.
