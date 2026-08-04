# H55 — Eser ekseni: 9.404 eser kişiye bağlandı, üretim derlemesi onarıldı

**Tarih:** 2026-08-03/04
**Durum:** kapandı (kalan maddeler aşağıda)
**Commit:** `838394ce`, `4b29cd59`

Kişi (H44–H50) ve yer (H51–H54) eksenlerinden sonra sıra hiç denetlenmemiş
**eser (`work`)** namespace'ine geldi: 9.404 kayıt, Kütüphane'ye bağlı.

---

## Manşet bulgu: havuz büyüyordu, eser ekseninde karşılığı sıfırdı

Mağazada **9.404 eser** var. Sitede okunabilen **17**. Kalan 9.387'nin
hiçbir sayfası yoktu.

Ulema Havuzu'nda **2.246 kişi** "OpenITI külliyatı" rozeti taşıyordu ve
rozetin `href`'i **sabit `null`**'dı. Kodda kendi yazdığım yorum duruyordu:

> `/* OpenITI külliyatı: eser mağazada var ama sitede yalnız 17 kitap okunabilir. */`

Yani Ali'nin tekrar tekrar sorduğu **"havuzu artırınca ne elde ediyoruz?"**
sorusunun bu eksendeki cevabı dürüstçe **"hiçbir şey"**di.

**Yapılan:** müellif → eser köprüsü (`build_author_works.py`). Kişi panelinde
"Merkezî defterdeki eserleri (N)" bölümü: Arapça başlık, translit başlık, konu,
tarih sınırı, OpenITI bağı ve **okunabilirlik durumu**. 3.652 müellif,
9.385 bağ.

---

## Bulgu 1 — birleştirme eser katmanına hiç uğramamış

H49/H50 kimlik birleştirmesi kişileri yumuşak-sildi. Eser kayıtlarının
`authors` alanına **hiç dokunulmadı**.

Ölçüldü: **9.385 bağın 1.177'si** yumuşak-silinmiş pid'e gidiyor. Canonical'da
bağ *duruyor* — bu yüzden veriye bakan biri kusuru göremez; ama havuzda
karşılığı yok, eser "müellifsiz" görünürdü.

Çözüm, H49'da isnâd uçlarında kullanılan desenin aynısı: **canonical'a
dokunma, yayın katmanında yönlendir.** Zincir takibi var (A→B→C) ve döngü
koruması var. Çözülemeyen bağ: **0**.

Yan kazanç ölçüldü: İbn Teymiyye'nin 124 eseri, translit adlı bir kopya kayıt
(`person-00008671`) yerine artık DİA adlı asıl kayda (`4054`) düşüyor.

## Bulgu 2 — rozetin kaynağı yanlıştı

`bo` rozeti `source_curie`'deki `openiti:` önekinden türüyordu — yani **kişinin
mint kaynağından**. Oysa DİA'dan mint edilmiş birinin de OpenITI'de eseri
olabilir. Câhiz'in **58**, Bîrûnî'nin **21**, Harezmî'nin 3 eseri vardı ve
rozetleri yoktu.

Rozet artık **eserin varlığından** türüyor: **2.246 → 3.553**. Eksik 1.307,
fazla **0** — yani eski rozet gerçeğin öz alt kümesiydi; ekleme yapıldı,
kimseden rozet alınmadı.

## Bulgu 3 — `composition_temporal` telif tarihi DEĞİL

Alan adı "telif zamanı" diyor. Gerçekte: 9.385 kaydın **9.158'inde**
`start_ah`, OpenITI URI'sindeki **müellifin ölüm yılı** ile birebir aynı ve
**9.159'u** `approximation: "before"` taşıyor.

Yani alanın anlamı "müellif ölmeden önce yazıldı" sınırıdır. Çıplak yıl
basmak — "telif: 911" — **olmayan bir kesinlik üretirdi**; deponun en sert
kuralının ihlali. Arayüz "**911 (H) öncesi**" yazıyor ve sözleşme testle
kilitli (`y` varsa `yk` de olmalı).

## Bulgu 4 — ham Python sözlüğü panele sızıyordu

Bilim katmanı adaptörü eser bilgisini nota **repr** olarak basmış:

```
Key works: {'title': {'en': 'Al-Kitāb al-Mukhtaṣar…', 'tr': "el-Kitâbü'l-…"}, 'year': 820, …}
```

**133 kişide** bu ham metin ekranda görünüyordu (Hârizmî, Câhiz, İbn Heysem…).
Düşürüldü — ve içindeki bilgi kaybolmadı: eserler artık köprüde düzgün
listeleniyor. 133 → **0**.

---

