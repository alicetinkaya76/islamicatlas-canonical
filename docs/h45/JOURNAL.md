# H45 — Havuza giren ve çıkan yollar açıldı

**Tarih:** 2026-07-30
**Durum:** 3/4 madde kapandı (`b` rozeti ayrı tutuldu — gerekçe aşağıda)

H44 denetiminin kalan maddelerinden üçü. Her biri için önce ölçülmüş reçete
çıkarıldı (4 paralel ajan, 36 adım), sonra tek elden uygulandı.

## 1. EI-1 köprüsü — 972 ölü rozet canlandı

`person_bridge.json`'da **ei1 haritası yoktu**; `BRIDGE_SOURCES` ei1'i baştan
beri topluyordu ama `build_maps()` yalnız alam/dia haritası kuruyordu. Sonuç:
yalnız-EI1 kişiler ters indekse hiç girmiyor, havuzdaki `EI-1` rozeti
tıklanamıyordu.

Üç yönlü hâle getirildi. Ölçüm: `n_ei1=1144`, **yalnız-EI1 kişi 972**.
Doğrulandı (tarayıcı): rozet artık `<a href="#ei1/12">` — önce ölü `<span>`'dı.

**Yayın kapısı.** Mağazadaki 1.174 ei1 curie'sinin **30'u** yayınlanan katalogda
yok (27'si h22 hayalet defteri, yumuşak-silinmiş). Kapı olmasa bu 30 rozet
tıklanabilir görünüp boş karta götürürdü. Kapı sonrası: **1.144 anahtar,
katalog dışı 0**. Dürüst boşluk, sahte tıklanabilirlikten yeğdir.

Üretici hiçbir zincirde değildi (bayatlamaya açıktı) → `Makefile` ve
`start_local.sh`'a `build_lookup`'ın ardına eklendi; iki zincir `diff` ile aynı.

## 2. Kitap müellifi ↔ havuz — iki yön birden

17 manifestin 17'sinde `author.pid` vardı ve 17'sinin de havuzda karşılığı
bulunuyordu; buna karşılık **11 müellif tamamen çıkışsızdı** (bağı olan 6 kitap:
dia_slug 3 + alam_id 3).

- **İleri:** müellif kutusuna `#scholars?pid=` rozeti — 17/17 çalışır.
- **Geri:** havuz panelinde "Kütüphanede eseri" → `#library?book=<pidnum>`.
  Doğrulandı: Belâzürî → *Fütûhu'l-Büldân*.
- DİA bağı `?search=<ad>` yerine `#dia/<slug>`'a yükseltildi (ad araması
  çoklu/yanlış sonuç verebiliyordu).

Rozet 22.824 kişinin **17'sinde (%0,07)** çıkar. Bu bir "özellik" olarak
duyurulmamalı; külliyat büyüdükçe kendiliğinden büyüyen bir kapıdır.

### Yapılmayan: ham translit adlar
9 müellif adı ham OpenITI transliti (`Tabari`, `Maqrizi`, `IbnHisham`…).
Denetimin "havuzun `ad_tr`'siyle değiştir" önerisi **ölçüldü ve kapalı çıktı**:
havuzun `ad_tr`'si 16/17'de manifestle birebir aynı, çünkü ikisi de aynı
canonical alandan (`labels.prefLabel.tr`) geliyor. `Tabari → Taberî` yapmak
**kaynağı olmayan bir ad üretmektir**. Bu 9 kayıt `needs_human_review`; ayrı bir
veri-onarım maddesi (kaynak: DİA/Aʿlâm eşleştirmesi ya da tarihçi kararı).

## 3. Kaynak kartlarından havuza dönüş

Havuza dışarıdan pid ile giren yalnız iki rota vardı (şerit 231 kişi, isnâd ağı
3.393 düğüm). Kullanıcı el-Aʿlâm/DİA/EI-1 maddesine gidiyor ve **orada
kalıyordu** — aynı kişinin öbür izlerine dönemiyordu.

Ortak `PoolLink` bileşeni üç karta eklendi. Ölçüm — pid `view-data` sürümlerinde
zaten var ve havuzda %100 karşılık buluyor:

| kaynak | kayıt | pid taşıyan |
|---|---|---|
| el-Aʿlâm | 13.844 | **12.476** |
| DİA | 8.491 | **7.346** |
| EI-1 | 7.538 | **1.144** |

pid yoksa düğme **hiç çıkmaz**. Bileşen hook kullanmaz — erken return'lü
kartlarda güvenli (H42'de koşullu-hook hatası bu depoda bir kez daha ölçülmüştü).

## Guard testleri (9) — mutasyonla sınandı

Bir guard **ilk sürümünde kusuru kaçırdı**: dosyada `"BR.ei1"` arıyordu ve
`bridgeFromEi1` yardımcısı yüzünden ters indeks silinse bile yeşil yanıyordu.
Guard, ters indeksin **gövdesine** bakacak şekilde sıkılaştırıldı; mutasyon
tekrarında kırmızı yandı. *(Yanlış ölçen guard, guard olmamaktan beterdir —
H38'de öğrenilen kural burada yine işe yaradı.)*

## Ayrı tutulan: `b` (Kitap/diğer) rozeti

Denetimin 2. maddesi bilinçli olarak bu commit'e alınmadı. Gerekçe reçetenin
ölçtüğü bir tuzak: **263 kişinin dia-chunks slug'ı BAŞKA bir pid'e bağlı** ve
'b' tek rozetli 26 dia-chunks kişisinin 19'u tam olarak bu gruptan — slug'a
bakıp link üretmek bu 19 kişide **kesinlikle yanlış DİA maddesini** açardı.
Ayrıca 3.105 ölü rozetin **2.294'ü ölü kalacak** (2.247 openiti-only + 47
alatli-only): eserleri mağazada var ama sitede yalnız 17 kitap okunabiliyor.
Kazanç ~811 kişiyle sınırlı, risk yüksek → pid eşitlik kontrolüyle ayrı bir
turda yapılmalı.

## Doğrulama
- `make test` → **191 geçti**, 2 atlandı, 3 xfail (+9 yeni guard).
- Tarayıcı: EI-1 rozeti canlı link; Belâzürî panelinde kitap rozeti; havuz
  paneli doğum yeri/uzmanlık/talebe gösteriyor; konsol temiz.
