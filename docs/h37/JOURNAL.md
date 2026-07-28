# H37 — Nedensellik onay kapısı: 170 bağ kullanılabilir hâle geldi

**Tarih:** 2026-07-28
**Durum:** kapandı (tarihçi kuyruğu Ali'ye devredildi)

## Sorun

H36 sonunda elimizde 170 kaynak-tanıklı nedensel bağ vardı — ama **hepsi
kullanılamaz durumdaydı**. Her kayıt `needs_human_review: true` taşıyordu ve
doktrin gereği onay olmadan hiçbir görünüme giremezdi. Yani katman teknik
olarak bitmişti, pratikte ölü veriydi: onaylamanın bir **yolu yoktu**.

Bu tur o yolu açtı. İkinci bir amaç daha taşıdı: H33'te kurduğum
"yeni görünüm = registry'ye 1 satır" oto-uyum altyapısının **gerçek bir
eklemeyle sınanması**.

## Yapılanlar

### 1. ⚖️ Nedensellik Onayı ekranı (`CausalReview.jsx`)

Her bağ tek tek gösterilir: Arapça asıl pasaj (kanıtın kendisi), bağlaç,
sebep/sonuç okuması, kaynak künyesi (kitap · § · sayfa · tarih) ve H36
denetimlerinin ürettiği kalite rozetleri — `link_type`, güven, *kanıt eksik*,
*sebep çıplak ad*, *sonuç gerçekleşmedi*, *kim iddia ediyor*.

✓ onayla · ✗ reddet · ⏭ atla. Kararlar `localStorage`da tutulur (oturum
kaybında iş gitmez), "Kararları indir" ile JSON'a çıkar.

Süzgeçler ölçüldü: **97 yüksek güven**, **34 işaretli (riskli)**, 170 toplam.
Tarihçi yüksek güvenle başlayıp işaretlileri ayrı bir oturuma bırakabilir.

**Ekran veriyi değiştirmez.** Kararlar ayrı dosyaya çıkar; veriye ancak
aşağıdaki script'le, bilinçli bir adımda döner.

### 2. Döngünün kapanan ucu (`apply_causal_decisions.py`)

İlk hâlinde indirilen karar dosyası **hiçbir yere gitmiyordu** — araç ölü uçta
bitiyordu. Onay kapısının anlamı, kararın veriye dönmesi:

```
ekran → indir → apply_causal_decisions.py → causal_links.json
      → make view-data → ekran neyin karara bağlandığını gösterir
```

Kurallar:
- Karar **yalnız dışarıdan** gelir; script kendi kararını vermez.
- **Reddedilen kayıt silinmez** — `verdict: reject` ile durur. Neyin neden
  elendiği, kabul edilenler kadar kayda değer bir bulgudur.
- `skip` karar değildir → kayıt kuyrukta kalır (`ertelenen` olarak sayılır).
- Eşleşmeyen anahtar sessiz geçilmez, sayılıp bildirilir.
- Mevcut kararın üzerine yazmak `--force` ister.

### 3. Elle kopyalama borcu kapatıldı (`build_causal_review.py`)

Sidecar → `web/public/view-data/` kopyası elle yapılmıştı; bu tam olarak H33'te
kapattığımız **sessiz bayatlama** sınıfı. Artık `make view-data` zincirinin bir
halkası ve bir guard test kaynakla arayüzün kayıt sayısını karşılaştırıyor.

### 4. Bütünlük kilidi (`test_causal_layer_integrity.py`, 7 test)

H36'nın iki denetimi, meşruiyetin iki ayrı yoldan kaybedilebildiğini ölçmüştü
(döngüsellik; sahte eşleşme, 308/415). Testler o kayıpları sessiz olmaktan
çıkarır:

- her bağın Arapça asıl alıntısı var,
- **bağlaç alıntının içinde geçer** (geçmiyorsa kanıt yok demektir),
- sebep/sonuç dolu,
- **onay kapısı delinmemiş** (çift yönlü: kendiliğinden onaylı görünen bağ da,
  karara bağlandığı hâlde kuyrukta kalan bağ da hata),
- karar değerleri geçerli, anahtarlar tekil,
- arayüz verisi kaynakla aynı sayıda.

## Oto-uyum sınavı — H33'ün vaadi tuttu mu?

**Tuttu.** Yeni sekme için yapılan dokunuş:

| Dosya | Değişiklik |
|---|---|
| `navRegistry.js` | **1 giriş** |
| `App.jsx` | 1 lazy import + 1 render dalı |

Bunun karşılığında sekme masaüstü "Analiz ▾" açılırında, mobil çekmecede, alt
sekme çubuğunda ve `VALID_TAB_IDS`te **kendiliğinden** belirdi — ölçüldü.
H27 denetiminin tarif ettiği eski maliyet ~8 dokunuştu ve biri unutulunca
sessiz kırılıyordu.

## Ölçümle yakalanan iki kusur

1. **İkon çakışması.** İlk hâlinde menüde `🔗 Nedensellik` (v1) ile
   `🔗 Nedensellik İncelemesi` yan yana düştü — ayırt edilemiyordu.
   ⚖️ ile ayrıldı; ⚖ = tarihçi kararı, 🔗 = katmanın kendisi.
2. **Menü sırası yorumla uyuşmuyordu.** Yorum "links'in hemen ardında" diyordu,
   ölçümde Âlimler araya giriyordu. Konum yoruma göre düzeltildi.

## Devredilen iş (Ali'nin kapısı — otomatik çözülmez)

- **97 yüksek güvenli bağ** — ilk oturum için doğal küme.
- **34 işaretli kayıt** — kanıt eksik / sebep çıplak ad / sonuç gerçekleşmemiş.
- **Kronikler arası tekrarlar (~%14)** — aynı olaya farklı kronikçilerin farklı
  sebep atfetmesi historiografik olarak **değerlidir**; silinmez, bağlanır.

## Doğrulama

- `make test` → 175 geçti, 2 atlandı, 3 xfail. Şema/projector/resolver temiz.
- Tarayıcı: ekran 170 kayıtla açılıyor, onay sayacı ve ilerleme çalışıyor,
  süzgeçler 97/34'e daralıyor, konsol hatasız.
- `apply_causal_decisions.py` uçtan uca sınandı (`--dry-run`): eşleşen işlendi,
  eşleşmeyen ve ertelenen ayrı ayrı raporlandı.
