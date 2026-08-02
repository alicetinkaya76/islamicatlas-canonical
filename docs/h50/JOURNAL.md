# H50 — Kimlik birleştirmesi tamamlandı: 22.824 → 21.460

**Tarih:** 2026-07-31
**Durum:** kapandı

Kalan **796 küme** de yargılandı (48 ajan, iki paralel tur). Toplam **1.460 karar**;
birleştirilen **1.245 küme / 1.364 kayıt**. Havuz **22.824 → 21.460**.

## Tam tarama, bir varsayımı çürüttü

İlk iki turda "kesin" katman 150 kümede **sıfır** yanlış vermişti ve ben
*"kesin katmanı tam taramak düşük getirili"* demiştim. Tam tarama (945 küme)
bunu çürüttü:

| güven | n | aynı kişi | **ayrı kişi** | belirsiz |
|---|---|---|---|---|
| kesin | 945 | 924 (%97) | **6 (%0,6)** | 15 |
| olası | 485 | 318 (%65) | 73 (%15) | 94 |
| zayıf | 30 | 3 (%10) | 15 (%50) | 12 |

**Örneklem 0 gösterdi diye popülasyon 0 değildir.** H10'da öğrenilen
"popülasyon ölçümü nihai hakemdir" kuralının bir örneği daha. O 6 küme
birleştirilseydi altı ayrı tarihsel şahıs yanlışlıkla tek kayda inecekti.

Kalibrasyon guard'ı buna göre düzeltildi: artık `hayir == 0` değil, **oran
< %2** bekliyor. Testin eski hâli bir varsayımı kilitliyordu; şimdi ölçümü
kilitliyor.

## Yakalanan hata sınıfları (bu turda eklenenler)

Önceki turlardaki baba-oğul / efendi-âzatlı / kabile-nisbesi sınıflarına
eklenenler:

- **Kolektif künye ↔ tekil şahıs:** `Benû Mûsâ` (Mûsâ b. Şâkir'in üç oğlunun
  ortak adı) ile `İbn Mûsâ` birleştirilmedi — bir kolektifi tek kişiye indirmek
  ayrı bir hata sınıfı.
- **Aynı nisbe, farklı şehir:** `en-Nûrî` kaydında A'lâm koordinatı Tunus'u,
  DİA kaydı Kahire'yi gösteriyordu → belirsiz.

## İki gerçek kusur — ikisi de bu turda çıktı ve kapatıldı

### 1. Ledger üzerine yazıldı, 468 kayıt kayboldu
İkinci tur ledger'ı **ezdi**; ilk turun 468 birleştirmesi kaydı gitti ve
`--restore` onları geri alamaz hâle geldi. **Geri alma yolu, kaydın
bütünlüğüne bağlıdır** — bunu ancak ikinci turda fark ettim.

Onarım: ledger artık **kümülatif**; kayıp 468 küme canonical kayıtlardaki
`[h49_001]` işaretinden geri türetildi (ledger 1.245 küme / 1.364 kayıt).

### 2. Yönlendirme ledger'a bağlıydı
Yönlendirme haritasını ledger'dan üretiyordum. Ledger ezilince **544 bağ
sessizce koparadı**. Artık **canonical kayıtların kendisinden** türetiliyor
(`deprecated_in_favor_of` — tek gerçek kaynak); ledger yalnız denetim ve geri
alma için.

## Sonuç ölçümleri

| | |
|---|---|
| havuz kaydı | **21.460** (22.824'ten) |
| yönlendirme | 1.501 · hedefi havuzda olmayan **0** |
| kitap müellifi kopuk bağ | **0/17** |
| isnâd ucu havuz dışı | **0** |
| gösterilen küme | 15 (kesin) + 94 (olası); 187 zayıf gizli |

`make test` → **208 geçti**, 2 atlandı, 3 xfail.

## Ali'ye kalan
- **109 "belirsiz"** küme — iki mercek çelişti ya da kanıt yetmedi. Tarihçi
  bakışı gerekir; otomatik çözülmez.
- **96 "ayrı kişi"** kararı — bunlar veri hatası değil, doğru ayrımlar; kümeden
  çıkarıldılar ve bir daha önerilmeyecekler.
- **187 zayıf küme** — arayüzde gizli, aday listesi olarak duruyor.