## Bulgu 5 (en ağırı) — `vite build` H51'den beri ÇÖKÜYORDU

Kendi regresyonum. H51'de "tek otorite normalize" onarımını yaparken yedi
dosyaya `from '../../shared/bookkit/normalize'` yazmışım. Doğrusu
`../shared/...`; `../../` `web/src/shared/` demek ve öyle bir dizin yok.

**Üretim derlemesi tamamen kırıktı** ve H51'den H55'e kadar fark edilmedi.

Neden fark edilmedi? Çünkü `make test` yalnız Python tarafını sınıyordu —
**hiçbir kapı ön yüzü derlemiyordu.** Geliştirme sunucusu da sessiz kaldı,
zira o oturumlarda kırık modülleri yükleyen görünümlere girilmemişti.

Yedi import onarıldı; `vite build` yeşil. Kalıcı kapı kondu: her göreli import
statik olarak dosya sistemine karşı çözülüyor (`vite build` koşulmuyor —
milisaniyeler sürüyor). **Mutasyonla doğrulandı**: kusur geri konunca 3 test
kızardı.

Kapı ilk koşusunda **yanlış alarm** verdi: `evliya/index.js`'in JSDoc'undaki
örnek `import … from './components/evliya'` satırı gerçek import sanıldı.
*Yanlış alarm veren kapı, görmezden gelinen kapıdır* — yorumlar taramadan
çıkarıldı.

**Ders (H51'in kendi dersinin devamı):** "tek kaynağa taşıdım" demek yetmez;
**taşımanın kendisi de sınanmalıdır.**

---

## Bulgu 6 — üreticiyi yazdım, zincire bağlamayı unuttum

`build_author_works.py` yazıldı, çıktısı üretildi, arayüz bağlandı — ama
`make build-view-data` zincirine eklenmedi. `view-data/` gitignore'da olduğu
için **temiz bir kopyada dosya hiç oluşmayacaktı** ve bölüm sessizce boş
kalacaktı.

İkinci kapı: her `build_*.py` ya zincirde olacak ya da `ZINCIR_DISI`
listesinde **gerekçesiyle** bulunacak. Amaç zorlamak değil, **kararı kayda
geçirmek** — "unutuldu" ile "bilerek dışarıda" ayrılsın. Zincir dışı beşi
gerekçelendirildi.

---

## Yan onarımlar

- **LibraryView'daki son kopya normalize silindi.** Kod noktası olarak doğruydu
  ama sınıfı **ham karakterle** yazılmıştı (kaynakta bidi ile yeniden
  sıralanan, gözle denetlenemeyen kalıp) ve bookkit'ten geri kapsamlıydı
  (U+0610–061A, tatvîl, TR/DMG eşlemeleri yok). Tek otoriteye bağlandı.
- **`openitiRepoUrl` bookkit'e terfi etti** — ikinci tüketici kuralı (H17
  KARAR-2) gereği. Kendi yazdığım basitleştirilmiş URL yanlıştı; asıl
  fonksiyon 25 yıllık kova hesabını yapıyor.

## Doğrulama (tarayıcı, canlı)

- Süyûtî: **138 eser**, Arapça başlıklar, "911 (H) öncesi", "+130 eser daha"
- Belâzürî: "📖 sitede oku" → `#library?book=00001293` → **91 bölüm** açılıyor
- Arapça bölüm araması (`فتوح`): **8/91** — bookkit normalize'a geçiş sağlam
- Hârizmî: ham sözlük gitti, yerine gerçek not
- Konsol hatası: **yok**

**Test 216 → 234.**

---

## Kalan / açık

- **`genre` alanı 9.404 kayıtta boş.** Konu bilgisi `subjects`'te (39 tekil
  değer) duruyor ve kullanılan o. Şemadaki ölü alan — ADR-016'nın gerekçe
  kalıbıyla değerlendirilmeli, tek başına silme kararı verilmedi.
- **İlişkisel alanların tamamı boş**: `commentary_on`, `translation_of`,
  `abridgement_of`, `cites_works`, `mentions_persons`, `mentions_places`,
  `extant_manuscripts` → hepsi **0**. Şerh/muhtasar ağı — bir İslam eser
  külliyatının en anlamlı yapısı — kurulmamış. Faz-2 işi; **tahminle
  doldurulmaz.**
- **842 eserin Arapça başlığı yok** (yalnız translit). Ad uydurulmaz.
- **19 eser müellifsiz.**
- Zincir dışı beş üreticinin bayatlama riski gerekçelendirildi ama
  **çözülmedi**; source_counts depoda izlenen dosyaya yazdığı için zincire
  alınamıyor.
